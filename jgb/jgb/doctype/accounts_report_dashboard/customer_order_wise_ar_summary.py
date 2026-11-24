# Copyright (c) 2025, JGB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, today, date_diff, format_date, fmt_money, escape_html
from frappe.utils.pdf import get_pdf
from datetime import datetime
from collections import defaultdict

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from six import BytesIO

from jgb.jgb.doctype.accounts_report_dashboard.report_styles import *


@frappe.whitelist()
def download():
	filename = "Accounts Receivable Aging Report SO wise"
	build_xlsx_response(filename)


@frappe.whitelist()
def download_pdf():
	args = frappe.local.form_dict
	html = get_print_html(args)
	pdf = get_pdf(html)
	frappe.response["filename"] = "Accounts Receivable Aging Report SO wise.pdf"
	frappe.response["filecontent"] = pdf
	frappe.response["type"] = "binary"


def build_xlsx_response(filename):
	xlsx_file = make_xlsx(filename)
	frappe.response["filename"] = filename + ".xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"


def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
	args = frappe.local.form_dict
	if wb is None:
		wb = Workbook()
	sheet_name = sheet_name or "AR Aging SO wise"
	ws = wb.create_sheet(sheet_name, 0)
	if "Sheet" in wb.sheetnames:
		wb.remove(wb["Sheet"])

	widths = [25, 18, 18, 14, 22, 14, 14, 14, 14]
	for i, w in enumerate(widths, 1):
		ws.column_dimensions[get_column_letter(i)].width = w

	ws.append([args.get("company") or ""])
	ws.append(["Accounts Receivable Aging Report SO wise"])
	report_date = (
		format_date(args.get("to_date"))
		if args.get("to_date")
		else datetime.now().strftime("%d-%m-%Y")
	)
	ws.append(["Report Date: " + report_date])
	if args.get("customer"):
		ws.append(["Customer: " + args.get("customer")])
	else:
		ws.append([])

	currency = frappe.db.get_value('Company', args.get("company"), 'default_currency') or 'SAR'
	ws.append([f"Currency: {currency}"])

	headers = [
		"Customer",
		"Order No",
		"Invoice No",
		"Order/Invoice Date",
		"Customer LPO / Invoice Ref",
		"Credit",
		"Received",
		"Credit Note",
		"Outstanding",
	]
	ws.append(headers)

	report_data = get_data(args)
	for row in report_data:
		ws.append(row)

	num_cols = 9
	header_row_idx = 5

	# --- Title rows (rows 1-4) ---
	# Row 1 - company
	for cell in ws[1]:
		cell.font = company_font
		cell.alignment = align_center
		cell.border = border_thin
	# Row 2 - title
	for cell in ws[2]:
		cell.font = title_font
		cell.alignment = align_center
		cell.border = border_thin
	# Row 3 - report date
	for cell in ws[3]:
		cell.font = date_font
		cell.alignment = align_center
		cell.border = border_thin
	# Row 4 - customer filter or blank spacer
	for cell in ws[4]:
		cell.font = bold_font
		cell.alignment = align_center
		cell.border = border_thin

	# --- Header row (row 5) ---
	apply_header_row(ws, header_row_idx, num_cols)

	# --- Data rows ---
	data_start_row = 6
	data_end_row = data_start_row + len(report_data) - 1
	alt_row = False

	for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=num_cols):
		row_label = str(row[0].value or "")
		is_customer = row_label.startswith("CUSTOMER:")
		is_subtotal = row_label.startswith("Subtotal:")
		is_grand_total = row_label == "GRAND TOTAL"

		for i, cell in enumerate(row):
			cell.border = border_thin

			if is_customer:
				cell.font = salesperson_font
				cell.fill = salesperson_fill
				cell.alignment = align_center

			elif is_grand_total:
				cell.font = grand_total_font
				cell.fill = grand_total_fill
				cell.alignment = align_left if i < 5 else align_right
				if i >= 5:
					cell.number_format = currency_format

			elif is_subtotal:
				cell.font = subtotal_font
				cell.fill = subtotal_fill
				cell.alignment = align_left if i < 5 else align_right
				if i >= 5:
					cell.number_format = currency_format

			else:
				cell.font = data_font
				if i in [0, 1, 2, 4]:
					cell.alignment = align_left
				elif i == 3:
					cell.alignment = align_center
				else:
					cell.alignment = align_right
				if i >= 5:
					cell.number_format = currency_format
				if alt_row:
					cell.fill = alt_row_fill

		if is_customer:
			ws.merge_cells(
				start_row=row[0].row,
				start_column=1,
				end_row=row[0].row,
				end_column=num_cols,
			)
			alt_row = False
		elif is_subtotal or is_grand_total:
			ws.merge_cells(
				start_row=row[0].row,
				start_column=1,
				end_row=row[0].row,
				end_column=5,
			)
			alt_row = False
		else:
			alt_row = not alt_row

	# Merge title rows
	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
	ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
	ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=num_cols)
	ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=num_cols)

	# Row heights
	ws.row_dimensions[1].height = 22
	ws.row_dimensions[2].height = 28
	ws.row_dimensions[3].height = 20
	ws.row_dimensions[5].height = 25

	# Page setup
	setup_page(ws, orientation="landscape")

	xlsx_file = BytesIO()
	wb.save(xlsx_file)
	return xlsx_file



def get_data(args):
	company = args.get("company")
	if not company:
		frappe.throw(_("Company is required"))

	customer = args.get("customer")
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	sales_order = args.get("sales_order")
	division = args.get("division")
	account = args.get("account")

	conditions = ["company = %s", "docstatus = 1"]
	values = [company]

	if customer:
		conditions.append("customer = %s")
		values.append(customer)
	if sales_order:
		conditions.append("name = %s")
		values.append(sales_order)
	if division:
		conditions.append("custom_division = %s")
		values.append(division)
	if from_date:
		conditions.append("transaction_date >= %s")
		values.append(from_date)
	if to_date:
		conditions.append("transaction_date <= %s")
		values.append(to_date)

	so_list = frappe.db.sql(
		"""
		SELECT name, transaction_date, customer, customer_name, po_no, base_grand_total
		FROM `tabSales Order`
		WHERE {0}
		ORDER BY customer, transaction_date
		""".format(" AND ".join(conditions)),
		tuple(values),
		as_dict=True,
	)

	so_names = [so.name for so in so_list]

	invoice_map = defaultdict(list)
	all_invoice_names = set()

	if so_names:
		invoice_query = """
			SELECT sii.sales_order, si.name, si.base_grand_total, si.is_return
			FROM `tabSales Invoice` si
			INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
			WHERE (
		"""
		if frappe.db.has_column("Sales Invoice", "sales_order"):
			invoice_query += "sii.sales_order IN %s OR si.sales_order IN %s) AND si.docstatus = 1"
			invoice_params = [tuple(so_names), tuple(so_names)]
		else:
			invoice_query += "sii.sales_order IN %s) AND si.docstatus = 1"
			invoice_params = [tuple(so_names)]

		if account:
			invoice_query += " AND si.debit_to = %s"
			invoice_params.append(account)

		invoice_list = frappe.db.sql(invoice_query, tuple(invoice_params), as_dict=True)

		for inv in invoice_list:
			invoice_map[inv.sales_order].append(inv)
			all_invoice_names.add(inv.name)

		if account:
			so_list = [so for so in so_list if so.name in invoice_map]
			so_names = [so.name for so in so_list]

	standalone_list = []
	if not sales_order:
		si_conditions = ["si.company = %s", "si.docstatus = 1"]
		si_values = [company]

		if customer:
			si_conditions.append("si.customer = %s")
			si_values.append(customer)
		if division:
			si_conditions.append("si.custom_division = %s")
			si_values.append(division)
		if from_date:
			si_conditions.append("si.posting_date >= %s")
			si_values.append(from_date)
		if to_date:
			si_conditions.append("si.posting_date <= %s")
			si_values.append(to_date)
		if account:
			si_conditions.append("si.debit_to = %s")
			si_values.append(account)

		not_exists = """
			AND NOT EXISTS (
				SELECT 1 FROM `tabSales Invoice Item` sii2
				WHERE sii2.parent = si.name AND sii2.sales_order IS NOT NULL AND sii2.sales_order != ''
			)
		"""
		if frappe.db.has_column("Sales Invoice", "sales_order"):
			not_exists += " AND (si.sales_order IS NULL OR si.sales_order = '')"

		standalone_list = frappe.db.sql(
			"""
			SELECT si.name, si.customer, si.customer_name, si.posting_date, si.po_no, si.base_grand_total, si.is_return
			FROM `tabSales Invoice` si
			WHERE {0} {1}
			ORDER BY si.customer, si.posting_date
			""".format(" AND ".join(si_conditions), not_exists),
			tuple(si_values),
			as_dict=True,
		)
		for si in standalone_list:
			all_invoice_names.add(si.name)

	payment_map = defaultdict(float)
	if all_invoice_names:
		payments = frappe.db.sql(
			"""
			SELECT per.reference_name, per.allocated_amount, per.exchange_rate
			FROM `tabPayment Entry Reference` per
			INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
			WHERE per.reference_name IN %s AND pe.company = %s AND pe.docstatus = 1
			""",
			(tuple(all_invoice_names), company),
			as_dict=True,
		)
		for p in payments:
			payment_map[p.reference_name] += flt(p.allocated_amount) * (p.exchange_rate or 1)

	so_payment_map = defaultdict(float)
	if so_names:
		so_payments = frappe.db.sql(
			"""
			SELECT per.reference_name, per.allocated_amount, per.exchange_rate
			FROM `tabPayment Entry Reference` per
			INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
			WHERE per.reference_doctype = 'Sales Order' AND per.reference_name IN %s
			AND pe.company = %s AND pe.docstatus = 1
			""",
			(tuple(so_names), company),
			as_dict=True,
		)
		for p in so_payments:
			so_payment_map[p.reference_name] += flt(p.allocated_amount) * (p.exchange_rate or 1)

	grouped = defaultdict(list)

	for so in so_list:
		invs = invoice_map.get(so.name, [])
		credit_notes = 0.0
		inv_paid = 0.0

		for inv in invs:
			if inv.is_return:
				credit_notes += abs(flt(inv.base_grand_total))
			else:
				inv_paid += payment_map.get(inv.name, 0.0)

		so_paid = so_payment_map.get(so.name, 0.0)
		received = inv_paid + so_paid
		credit = flt(so.base_grand_total)
		outstanding = credit - received - credit_notes
		age = date_diff(today(), so.transaction_date) if so.transaction_date else 0

		if abs(outstanding) <= 0.01:
			continue

		grouped[so.customer].append({
			"type": "order",
			"customer_code": so.customer,
			"customer_name": so.customer_name or so.customer,
			"order_no": so.name,
			"invoice_no": "",
			"date": so.transaction_date,
			"po_no": so.po_no or "-",
			"credit": credit,
			"received": received,
			"credit_note": credit_notes,
			"outstanding": outstanding,
			"age": age,
			"a0_30": outstanding if 0 <= age <= 30 else 0,
			"a31_60": outstanding if 31 <= age <= 60 else 0,
			"a61_90": outstanding if 61 <= age <= 90 else 0,
			"a90": outstanding if age > 90 else 0,
		})

	for si in standalone_list:
		credit = flt(si.base_grand_total) if not si.is_return else 0.0
		credit_notes = abs(flt(si.base_grand_total)) if si.is_return else 0.0
		received = payment_map.get(si.name, 0.0)
		outstanding = credit - received - credit_notes
		age = date_diff(today(), si.posting_date) if si.posting_date else 0

		if abs(outstanding) <= 0.01:
			continue

		grouped[si.customer].append({
			"type": "no_order",
			"customer_code": si.customer,
			"customer_name": si.customer_name or si.customer,
			"order_no": "No Order",
			"invoice_no": si.name,
			"date": si.posting_date,
			"po_no": si.po_no or si.name,
			"credit": credit,
			"received": received,
			"credit_note": credit_notes,
			"outstanding": outstanding,
			"age": age,
			"a0_30": outstanding if 0 <= age <= 30 else 0,
			"a31_60": outstanding if 31 <= age <= 60 else 0,
			"a61_90": outstanding if 61 <= age <= 90 else 0,
			"a90": outstanding if age > 90 else 0,
		})

	data = []
	grand_credit = grand_received = grand_cn = grand_out = 0.0

	for customer_code in sorted(grouped.keys()):
		rows = grouped[customer_code]
		if not rows:
			continue
		customer_name = rows[0]["customer_name"]
		rows.sort(key=lambda x: (0 if x["type"] == "order" else 1, x["date"] or ""))
		data.append([f"CUSTOMER: {customer_code} - {customer_name}"] + [""] * 8)

		cust_credit = cust_received = cust_cn = cust_out = 0.0

		for r in rows:
			data.append([
				r["customer_code"],
				r["order_no"],
				r["invoice_no"],
				r["date"].strftime("%d-%m-%Y") if hasattr(r["date"], "strftime") else r["date"],
				r["po_no"],
				round(r["credit"], 2),
				round(r["received"], 2),
				round(r["credit_note"], 2),
				round(r["outstanding"], 2),
			])
			cust_credit += r["credit"]
			cust_received += r["received"]
			cust_cn += r["credit_note"]
			cust_out += r["outstanding"]

		data.append([
			"Subtotal:", "", "", "", "",
			round(cust_credit, 2),
			round(cust_received, 2),
			round(cust_cn, 2),
			round(cust_out, 2),
		])

		grand_credit += cust_credit
		grand_received += cust_received
		grand_cn += cust_cn
		grand_out += cust_out

	data.append([
		"GRAND TOTAL", "", "", "", "",
		round(grand_credit, 2),
		round(grand_received, 2),
		round(grand_cn, 2),
		round(grand_out, 2),
	])

	return data




def get_print_html(args):
	company = args.get("company") or ""
	customer_filter = args.get("customer") or ""
	to_date = args.get("to_date") or ""
	report_date = format_date(to_date) if to_date else datetime.now().strftime("%d-%m-%Y")

	rows = get_data(args)
	headers = [
		"Customer",
		"Order No",
		"Invoice No",
		"Order/Invoice Date",
		"Customer LPO / Invoice Ref",
		"Credit",
		"Received",
		"Credit Note",
		"Outstanding",
	]

	html_rows = []
	for row in rows:
		label = str(row[0] or "")
		if label.startswith("CUSTOMER:"):
			html_rows.append(
				'<tr><td colspan="9" class="customer-header">{0}</td></tr>'.format(escape_html(label))
			)
		elif label.startswith("Subtotal:") or label == "GRAND TOTAL":
			cells = []
			for idx, val in enumerate(row):
				if idx == 0:
					cells.append('<td colspan="5" class="subtotal-label">{0}</td>'.format(escape_html(str(val))))
				elif idx < 5:
					continue
				else:
					cells.append('<td class="text-right">{0}</td>'.format(fmt_money(val) if isinstance(val, (int, float)) else val))
			html_rows.append("<tr>" + "".join(cells) + "</tr>")
		else:
			cells = []
			for idx, val in enumerate(row):
				css = "text-center" if idx in [3] else ("text-right" if idx >= 5 else "text-left")
				if idx >= 5 and isinstance(val, (int, float)):
					val_str = fmt_money(val)
				else:
					val_str = escape_html(str(val))
				cells.append('<td class="{0}">{1}</td>'.format(css, val_str))
			html_rows.append("<tr>" + "".join(cells) + "</tr>")

	header_cells = "".join(['<th>{0}</th>'.format(h) for h in headers])
	html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
	body {{ font-family: Arial, sans-serif; font-size: 8pt; }}
	.header {{ text-align: center; margin-bottom: 10px; }}
	.header h2 {{ margin: 0; font-size: 14pt; }}
	.header p {{ margin: 2px 0; }}
	table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
	th, td {{ border: 1px solid #000; padding: 4px; }}
	th {{ background-color: #0F0F5C; color: #fff; text-align: center; }}
	.text-right {{ text-align: right; }}
	.text-center {{ text-align: center; }}
	.text-left {{ text-align: left; }}
	.customer-header {{ font-weight: bold; background-color: #E8ECF7; font-size: 10pt; }}
	.subtotal-label {{ font-weight: bold; background-color: #D9E1F2; }}
	.grand-total {{ font-weight: bold; background-color: #D3D3D3; }}
</style>
</head>
<body>
	<div class="header">
		<h2>Accounts Receivable Aging Report SO wise</h2>
		<p><strong>Company:</strong> {company}</p>
		<p><strong>Report Date:</strong> {report_date}</p>
		{customer_line}
	</div>
	<table>
		<thead><tr>{header_cells}</tr></thead>
		<tbody>{rows}</tbody>
	</table>
</body>
</html>
""".format(
		company=escape_html(company),
		report_date=escape_html(report_date),
		customer_line='<p><strong>Customer:</strong> {0}</p>'.format(escape_html(customer_filter)) if customer_filter else "",
		header_cells=header_cells,
		rows="\n".join(html_rows),
	)
	return html
