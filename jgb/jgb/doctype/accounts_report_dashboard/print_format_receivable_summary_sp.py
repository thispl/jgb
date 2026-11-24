# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# Print format for "Accounts Receivable Summary by Sales Person" report.

import frappe
from jgb.jgb.doctype.accounts_report_dashboard.print_format_helpers import build_table_html


@frappe.whitelist()
def receivable_summary_salesperson(doc):
	import json

	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))
	if not doc.get("company"):
		frappe.throw("Kindly choose company")

	from jgb.jgb.doctype.accounts_report_dashboard.receivable_summary_salesperson import accounts_receivable_summary

	args = frappe._dict({
		"company": doc.get("company"),
		"sales_person": doc.get("sales_person") or None,
		"region": doc.get("region") or None,
		"to_date": doc.get("to_date") or None
	})

	data_rows = accounts_receivable_summary(args) or []

	headers = [
		"Customer Code", "Customer Name",
		"Invoiced", "Paid", "Credit Note", "Outstanding"
	]

	widths = ["15%", "30%", "15%", "15%", "15%", "15%"]

	return build_table_html(
		headers=headers,
		widths=widths,
		data_rows=data_rows,
		text_cols=2,
		total_cols=2
	)
