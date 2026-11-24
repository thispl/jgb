# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

# Financial Statement mapping for Joint Global Business Co LLC (JGB).
# Source: "Chart of Accounts Mapping for Financial Statements.xlsx" (sheet: Chart of Accounts).
#
# The mapping is persisted on the Account doctype via two custom fields:
#   - custom_fs_category      (Financial Statement Category)
#   - custom_fs_sub_category  (Financial Statement Line Item)
# so newly created accounts can be classified directly from the Account form.
# ACCOUNT_MAPPING below is the seed data used to populate those fields and as a
# fallback by the "Financial Statements" report when a field is left blank.

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

FS_CATEGORY_FIELD = "custom_fs_category"
FS_SUBCATEGORY_FIELD = "custom_fs_sub_category"
CF_LINE_FIELD = "custom_cash_flow"

# Canonical categories (order = presentation order in the Account form dropdown)
FS_CATEGORIES = [
	"Revenue",
	"Cost of Goods Sold",
	"Operating Expense",
	"Other Income or Loss",
	"Non Cash Expense",
	"Finance Cost",
	"Zakat and Income Tax",
	"Current Assets",
	"Non Current Assets",
	"Current Liabilities",
	"Non Current Liabilities",
	"Partners Equity",
	"Retained Earnings",
]

# Valid line items per category (from the "Lists" sheet of the source workbook,
# including line items reserved for future use)
CATEGORY_SUBCATEGORIES = {
	"Revenue": ["Sales"],
	"Cost of Goods Sold": ["Cost of Goods Sold", "Direct Expenses"],
	"Operating Expense": ["Selling & Marketing Expenses", "General & Administrative expenses"],
	"Other Income or Loss": ["Other Income / loss", "Profit/Loss on Sale of Fixed Asset"],
	"Non Cash Expense": ["Depreciation", "Amortization"],
	"Finance Cost": ["Finance Charges"],
	"Zakat and Income Tax": ["Zakat and income Tax"],
	"Current Assets": [
		"Cash and banks",
		"Accounts Receivables",
		"Prepayments and Other Receivables",
		"Retention Receivables",
		"Due from Related Parties",
		"Inventory",
	],
	"Non Current Assets": [
		"Machinery & Equipments",
		"Vehicle",
		"Office Equipments",
		"Computer & Accessories",
		"Furniture & Fixtures",
		"Leasehold Improvement",
		"Capital Lease-Vehicles",
		"Electrical Equipments",
		"Other Assets",
		"Intangible Assets",
		"Fixed Asset in Transit",
	],
	"Current Liabilities": [
		"Bank Overdraft",
		"Short Term Loans",
		"Obligation against Leased Assets",
		"Accounts payable",
		"Accruals & Other payables",
		"Advance from customers",
		"Due to Related Parties",
	],
	"Non Current Liabilities": ["End of Service Benefits", "Long Term Loans"],
	"Partners Equity": ["Capital", "Statutory Reserve", "Due to partner"],
	"Retained Earnings": ["Retained Income / Loss", "Current Year Income / Loss"],
}

# account_number -> (category, sub_category)
ACCOUNT_MAPPING = {
    "1910": ("Current Assets", "Cash and banks"),
    "1002": ("Current Assets", "Cash and banks"),
    "1003": ("Current Assets", "Cash and banks"),
    "1004": ("Current Assets", "Cash and banks"),
    "1005": ("Current Assets", "Cash and banks"),
    "1006": ("Current Assets", "Cash and banks"),
    "1103": ("Current Assets", "Prepayments and Other Receivables"),
    "1101": ("Current Assets", "Accounts Receivables"),
    "1201": ("Current Assets", "Inventory"),
    "1203": ("Current Assets", "Inventory"),
    "1204": ("Current Assets", "Inventory"),
    "1305": ("Current Assets", "Due from Related Parties"),
    "1306": ("Current Assets", "Due from Related Parties"),
    "1403": ("Current Assets", "Prepayments and Other Receivables"),
    "1404": ("Current Assets", "Prepayments and Other Receivables"),
    "1405": ("Current Assets", "Prepayments and Other Receivables"),
    "1406": ("Current Assets", "Prepayments and Other Receivables"),
    "1408": ("Current Assets", "Prepayments and Other Receivables"),
    "1501": ("Current Assets", "Prepayments and Other Receivables"),
    "1502": ("Current Assets", "Prepayments and Other Receivables"),
    "1503": ("Current Assets", "Prepayments and Other Receivables"),
    "1504": ("Current Assets", "Prepayments and Other Receivables"),
    "1505": ("Current Assets", "Prepayments and Other Receivables"),
    "1506": ("Current Assets", "Prepayments and Other Receivables"),
    "1507": ("Current Assets", "Prepayments and Other Receivables"),
    "1508": ("Current Assets", "Prepayments and Other Receivables"),
    "1509": ("Current Assets", "Prepayments and Other Receivables"),
    "1510": ("Current Assets", "Prepayments and Other Receivables"),
    "1511": ("Current Assets", "Prepayments and Other Receivables"),
    "1701": ("Non Current Assets", "Machinery & Equipments"),
    "1702": ("Non Current Assets", "Vehicle"),
    "1703": ("Non Current Assets", "Office Equipments"),
    "1704": ("Non Current Assets", "Computer & Accessories"),
    "1705": ("Non Current Assets", "Furniture & Fixtures"),
    "1706": ("Non Current Assets", "Electrical Equipments"),
    "1707": ("Non Current Assets", "Other Assets"),
    "1708": ("Non Current Assets", "Leasehold Improvement"),
    "1709": ("Non Current Assets", "Capital Lease-Vehicles"),
    "1710": ("Non Current Assets", "Intangible Assets"),
    "1711": ("Non Current Assets", "Fixed Asset in Transit"),
    "1202": ("Current Assets", "Inventory"),
    "1601": ("Non Current Assets", "Machinery & Equipments"),
    "1602": ("Non Current Assets", "Vehicle"),
    "1603": ("Non Current Assets", "Office Equipments"),
    "1604": ("Non Current Assets", "Computer & Accessories"),
    "1605": ("Non Current Assets", "Furniture & Fixtures"),
    "1606": ("Non Current Assets", "Electrical Equipments"),
    "1607": ("Non Current Assets", "Other Assets"),
    "1608": ("Non Current Assets", "Leasehold Improvement"),
    "1609": ("Non Current Assets", "Capital Lease-Vehicles"),
    "1610": ("Non Current Assets", "Intangible Assets"),
    "1611": ("Non Current Assets", "Fixed Asset in Transit"),
    "1402": ("Current Assets", "Prepayments and Other Receivables"),
    "1211": ("Current Assets", "Inventory"),
    "1007": ("Current Assets", "Cash and banks"),
    "1407": ("Current Assets", "Prepayments and Other Receivables"),
    "1307": ("Current Assets", "Prepayments and Other Receivables"),
    "1106": ("Current Assets", "Prepayments and Other Receivables"),
    "1401": ("Current Assets", "Prepayments and Other Receivables"),
    "1911": ("Current Assets", "Prepayments and Other Receivables"),
    "1104": ("Current Assets", "Prepayments and Other Receivables"),
    "1205": ("Current Assets", "Inventory"),
    "1107": ("Current Assets", "Prepayments and Other Receivables"),
    "1001": ("Current Assets", "Cash and banks"),
    "1051": ("Current Assets", "Cash and banks"),
    "1052": ("Current Assets", "Cash and banks"),
    "1053": ("Current Assets", "Cash and banks"),
    "1054": ("Current Assets", "Cash and banks"),
    "1301": ("Current Assets", "Due from Related Parties"),
    "1302": ("Current Assets", "Due from Related Parties"),
    "1303": ("Current Assets", "Due from Related Parties"),
    "1304": ("Current Assets", "Due from Related Parties"),
    "1105": ("Current Assets", "Prepayments and Other Receivables"),
    "1102": ("Current Assets", "Retention Receivables"),
    "3001": ("Partners Equity", "Capital"),
    "3002": ("Partners Equity", "Statutory Reserve"),
    "3003": ("Partners Equity", "Due to partner"),
    "3004": ("Retained Earnings", "Retained Income / Loss"),
    "3005": ("Retained Earnings", "Current Year Income / Loss"),
    "2221": ("Current Liabilities", "Accruals & Other payables"),
    "2220": ("Current Liabilities", "Accruals & Other payables"),
    "2101": ("Current Liabilities", "Due to Related Parties"),
    "2102": ("Current Liabilities", "Due to Related Parties"),
    "2103": ("Current Liabilities", "Due to Related Parties"),
    "2104": ("Current Liabilities", "Due to Related Parties"),
    "2105": ("Current Liabilities", "Due to Related Parties"),
    "2106": ("Current Liabilities", "Due to Related Parties"),
    "2203": ("Current Liabilities", "Accruals & Other payables"),
    "2206": ("Current Liabilities", "Accruals & Other payables"),
    "2207": ("Current Liabilities", "Accruals & Other payables"),
    "2208": ("Current Liabilities", "Accruals & Other payables"),
    "2209": ("Current Liabilities", "Accruals & Other payables"),
    "2210": ("Current Liabilities", "Accruals & Other payables"),
    "2211": ("Current Liabilities", "Accruals & Other payables"),
    "2212": ("Current Liabilities", "Accruals & Other payables"),
    "2231": ("Current Liabilities", "Accruals & Other payables"),
    "2232": ("Current Liabilities", "Accruals & Other payables"),
    "2233": ("Current Liabilities", "Accruals & Other payables"),
    "2234": ("Current Liabilities", "Accruals & Other payables"),
    "2235": ("Current Liabilities", "Accruals & Other payables"),
    "2301": ("Current Liabilities", "Short Term Loans"),
    "2302": ("Current Liabilities", "Short Term Loans"),
    "2303": ("Non Current Liabilities", "Long Term Loans"),
    "2304": ("Non Current Liabilities", "Long Term Loans"),
    "2305": ("Non Current Liabilities", "Long Term Loans"),
    "2501": ("Current Liabilities", "Accruals & Other payables"),
    "2502": ("Current Liabilities", "Accruals & Other payables"),
    "2503": ("Current Liabilities", "Accruals & Other payables"),
    "2504": ("Current Liabilities", "Accruals & Other payables"),
    "2401": ("Current Liabilities", "Accruals & Other payables"),
    "2402": ("Current Liabilities", "Accruals & Other payables"),
    "2403": ("Current Liabilities", "Accruals & Other payables"),
    "2404": ("Current Liabilities", "Accruals & Other payables"),
    "2405": ("Current Liabilities", "Accruals & Other payables"),
    "2001": ("Current Liabilities", "Accounts payable"),
    "2002": ("Current Liabilities", "Accounts payable"),
    "2201": ("Current Liabilities", "Accruals & Other payables"),
    "2251": ("Current Liabilities", "Accruals & Other payables"),
    "2505": ("Current Liabilities", "Accruals & Other payables"),
    "2252": ("Current Liabilities", "Accruals & Other payables"),
    "2202": ("Current Liabilities", "Accruals & Other payables"),
    "2120": ("Current Liabilities", "Accruals & Other payables"),
    "2253": ("Current Liabilities", "Accruals & Other payables"),
    "2237": ("Current Liabilities", "Accruals & Other payables"),
    "2204": ("Current Liabilities", "Accruals & Other payables"),
    "2238": ("Current Liabilities", "Accruals & Other payables"),
    "2239": ("Non Current Liabilities", "End of Service Benefits"),
    "2406": ("Current Liabilities", "Accruals & Other payables"),
    "4111": ("Revenue", "Sales"),
    "4121": ("Revenue", "Sales"),
    "4001": ("Revenue", "Sales"),
    "4002": ("Revenue", "Sales"),
    "4003": ("Revenue", "Sales"),
    "4004": ("Revenue", "Sales"),
    "4101": ("Revenue", "Sales"),
    "4102": ("Revenue", "Sales"),
    "4103": ("Revenue", "Sales"),
    "4104": ("Revenue", "Sales"),
    "4011": ("Revenue", "Sales"),
    "4013": ("Revenue", "Sales"),
    "4012": ("Revenue", "Sales"),
    "4005": ("Revenue", "Sales"),
    "5212": ("Operating Expense", "General & Administrative expenses"),
    "5218": ("Operating Expense", "General & Administrative expenses"),
    "5219": ("Other Income or Loss", "Other Income / loss"),
    "5220": ("Other Income or Loss", "Other Income / loss"),
    "5101": ("Operating Expense", "General & Administrative expenses"),
    "5102": ("Operating Expense", "General & Administrative expenses"),
    "5103": ("Operating Expense", "General & Administrative expenses"),
    "5104": ("Operating Expense", "General & Administrative expenses"),
    "5105": ("Operating Expense", "General & Administrative expenses"),
    "5106": ("Operating Expense", "General & Administrative expenses"),
    "5108": ("Operating Expense", "General & Administrative expenses"),
    "5109": ("Operating Expense", "General & Administrative expenses"),
    "5952": ("Operating Expense", "General & Administrative expenses"),
    "5953": ("Operating Expense", "General & Administrative expenses"),
    "5110": ("Operating Expense", "General & Administrative expenses"),
    "5111": ("Operating Expense", "General & Administrative expenses"),
    "5112": ("Operating Expense", "General & Administrative expenses"),
    "5213": ("Non Cash Expense", "Depreciation"),
    "5803": ("Operating Expense", "General & Administrative expenses"),
    "5013": ("Cost of Goods Sold", "Direct Expenses"),
    "5043": ("Cost of Goods Sold", "Direct Expenses"),
    "5151": ("Operating Expense", "General & Administrative expenses"),
    "5152": ("Operating Expense", "General & Administrative expenses"),
    "5153": ("Operating Expense", "General & Administrative expenses"),
    "5154": ("Operating Expense", "General & Administrative expenses"),
    "5155": ("Operating Expense", "General & Administrative expenses"),
    "5156": ("Operating Expense", "General & Administrative expenses"),
    "5201": ("Operating Expense", "General & Administrative expenses"),
    "5202": ("Operating Expense", "General & Administrative expenses"),
    "5203": ("Operating Expense", "General & Administrative expenses"),
    "5251": ("Operating Expense", "General & Administrative expenses"),
    "5252": ("Operating Expense", "General & Administrative expenses"),
    "5301": ("Operating Expense", "General & Administrative expenses"),
    "5302": ("Operating Expense", "General & Administrative expenses"),
    "5351": ("Operating Expense", "General & Administrative expenses"),
    "5352": ("Operating Expense", "General & Administrative expenses"),
    "5353": ("Operating Expense", "General & Administrative expenses"),
    "5401": ("Operating Expense", "General & Administrative expenses"),
    "5402": ("Operating Expense", "General & Administrative expenses"),
    "5403": ("Operating Expense", "General & Administrative expenses"),
    "5404": ("Operating Expense", "General & Administrative expenses"),
    "5405": ("Operating Expense", "General & Administrative expenses"),
    "5406": ("Operating Expense", "General & Administrative expenses"),
    "5451": ("Operating Expense", "General & Administrative expenses"),
    "5452": ("Operating Expense", "General & Administrative expenses"),
    "5453": ("Operating Expense", "General & Administrative expenses"),
    "5454": ("Operating Expense", "General & Administrative expenses"),
    "5551": ("Operating Expense", "Selling & Marketing Expenses"),
    "5552": ("Operating Expense", "Selling & Marketing Expenses"),
    "5553": ("Operating Expense", "Selling & Marketing Expenses"),
    "5554": ("Operating Expense", "Selling & Marketing Expenses"),
    "5555": ("Operating Expense", "General & Administrative expenses"),
    "5601": ("Operating Expense", "General & Administrative expenses"),
    "5602": ("Operating Expense", "General & Administrative expenses"),
    "5603": ("Operating Expense", "General & Administrative expenses"),
    "5604": ("Zakat and Income Tax", "Zakat and income Tax"),
    "5605": ("Operating Expense", "General & Administrative expenses"),
    "5606": ("Operating Expense", "General & Administrative expenses"),
    "5651": ("Operating Expense", "General & Administrative expenses"),
    "5652": ("Operating Expense", "General & Administrative expenses"),
    "5653": ("Operating Expense", "General & Administrative expenses"),
    "5654": ("Operating Expense", "General & Administrative expenses"),
    "5655": ("Operating Expense", "General & Administrative expenses"),
    "5701": ("Operating Expense", "General & Administrative expenses"),
    "5703": ("Finance Cost", "Finance Charges"),
    "5704": ("Finance Cost", "Finance Charges"),
    "5705": ("Operating Expense", "General & Administrative expenses"),
    "5801": ("Operating Expense", "General & Administrative expenses"),
    "5802": ("Operating Expense", "General & Administrative expenses"),
    "5901": ("Non Cash Expense", "Depreciation"),
    "5902": ("Non Cash Expense", "Depreciation"),
    "5903": ("Non Cash Expense", "Depreciation"),
    "5904": ("Non Cash Expense", "Depreciation"),
    "5905": ("Non Cash Expense", "Depreciation"),
    "5906": ("Non Cash Expense", "Depreciation"),
    "5907": ("Non Cash Expense", "Depreciation"),
    "5908": ("Non Cash Expense", "Depreciation"),
    "5909": ("Non Cash Expense", "Depreciation"),
    "5910": ("Non Cash Expense", "Depreciation"),
    "5954": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5503": ("Operating Expense", "Selling & Marketing Expenses"),
    "5656": ("Operating Expense", "General & Administrative expenses"),
    "5023": ("Cost of Goods Sold", "Direct Expenses"),
    "5021": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5041": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5042": ("Cost of Goods Sold", "Direct Expenses"),
    "5011": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5012": ("Cost of Goods Sold", "Direct Expenses"),
    "5097": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5095": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5094": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5093": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5407": ("Operating Expense", "General & Administrative expenses"),
    "5204": ("Operating Expense", "General & Administrative expenses"),
    "5014": ("Cost of Goods Sold", "Direct Expenses"),
    "5016": ("Cost of Goods Sold", "Direct Expenses"),
    "5015": ("Cost of Goods Sold", "Direct Expenses"),
    "5158": ("Operating Expense", "General & Administrative expenses"),
    "5502": ("Operating Expense", "Selling & Marketing Expenses"),
    "5408": ("Operating Expense", "General & Administrative expenses"),
    "5303": ("Operating Expense", "General & Administrative expenses"),
    "5096": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5702": ("Finance Cost", "Finance Charges"),
    "5107": ("Operating Expense", "General & Administrative expenses"),
    "5157": ("Operating Expense", "General & Administrative expenses"),
    "5022": ("Cost of Goods Sold", "Direct Expenses"),
    "5501": ("Operating Expense", "Selling & Marketing Expenses"),
    "5031": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5032": ("Cost of Goods Sold", "Direct Expenses"),
    "5033": ("Cost of Goods Sold", "Direct Expenses"),
    "5051": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5052": ("Cost of Goods Sold", "Direct Expenses"),
    "5053": ("Cost of Goods Sold", "Direct Expenses"),
    "5092": ("Cost of Goods Sold", "Direct Expenses"),
    "5091": ("Cost of Goods Sold", "Cost of Goods Sold"),
    "5024": ("Cost of Goods Sold", "Direct Expenses"),
}
# ---------------------------------------------------------------------------
# Cash Flow mapping (statement = "Cash Flow" in the Financial Statements report)
# Source: "Cash Flow.xlsx" (sheet: cash flow classification).
#
# Persisted on the Account doctype via the custom_cash_flow Select field
# (options = CF_LINES). CF_ACCOUNT_MAPPING is the seed/fallback, keyed by
# account_number. Buckets that have no account yet are kept as options so
# future accounts can be mapped without code changes.
# ---------------------------------------------------------------------------

CF_LINES = [
	"Cash and banks",
	"Change in inventory",
	"Change in trade receivables",
	"Change in prepayments and other receivables",
	"Change in financial assets",
	"Change in trade payables",
	"Change in due from related parties",
	"Change in due to related parties",
	"Change in accrued and other liabilities",
	"Provision For GOSI",
	"Provision For Leave Pay",
	"Provision For Air Fare",
	"Provision for zakat",
	"Employees' end of service benefits",
	"Zakat paid",
	"Employees' end of service benefits paid",
	"Property and equipment",
	"Intangible assets",
	"Property investment",
	"Investment",
	"Shareholder current account",
	"Issuance of capital",
	"Dividend paid",
	"Additional contribution",
	"Capital",
	"Short-Term Loan",
	"Current Portion Long-Term Debt",
	"Long Term Debt-Noncurrent",
	"Loan - Others",
	"Lease to Own Vehicles",
	"Excluded (non-cash)",
]

# account_number -> cash flow line (from the classification sheet; the sheet's
# combined "purchase and disposal of asset -investing activity" bucket is split
# into "Property and equipment" / "Intangible assets", and accumulated
# depreciation + pure-equity-transfer accounts are marked "Excluded (non-cash)")
CF_ACCOUNT_MAPPING = {
	"1001": "Cash and banks",
	"1002": "Cash and banks",
	"1003": "Cash and banks",
	"1004": "Cash and banks",
	"1005": "Cash and banks",
	"1006": "Cash and banks",
	"1007": "Cash and banks",
	"1051": "Cash and banks",
	"1052": "Cash and banks",
	"1053": "Cash and banks",
	"1054": "Cash and banks",
	"1101": "Change in trade receivables",
	"1102": "Change in trade receivables",
	"1103": "Change in trade receivables",
	"1107": "Change in trade receivables",
	"1201": "Change in inventory",
	"1202": "Change in inventory",
	"1203": "Change in inventory",
	"1204": "Change in inventory",
	"1205": "Change in inventory",
	"1211": "Change in inventory",
	"1301": "Change in due from related parties",
	"1302": "Change in due from related parties",
	"1303": "Change in due from related parties",
	"1304": "Change in due from related parties",
	"1305": "Change in due from related parties",
	"1306": "Change in due from related parties",
	"1401": "Change in prepayments and other receivables",
	"1402": "Change in prepayments and other receivables",
	"1403": "Change in prepayments and other receivables",
	"1404": "Change in prepayments and other receivables",
	"1405": "Change in prepayments and other receivables",
	"1406": "Change in prepayments and other receivables",
	"1407": "Change in prepayments and other receivables",
	"1408": "Change in prepayments and other receivables",
	"1501": "Change in prepayments and other receivables",
	"1502": "Change in prepayments and other receivables",
	"1503": "Change in prepayments and other receivables",
	"1504": "Change in prepayments and other receivables",
	"1505": "Change in prepayments and other receivables",
	"1506": "Change in prepayments and other receivables",
	"1507": "Change in prepayments and other receivables",
	"1508": "Change in prepayments and other receivables",
	"1509": "Change in prepayments and other receivables",
	"1510": "Change in prepayments and other receivables",
	"1511": "Change in prepayments and other receivables",
	"1911": "Change in prepayments and other receivables",
	"1104": "Change in prepayments and other receivables",
	"1105": "Change in prepayments and other receivables",
	"1106": "Change in prepayments and other receivables",
	"1307": "Change in prepayments and other receivables",
	"1601": "Property and equipment",
	"1602": "Property and equipment",
	"1603": "Property and equipment",
	"1604": "Property and equipment",
	"1605": "Property and equipment",
	"1606": "Property and equipment",
	"1607": "Property and equipment",
	"1608": "Property and equipment",
	"1609": "Property and equipment",
	"1610": "Intangible assets",
	"1611": "Property and equipment",
	"1701": "Excluded (non-cash)",
	"1702": "Excluded (non-cash)",
	"1703": "Excluded (non-cash)",
	"1704": "Excluded (non-cash)",
	"1705": "Excluded (non-cash)",
	"1706": "Excluded (non-cash)",
	"1707": "Excluded (non-cash)",
	"1708": "Excluded (non-cash)",
	"1709": "Excluded (non-cash)",
	"1710": "Excluded (non-cash)",
	"1711": "Excluded (non-cash)",
	"1910": "Excluded (non-cash)",
	"2001": "Change in trade payables",
	"2002": "Change in trade payables",
	"2101": "Change in due to related parties",
	"2102": "Change in due to related parties",
	"2103": "Change in due to related parties",
	"2104": "Change in due to related parties",
	"2105": "Change in due to related parties",
	"2106": "Change in due to related parties",
	"2201": "Change in accrued and other liabilities",
	"2202": "Change in accrued and other liabilities",
	"2203": "Change in accrued and other liabilities",
	"2204": "Change in accrued and other liabilities",
	"2206": "Change in accrued and other liabilities",
	"2207": "Change in accrued and other liabilities",
	"2208": "Change in accrued and other liabilities",
	"2209": "Change in accrued and other liabilities",
	"2210": "Change in accrued and other liabilities",
	"2211": "Change in accrued and other liabilities",
	"2212": "Change in accrued and other liabilities",
	"2220": "Change in accrued and other liabilities",
	"2221": "Change in accrued and other liabilities",
	"2237": "Change in accrued and other liabilities",
	"2238": "Change in accrued and other liabilities",
	"2251": "Change in accrued and other liabilities",
	"2252": "Change in accrued and other liabilities",
	"2253": "Change in accrued and other liabilities",
	"2120": "Change in accrued and other liabilities",
	"2401": "Change in accrued and other liabilities",
	"2402": "Change in accrued and other liabilities",
	"2403": "Change in accrued and other liabilities",
	"2404": "Change in accrued and other liabilities",
	"2405": "Change in accrued and other liabilities",
	"2406": "Change in accrued and other liabilities",
	"2501": "Change in accrued and other liabilities",
	"2502": "Change in accrued and other liabilities",
	"2503": "Change in accrued and other liabilities",
	"2504": "Change in accrued and other liabilities",
	"2505": "Change in accrued and other liabilities",
	"2231": "Provision For GOSI",
	"2232": "Provision For Leave Pay",
	"2233": "Provision For Air Fare",
	"2234": "Provision for zakat",
	"2235": "Employees' end of service benefits",
	"2239": "Employees' end of service benefits paid",
	"2301": "Short-Term Loan",
	"2302": "Current Portion Long-Term Debt",
	"2303": "Long Term Debt-Noncurrent",
	"2304": "Loan - Others",
	"2305": "Lease to Own Vehicles",
	"3001": "Issuance of capital",
	"3002": "Excluded (non-cash)",
	"3003": "Shareholder current account",
	"3004": "Excluded (non-cash)",
	"3005": "Excluded (non-cash)",
}


ALL_SUBCATEGORIES = []
for _subs in CATEGORY_SUBCATEGORIES.values():
	for _sub in _subs:
		if _sub not in ALL_SUBCATEGORIES:
			ALL_SUBCATEGORIES.append(_sub)

# Line items defined in the mapping workbook ("Lists" sheet) that no account uses
# yet; kept as dropdown options so future accounts can be mapped to them
RESERVED_SUBCATEGORIES = [
	"Profit/Loss on Sale of Fixed Asset",
	"Amortization",
	"Bank Overdraft",
	"Obligation against Leased Assets",
	"Advance from customers",
]
for _sub in RESERVED_SUBCATEGORIES:
	if _sub not in ALL_SUBCATEGORIES:
		ALL_SUBCATEGORIES.append(_sub)


def create_fs_custom_fields():
	"""Create the mapping fields on the Account doctype (idempotent)."""
	create_custom_fields(
		{
			"Account": [
				dict(
					fieldname=FS_CATEGORY_FIELD,
					label="Financial Statement Category",
					fieldtype="Select",
					options="\n".join(FS_CATEGORIES),
					insert_after="account_type",
					print_hide=1,
					read_only=0,
					in_standard_filter=1,
					allow_on_submit=0,
					description="Used by the 'Financial Statements' report to group accounts",
				),
				dict(
					fieldname=FS_SUBCATEGORY_FIELD,
					label="Financial Statement Line Item",
					fieldtype="Select",
					options="\n".join(ALL_SUBCATEGORIES),
					insert_after=FS_CATEGORY_FIELD,
					print_hide=1,
					read_only=0,
					in_standard_filter=1,
					allow_on_submit=0,
					description="Statement line item this account is presented under",
				),
				dict(
					fieldname=CF_LINE_FIELD,
					label="Cash Flow Line",
					fieldtype="Select",
					options="\n".join(CF_LINES),
					insert_after=FS_SUBCATEGORY_FIELD,
					print_hide=1,
					read_only=0,
					in_standard_filter=1,
					allow_on_submit=0,
					description="Cash Flow Statement line this account feeds (statement = Cash Flow)",
				),
			]
		},
		update=True,
	)


def populate_account_fs_mapping(company=None):
	"""Seed custom_fs_category / custom_fs_sub_category on accounts from ACCOUNT_MAPPING.

	Matches accounts by account_number. Returns a summary dict.
	"""
	if not frappe.db.exists("DocType", "Account"):
		return {}

	meta = frappe.get_meta("Account")
	if not meta.has_field(FS_CATEGORY_FIELD):
		create_fs_custom_fields()

	accounts = frappe.get_all(
		"Account",
		filters={"is_group": 0, "company": company} if company else {"is_group": 0},
		fields=["name", "account_number"],
	)

	updated, unmapped, unknown_numbers = 0, [], []
	for acc in accounts:
		number = (acc.account_number or "").strip()
		entry = ACCOUNT_MAPPING.get(number)
		if not entry:
			if number:
				unknown_numbers.append(number)
			continue
		frappe.db.set_value(
			"Account",
			acc.name,
			{FS_CATEGORY_FIELD: entry[0], FS_SUBCATEGORY_FIELD: entry[1]},
			update_modified=False,
		)
		updated += 1

	mapped_numbers = set(ACCOUNT_MAPPING)
	site_numbers = {(a.account_number or "").strip() for a in accounts}
	missing_on_site = sorted(mapped_numbers - site_numbers)

	return {
		"company": company,
		"accounts_found": len(accounts),
		"accounts_updated": updated,
		"site_accounts_not_in_mapping": sorted(n for n in unknown_numbers if n not in mapped_numbers),
		"mapping_codes_not_on_site": missing_on_site,
	}


def populate_account_cf_mapping(company=None):
	"""Seed custom_cash_flow on accounts from CF_ACCOUNT_MAPPING (idempotent).

	Matches accounts by account_number. Returns a summary dict.
	"""
	if not frappe.db.exists("DocType", "Account"):
		return {}

	meta = frappe.get_meta("Account")
	if not meta.has_field(CF_LINE_FIELD):
		create_fs_custom_fields()

	accounts = frappe.get_all(
		"Account",
		filters={"is_group": 0, "company": company} if company else {"is_group": 0},
		fields=["name", "account_number"],
	)

	updated, unknown_numbers = 0, []
	for acc in accounts:
		number = (acc.account_number or "").strip()
		entry = CF_ACCOUNT_MAPPING.get(number)
		if not entry:
			if number:
				unknown_numbers.append(number)
			continue
		frappe.db.set_value("Account", acc.name, CF_LINE_FIELD, entry, update_modified=False)
		updated += 1

	return {
		"company": company,
		"accounts_found": len(accounts),
		"accounts_updated": updated,
		"site_accounts_not_in_mapping": sorted(unknown_numbers),
	}
