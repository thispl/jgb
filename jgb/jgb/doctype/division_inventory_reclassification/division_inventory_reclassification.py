# Copyright (c) 2026, JGB and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowtime
import erpnext
from erpnext.accounts.general_ledger import make_gl_entries

JGB_COMPANY = "Joint Global Business Co LLC"
CUTOFF_DATE_STR = "2026-01-01"
CONTROL_ACCOUNT = "1211 - Inventory - General - JGB"


class DivisionInventoryReclassification(Document):
	def validate(self):
		self.validate_company()
		self.validate_accounts()

	def validate_company(self):
		if not self.company:
			self.company = frappe.db.get_default("company")
		if self.company != JGB_COMPANY:
			throw(_("This doctype is only for {0}.").format(JGB_COMPANY))

	def validate_accounts(self):
		if not self.get("division_reclass_items"):
			throw(_("Please add at least one row in the Division Reclass Items table."))
		for row in self.get("division_reclass_items"):
			if not row.inventory_account:
				throw(_("Inventory Account is required in row {0}.").format(row.idx))
			acc_details = frappe.db.get_value(
				"Account", row.inventory_account, ["company", "is_group", "disabled"], as_dict=True
			)
			if not acc_details:
				throw(_("Account {0} does not exist.").format(row.inventory_account))
			if acc_details.company != self.company:
				throw(_("Account {0} does not belong to Company {1}.").format(row.inventory_account, self.company))
			if acc_details.is_group:
				throw(_("Account {0} cannot be a Group Account.").format(row.inventory_account))
			if acc_details.disabled:
				throw(_("Account {0} is disabled.").format(row.inventory_account))

	def before_submit(self):
		self.status = "Submitted"

	def on_submit(self):
		self.make_gl_entries(cancel=False)

	def before_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry",)
		self.status = "Cancelled"

	def on_cancel(self):
		self.make_gl_entries(cancel=True)

	def make_gl_entries(self, cancel=False):
		"""Dr/Cr each division's inventory account against the control account (1211).
		Follows the same pattern as the DirectExpenseEntry doctype's GL entry logic.
		"""
		gl_entries = []
		company_currency = erpnext.get_company_currency(self.company)
		control_currency = frappe.db.get_value("Account", CONTROL_ACCOUNT, "account_currency") or company_currency
		company_cost_center = frappe.db.get_value("Company", self.company, "cost_center")

		for row in self.get("division_reclass_items"):
			amount = flt(row.amount)
			if amount == 0:
				continue

			account_currency = frappe.db.get_value("Account", row.inventory_account, "account_currency") or company_currency
			cost_center = _get_division_cost_center(row.division, self.company) or company_cost_center

			is_stock_in = amount > 0
			row_remarks = self.remarks or _("Division Inventory Reclassification")

			# Division account entry: Dr if stock IN, Cr if stock OUT
			gl_entries.append(frappe._dict({
				"company": self.company,
				"posting_date": self.posting_date,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"remarks": row_remarks,
				"account": row.inventory_account,
				"party_type": None,
				"party": None,
				"against": CONTROL_ACCOUNT,
				"debit": amount if is_stock_in else 0.0,
				"debit_in_account_currency": amount if is_stock_in else 0.0,
				"credit": 0.0 if is_stock_in else abs(amount),
				"credit_in_account_currency": 0.0 if is_stock_in else abs(amount),
				"account_currency": account_currency,
				"cost_center": cost_center,
				"project": None,
				"is_opening": "No",
			}))

			# Control account entry: Cr if stock IN, Dr if stock OUT
			gl_entries.append(frappe._dict({
				"company": self.company,
				"posting_date": self.posting_date,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"remarks": row_remarks,
				"account": CONTROL_ACCOUNT,
				"party_type": None,
				"party": None,
				"against": row.inventory_account,
				"debit": 0.0 if is_stock_in else abs(amount),
				"debit_in_account_currency": 0.0 if is_stock_in else abs(amount),
				"credit": amount if is_stock_in else 0.0,
				"credit_in_account_currency": amount if is_stock_in else 0.0,
				"account_currency": control_currency,
				"cost_center": company_cost_center,
				"project": None,
				"is_opening": "No",
			}))

		if gl_entries:
			make_gl_entries(gl_entries, cancel=cancel)


def _get_division_cost_center(division, company):
	"""Return the division's cost center from Division Account Details, if that field
	exists on this site (it's not present on every environment — e.g. missing on the
	dev site as of 2026-08-12 despite existing on production). Falls back to None,
	letting the caller apply the company default cost center instead."""
	if not frappe.db.has_column("Division Account Details", "cost_center"):
		return None
	return frappe.db.get_value("Division Account Details", {"parent": division, "company": company}, "cost_center")


def _get_division_and_account(item_code, warehouse=None):
	"""Resolve (division, inventory_account) for an item via its Item Group's
	custom_group_name -> Division Account Details.inventory_account mapping."""
	item_group = frappe.db.get_value("Item", item_code, "item_group")
	if not item_group:
		return None, None
	division = frappe.db.get_value("Item Group", item_group, "custom_group_name")
	if not division:
		return None, None
	inventory_account = frappe.db.get_value(
		"Division Account Details", {"parent": division, "company": JGB_COMPANY}, "inventory_account"
	)
	if not inventory_account:
		return division, None
	return division, inventory_account


def get_division_totals_for_voucher(voucher_type, voucher_no):
	"""Read stock_value_difference from Stock Ledger Entry (NOT item child tables) for
	the given voucher, grouped by division. Returns a dict:
	{division: {"inventory_account": ..., "amount": float}}
	"""
	sle_rows = frappe.db.sql(
		"""
		SELECT item_code, warehouse, stock_value_difference
		FROM `tabStock Ledger Entry`
		WHERE voucher_type = %(voucher_type)s
		  AND voucher_no = %(voucher_no)s
		  AND is_cancelled = 0
		  AND stock_value_difference != 0
		""",
		{"voucher_type": voucher_type, "voucher_no": voucher_no},
		as_dict=True,
	)

	division_totals = {}
	for sle in sle_rows:
		division, inventory_account = _get_division_and_account(sle.item_code, sle.warehouse)
		if not division:
			frappe.logger().warning(
				f"[Division Reclass] Item {sle.item_code} has no division mapping — "
				f"skipping in reclass for {voucher_type} {voucher_no}"
			)
			continue
		if not inventory_account:
			frappe.logger().warning(
				f"[Division Reclass] Division {division} has no inventory_account for "
				f"{JGB_COMPANY} — skipping item {sle.item_code} in {voucher_type} {voucher_no}"
			)
			continue

		if division not in division_totals:
			division_totals[division] = {"inventory_account": inventory_account, "amount": 0.0}
		division_totals[division]["amount"] += flt(sle.stock_value_difference)

	# Drop divisions that net to ~zero
	return {d: v for d, v in division_totals.items() if abs(v["amount"]) > 0.01}


def get_non_sle_gl_totals_for_voucher(voucher_type, voucher_no):
	"""Fallback for non-stock items (e.g. fixed assets) that post GL entries to
	the control account (1211) but generate no Stock Ledger Entries.

	Reads GL entries to 1211 for the voucher and determines the target account:
	- For Purchase Receipts with fixed assets: uses the asset account from the
	  2221 (Asset Received But Not Billed) GL entry's `against` field.
	- For other non-stock items: uses the item's division inventory account via
	  Item Group → Division Account Details mapping.

	Returns a dict: {target_account: {"division": str, "inventory_account": str, "amount": float}}
	"""
	# Get GL entries to 1211 for this voucher
	gl_1211_rows = frappe.db.sql(
		"""
		SELECT account, debit, credit, against, remarks
		FROM `tabGL Entry`
		WHERE voucher_type = %(voucher_type)s
		  AND voucher_no = %(voucher_no)s
		  AND account = %(control_account)s
		  AND is_cancelled = 0
		""",
		{"voucher_type": voucher_type, "voucher_no": voucher_no, "control_account": CONTROL_ACCOUNT},
		as_dict=True,
	)
	if not gl_1211_rows:
		return {}

	# For Purchase Receipts, the 2221 GL entry's `against` field holds the
	# final asset account (e.g. 1604, 1606, 1609).  We group by that target
	# account and use the 1211 GL net (debit - credit) as the reclass amount.
	# The 1211 entry is a Dr for asset PRs (stock IN), so the amount is
	# positive → make_gl_entries will Dr asset / Cr 1211 (correct).
	asset_against = {}
	if voucher_type == "Purchase Receipt":
		against_rows = frappe.db.sql(
			"""
			SELECT against, SUM(debit - credit) as net_2221
			FROM `tabGL Entry`
			WHERE voucher_type = %(voucher_type)s
			  AND voucher_no = %(voucher_no)s
			  AND account LIKE '2221%%'
			  AND is_cancelled = 0
			GROUP BY against
			""",
			{"voucher_type": voucher_type, "voucher_no": voucher_no},
			as_dict=True,
		)
		# The 2221 entry is a credit (Cr 2221), so net_2221 is negative.
		# The 1211 entry is a debit (Dr 1211) of the same magnitude, so the
		# reclass amount should be the positive value (Dr asset / Cr 1211).
		for r in against_rows:
			if r.against and r.against != CONTROL_ACCOUNT:
				asset_against[r.against] = abs(flt(r.net_2221))

	totals = {}
	if asset_against:
		# Asset PRs: reclassify 1211 → asset account
		for acct, amt in asset_against.items():
			if abs(amt) > 0.01:
				totals[acct] = {
					"division": _("Fixed Assets"),
					"inventory_account": acct,
					"amount": amt,
				}
	else:
		# Non-stock, non-asset items: try division mapping via item group
		item_doctype = {
			"Purchase Receipt": "Purchase Receipt Item",
			"Purchase Invoice": "Purchase Invoice Item",
			"Delivery Note": "Delivery Note Item",
			"Sales Invoice": "Sales Invoice Item",
		}.get(voucher_type)

		if item_doctype:
			items = frappe.db.sql(
				"""SELECT item_code, amount
				   FROM `tab%s` WHERE parent = %%s""" % item_doctype,
				(voucher_no,), as_dict=True,
			)
			for it in items:
				division, inventory_account = _get_division_and_account(it.item_code)
				if not division or not inventory_account:
					continue
				key = inventory_account
				if key not in totals:
					totals[key] = {
						"division": division,
						"inventory_account": inventory_account,
						"amount": 0.0,
					}
				totals[key]["amount"] += flt(it.amount)

	# Drop entries that net to ~zero
	return {k: v for k, v in totals.items() if abs(v["amount"]) > 0.01}


def create_division_reclass(doc, method=None):
	"""Create a Division Inventory Reclassification from a stock transaction on submit.
	Wired via hooks.py on_submit for Purchase Receipt / Purchase Invoice / Delivery Note /
	Sales Invoice / Stock Entry / Stock Reconciliation.
	"""
	if doc.company != JGB_COMPANY:
		return

	if getdate(doc.posting_date) < getdate(CUTOFF_DATE_STR):
		frappe.logger().info(
			f"[Division Reclass] Skipping historical transaction {doc.doctype} {doc.name} "
			f"(posting date {doc.posting_date})"
		)
		return

	if doc.doctype in ("Purchase Invoice", "Sales Invoice") and not doc.get("update_stock"):
		return

	division_totals = get_division_totals_for_voucher(doc.doctype, doc.name)

	# Fallback: if no SLE-based totals (e.g. non-stock items / fixed assets),
	# check for GL entries to 1211 that need reclassification
	if not division_totals:
		division_totals = get_non_sle_gl_totals_for_voucher(doc.doctype, doc.name)

	if not division_totals:
		return

	existing = frappe.db.exists(
		"Division Inventory Reclassification",
		{"reference_doctype": doc.doctype, "reference_name": doc.name, "docstatus": 1},
	)
	if existing:
		frappe.logger().info(
			f"[Division Reclass] {existing} already exists for {doc.doctype} {doc.name} — skipping"
		)
		return

	reclass_doc = frappe.new_doc("Division Inventory Reclassification")
	reclass_doc.posting_date = doc.posting_date
	reclass_doc.posting_time = doc.get("posting_time") or nowtime()
	reclass_doc.reference_doctype = doc.doctype
	reclass_doc.reference_name = doc.name
	reclass_doc.company = doc.company
	reclass_doc.remarks = _("Auto-generated from {0} {1}").format(doc.doctype, doc.name)

	for division, data in division_totals.items():
		reclass_doc.append("division_reclass_items", {
			"division": division,
			"inventory_account": data["inventory_account"],
			"amount": data["amount"],
		})
		# Note: each row here is one-sided (e.g. all "stock in" for a Purchase Receipt).
		# The offsetting leg against the control account (1211) is derived programmatically
		# in make_gl_entries() for every row — it is not stored as a table row, so rows are
		# not expected to net to zero among themselves.

	reclass_doc.insert(ignore_permissions=True)
	reclass_doc.submit()


def cancel_division_reclass(doc, method=None):
	"""Cancel the linked Division Inventory Reclassification when the source
	stock transaction is cancelled. Wired via hooks.py on_cancel."""
	if doc.company != JGB_COMPANY:
		return

	if getdate(doc.posting_date) < getdate(CUTOFF_DATE_STR):
		return

	reclass_name = frappe.db.get_value(
		"Division Inventory Reclassification",
		{"reference_doctype": doc.doctype, "reference_name": doc.name, "docstatus": 1},
	)
	if reclass_name:
		reclass_doc = frappe.get_doc("Division Inventory Reclassification", reclass_name)
		reclass_doc.cancel()


# ---------------------------------------------------------------------------
# SLE Reposting Handler
# ---------------------------------------------------------------------------
# When ERPNext reposts Stock Ledger Entries (via Landed Cost Voucher, Stock
# Reconciliation, document amendment, Repost Item Valuation, etc.), the
# stock_value_difference on existing SLEs changes.  Any Division Inventory
# Reclassification that was created from those SLEs is now stale — it still
# holds the old amount.
#
# All reposting scenarios go through the repost() function in
# repost_item_valuation.py, which we monkey-patch in jgb/__init__.py.  After
# each repost job completes, we cancel the old reclass and create a fresh one
# using the current SLE values.  This covers LCV, Stock Reconciliation,
# amendments, manual reposts, and any other trigger.

RECLASS_VOUCHER_TYPES = (
	"Purchase Receipt",
	"Purchase Invoice",
	"Delivery Note",
	"Sales Invoice",
	"Stock Entry",
	"Stock Reconciliation",
)


def _recreate_reclass_for_voucher(voucher_type, voucher_no):
	"""Cancel the existing reclass for a voucher and create a fresh one using
	current SLE values.  Called after SLE reposting."""
	if voucher_type not in RECLASS_VOUCHER_TYPES:
		return

	# Skip if the voucher is cancelled
	if frappe.db.get_value(voucher_type, voucher_no, "docstatus") != 1:
		return

	# Skip pre-cutoff vouchers
	posting_date = frappe.db.get_value(voucher_type, voucher_no, "posting_date")
	if not posting_date or getdate(posting_date) < getdate(CUTOFF_DATE_STR):
		return

	# Skip non-JGB vouchers
	company = frappe.db.get_value(voucher_type, voucher_no, "company")
	if company != JGB_COMPANY:
		return

	# Cancel existing reclass
	reclass_name = frappe.db.get_value(
		"Division Inventory Reclassification",
		{"reference_doctype": voucher_type, "reference_name": voucher_no, "docstatus": 1},
	)
	if reclass_name:
		try:
			reclass_doc = frappe.get_doc("Division Inventory Reclassification", reclass_name)
			reclass_doc.cancel()
			frappe.logger().info(
				f"[Division Reclass] Cancelled stale reclass {reclass_name} for "
				f"{voucher_type} {voucher_no} after SLE repost"
			)
		except Exception:
			frappe.log_error(
				title=f"[Division Reclass] Failed to cancel stale reclass {reclass_name}",
				message=frappe.get_traceback(),
			)
			return

	# Create fresh reclass with current SLE values
	try:
		doc = frappe.get_doc(voucher_type, voucher_no)
		create_division_reclass(doc, method="repost")
	except Exception:
		frappe.log_error(
			title=f"[Division Reclass] Failed to recreate reclass for {voucher_type} {voucher_no}",
			message=frappe.get_traceback(),
		)


def on_repost_item_valuation_update(doc, method=None):
	"""Hook for Repost Item Valuation on_update.
	Fires when the background repost job sets status to 'Completed'.
	Recreates reclass entries for all affected vouchers.

	NOTE: The repost() function uses db_set() to update status, which does NOT
	trigger on_update.  This hook is kept as a safety net for cases where the
	document is saved through the normal save() cycle (e.g. manual status
	changes from the UI).  The primary mechanism is the monkey-patch of
	repost() in jgb/__init__.py.
	"""
	if doc.company != JGB_COMPANY:
		return

	# Only act when the job just completed
	if doc.status != "Completed":
		return

	_recreate_reclass_for_repost(doc)


def _recreate_reclass_for_repost(doc):
	"""Core logic: find all vouchers affected by a Repost Item Valuation and
	recreate their reclass entries.  Called both from the on_update hook and
	from the monkey-patched repost() function."""
	# Collect all affected vouchers
	vouchers = set()

	# 1. The source voucher itself (if Transaction-based)
	if doc.based_on == "Transaction" and doc.voucher_type and doc.voucher_no:
		vouchers.add((doc.voucher_type, doc.voucher_no))

	# 2. All affected (downstream) transactions that had their SLEs reposted
	from erpnext.stock.stock_ledger import get_affected_transactions

	affected = get_affected_transactions(doc)
	for vt, vn in affected:
		vouchers.add((vt, vn))

	# 3. Directly dependent vouchers (from _get_directly_dependent_vouchers)
	#    These are future stock vouchers for the same item/warehouse combo.
	#    We re-query them here since the repost function computed them internally.
	if doc.based_on == "Transaction" and doc.voucher_type and doc.voucher_no:
		from erpnext.accounts.utils import get_future_stock_vouchers
		from erpnext.stock.stock_ledger import get_items_to_be_repost

		try:
			ref_doc = frappe.get_doc(doc.voucher_type, doc.voucher_no)
			doc_items, doc_warehouses = ref_doc.get_items_and_warehouses()
			sles = get_items_to_be_repost(doc.voucher_type, doc.voucher_no)
			doc_items.update({sle.item_code for sle in sles})
			doc_warehouses.update({sle.warehouse for sle in sles})

			future_vouchers = get_future_stock_vouchers(
				posting_date=doc.posting_date,
				posting_time=doc.posting_time or "00:00:00",
				for_warehouses=list(doc_warehouses),
				for_items=list(doc_items),
				company=doc.company,
			)
			for vt, vn in future_vouchers:
				vouchers.add((vt, vn))
		except Exception:
			frappe.log_error(
				title=f"[Division Reclass] Failed to get future vouchers for repost {doc.name}",
				message=frappe.get_traceback(),
			)

	if not vouchers:
		return

	frappe.logger().info(
		f"[Division Reclass] Repost {doc.name} completed — recreating reclass for "
		f"{len(vouchers)} vouchers"
	)

	for voucher_type, voucher_no in vouchers:
		_recreate_reclass_for_voucher(voucher_type, voucher_no)


# Warehouses that, before the 2026-08-12 fix, had no explicit `account` set and were
# silently falling back to an arbitrary Stock account (1205 - Misting) instead of the
# control account (1211). Any already-submitted voucher that touched one of these
# warehouses has a wrong GL entry under its own voucher_type/voucher_no and needs its
# accounting ledger reposted (not just a bulk correcting JV) so that voucher's own
# ledger trail shows the correct account.
BACKFILL_BROKEN_WAREHOUSES = {
	"JGB Warehouse - 2nd Industrial",
	"JGB Warehouse - Filtration",
	"JGB Warehouse - Jeddah",
	"JGB Warehouse - Khalidiyah",
	"JGB Warehouse - Riyadh",
	"Transit Warehouse - JGB",
}

BACKFILL_VOUCHER_DOCTYPES = [
	"Purchase Receipt",
	"Purchase Invoice",
	"Delivery Note",
	"Sales Invoice",
	"Stock Entry",
	"Stock Reconciliation",
]


def _voucher_touches_broken_warehouse(voucher_type, voucher_no):
	warehouses = frappe.db.sql(
		"""
		SELECT DISTINCT warehouse FROM `tabStock Ledger Entry`
		WHERE voucher_type=%(voucher_type)s AND voucher_no=%(voucher_no)s AND is_cancelled=0
		""",
		{"voucher_type": voucher_type, "voucher_no": voucher_no},
		as_list=True,
	)
	return bool({w[0] for w in warehouses} & BACKFILL_BROKEN_WAREHOUSES)


def _repost_allowed_types():
	from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import (
		get_allowed_types_from_settings,
	)
	return set(get_allowed_types_from_settings())


def _repost_voucher_gl(voucher_type, voucher_no, company):
	"""Repost a single voucher's own GL entries using erpnext's Repost Accounting
	Ledger tool. This cancels the voucher's existing (wrong) GL entries and
	recreates them under the SAME voucher_type/voucher_no, using the now-fixed
	warehouse account mapping — so drilling into the original document shows
	the correct account directly, unlike a separate correcting Journal Entry.

	If this voucher_type isn't enabled in "Repost Accounting Ledger Settings"
	on this site, this is a no-op (logged) rather than a hard failure, since
	that's a site-level configuration difference rather than a bug in this
	function.
	"""
	if voucher_type not in _repost_allowed_types():
		frappe.logger().warning(
			f"[Division Reclass Backfill] {voucher_type} is not enabled in Repost Accounting "
			f"Ledger Settings on this site — skipping repost for {voucher_type} {voucher_no}. "
			f"Enable it there if this voucher's own ledger needs to show the corrected account."
		)
		return False

	repost_doc = frappe.new_doc("Repost Accounting Ledger")
	repost_doc.company = company
	repost_doc.append("vouchers", {"voucher_type": voucher_type, "voucher_no": voucher_no})
	repost_doc.insert(ignore_permissions=True)
	repost_doc.submit()
	return True


@frappe.whitelist()
def backfill_historical_division_reclass(from_date=CUTOFF_DATE_STR, to_date=None, company=JGB_COMPANY):
	"""One-time backfill for stock transactions that were already submitted before the
	Division Inventory Reclassification hooks went live (or before the warehouse
	account bug was fixed on 2026-08-12).

	For every qualifying transaction, in order, this method:
	  1. Opens the document (frappe.get_doc).
	  2. If it touched one of the warehouses affected by the account-routing bug,
	     reposts its own GL entries via Repost Accounting Ledger so the voucher's
	     own ledger trail shows the correct account (1211, or its dedicated
	     warehouse account) instead of the misrouted one.
	  3. Creates the linked Division Inventory Reclassification for the voucher
	     using the same logic that runs automatically for new transactions
	     (create_division_reclass), so the division breakdown is available.

	Idempotent: create_division_reclass() skips vouchers that already have a
	submitted reclass; repost is safe to re-run (it just re-derives the same GL
	from current data). Commits after each voucher so it can be safely re-run if
	interrupted partway through.

	Returns a summary dict; does not raise on a per-voucher failure — those are
	collected in the "errors" list and logged via frappe.log_error so the run can
	be reviewed and retried for just the failed vouchers.
	"""
	to_date = to_date or frappe.utils.nowdate()
	summary = {"reposted": 0, "reclassed": 0, "skipped": 0, "errors": []}

	for doctype in BACKFILL_VOUCHER_DOCTYPES:
		filters = {
			"company": company,
			"docstatus": 1,
			"posting_date": ["between", [from_date, to_date]],
		}
		if doctype in ("Purchase Invoice", "Sales Invoice"):
			filters["update_stock"] = 1

		names = frappe.get_all(doctype, filters=filters, pluck="name", order_by="posting_date asc")

		for name in names:
			try:
				doc = frappe.get_doc(doctype, name)

				if _voucher_touches_broken_warehouse(doctype, name):
					if _repost_voucher_gl(doctype, name, company):
						summary["reposted"] += 1

				before = frappe.db.count(
					"Division Inventory Reclassification",
					{"reference_doctype": doctype, "reference_name": name, "docstatus": 1},
				)
				create_division_reclass(doc, method="backfill")
				after = frappe.db.count(
					"Division Inventory Reclassification",
					{"reference_doctype": doctype, "reference_name": name, "docstatus": 1},
				)
				if after > before:
					summary["reclassed"] += 1
				else:
					summary["skipped"] += 1

				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
				summary["errors"].append({"voucher_type": doctype, "voucher_no": name})
				frappe.log_error(
					title=f"Division Reclass Backfill Error: {doctype} {name}",
					message=frappe.get_traceback(),
				)

	return summary


def add_division_reclass_link(data):
	"""Add 'Division Inventory Reclassification' to the Connections panel of the
	source doctypes (Purchase Receipt, Purchase Invoice, Delivery Note, Sales
	Invoice, Stock Entry, Stock Reconciliation) so users can see, from the
	original transaction, that its division breakdown lives on a linked
	document (since that document's own ledger only ever shows the control
	account 1211, not the division account — see doctype docstring).

	Wired via hooks.py `override_doctype_dashboards`.
	"""
	data.setdefault("non_standard_fieldnames", {})
	data["non_standard_fieldnames"]["Division Inventory Reclassification"] = "reference_name"

	data.setdefault("transactions", [])
	data["transactions"].append({
		"label": _("Division Accounting"),
		"items": ["Division Inventory Reclassification"],
	})
	return data


def add_purchase_receipt_links(data):
	"""Purchase Receipt dashboard: Division Reclassification (shared above) +
	the Manufacture Stock Entries created from this PR via
	`Stock Entry.custom_purchase_receipt`."""
	data = add_division_reclass_link(data)
	data.setdefault("non_standard_fieldnames", {})
	data["non_standard_fieldnames"]["Stock Entry"] = "custom_purchase_receipt"
	data.setdefault("transactions", [])
	data["transactions"].append({"label": _("Manufacture"), "items": ["Stock Entry"]})
	return data
