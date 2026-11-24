# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# Print format for "Advance Received From Customer" report.

import frappe
from jgb.jgb.doctype.accounts_report_dashboard.print_format_helpers import build_table_html


@frappe.whitelist()
def ageing_report_summary_advance_received(doc):
	import json
	from frappe.utils import cstr

	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))
	if not doc.get("company"):
		frappe.throw("Kindly choose Company")

	from jgb.jgb.doctype.accounts_report_dashboard.advance_received_from_customer import customer_advances_aging

	filters = frappe._dict({
		"company": doc.company,
		"customer": doc.get("customer"),
		"to_date": doc.get("to_date")
	})

	data_rows = customer_advances_aging(filters)

	headers = [
		"Posting Date", "Voucher No", "Sales Engineer", "Reference / Remarks",
		"Advance Received", "Allocated Amount", "Credit Note", "Unallocated Amount",
		"Age (Days)", "0-30", "31-60", "61-90", "Above 90"
	]

	widths = [
		"9%", "12%", "12%", "15%",
		"8%", "8%", "8%", "8%",
		"5%", "5%", "5%", "5%", "8%"
	]

	return build_table_html(
		headers=headers,
		widths=widths,
		data_rows=data_rows,
		text_cols=4,
		total_cols=4
	)
