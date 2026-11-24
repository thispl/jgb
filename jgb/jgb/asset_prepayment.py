# Asset Prepayment — amortizes a prepaid amount on an Asset over a schedule,
# mirroring the depreciation flow (Asset Depreciation Schedule).
#
# Lifecycle: Asset saved with custom_is_prepaid -> draft Asset Prepayment
# Schedule -> Asset submit -> schedule Active -> nightly
# post_prepayment_entries creates DRAFT Journal Entries (voucher_type
# "Prepayment Entry") for due rows; manual approval via the normal JE
# workflow. Asset cancel -> schedule + its JEs cancelled.

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from erpnext.assets.doctype.asset.depreciation import (
	get_acc_frozen_upto,
	get_checks_for_pl_and_bs_accounts,
)

SCHEDULE_DOCTYPE = "Asset Prepayment Schedule"
ROW_DOCTYPE = "Prepayment Schedule"


# ---------------------------------------------------------------------------
# Asset lifecycle hooks
# ---------------------------------------------------------------------------

def make_or_update_prepayment_schedule(asset, method=None):
	"""Asset.validate: manage the draft Asset Prepayment Schedule."""
	if asset.flags.in_import or asset.flags.in_migrate:
		return

	if asset.is_new() or asset.docstatus != 0:
		# name not generated yet (after_insert creates it), or submit/cancel in
		# progress — only draft assets manage the draft schedule
		return

	if not asset.get("custom_is_prepaid") or asset.get("split_from"):
		for name in frappe.get_all(SCHEDULE_DOCTYPE, {"asset": asset.name, "docstatus": 0}, pluck="name"):
			frappe.delete_doc(SCHEDULE_DOCTYPE, name, force=1)
		return

	credit_account, debit_account = get_prepaid_and_expense_accounts(asset)
	draft = _get_schedule_doc(asset.name, 0)
	aps = draft or frappe.new_doc(SCHEDULE_DOCTYPE)

	changed = (
		not draft
		or aps.prepaid_amount != flt(asset.custom_prepaid_amount)
		or aps.opening_amortized_prepayment != flt(asset.get("custom_opening_amortized_prepayment"))
		or cint(aps.total_number_of_prepayments) != cint(asset.custom_total_number_of_prepayments)
		or cint(aps.frequency_of_prepayment) != cint(asset.custom_frequency_of_prepayment)
		or getdate(aps.prepayment_start_date) != getdate(asset.custom_prepayment_start_date)
	)

	aps.asset = asset.name
	aps.company = asset.company
	aps.prepaid_amount = flt(asset.custom_prepaid_amount)
	aps.opening_amortized_prepayment = flt(asset.get("custom_opening_amortized_prepayment"))
	aps.total_number_of_prepayments = cint(asset.custom_total_number_of_prepayments)
	aps.frequency_of_prepayment = cint(asset.custom_frequency_of_prepayment)
	aps.prepayment_start_date = asset.custom_prepayment_start_date
	aps.prepaid_account = credit_account
	aps.prepayment_expense_account = debit_account
	aps.cost_center = asset.cost_center
	if changed:
		aps.prepayment_schedule = []

	if draft:
		aps.save()
	else:
		aps.insert()
		frappe.msgprint(
			_("Asset Prepayment Schedule {0} created. Please check it and submit the Asset.").format(
				frappe.utils.get_link_to_form(SCHEDULE_DOCTYPE, aps.name)
			)
		)


def activate_prepayment_schedules(asset, method=None):
	"""Asset.on_submit: submit draft schedules so they become Active."""
	for name in frappe.get_all(SCHEDULE_DOCTYPE, {"asset": asset.name, "docstatus": 0}, pluck="name"):
		frappe.get_doc(SCHEDULE_DOCTYPE, name).submit()


def cancel_prepayment_schedules(asset, method=None):
	"""Asset.on_cancel: cancel schedules (which cancels their JEs)."""
	for name in frappe.get_all(
		SCHEDULE_DOCTYPE, {"asset": asset.name, "docstatus": ["<", 2]}, pluck="name"
	):
		frappe.get_doc(SCHEDULE_DOCTYPE, name).cancel()


def on_asset_update(asset, method=None):
	"""Asset.on_update: on disposal (Scrapped/Sold) book all remaining
	prepayment rows as draft JEs — mirrors scrap_asset posting pending
	depreciation before disposal."""
	if asset.docstatus != 1 or asset.status not in ("Scrapped", "Sold"):
		return
	old = asset.get_doc_before_save()
	if old and old.status in ("Scrapped", "Sold"):
		return
	for name in frappe.get_all(SCHEDULE_DOCTYPE, {"asset": asset.name, "docstatus": 1}, pluck="name"):
		doc = frappe.get_doc(SCHEDULE_DOCTYPE, name)
		for row in doc.get("prepayment_schedule"):
			if _row_unposted(row):
				_make_prepayment_journal_entry(doc, row)
		update_asset_prepaid_amounts(asset.name)


@frappe.whitelist()
def create_prepayment_schedule(asset_name):
	"""Asset form button: create (and activate) a schedule on a submitted asset,
	or return the existing one."""
	asset = frappe.get_doc("Asset", asset_name)
	if asset.docstatus != 1:
		frappe.throw(_("Submit the Asset first."))

	existing = frappe.db.get_value(
		SCHEDULE_DOCTYPE, {"asset": asset_name, "docstatus": ["<", 2]}, "name"
	)
	if existing:
		return existing

	credit_account, debit_account = get_prepaid_and_expense_accounts(asset)
	aps = frappe.new_doc(SCHEDULE_DOCTYPE)
	aps.asset = asset.name
	aps.company = asset.company
	aps.prepaid_amount = flt(asset.custom_prepaid_amount)
	aps.opening_amortized_prepayment = flt(asset.get("custom_opening_amortized_prepayment"))
	aps.total_number_of_prepayments = cint(asset.custom_total_number_of_prepayments)
	aps.frequency_of_prepayment = cint(asset.custom_frequency_of_prepayment)
	aps.prepayment_start_date = asset.custom_prepayment_start_date
	aps.prepaid_account = credit_account
	aps.prepayment_expense_account = debit_account
	aps.cost_center = asset.cost_center
	aps.insert()
	aps.submit()
	return aps.name


def _get_schedule_doc(asset_name, docstatus):
	name = frappe.db.get_value(SCHEDULE_DOCTYPE, {"asset": asset_name, "docstatus": docstatus}, "name")
	return frappe.get_doc(SCHEDULE_DOCTYPE, name) if name else None


def get_prepaid_and_expense_accounts(asset):
	"""Returns (prepaid_account=credit, expense_account=debit) from the Asset
	Category's per-company account row — same place depreciation accounts live."""
	row = frappe.db.get_value(
		"Asset Category Account",
		{"parent": asset.asset_category, "company_name": asset.company},
		["custom_prepaid_account", "custom_prepayment_expense_account"],
		as_dict=True,
	)
	if not row or not row.custom_prepaid_account or not row.custom_prepayment_expense_account:
		frappe.throw(
			_(
				"Set Prepaid Account and Prepayment Expense Account on Asset Category {0} "
				"(Accounts row for company {1})."
			).format(asset.asset_category, asset.company)
		)
	return row.custom_prepaid_account, row.custom_prepayment_expense_account


# ---------------------------------------------------------------------------
# Nightly posting — mirrors erpnext post_depreciation_entries, but leaves the
# Journal Entries as DRAFTS for manual approval.
# ---------------------------------------------------------------------------

def post_prepayment_entries(date=None):
	date = getdate(date) if date else getdate(today())

	rows = _get_due_prepayment_rows(date)
	for aps_name, asset_name in {r[0]: r[1] for r in rows}.items():
		try:
			doc = frappe.get_doc(SCHEDULE_DOCTYPE, aps_name)
			for row in doc.get("prepayment_schedule"):
				if getdate(row.schedule_date) <= date and _row_unposted(row):
					_make_prepayment_journal_entry(doc, row)
			update_asset_prepaid_amounts(asset_name)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				frappe.get_traceback(),
				f"Prepayment Entry posting failed for Asset {asset_name}",
			)

	frappe.db.commit()


def _row_unposted(row):
	if not row.journal_entry:
		return True
	# draft/submitted JE counts as posted; cancelled or deleted does not
	return frappe.db.get_value("Journal Entry", row.journal_entry, "docstatus") in (None, 2)


def _get_due_prepayment_rows(date):
	frozen = get_acc_frozen_upto()
	frozen_clause = "AND ps.schedule_date > %(frozen)s" if frozen else ""
	return frappe.db.sql(
		f"""
		SELECT aps.name, aps.asset
		FROM `tabAsset Prepayment Schedule` aps
		JOIN `tabAsset` a ON aps.asset = a.name
		JOIN `tabPrepayment Schedule` ps ON ps.parent = aps.name
		LEFT JOIN `tabJournal Entry` je ON ps.journal_entry = je.name
		WHERE aps.docstatus = 1
			AND a.docstatus = 1
			AND ps.schedule_date <= %(date)s
			AND (ps.journal_entry IS NULL OR je.docstatus = 2 OR je.name IS NULL)
			{frozen_clause}
		GROUP BY aps.name
		""",
		{"date": date, "frozen": frozen},
	)


def _make_prepayment_journal_entry(aps_doc, row):
	asset = frappe.get_doc("Asset", aps_doc.asset)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Prepayment Entry"
	je.posting_date = row.schedule_date
	je.company = aps_doc.company
	je.finance_book = asset.default_finance_book
	je.remark = f"Prepayment Entry against {asset.name} worth {row.prepayment_amount}"

	cost_center = asset.cost_center or aps_doc.cost_center
	credit_entry = {
		"account": aps_doc.prepaid_account,
		"credit_in_account_currency": row.prepayment_amount,
		"reference_type": "Asset",
		"reference_name": asset.name,
		"cost_center": cost_center,
	}
	debit_entry = {
		"account": aps_doc.prepayment_expense_account,
		"debit_in_account_currency": row.prepayment_amount,
		"reference_type": "Asset",
		"reference_name": asset.name,
		"cost_center": cost_center,
	}

	for dimension in get_checks_for_pl_and_bs_accounts():
		if asset.get(dimension["fieldname"]) or dimension.get("mandatory_for_bs"):
			credit_entry[dimension["fieldname"]] = asset.get(dimension["fieldname"]) or dimension.get(
				"default_dimension"
			)
		if asset.get(dimension["fieldname"]) or dimension.get("mandatory_for_pl"):
			debit_entry[dimension["fieldname"]] = asset.get(dimension["fieldname"]) or dimension.get(
				"default_dimension"
			)

	je.set("accounts", [credit_entry, debit_entry])
	je.flags.ignore_permissions = True
	je.insert()  # left as Draft — approved manually via the JE workflow

	row.db_set("journal_entry", je.name)
	return je


# ---------------------------------------------------------------------------
# Asset totals + Journal Entry hook
# ---------------------------------------------------------------------------

def update_asset_prepaid_amounts(asset_name, method=None):
	"""Recompute custom_prepaid_amortized / custom_prepaid_balance on the Asset
	from schedule rows whose JE is submitted."""
	prepaid = flt(frappe.db.get_value("Asset", asset_name, "custom_prepaid_amount"))
	amortized = flt(
		frappe.db.sql(
			"""
			SELECT SUM(ps.prepayment_amount)
			FROM `tabPrepayment Schedule` ps
			JOIN `tabAsset Prepayment Schedule` aps ON ps.parent = aps.name
			JOIN `tabJournal Entry` je ON ps.journal_entry = je.name
			WHERE aps.asset = %s AND aps.docstatus = 1 AND je.docstatus = 1
			""",
			asset_name,
		)[0][0]
	)
	frappe.db.set_value(
		"Asset",
		asset_name,
		{
			"custom_prepaid_amortized": amortized,
			"custom_prepaid_balance": prepaid - amortized,
		},
	)


def on_prepayment_je_change(doc, method=None):
	"""Journal Entry on_submit/on_cancel/on_trash: unlink the schedule row and
	refresh the Asset's prepaid totals. Unlinking mirrors JE's own
	update_booked_depreciation and is what lets the JE cancel/delete pass the
	back-link check."""
	if doc.voucher_type != "Prepayment Entry":
		return
	if method in ("on_cancel", "on_trash"):
		frappe.db.set_value(ROW_DOCTYPE, {"journal_entry": doc.name}, "journal_entry", None)
	for row in doc.get("accounts"):
		if row.reference_type == "Asset" and row.reference_name:
			update_asset_prepaid_amounts(row.reference_name)


@frappe.whitelist()
def get_asset_prepayment_schedule_doc(asset_name):
	"""Asset form: schedule doc to render in the custom_prepayment_schedule_view
	HTML field (mirrors get_asset_depr_schedule_doc). Prefers Active, falls back
	to Draft."""
	name = frappe.db.get_value(
		SCHEDULE_DOCTYPE, {"asset": asset_name, "docstatus": ["<", 2]}, "name"
	)
	return frappe.get_doc(SCHEDULE_DOCTYPE, name) if name else None


# ---------------------------------------------------------------------------
# Asset dashboard — show the schedule under Connections
# ---------------------------------------------------------------------------

def get_dashboard_data(data):
	data.setdefault("non_standard_fieldnames", {})
	data["non_standard_fieldnames"][SCHEDULE_DOCTYPE] = "asset"
	data.setdefault("transactions", [])
	data["transactions"].append(
		{"label": _("Prepayment"), "items": [SCHEDULE_DOCTYPE]}
	)
	return data
