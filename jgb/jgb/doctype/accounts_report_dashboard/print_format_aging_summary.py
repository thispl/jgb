# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# Print format for "Accounts Receivable Aging Summary" report.

import frappe
from jgb.jgb.doctype.accounts_report_dashboard.print_format_helpers import build_table_html


@frappe.whitelist()
def ageing_report_summary(doc):
	import json

	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))
	if not doc.get("company"):
		frappe.throw("Kindly choose company")

	from jgb.jgb.doctype.accounts_report_dashboard.accounts_aging import accounts_aging

	data_rows = accounts_aging(frappe._dict({
		"company": doc.company,
		"customer": doc.customer,
		"to_date": doc.get("to_date")
	}))

	headers = [
		"Posting Date", "Voucher No", "Customer Code", "Customer Name",
		"Sales Engineer", "Customer LPO",
		"Invoiced", "Paid", "Credit Note", "Outstanding",
		"Age", "0-30", "31-60", "61-90", "Above 90"
	]

	widths = [
		"7%", "10%", "8%", "12%", "10%", "10%",
		"7%", "7%", "7%", "7%",
		"4%", "5%", "5%", "5%", "5%"
	]

	return build_table_html(
		headers=headers,
		widths=widths,
		data_rows=data_rows,
		text_cols=6,
		total_cols=6
	)
