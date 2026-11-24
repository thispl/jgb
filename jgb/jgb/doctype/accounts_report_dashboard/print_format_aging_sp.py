# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# Print format for "Accounts Receivable Aging Summary by Sales Person" report.
# Uses inline styles for maximum wkhtmltopdf compatibility.
# Combines Customer Code and Customer Name into a single column to save width.

import frappe
from jgb.jgb.doctype.accounts_report_dashboard.print_format_helpers import (
	fmt_currency, esc,
)


@frappe.whitelist()
def ageing_report_summary_sales_person(doc):
	import json

	try:
		if isinstance(doc, str):
			doc = frappe._dict(json.loads(doc))

		if not doc.get("company"):
			frappe.throw("Kindly choose company")

		from jgb.jgb.doctype.accounts_report_dashboard.aging_report_summary_sales_person import accounts_aging as accounts_aging_sales_person

		args = frappe._dict({
			"company": doc.get("company"),
			"sales_person": doc.get("sales_person") or None,
			"region": doc.get("region") or None,
			"to_date": doc.get("to_date") or None
		})

		raw_rows = accounts_aging_sales_person(args) or []

		# --- Transform 14-col data into 13-col by merging Customer Code + Name ---
		data_rows = []
		for row in raw_rows:
			if not row:
				continue
			row_str = str(row[0])

			if row_str.startswith("SALESPERSON:"):
				data_rows.append([row_str] + [''] * 12)
			elif row_str.startswith("Subtotal:") or row_str == "GRAND TOTAL":
				new_row = [row_str]
				new_row += ['', '', '']
				new_row += list(row[5:])
				data_rows.append(new_row)
			else:
				customer_cell = f"{row[2]} : {row[3]}" if row[2] else str(row[3])
				new_row = [
					row[0], row[1], customer_cell, row[4],
					row[5], row[6], row[7], row[8], row[9],
					row[10], row[11], row[12], row[13],
				]
				data_rows.append(new_row)

		headers = [
			"Posting Date", "Voucher No", "Customer", "Customer LPO",
			"Invoiced", "Paid", "Credit Note", "Outstanding", "Age",
			"0-30", "31-60", "61-90", "Above 90"
		]
		# Percentage widths - WeasyPrint handles these correctly
		col_widths = [
			"6%", "10%", "16%", "8%",
			"7%", "7%", "7%", "8%", "3%",
			"7%", "7%", "7%", "7%"
		]

		num_cols = 13
		text_cols = 4
		total_cols = 4

		tbl_style = (
			"width:100%; border-collapse:collapse; "
			"font-family:'Calibri',Arial,sans-serif; font-size:9px; "
			"table-layout:fixed;"
		)
		th_style = (
			"background:#1F3864; color:#FFFFFF; font-weight:bold; "
			"text-align:center; padding:6px 2px; border:1px solid #1F3864; "
			"font-size:10px; word-wrap:break-word; overflow-wrap:break-word;"
		)
		td_base = (
			"padding:3px 2px; border:1px solid #D0D0D0; "
			"word-wrap:break-word; overflow-wrap:break-word;"
		)
		td_left = td_base + " text-align:left;"
		td_right = td_base + " text-align:right; font-variant-numeric:tabular-nums;"

		td_sp = (
			"background:#4472C4; color:#FFFFFF; font-weight:bold; "
			"font-size:12px; text-align:center; padding:8px; "
			"border:1px solid #4472C4;"
		)
		# Customer subtotal - lighter shade (light blue)
		td_csub_l = (
			"background:#E9EEF7; color:#1F3864; font-weight:bold; "
			"font-size:9px; padding:3px 2px; border:1px solid #B4C6E7; text-align:left;"
		)
		td_csub_r = (
			"background:#E9EEF7; color:#1F3864; font-weight:bold; "
			"font-size:9px; padding:3px 2px; border:1px solid #B4C6E7; "
			"text-align:right; font-variant-numeric:tabular-nums;"
		)
		# Sales person subtotal - medium shade (light blue)
		td_sub_l = (
			"background:#D9E1F2; color:#1F3864; font-weight:bold; "
			"font-size:10px; padding:4px 2px; border:1px solid #D0D0D0; text-align:left;"
		)
		td_sub_r = (
			"background:#D9E1F2; color:#1F3864; font-weight:bold; "
			"font-size:10px; padding:4px 2px; border:1px solid #D0D0D0; "
			"text-align:right; font-variant-numeric:tabular-nums;"
		)
		td_gt_l = (
			"background:#1F3864; color:#FFFFFF; font-weight:bold; "
			"font-size:11px; padding:4px 2px; border:1px solid #1F3864; text-align:left;"
		)
		td_gt_r = (
			"background:#1F3864; color:#FFFFFF; font-weight:bold; "
			"font-size:11px; padding:4px 2px; border:1px solid #1F3864; "
			"text-align:right; font-variant-numeric:tabular-nums;"
		)
		alt_bg = "background:#F7F9FC;"

		html_output = f"<table style='{tbl_style}'>"
		html_output += "<thead><tr>"
		for i, head in enumerate(headers):
			html_output += f"<th style='{th_style} width:{col_widths[i]};'>{esc(head)}</th>"
		html_output += "</tr></thead><tbody>"

		alt_row = False
		for row in data_rows:
			if not row:
				continue
			row_str = str(row[0])

			# Salesperson heading
			if row_str.startswith("SALESPERSON:"):
				label = row_str.replace("SALESPERSON:", "").strip()
				html_output += f"<tr><td colspan='{num_cols}' style='{td_sp}'>{esc(label)}</td></tr>"
				alt_row = False
				continue

			# Grand Total
			if row_str == "GRAND TOTAL":
				html_output += f"<tr><td colspan='{total_cols}' style='{td_gt_l}'>{esc(row_str)}</td>"
				for cell in row[total_cols:]:
					html_output += f"<td style='{td_gt_r}'>{esc(fmt_currency(cell))}</td>"
				html_output += "</tr>"
				alt_row = False
				continue

			# Customer Subtotal (lighter shade)
			if row_str.startswith("Customer Subtotal:"):
				html_output += f"<tr><td colspan='{total_cols}' style='{td_csub_l}'>{esc(row_str)}</td>"
				for cell in row[total_cols:]:
					html_output += f"<td style='{td_csub_r}'>{esc(fmt_currency(cell))}</td>"
				html_output += "</tr>"
				alt_row = False
				continue

			# Sales Person Subtotal
			if row_str.startswith("Subtotal:"):
				html_output += f"<tr><td colspan='{total_cols}' style='{td_sub_l}'>{esc(row_str)}</td>"
				for cell in row[total_cols:]:
					html_output += f"<td style='{td_sub_r}'>{esc(fmt_currency(cell))}</td>"
				html_output += "</tr>"
				alt_row = False
				continue

			# Regular data row
			row_bg = f" style='{alt_bg}'" if alt_row else ""
			html_output += f"<tr{row_bg}>"
			for i, cell in enumerate(row):
				if i < text_cols:
					html_output += f"<td style='{td_left}'>{esc(cell)}</td>"
				else:
					html_output += f"<td style='{td_right}'>{esc(fmt_currency(cell))}</td>"
			html_output += "</tr>"
			alt_row = not alt_row

		html_output += "</tbody></table>"
		return html_output

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Ageing Report Sales Person Print Format Error")
		frappe.throw(f"Report Error: {str(e)}")
