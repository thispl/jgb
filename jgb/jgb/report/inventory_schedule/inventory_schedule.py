# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

# "Inventory Schedule" report for Joint Global Business Co LLC (JGB).
# Divisionwise stock balance (qty + value) as of the As-of Date.
#
# Division = the item's Item Group (Item Group.custom_group_name -> Division,
# the same mapping the Division Inventory Reclassification doctype uses).
#
# VALUE always comes from GL Entry on each division's leaf inventory account
# (Division Account Details), so division rows tie to the Trial Balance
# exactly. QTY comes from Stock Ledger Entry.
#
# report_type = Summary      -> divisionwise summary: one line per division
#             = Divisionwise -> division heading rows with the items of
#                               that item group listed beneath

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	company = filters.company
	currency = frappe.get_cached_value("Company", company, "default_currency") or "SAR"

	buckets = get_division_buckets(company)
	if filters.get("division"):
		buckets = [b for b in buckets if b["division"] == filters.division]
		if not buckets:
			frappe.msgprint(
				_(
					"Division {0} has no leaf inventory account mapped in "
					"Division Account Details."
				).format(filters.division),
				indicator="yellow",
			)

	all_accounts = [acc for b in buckets for acc in b["accounts"]]
	gl = get_gl_balances(company, all_accounts, filters.to_date)
	sle = get_stock_by_division(company, filters.to_date)

	items = (
		get_stock_items(company, filters.to_date)
		if filters.report_type == "Divisionwise"
		else []
	)

	columns = get_columns(currency)
	rows = build_rows(buckets, gl, sle, items, filters, currency)

	last = rows[-1] if rows else {}
	total_val = flt(last.get("balance_value"))
	total_qty = flt(last.get("balance_qty"))
	report_summary = [
		dict(
			value=total_val,
			label=_("Closing Value (per Trial Balance)"),
			datatype="Currency",
			currency=currency,
			indicator="Blue",
		),
		dict(
			value=total_qty,
			label=_("Closing Qty"),
			datatype="Float",
			indicator="Blue",
		),
	]

	return columns, rows, None, None, report_summary


def validate_filters(filters):
	if not filters.company:
		filters.company = frappe.db.get_value("Company", {}, "name")
	if not filters.company or not frappe.db.exists("Company", filters.company):
		frappe.throw(_("Please select a valid Company"))

	filters.to_date = getdate(filters.get("to_date") or nowdate())
	if filters.get("from_date") and getdate(filters.from_date) > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date"))

	if filters.get("report_type") != "Divisionwise":
		filters.report_type = "Summary"


def get_division_buckets(company):
	"""One bucket per division's leaf inventory account (Division Account
	Details) plus a catch-all bucket for the remaining leaf accounts in the
	same stock group (control account 1211, unmapped stock accounts)."""
	dad_rows = frappe.get_all(
		"Division Account Details",
		filters={"company": company},
		fields=["parent", "inventory_account"],
		order_by="idx",
	)
	accounts = {
		a.name: a
		for a in frappe.get_all(
			"Account",
			filters={"company": company, "is_group": 0},
			fields=["name", "account_name", "account_number", "account_type", "parent_account"],
		)
	}

	buckets, claimed = [], set()
	for row in dad_rows:
		acc = row.inventory_account
		# group accounts (e.g. Common -> 1200) can never hold a GL balance
		if not acc or acc in claimed or acc not in accounts:
			continue
		claimed.add(acc)
		number = accounts[acc].account_number or acc.split(" - ")[0]
		buckets.append(
			{"division": row.parent, "label": f"{row.parent} ({number})", "accounts": [acc]}
		)
	buckets.sort(key=lambda b: b["accounts"][0])

	# catch-all: unclaimed leaf accounts in the same stock-in-hand group;
	# fall back to every Stock-type leaf account when no division is mapped
	stock_parents = {accounts[a].parent_account for b in buckets for a in b["accounts"]}
	others = sorted(
		name
		for name, a in accounts.items()
		if name not in claimed
		and (a.parent_account in stock_parents or (not stock_parents and a.account_type == "Stock"))
	)
	if others:
		label = others[0] if len(others) == 1 else _("General / Unallocated")
		buckets.append({"division": None, "label": label, "accounts": others})

	return buckets


def get_gl_balances(company, account_names, to_date):
	"""Cumulative debit-credit balance per account as of to_date."""
	if not account_names:
		return {}
	result = frappe.db.sql(
		"""
		select account, sum(debit - credit) as balance
		from `tabGL Entry`
		where company = %(company)s
			and is_cancelled = 0
			and posting_date <= %(td)s
			and account in %(accounts)s
		group by account
		""",
		{"company": company, "td": to_date, "accounts": tuple(account_names)},
		as_dict=True,
	)
	return {r.account: flt(r.balance) for r in result}


def get_stock_by_division(company, to_date):
	"""Closing stock qty per division from the stock ledger.
	Division = item.item_group -> Item Group.custom_group_name (matches
	Division Inventory Reclassification)."""
	result = frappe.db.sql(
		"""
		select ig.custom_group_name as division, sum(sle.actual_qty) as qty
		from `tabStock Ledger Entry` sle
		join `tabItem` i on i.name = sle.item_code
		left join `tabItem Group` ig on ig.name = i.item_group
		where sle.company = %(company)s
			and sle.is_cancelled = 0
			and sle.posting_date <= %(td)s
		group by ig.custom_group_name
		""",
		{"company": company, "td": to_date},
		as_dict=True,
	)
	return {r.division: flt(r.qty) for r in result}


def get_stock_items(company, to_date):
	"""Per-item closing qty + value from the stock ledger (Divisionwise mode).
	Value = sum(stock_value_difference); division via item group."""
	return frappe.db.sql(
		"""
		select sle.item_code, i.item_name, ig.custom_group_name as division,
			sum(sle.actual_qty) as qty,
			sum(sle.stock_value_difference) as val
		from `tabStock Ledger Entry` sle
		join `tabItem` i on i.name = sle.item_code
		left join `tabItem Group` ig on ig.name = i.item_group
		where sle.company = %(company)s
			and sle.is_cancelled = 0
			and sle.posting_date <= %(td)s
		group by sle.item_code
		order by sle.item_code
		""",
		{"company": company, "td": to_date},
		as_dict=True,
	)


def build_rows(buckets, gl, sle, items, filters, currency):
	"""Summary      -> one row per division + Total.
	Divisionwise -> division heading row (qty = ledger total of its items,
	                value = GL balance -> ties to TB) with item rows beneath,
	                plus a Non-item GL movements line when the GL and ledger
	                values differ."""
	general_idx = next((i for i, b in enumerate(buckets) if not b["division"]), None)
	# qty of items whose item group maps to no division bucket -> catch-all
	mapped_divs = {b["division"] for b in buckets if b["division"]}
	unmapped_qty = sum(qty for div, qty in sle.items() if div not in mapped_divs)

	def bucket_qty(i):
		return unmapped_qty if i == general_idx else flt(sle.get(buckets[i]["division"]))

	def bucket_val(i):
		return sum(flt(gl.get(acc)) for acc in buckets[i]["accounts"])

	def total_row(qty, val):
		return frappe._dict(
			particulars=_("Total Inventory"), indent=0, bold=1, currency=currency,
			balance_qty=norm(qty), balance_value=norm(val),
		)

	if filters.report_type == "Divisionwise":
		items_by_bucket = {}
		for it in items:
			idx = next(
				(i for i, b in enumerate(buckets) if b["division"] == it.division),
				general_idx,
			)
			if idx is not None:
				items_by_bucket.setdefault(idx, []).append(it)

		rows = []
		grand_qty = grand_val = 0.0
		for i, bucket in enumerate(buckets):
			val = bucket_val(i)
			div_items = [
				it for it in items_by_bucket.get(i, []) if flt(it.qty)
			]
			qty = sum(flt(it.qty) for it in div_items)
			if not qty and abs(val) < 0.005 and not filters.get("division"):
				continue
			rows.append(
				frappe._dict(
					particulars=bucket["label"], indent=0, bold=1,
					currency=currency,
					balance_qty=norm(qty), balance_value=norm(val),
				)
			)
			item_val_sum = 0.0
			for it in div_items:
				item_val_sum += flt(it.val)
				rows.append(
					frappe._dict(
						particulars=f"{it.item_code} : {it.item_name}",
						indent=1, currency=currency,
						balance_qty=norm(flt(it.qty)),
						balance_value=norm(flt(it.val)),
					)
				)
			residual = val - item_val_sum
			if abs(residual) >= 0.005:
				rows.append(
					frappe._dict(
						particulars=_("Non-item GL movements"), indent=1,
						currency=currency, balance_value=norm(residual),
					)
				)
			grand_qty += qty
			grand_val += val
		if rows:
			rows.append(total_row(grand_qty, grand_val))
		return rows

	rows = []
	grand_qty = grand_val = 0.0
	for i, bucket in enumerate(buckets):
		qty, val = bucket_qty(i), bucket_val(i)
		if not qty and abs(val) < 0.005 and not filters.get("division"):
			continue
		rows.append(
			frappe._dict(
				particulars=bucket["label"], indent=0, currency=currency,
				balance_qty=norm(qty), balance_value=norm(val),
			)
		)
		grand_qty += qty
		grand_val += val

	rows.append(total_row(grand_qty, grand_val))
	return rows


def norm(value):
	return None if value is None else flt(value) + 0.0  # + 0.0 normalizes -0.0


def get_columns(currency):
	return [
		dict(label=_("Particulars"), fieldname="particulars", fieldtype="Data", width=380),
		dict(label=_("Balance Qty"), fieldname="balance_qty", fieldtype="Float", width=120),
		dict(
			label=_("Balance Value"),
			fieldname="balance_value",
			fieldtype="Currency",
			options="currency",
			width=160,
		),
		dict(
			label=_("Currency"),
			fieldname="currency",
			fieldtype="Link",
			options="Currency",
			hidden=1,
		),
	]
