# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

# "Financial Statements" report for Joint Global Business Co LLC (JGB).
# Renders the Income Statement / Balance Sheet layouts defined in
# "Chart of Accounts Mapping for Financial Statements.xlsx", grouping accounts by
# the custom_fs_category / custom_fs_sub_category fields on the Account doctype
# (falls back to the seed mapping in jgb.financial_statement when blank).

import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, get_year_start, nowdate

from jgb.financial_statement import (
	ACCOUNT_MAPPING,
	CF_ACCOUNT_MAPPING,
	CF_LINE_FIELD,
	FS_CATEGORY_FIELD,
	FS_SUBCATEGORY_FIELD,
)

# Categories that belong to the Balance Sheet vs the Profit & Loss statement
BS_CATEGORIES = (
	"Current Assets",
	"Non Current Assets",
	"Current Liabilities",
	"Non Current Liabilities",
	"Partners Equity",
	"Retained Earnings",
)
PL_CATEGORIES = (
	"Revenue",
	"Cost of Goods Sold",
	"Operating Expense",
	"Other Income or Loss",
	"Non Cash Expense",
	"Finance Cost",
	"Zakat and Income Tax",
)

# sign: "debit" = present sum(debit - credit) as positive (expenses / assets)
#       "credit" = present sum(credit - debit) as positive (income / liabilities / equity)
INCOME_STATEMENT_LAYOUT = [
	dict(label="Sales", type="line", match=("Revenue", "Sales"), sign="credit", indent=0),
	dict(
		label="Cost of Goods Sold",
		type="line",
		match=("Cost of Goods Sold", "Cost of Goods Sold"),
		sign="debit",
		indent=0,
	),
	dict(
		label="Direct Expenses",
		type="line",
		match=("Cost of Goods Sold", "Direct Expenses"),
		sign="debit",
		indent=0,
	),
	dict(label="Gross Profit", type="calc", key="gross_profit", indent=0, bold=1),
	dict(
		label="Total Selling & Marketing Expenses",
		type="line",
		match=("Operating Expense", "Selling & Marketing Expenses"),
		sign="debit",
		indent=0,
	),
	dict(
		label="General & Administrative Expenses",
		type="line",
		match=("Operating Expense", "General & Administrative expenses"),
		sign="debit",
		indent=0,
	),
	dict(label="Total Operating Expenses", type="calc", key="total_opex", indent=0),
	dict(label="Operating Profit", type="calc", key="operating_profit", indent=0, bold=1),
	dict(
		label="Other Income / Loss",
		type="line",
		match=("Other Income or Loss", "Other Income / loss"),
		sign="credit",
		indent=0,
	),
	dict(
		label="Profit / (Loss) on Sale of Fixed Asset",
		type="line",
		match=("Other Income or Loss", "Profit/Loss on Sale of Fixed Asset"),
		sign="credit",
		indent=0,
	),
	dict(label="EBITDA", type="calc", key="ebitda", indent=0, bold=1),
	dict(label="Depreciation", type="line", match=("cat", "Non Cash Expense"), sign="debit", indent=0),
	dict(label="EBIT", type="calc", key="ebit", indent=0, bold=1),
	dict(label="Finance Charges", type="line", match=("cat", "Finance Cost"), sign="debit", indent=0),
	dict(label="Zakat and Income Tax", type="line", match=("cat", "Zakat and Income Tax"), sign="debit", indent=0),
	dict(label="Net Profit after Zakat & Tax", type="calc", key="net_profit", indent=0, bold=1),
]

BALANCE_SHEET_LAYOUT = [
	dict(label="Current Assets", type="header", indent=0),
	dict(label="Cash and Banks", type="line", match=("Current Assets", "Cash and banks"), sign="debit", indent=1),
	dict(
		label="Accounts Receivables",
		type="line",
		match=("Current Assets", "Accounts Receivables"),
		sign="debit",
		indent=1,
	),
	dict(
		label="Prepayments and Other Receivables",
		type="line",
		match=("Current Assets", "Prepayments and Other Receivables"),
		sign="debit",
		indent=1,
	),
	dict(
		label="Retention Receivables",
		type="line",
		match=("Current Assets", "Retention Receivables"),
		sign="debit",
		indent=1,
	),
	dict(
		label="Due from Related Parties",
		type="line",
		match=("Current Assets", "Due from Related Parties"),
		sign="debit",
		indent=1,
	),
	dict(label="Inventory", type="line", match=("Current Assets", "Inventory"), sign="debit", indent=1),
	dict(label="Total Current Assets", type="calc", key="total_current_assets", indent=0, bold=1),
	dict(label="Non Current Assets", type="header", indent=0),
	dict(
		label="Machinery & Equipments",
		type="line",
		match=("Non Current Assets", "Machinery & Equipments"),
		sign="debit",
		indent=1,
	),
	dict(label="Vehicle", type="line", match=("Non Current Assets", "Vehicle"), sign="debit", indent=1),
	dict(
		label="Office Equipments",
		type="line",
		match=("Non Current Assets", "Office Equipments"),
		sign="debit",
		indent=1,
	),
	dict(
		label="Computer & Accessories",
		type="line",
		match=("Non Current Assets", "Computer & Accessories"),
		sign="debit",
		indent=1,
	),
	dict(
		label="Furniture & Fixtures",
		type="line",
		match=("Non Current Assets", "Furniture & Fixtures"),
		sign="debit",
		indent=1,
	),
	dict(
		label="Leasehold Improvement",
		type="line",
		match=("Non Current Assets", "Leasehold Improvement"),
		sign="debit",
		indent=1,
	),
	dict(
		label="Capital Lease-Vehicles",
		type="line",
		match=("Non Current Assets", "Capital Lease-Vehicles"),
		sign="debit",
		indent=1,
	),
	dict(label="Total Non Current Assets", type="calc", key="total_non_current_assets", indent=0, bold=1),
	dict(label="TOTAL ASSETS", type="calc", key="total_assets", indent=0, bold=1),
	dict(label="Liabilities", type="header", indent=0),
	dict(label="Current Liabilities", type="header", indent=1),
	dict(
		label="Bank Overdraft",
		type="line",
		match=("Current Liabilities", "Bank Overdraft"),
		sign="credit",
		indent=2,
	),
	dict(
		label="Short Term Loans",
		type="line",
		match=("Current Liabilities", "Short Term Loans"),
		sign="credit",
		indent=2,
	),
	dict(
		label="Obligation against Leased Assets",
		type="line",
		match=("Current Liabilities", "Obligation against Leased Assets"),
		sign="credit",
		indent=2,
	),
	dict(
		label="Accounts Payable",
		type="line",
		match=("Current Liabilities", "Accounts payable"),
		sign="credit",
		indent=2,
	),
	dict(
		label="Due to Related Parties",
		type="line",
		match=("Current Liabilities", "Due to Related Parties"),
		sign="credit",
		indent=2,
	),
	dict(
		label="Accruals & Other Payables",
		type="line",
		match=("Current Liabilities", "Accruals & Other payables"),
		sign="credit",
		indent=2,
	),
	dict(
		label="Advance from Customers",
		type="line",
		match=("Current Liabilities", "Advance from customers"),
		sign="credit",
		indent=2,
	),
	dict(label="Total Current Liabilities", type="calc", key="total_current_liabilities", indent=1, bold=1),
	dict(label="Non Current Liabilities", type="header", indent=1),
	dict(
		label="End of Service Benefits",
		type="line",
		match=("Non Current Liabilities", "End of Service Benefits"),
		sign="credit",
		indent=2,
	),
	dict(
		label="Long Term Loans",
		type="line",
		match=("Non Current Liabilities", "Long Term Loans"),
		sign="credit",
		indent=2,
	),
	dict(
		label="Total Non Current Liabilities",
		type="calc",
		key="total_non_current_liabilities",
		indent=1,
		bold=1,
	),
	dict(label="Total Liabilities", type="calc", key="total_liabilities", indent=0, bold=1),
	dict(label="Partners' Equity", type="header", indent=0),
	dict(label="Capital", type="line", match=("Partners Equity", "Capital"), sign="credit", indent=1),
	dict(
		label="Statutory Reserve",
		type="line",
		match=("Partners Equity", "Statutory Reserve"),
		sign="credit",
		indent=1,
	),
	dict(
		label="Due to Partner",
		type="line",
		match=("Partners Equity", "Due to partner"),
		sign="credit",
		indent=1,
	),
	dict(label="Retained Income / Loss", type="calc", key="retained", indent=1),
	dict(label="Current Year Income / Loss", type="calc", key="cy_pl", indent=1),
	dict(label="Total Partners' Equity", type="calc", key="total_equity", indent=0, bold=1),
	dict(label="TOTAL LIABILITIES & EQUITY", type="calc", key="total_liabilities_equity", indent=0, bold=1),
]

# ---------------------------------------------------------------------------
# Cash Flow layout (indirect method).
# Source: "Cash Flow.xlsx" (sheet: CF FORMAT).
#
# Line spec fields:
#   sources  - list of ("cf", <cash flow bucket>) | ("nums", {account numbers})
#              | ("fs", (category, sub_category), {excluded account numbers})
#   side     - which GL side to aggregate: "net" (debit-credit), "debit", "credit"
#   sign     - "debit" presents the raw value as positive, "credit" negates it
#   section  - "op" / "inv" / "fin": which subtotal the line feeds
#
# Sign cheat-sheet:
#   * balance-sheet movement lines (working capital, loans, equity): side="net",
#     sign="credit"  ->  asset increase / liability decrease shows as outflow
#   * P&L add-backs: side="net", sign="debit"  ->  expense = positive add-back,
#     a net credit (gain on disposal) shows negative and is subtracted
#   * provision add-backs that have a matching "paid" line: side="credit",
#     sign="debit"  ->  the charge only
#   * "paid" lines: side="debit", sign="credit"  ->  the cash outflow, negative
#   * investing purchases: side="debit", sign="credit"; proceeds: side="credit",
#     sign="debit"
# ---------------------------------------------------------------------------
CASH_FLOW_LAYOUT = [
	dict(label="Net (loss) income for the year", type="calc", key="net_income", bold=1),
	dict(label="Adjustments:", type="label", indent=0),
	dict(
		label="Gain (loss) in disposal of assets",
		type="line",
		key="gain_on_disposal",
		sources=[("nums", {"5220"})],
		side="net",
		sign="debit",
		section="op",
		indent=1,
	),
	dict(
		label="Provision For GOSI",
		type="line",
		key="prov_gosi",
		sources=[("cf", "Provision For GOSI")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Provision For Leave Pay",
		type="line",
		key="prov_leave",
		sources=[("cf", "Provision For Leave Pay")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Provision For Air Fare",
		type="line",
		key="prov_airfare",
		sources=[("cf", "Provision For Air Fare")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Provision for zakat",
		type="line",
		key="prov_zakat",
		sources=[("cf", "Provision for zakat")],
		side="credit",
		sign="debit",
		section="op",
		indent=1,
	),
	dict(
		label="Employees' end of service benefits",
		type="line",
		key="prov_eosb",
		sources=[("cf", "Employees' end of service benefits")],
		side="credit",
		sign="debit",
		section="op",
		indent=1,
	),
	dict(
		label="Depreciation",
		type="line",
		key="depreciation",
		sources=[("fs", ("Non Cash Expense", "Depreciation"), {"5910"})],
		side="net",
		sign="debit",
		section="op",
		indent=1,
	),
	dict(
		label="Amortisation of intangible assets",
		type="line",
		key="amortisation",
		sources=[("nums", {"5910"}), ("fs", ("Non Cash Expense", "Amortization"))],
		side="net",
		sign="debit",
		section="op",
		indent=1,
	),
	dict(label="Changes in operating assets and liabilities", type="header", indent=0),
	dict(
		label="Change in inventory",
		type="line",
		key="wc_inventory",
		sources=[("cf", "Change in inventory")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Change in trade receivables",
		type="line",
		key="wc_ar",
		sources=[("cf", "Change in trade receivables")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Change in prepayments and other receivables",
		type="line",
		key="wc_prepay",
		sources=[("cf", "Change in prepayments and other receivables")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Change in financial assets",
		type="line",
		key="wc_fin_assets",
		sources=[("cf", "Change in financial assets")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Change in trade payables",
		type="line",
		key="wc_ap",
		sources=[("cf", "Change in trade payables")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Change in due from related parties",
		type="line",
		key="wc_due_from",
		sources=[("cf", "Change in due from related parties")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Change in due to related parties",
		type="line",
		key="wc_due_to",
		sources=[("cf", "Change in due to related parties")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Change in accrued and other liabilities",
		type="line",
		key="wc_accrued",
		sources=[("cf", "Change in accrued and other liabilities")],
		side="net",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Zakat paid",
		type="line",
		key="zakat_paid",
		sources=[("cf", "Provision for zakat"), ("cf", "Zakat paid")],
		side="debit",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(
		label="Employees' end of service benefits paid",
		type="line",
		key="eosb_paid",
		sources=[
			("cf", "Employees' end of service benefits"),
			("cf", "Employees' end of service benefits paid"),
		],
		side="debit",
		sign="credit",
		section="op",
		indent=1,
	),
	dict(label="Net cash from operating activities", type="calc", key="net_operating", bold=1),
	dict(label="Cash flow from investing activities", type="header", indent=0),
	dict(
		label="Purchase of property and equipment",
		type="line",
		key="purchase_ppe",
		sources=[("cf", "Property and equipment")],
		side="debit",
		sign="credit",
		section="inv",
		indent=1,
	),
	dict(
		label="Proceeds from disposals",
		type="line",
		key="proceeds_disposal",
		sources=[("cf", "Property and equipment")],
		side="credit",
		sign="debit",
		section="inv",
		indent=1,
	),
	dict(
		label="Property investement",
		type="line",
		key="property_investment",
		sources=[("cf", "Property investment")],
		side="net",
		sign="credit",
		section="inv",
		indent=1,
	),
	dict(
		label="intangible assets",
		type="line",
		key="intangibles",
		sources=[("cf", "Intangible assets")],
		side="net",
		sign="credit",
		section="inv",
		indent=1,
	),
	dict(
		label="investement",
		type="line",
		key="investment",
		sources=[("cf", "Investment")],
		side="net",
		sign="credit",
		section="inv",
		indent=1,
	),
	dict(label="Net cash from investing activities", type="calc", key="net_investing", bold=1),
	dict(label="Cash flow from financing activities", type="header", indent=0),
	dict(
		label="Shareholder current account",
		type="line",
		key="fin_shareholder",
		sources=[("cf", "Shareholder current account")],
		side="net",
		sign="credit",
		section="fin",
		indent=1,
	),
	dict(
		label="Issuance of capital",
		type="line",
		key="fin_capital_issue",
		sources=[("cf", "Issuance of capital")],
		side="net",
		sign="credit",
		section="fin",
		indent=1,
	),
	dict(
		label="Dividend paid",
		type="line",
		key="fin_dividend",
		sources=[("cf", "Dividend paid")],
		side="net",
		sign="credit",
		section="fin",
		indent=1,
	),
	dict(
		label="Additional contribution",
		type="line",
		key="fin_contribution",
		sources=[("cf", "Additional contribution")],
		side="net",
		sign="credit",
		section="fin",
		indent=1,
	),
	dict(
		label="Capital",
		type="line",
		key="fin_capital",
		sources=[("cf", "Capital")],
		side="net",
		sign="credit",
		section="fin",
		indent=1,
	),
	dict(
		label="Short-Term Loan",
		type="line",
		key="fin_st_loan",
		sources=[("cf", "Short-Term Loan")],
		side="net",
		sign="credit",
		section="fin",
		indent=1,
	),
	dict(
		label="Current Portion Long-Term Debt",
		type="line",
		key="fin_current_ltd",
		sources=[("cf", "Current Portion Long-Term Debt")],
		side="net",
		sign="credit",
		section="fin",
		indent=1,
	),
	dict(
		label="Long Term Debt-Noncurrent",
		type="line",
		key="fin_ltd",
		sources=[("cf", "Long Term Debt-Noncurrent")],
		side="net",
		sign="credit",
		section="fin",
		indent=1,
	),
	dict(
		label="Loan - Others",
		type="line",
		key="fin_loan_others",
		sources=[("cf", "Loan - Others")],
		side="net",
		sign="credit",
		section="fin",
		indent=1,
	),
	dict(
		label="Lease to Own Vehicles",
		type="line",
		key="fin_lease",
		sources=[("cf", "Lease to Own Vehicles")],
		side="net",
		sign="credit",
		section="fin",
		indent=1,
	),
	dict(label="Net cash from financing activities", type="calc", key="net_financing", bold=1),
	dict(
		label="Other non-cash and unmapped movements",
		type="calc",
		key="other_movements",
		hide_if_zero=1,
	),
	dict(
		label="Net cash and cash equivalent during the year",
		type="calc",
		key="net_change",
		bold=1,
	),
	dict(
		label="Cash and cash equivalent at beginning of the year",
		type="calc",
		key="opening_cash",
		bold=1,
	),
	dict(
		label="Cash and cash equivalent at end of the year",
		type="calc",
		key="closing_cash",
		bold=1,
	),
]

# Row after which unmapped line items (with balances) are inserted, per category
EXTRA_LINE_ANCHORS = {
	"Current Assets": "Total Current Assets",
	"Non Current Assets": "Total Non Current Assets",
	"Current Liabilities": "Total Current Liabilities",
	"Non Current Liabilities": "Total Non Current Liabilities",
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	company = filters.company
	currency = frappe.get_cached_value("Company", company, "default_currency") or "SAR"
	periods = get_periods(filters)
	divisionwise = filters.get("report_type") == "Divisionwise"

	accounts, used_fallback, unmapped = get_mapped_accounts(company)

	if divisionwise:
		cost_centers = get_cost_centers(company)
		data = aggregate_balances_by_cc(company, accounts, periods[0], cost_centers)
		keys = [cc["fieldname"] for cc in cost_centers]
		# the Balance Sheet reads cumulative balances, the Income Statement period
		# movement -- only show "Unallocated" if the relevant section actually has
		# untagged postings.
		section = "sub_cumul" if filters.statement == "Balance Sheet" else "sub_period"
		has_unallocated = any(
			abs(v) > 0.005 for v in data[section]["unallocated"].values()
		)
		if has_unallocated:
			keys.append("unallocated")
		keys.append("total")
		columns = get_columns(periods, cost_centers, keys)
		total_key = "total"
		if has_unallocated and filters.statement == "Balance Sheet":
			frappe.msgprint(
				_(
					"Many Balance Sheet postings carry no cost center (see the Unallocated "
					"column), so per-division asset/liability figures are indicative only. "
					"The Total column reconciles with the Summary view."
				),
				indicator="yellow",
			)
	else:
		data = None if filters.statement == "Cash Flow" else aggregate_balances(company, accounts, periods)
		keys = [p["key"] for p in periods]
		columns = get_columns(periods)
		total_key = "current"

	if filters.statement == "Income Statement":
		rows = build_income_statement(data, accounts, keys, filters, currency)
	elif filters.statement == "Balance Sheet":
		rows = build_balance_sheet(data, accounts, keys, filters, currency)
	else:
		rows = build_cash_flow(company, accounts, periods, keys, filters, currency)

	warn_unmapped_accounts(unmapped, used_fallback)

	report_summary = get_report_summary(rows, filters.statement, currency, total_key)

	return columns, rows, None, None, report_summary


def validate_filters(filters):
	if not filters.company:
		filters.company = frappe.db.get_value("Company", {}, "name")
	if not filters.company or not frappe.db.exists("Company", filters.company):
		frappe.throw(_("Please select a valid Company"))

	filters.from_date = getdate(filters.get("from_date") or get_year_start(nowdate()))
	filters.to_date = getdate(filters.get("to_date") or nowdate())
	if filters.to_date < filters.from_date:
		frappe.throw(_("To Date cannot be before From Date"))

	if filters.get("statement") not in ("Income Statement", "Balance Sheet", "Cash Flow"):
		filters.statement = "Income Statement"

	if filters.get("report_type") not in ("Summary", "Summary without Comparison", "Divisionwise"):
		filters.report_type = "Summary"
	if filters.statement == "Cash Flow":
		# divisionwise is meaningless for cash flow (BS postings are partially
		# cost-center tagged) -- always Summary
		filters.report_type = "Summary"


def get_periods(filters):
	"""Current period plus a comparison period, per the 'compare_with' filter.

	- Same Period Last Year: identical span shifted back 12 months.
	- Previous Period: the immediately preceding window of equal length.
	- None: no comparison column.
	- Auto (default): ranges spanning more than one calendar month compare
	  year-over-year (Jan-Aug 2026 -> Jan-Aug 2025); a whole month compares
	  month-over-month (Sep 2026 -> Aug 2026); a partial month compares the
	  same day range in the previous month (Sep 1-14 -> Aug 1-14).
	"""
	fd, td = filters.from_date, filters.to_date
	mode = filters.get("compare_with") or "Auto"

	if mode == "None" or filters.get("report_type") in (
		"Divisionwise",
		"Summary without Comparison",
	):
		return [dict(key="current", from_date=fd, to_date=td, label=period_label(fd, td))]

	if mode == "Same Period Last Year":
		prev_fd = add_months(fd, -12)
		prev_td = add_months(td, -12)
	elif mode == "Previous Period":
		prev_td = add_days(fd, -1)
		prev_fd = add_days(prev_td, -((td - fd).days))
	elif fd == get_first_day(fd) and td == get_last_day(td):
		months = (td.year - fd.year) * 12 + td.month - fd.month + 1
		shift = 12 if months > 1 else 1
		prev_fd = add_months(fd, -shift)
		prev_td = add_days(add_months(add_days(td, 1), -shift), -1)
	elif (td.year - fd.year) * 12 + td.month - fd.month >= 1:
		# partial range spanning multiple months -> same span last year
		prev_fd = add_months(fd, -12)
		prev_td = add_months(td, -12)
	else:
		# within one (partial) month -> same days in the previous month
		prev_fd = add_months(fd, -1)
		prev_td = add_months(td, -1)

	return [
		dict(key="current", from_date=fd, to_date=td, label=period_label(fd, td)),
		dict(key="previous", from_date=prev_fd, to_date=prev_td, label=period_label(prev_fd, prev_td)),
	]


def period_label(fd, td):
	if fd.day == 1 and fd.month == 1 and td.month == 12 and td.day == 31 and fd.year == td.year:
		return str(fd.year)
	if fd == get_first_day(fd) and td == get_last_day(td) and fd.month == td.month and fd.year == td.year:
		return td.strftime("%b %Y")
	return f"{fd.strftime('%d %b %Y')} - {td.strftime('%d %b %Y')}"


def get_mapped_accounts(company):
	"""Leaf accounts of the company with their effective (category, line item)."""
	meta = frappe.get_meta("Account")
	has_fields = meta.has_field(FS_CATEGORY_FIELD) and meta.has_field(FS_SUBCATEGORY_FIELD)
	has_cf_field = meta.has_field(CF_LINE_FIELD)

	fields = ["name", "account_number", "account_name", "root_type", "account_type"]
	if has_fields:
		fields += [FS_CATEGORY_FIELD, FS_SUBCATEGORY_FIELD]
	if has_cf_field:
		fields.append(CF_LINE_FIELD)

	accounts = frappe.get_all(
		"Account", filters={"company": company, "is_group": 0}, fields=fields, order_by="account_number"
	)

	unmapped, used_fallback = [], False
	for acc in accounts:
		number = (acc.account_number or "").strip()
		cat = sub = None
		if has_fields:
			cat = (acc.get(FS_CATEGORY_FIELD) or "").strip() or None
			sub = (acc.get(FS_SUBCATEGORY_FIELD) or "").strip() or None
		if not (cat and sub):
			seed = ACCOUNT_MAPPING.get(number)
			if seed:
				cat, sub = seed
				used_fallback = True
		if cat and sub:
			acc.fs_category, acc.fs_sub_category = cat.strip(), sub.strip()
		else:
			acc.fs_category, acc.fs_sub_category = None, None
			unmapped.append(acc)

		cf = None
		if has_cf_field:
			cf = (acc.get(CF_LINE_FIELD) or "").strip() or None
		if not cf:
			cf = CF_ACCOUNT_MAPPING.get(number)
			if cf:
				used_fallback = True
		acc.cash_flow = cf

	return accounts, used_fallback, unmapped


def aggregate_balances(company, accounts, periods):
	"""GL balances per account and per (category, line item).

	- Period movement (P&L accounts, excluding Period Closing Voucher entries):
	  used for the Income Statement lines and for the Balance Sheet equity
	  section ("Current Year Income / Loss").
	- Cumulative balances (Balance Sheet accounts, closing entries included):
	  used for the Balance Sheet lines.
	"""
	pl_accounts = [a.name for a in accounts if a.fs_category in PL_CATEGORIES]
	bs_accounts = [a.name for a in accounts if a.fs_category in BS_CATEGORIES]
	account_map = {a.name: a for a in accounts}

	data = {
		"sub_period": {p["key"]: {} for p in periods},
		"sub_cumul": {p["key"]: {} for p in periods},
		"acc_period": {p["key"]: {} for p in periods},
		"acc_cumul": {p["key"]: {} for p in periods},
	}

	for period in periods:
		key = period["key"]

		for name, value in get_gl_by_account(company, pl_accounts, period, cumulative=False).items():
			data["acc_period"][key][name] = value
			acc = account_map.get(name)
			if acc and acc.fs_category:
				k = (acc.fs_category, acc.fs_sub_category)
				data["sub_period"][key][k] = data["sub_period"][key].get(k, 0) + value

		for name, value in get_gl_by_account(company, bs_accounts, period, cumulative=True).items():
			data["acc_cumul"][key][name] = value
			acc = account_map.get(name)
			if acc and acc.fs_category:
				k = (acc.fs_category, acc.fs_sub_category)
				data["sub_cumul"][key][k] = data["sub_cumul"][key].get(k, 0) + value

	return data


def get_gl_by_account(company, account_names, period, cumulative):
	if not account_names:
		return {}

	conditions = ["company = %(company)s", "is_cancelled = 0", "posting_date <= %(to_date)s"]
	if not cumulative:
		conditions += ["posting_date >= %(from_date)s", "voucher_type != 'Period Closing Voucher'"]

	result = frappe.db.sql(
		f"""
		select account, sum(debit - credit) as balance
		from `tabGL Entry`
		where {' and '.join(conditions)}
			and account in %(accounts)s
		group by account
		""",
		{
			"company": company,
			"from_date": period["from_date"],
			"to_date": period["to_date"],
			"accounts": tuple(account_names),
		},
	)
	return {r[0]: flt(r[1]) for r in result}


def get_cost_centers(company):
	"""Leaf cost centers of the company as column descriptors (tree order)."""
	ccs = frappe.get_all(
		"Cost Center",
		filters={"company": company, "is_group": 0, "disabled": 0},
		fields=["name", "cost_center_name"],
		order_by="lft",
	)
	return [
		dict(name=cc.name, fieldname=f"cc_{i}", label=cc.cost_center_name or cc.name)
		for i, cc in enumerate(ccs)
	]


def aggregate_balances_by_cc(company, accounts, period, cost_centers):
	"""Same aggregates as aggregate_balances, split by cost center.

	Data dicts are keyed by the cost-center fieldnames plus "total". GL
	entries with no cost center land in "unallocated" (kept only if non-zero).
	"""
	pl_accounts = [a.name for a in accounts if a.fs_category in PL_CATEGORIES]
	bs_accounts = [a.name for a in accounts if a.fs_category in BS_CATEGORIES]
	account_map = {a.name: a for a in accounts}
	cc_of = {cc["name"]: cc["fieldname"] for cc in cost_centers}
	fields = [cc["fieldname"] for cc in cost_centers] + ["unallocated"]

	data = {
		"sub_period": {f: {} for f in fields},
		"sub_cumul": {f: {} for f in fields},
		"acc_period": {f: {} for f in fields},
		"acc_cumul": {f: {} for f in fields},
	}

	for name, cc, value in get_gl_by_account_cc(company, pl_accounts, period, cumulative=False):
		f = cc_of.get(cc) or "unallocated"
		data["acc_period"][f][name] = data["acc_period"][f].get(name, 0) + value
		acc = account_map.get(name)
		if acc and acc.fs_category:
			k = (acc.fs_category, acc.fs_sub_category)
			data["sub_period"][f][k] = data["sub_period"][f].get(k, 0) + value

	for name, cc, value in get_gl_by_account_cc(company, bs_accounts, period, cumulative=True):
		f = cc_of.get(cc) or "unallocated"
		data["acc_cumul"][f][name] = data["acc_cumul"][f].get(name, 0) + value
		acc = account_map.get(name)
		if acc and acc.fs_category:
			k = (acc.fs_category, acc.fs_sub_category)
			data["sub_cumul"][f][k] = data["sub_cumul"][f].get(k, 0) + value

	for section in data.values():
		total = {}
		for f in fields:
			for k, v in section[f].items():
				total[k] = total.get(k, 0) + v
		section["total"] = total

	return data


def get_gl_by_account_cc(company, account_names, period, cumulative):
	if not account_names:
		return []

	conditions = ["company = %(company)s", "is_cancelled = 0", "posting_date <= %(to_date)s"]
	if not cumulative:
		conditions += ["posting_date >= %(from_date)s", "voucher_type != 'Period Closing Voucher'"]

	return frappe.db.sql(
		f"""
		select account, cost_center, sum(debit - credit) as balance
		from `tabGL Entry`
		where {' and '.join(conditions)}
			and account in %(accounts)s
		group by account, cost_center
		""",
		{
			"company": company,
			"from_date": period["from_date"],
			"to_date": period["to_date"],
			"accounts": tuple(account_names),
		},
	)


def resolve_match(match, totals):
	"""Value for a layout match: ("cat", Category) or (Category, LineItem)."""
	match = tuple(match)
	if match[0] == "cat":
		return sum(v for (c, _), v in totals.items() if c == match[1])
	return totals.get(match, 0)


def build_income_statement(data, accounts, keys, filters, currency):
	values = {}

	for key in keys:
		totals = data["sub_period"].get(key, {})

		def line(*match, _totals=totals, _sign="debit"):
			return apply_sign(resolve_match(match, _totals), _sign)

		v = dict(
			sales=line("Revenue", "Sales", _sign="credit"),
			cogs=line("Cost of Goods Sold", "Cost of Goods Sold"),
			direct_expenses=line("Cost of Goods Sold", "Direct Expenses"),
			selling_marketing=line("Operating Expense", "Selling & Marketing Expenses"),
			ga=line("Operating Expense", "General & Administrative expenses"),
			other_income=line("Other Income or Loss", "Other Income / loss", _sign="credit"),
			pl_on_fa=line("Other Income or Loss", "Profit/Loss on Sale of Fixed Asset", _sign="credit"),
			depreciation=line("cat", "Non Cash Expense"),
			finance_charges=line("cat", "Finance Cost"),
			zakat=line("cat", "Zakat and Income Tax"),
		)
		v["gross_profit"] = v["sales"] - v["cogs"] - v["direct_expenses"]
		v["total_opex"] = v["selling_marketing"] + v["ga"]
		v["operating_profit"] = v["gross_profit"] - v["total_opex"]
		v["ebitda"] = v["operating_profit"] + v["other_income"] + v["pl_on_fa"]
		v["ebit"] = v["ebitda"] - v["depreciation"]
		v["net_profit"] = v["ebit"] - v["finance_charges"] - v["zakat"]
		values[key] = v

	rows = []
	for spec in INCOME_STATEMENT_LAYOUT:
		row = base_row(spec, keys, currency)
		for key in keys:
			if spec["type"] == "calc":
				row[key] = normalize(values[key][spec["key"]])
			else:
				row[key] = normalize(
					apply_sign(
						resolve_match(spec["match"], data["sub_period"].get(key, {})), spec["sign"]
					)
				)
		rows.append(row)

		if filters.get("include_details") and spec["type"] == "line":
			rows += get_detail_rows(spec, data["acc_period"], accounts, currency, keys)

	return rows


def build_balance_sheet(data, accounts, keys, filters, currency):
	values = {}

	for key in keys:
		totals = data["sub_cumul"].get(key, {})

		def section_sum(category, _totals=totals, _sign="debit"):
			raw = sum(v for (cat, _), v in _totals.items() if cat == category)
			return apply_sign(raw, _sign)

		def line(*match, _totals=totals, _sign="credit"):
			return apply_sign(resolve_match(match, _totals), _sign)

		v = dict(
			total_current_assets=section_sum("Current Assets"),
			total_non_current_assets=section_sum("Non Current Assets"),
			total_current_liabilities=section_sum("Current Liabilities", _sign="credit"),
			total_non_current_liabilities=section_sum("Non Current Liabilities", _sign="credit"),
			capital=line("Partners Equity", "Capital"),
			statutory_reserve=line("Partners Equity", "Statutory Reserve"),
			due_to_partner=line("Partners Equity", "Due to partner"),
		)
		v["total_assets"] = v["total_current_assets"] + v["total_non_current_assets"]
		v["total_liabilities"] = v["total_current_liabilities"] + v["total_non_current_liabilities"]

		# Current year profit/loss = P&L movement for the selected period
		v["cy_pl"] = -sum(data["sub_period"].get(key, {}).values())

		# Retained = residual equity: everything that is not capital / statutory
		# reserve / partner current account / current year result. Equals the
		# Retained Earnings + Current Year Profit account balances once period
		# closing vouchers are posted; absorbs unclosed prior-year profits otherwise.
		v["retained"] = (
			v["total_assets"]
			- v["total_liabilities"]
			- v["capital"]
			- v["statutory_reserve"]
			- v["due_to_partner"]
			- v["cy_pl"]
		)
		v["total_equity"] = (
			v["capital"] + v["statutory_reserve"] + v["due_to_partner"] + v["retained"] + v["cy_pl"]
		)
		v["total_liabilities_equity"] = v["total_liabilities"] + v["total_equity"]
		values[key] = v

	# line items with balances that have no dedicated row in the layout
	extra_lines = get_extra_lines(data, keys)

	rows = []
	for spec in BALANCE_SHEET_LAYOUT:
		# append unmapped line items just before their section total
		extras_here = [e for e in extra_lines if EXTRA_LINE_ANCHORS.get(e.fs_category) == spec["label"]]
		for extra in extras_here:
			rows.append(extra)
			if filters.get("include_details"):
				extra_spec = dict(
					type="line",
					match=(extra.fs_category, extra.fs_sub_category),
					sign="debit" if "Assets" in extra.fs_category else "credit",
					indent=extra.indent,
				)
				rows += get_detail_rows(extra_spec, data["acc_cumul"], accounts, currency, keys)

		row = base_row(spec, keys, currency)
		if spec["type"] == "calc":
			for key in keys:
				row[key] = normalize(values[key][spec["key"]])
		elif spec["type"] == "line":
			for key in keys:
				row[key] = normalize(
					apply_sign(
						resolve_match(spec["match"], data["sub_cumul"].get(key, {})), spec["sign"]
					)
				)
		rows.append(row)

		if filters.get("include_details") and spec["type"] == "line":
			rows += get_detail_rows(spec, data["acc_cumul"], accounts, currency, keys)

	return rows


def get_gl_flows(company, account_names, period):
	"""Sum of debits and credits per account for the period.

	Same basis as the Income Statement: cancelled entries and Period Closing
	Voucher postings excluded (opening entries included -- net income must
	match the reported P&L).
	"""
	if not account_names:
		return {}

	result = frappe.db.sql(
		"""
		select account, sum(debit) as dr, sum(credit) as cr
		from `tabGL Entry`
		where company = %(company)s
			and is_cancelled = 0
			and voucher_type != 'Period Closing Voucher'
			and posting_date >= %(from_date)s
			and posting_date <= %(to_date)s
			and account in %(accounts)s
		group by account
		""",
		{
			"company": company,
			"from_date": period["from_date"],
			"to_date": period["to_date"],
			"accounts": tuple(account_names),
		},
	)
	return {r[0]: (flt(r[1]), flt(r[2])) for r in result}


def get_cash_balance(company, cash_accounts, before_date):
	"""Cumulative debit-credit balance of the cash/bank accounts before a date."""
	if not cash_accounts:
		return 0.0
	result = frappe.db.sql(
		"""
		select sum(debit - credit)
		from `tabGL Entry`
		where company = %(company)s
			and is_cancelled = 0
			and posting_date < %(before_date)s
			and account in %(accounts)s
		""",
		{"company": company, "before_date": before_date, "accounts": tuple(cash_accounts)},
	)
	return flt(result[0][0]) if result else 0.0


def cf_source_accounts(accounts, source):
	"""Account names matching a line source spec."""
	kind = source[0]
	if kind == "cf":
		return [a.name for a in accounts if a.cash_flow == source[1]]
	if kind == "nums":
		return [a.name for a in accounts if (a.account_number or "").strip() in source[1]]
	if kind == "fs":
		exclude = source[2] if len(source) > 2 else set()
		return [
			a.name
			for a in accounts
			if (a.fs_category, a.fs_sub_category) == source[1]
			and (a.account_number or "").strip() not in exclude
		]
	return []


def cf_line_accounts(accounts, spec):
	seen, names = set(), []
	for source in spec["sources"]:
		for name in cf_source_accounts(accounts, source):
			if name not in seen:
				seen.add(name)
				names.append(name)
	return names


def cf_side_sum(flows, names, side):
	"""Aggregate (debit, credit) tuples for the given accounts per `side`."""
	if side == "debit":
		return sum(flows.get(n, (0.0, 0.0))[0] for n in names)
	if side == "credit":
		return sum(flows.get(n, (0.0, 0.0))[1] for n in names)
	return sum(flows.get(n, (0.0, 0.0))[0] - flows.get(n, (0.0, 0.0))[1] for n in names)


def build_cash_flow(company, accounts, periods, keys, filters, currency):
	# cash & equivalents = accounts mapped to the "Cash and banks" CF bucket
	# (account_type is unreliable: Suspense/AR-AP offset are typed 'Bank', and
	# Temporary Opening is fs-mapped to Cash and banks despite being Temporary)
	cash_accounts = [a.name for a in accounts if a.cash_flow == "Cash and banks"]
	pl_names = [a.name for a in accounts if a.root_type in ("Income", "Expense")]
	all_names = [a.name for a in accounts]

	# resolve the account set of every "line" spec once
	line_accounts = {
		spec["key"]: cf_line_accounts(accounts, spec)
		for spec in CASH_FLOW_LAYOUT
		if spec["type"] == "line"
	}

	flows, opening = {}, {}
	for period in periods:
		key = period["key"]
		flows[key] = get_gl_flows(company, all_names, period)
		opening[key] = get_cash_balance(company, cash_accounts, period["from_date"])

	values = {}
	for key in keys:
		flows_map = flows[key]
		v = {}
		totals = {"op": 0.0, "inv": 0.0, "fin": 0.0}
		for spec in CASH_FLOW_LAYOUT:
			if spec["type"] != "line":
				continue
			val = apply_sign(
				cf_side_sum(flows_map, line_accounts[spec["key"]], spec["side"]), spec["sign"]
			)
			v[spec["key"]] = val
			totals[spec["section"]] += val

		# period net income = P&L movement (credit-debit on Income/Expense)
		v["net_income"] = -cf_side_sum(flows_map, pl_names, "net")
		totals["op"] += v["net_income"]

		v["net_operating"] = totals["op"]
		v["net_investing"] = totals["inv"]
		v["net_financing"] = totals["fin"]

		# actual movement of the cash/bank accounts; whatever the presented
		# lines don't capture (excluded accounts, acc-dep on disposals, ...)
		# surfaces as "Other non-cash and unmapped movements" so the statement
		# always foots: opening + net change = closing = real cash balance.
		actual_change = cf_side_sum(flows_map, cash_accounts, "net")
		v["other_movements"] = actual_change - (totals["op"] + totals["inv"] + totals["fin"])
		v["net_change"] = actual_change
		v["opening_cash"] = opening[key]
		v["closing_cash"] = opening[key] + actual_change
		values[key] = v

	warn_unmapped_cf(accounts, flows[keys[0]])

	rows = []
	for spec in CASH_FLOW_LAYOUT:
		if spec.get("hide_if_zero") and all(
			abs(values[key][spec["key"]]) < 0.005 for key in keys
		):
			continue
		row = base_row(spec, keys, currency)
		if spec["type"] in ("calc", "line"):
			for key in keys:
				row[key] = normalize(values[key][spec["key"]])
		rows.append(row)

		if filters.get("include_details") and spec["type"] == "line":
			rows += get_cf_detail_rows(spec, line_accounts[spec["key"]], flows, accounts, currency, keys)

	return rows


def get_cf_detail_rows(spec, names, flows, accounts, currency, keys):
	account_map = {a.name: a for a in accounts}
	rows = []
	for name in names:
		vals = {
			key: normalize(
				apply_sign(cf_side_sum(flows[key], [name], spec["side"]), spec["sign"])
			)
			for key in keys
		}
		if all(abs(v) < 0.005 for v in vals.values()):
			continue
		acc = account_map.get(name)
		label = (
			f"{acc.account_number} - {acc.account_name}"
			if acc and acc.account_number
			else (acc.account_name if acc else name)
		)
		rows.append(
			frappe._dict(particulars=label, indent=spec.get("indent", 0) + 1, currency=currency, **vals)
		)
	return rows


def warn_unmapped_cf(accounts, flows_map):
	"""BS-root leaf accounts that moved in the period but have no cash-flow line."""
	missing = []
	for a in accounts:
		if a.root_type not in ("Asset", "Liability", "Equity"):
			continue
		if a.cash_flow:
			continue
		dr, cr = flows_map.get(a.name, (0.0, 0.0))
		if abs(dr - cr) > 0.005:
			missing.append(a.name)
	if missing:
		names = ", ".join(missing[:15])
		more = f" … and {len(missing) - 15} more" if len(missing) > 15 else ""
		frappe.msgprint(
			_(
				"The following Balance Sheet accounts moved in the period but have no "
				"<b>Cash Flow Line</b> set; their effect is reported under "
				"<i>Other non-cash and unmapped movements</i>:<br><b>{0}{1}</b>"
			).format(names, more),
			indicator="orange",
		)


def get_extra_lines(data, keys):
	"""Sub-categories with balances that have no dedicated row in the layout."""
	layout_keys = {tuple(s["match"]) for s in BALANCE_SHEET_LAYOUT if s.get("match")}
	pairs, seen = [], set()
	for key in keys:
		for (cat, sub), value in data["sub_cumul"].get(key, {}).items():
			if (cat, sub) in layout_keys or (cat, sub) in seen or cat not in EXTRA_LINE_ANCHORS:
				continue
			if abs(value) < 0.005:
				continue
			seen.add((cat, sub))
			pairs.append((cat, sub))

	extras = []
	for cat, sub in pairs:
		sign = "debit" if "Assets" in cat else "credit"
		row = frappe._dict(
			particulars=sub, indent=1, currency=None, fs_category=cat, fs_sub_category=sub
		)
		for key in keys:
			row[key] = normalize(
				apply_sign(data["sub_cumul"].get(key, {}).get((cat, sub), 0), sign)
			)
		extras.append(row)
	return extras


def get_detail_rows(spec, account_totals, accounts, currency, keys):
	match = tuple(spec["match"])
	if match[0] == "cat":
		in_line = lambda acc: acc.fs_category == match[1]
	else:
		in_line = lambda acc: (acc.fs_category, acc.fs_sub_category) == match

	rows = []
	for acc in accounts:
		if not acc.fs_category or not in_line(acc):
			continue
		vals = {
			key: normalize(apply_sign(account_totals.get(key, {}).get(acc.name, 0), spec["sign"]))
			for key in keys
		}
		if all(abs(v) < 0.005 for v in vals.values()):
			continue
		label = f"{acc.account_number} - {acc.account_name}" if acc.account_number else acc.account_name
		rows.append(
			frappe._dict(particulars=label, indent=spec.get("indent", 0) + 1, currency=currency, **vals)
		)
	return rows


def base_row(spec, keys, currency):
	row = frappe._dict(
		particulars=spec["label"],
		indent=spec.get("indent", 0),
		currency=currency,
		bold=spec.get("bold", 0),
		header=spec.get("type") == "header",
	)
	for key in keys:
		row[key] = None
	return row


def normalize(value):
	return None if value is None else flt(value) + 0.0  # + 0.0 normalizes -0.0


def apply_sign(value, sign):
	return flt(value) if sign == "debit" else -flt(value)


def get_columns(periods, cost_centers=None, keys=None):
	columns = [
		dict(label=_("Particulars"), fieldname="particulars", fieldtype="Data", width=420),
	]
	if cost_centers:
		for cc in cost_centers:
			if cc["fieldname"] in keys:
				columns.append(
					dict(
						label=cc["label"],
						fieldname=cc["fieldname"],
						fieldtype="Currency",
						options="currency",
						width=140,
					)
				)
		if "unallocated" in keys:
			columns.append(
				dict(
					label=_("Unallocated"),
					fieldname="unallocated",
					fieldtype="Currency",
					options="currency",
					width=140,
				)
			)
		columns.append(
			dict(label=_("Total"), fieldname="total", fieldtype="Currency", options="currency", width=170)
		)
	else:
		columns.append(
			dict(
				label=periods[0]["label"],
				fieldname="current",
				fieldtype="Currency",
				options="currency",
				width=170,
			)
		)
		if len(periods) > 1:
			columns.append(
				dict(
					label=periods[1]["label"],
					fieldname="previous",
					fieldtype="Currency",
					options="currency",
					width=170,
				)
			)
	columns.append(
		dict(label=_("Currency"), fieldname="currency", fieldtype="Link", options="Currency", hidden=1)
	)
	return columns


def get_report_summary(rows, statement, currency, key="current"):
	lookup = {r.particulars: r for r in rows if r.get("particulars")}
	summary = []

	def add(label, row_name, indicator=None):
		row = lookup.get(row_name)
		if not row:
			return
		value = row.get(key) or 0
		if indicator is None:
			indicator = "Green" if value >= 0 else "Red"
		summary.append(
			dict(value=flt(value), label=label, datatype="Currency", currency=currency, indicator=indicator)
		)

	if statement == "Income Statement":
		add("Total Revenue", "Sales", "Blue")
		add("EBITDA", "EBITDA", "Blue")
		add("Net Profit after Zakat & Tax", "Net Profit after Zakat & Tax")
	elif statement == "Cash Flow":
		add("Net cash from operating activities", "Net cash from operating activities", "Blue")
		add("Net change in cash", "Net cash and cash equivalent during the year")
		add("Closing cash", "Cash and cash equivalent at end of the year", "Blue")
	else:
		add("Total Assets", "TOTAL ASSETS", "Blue")
		add("Total Liabilities", "Total Liabilities", "Blue")
		add("Total Partners' Equity", "Total Partners' Equity")

	return summary


def warn_unmapped_accounts(unmapped, used_fallback):
	if used_fallback:
		frappe.msgprint(
			_(
				"Some accounts have no Financial Statement Category / Line Item set and are grouped "
				"using the seed mapping. Set the fields on the Account to override."
			),
			indicator="yellow",
		)
	if unmapped:
		names = ", ".join(a.name for a in unmapped[:15])
		more = f" … and {len(unmapped) - 15} more" if len(unmapped) > 15 else ""
		frappe.msgprint(
			_(
				"The following accounts are not mapped to a Financial Statement Category / Line Item "
				"and are excluded from this report:<br><b>{0}{1}</b><br><br>"
				"Set <b>Financial Statement Category</b> and <b>Financial Statement Line Item</b> "
				"on these accounts to include them."
			).format(names, more),
			indicator="orange",
		)
