
# Copyright (c) 2025, JGB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, today, date_diff, format_date, fmt_money, escape_html, getdate
from frappe.utils.pdf import get_pdf
from datetime import datetime

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from six import BytesIO

from jgb.jgb.doctype.accounts_report_dashboard.accounts_payable_aging_report_po_wise import (
	get_data as get_aging_data,
)


@frappe.whitelist()
def download():
	filename = "Accounts Payable Summary"
	build_xlsx_response(filename)


@frappe.whitelist()
def download_pdf():
	args = frappe.local.form_dict
	html = get_print_html(args)
	pdf = get_pdf(html)
	frappe.response["filename"] = "Accounts Payable Summary.pdf"
	frappe.response["filecontent"] = pdf
	frappe.response["type"] = "binary"


def build_xlsx_response(filename):
	xlsx_file = make_xlsx(filename)
	frappe.response["filename"] = filename + ".xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"


def _row_type(row):
	if not row:
		return ""
	label = str(row[0] or "")
	if label.startswith("SUPPLIER:"):
		return "supplier_header"
	if label.startswith("Subtotal:"):
		return "subtotal"
	if label == "GRAND TOTAL":
		return "grand_total"
	po_no = row[1] or ""
	ref = row[3] or ""
	if po_no == "No Order":
		return "no_order"
	if po_no and po_no == ref:
		return "order"
	return "invoice"


def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
	args = frappe.local.form_dict
	if wb is None:
		wb = Workbook()
	sheet_name = sheet_name or "Accounts Payable Summary"
	ws = wb.create_sheet(sheet_name, 0)
	if "Sheet" in wb.sheetnames:
		wb.remove(wb["Sheet"])

	widths = [14, 18, 24, 24, 14, 14, 14, 14, 12, 12, 12, 12, 12]
	for i, w in enumerate(widths, 1):
		ws.column_dimensions[get_column_letter(i)].width = w

	ws.append([args.get("company") or ""])
	ws.append(["Accounts Payable Summary"])
	report_date = (
		format_date(args.get("to_date"))
		if args.get("to_date")
		else datetime.now().strftime("%d-%m-%Y")
	)
	ws.append(["Report Date: " + report_date])
	if args.get("supplier"):
		ws.append(["Supplier: " + args.get("supplier")])
	elif args.get("division"):
		ws.append(["Division: " + args.get("division")])

	currency = args.get('currency') or frappe.db.get_value('Company', args.get("company"), 'default_currency') or 'SAR'
	ws.append([f'Currency: {currency}'])

	headers = [
		"Posting Date",
		"PO No",
		"Purchase Invoice Number",
		"Supplier LPO / Invoice Ref",
		"Invoiced",
		"Paid",
		"Return",
		"Outstanding",
		"Age(Days)",
		"0-30",
		"31-60",
		"61-90",
		"Above 90",
	]
	ws.append(headers)

	report_data = get_data(args)
	for row in report_data:
		ws.append(row)

	align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
	align_right = Alignment(horizontal="right", vertical="bottom", wrap_text=True)
	align_left = Alignment(horizontal="left", vertical="bottom", wrap_text=True)
	header_fill = PatternFill(start_color="0F0F5C", end_color="0F0F5C", fill_type="solid")
	header_font = Font(bold=True, color="FFFFFF")
	title_font = Font(bold=True, size=14)
	supplier_fill = PatternFill(start_color="E8ECF7", end_color="E8ECF7", fill_type="solid")
	subtotal_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
	grand_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
	no_order_fill = PatternFill(start_color="FFF9E6", end_color="FFF9E6", fill_type="solid")
	invoice_fill = PatternFill(start_color="E6F2FF", end_color="E6F2FF", fill_type="solid")
	bold_font = Font(bold=True)
	border_thin = Border(
		left=Side(style="thin"),
		right=Side(style="thin"),
		top=Side(style="thin"),
		bottom=Side(style="thin"),
	)

	for row in ws.iter_rows(min_row=1, max_row=4, min_col=1, max_col=13):
		for cell in row:
			cell.font = title_font if cell.row == 2 else bold_font
			cell.alignment = align_center
			cell.border = border_thin

	header_row_idx = 5
	for cell in ws[header_row_idx]:
		cell.font = header_font
		cell.fill = header_fill
		cell.alignment = align_center
		cell.border = border_thin

	data_start_row = 6
	data_end_row = data_start_row + len(report_data) - 1
	for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=13):
		values = [c.value for c in row]
		rt = _row_type(values)

		if rt == "supplier_header":
			for cell in row:
				cell.border = border_thin
				cell.font = bold_font
				cell.fill = supplier_fill
				cell.alignment = align_left
			ws.merge_cells(
				start_row=row[0].row,
				start_column=1,
				end_row=row[0].row,
				end_column=13,
			)
		elif rt == "subtotal":
			for i, cell in enumerate(row):
				cell.border = border_thin
				cell.font = bold_font
				cell.fill = subtotal_fill
				cell.alignment = align_left if i in [0, 1, 2, 3] else align_right
			ws.merge_cells(
				start_row=row[0].row,
				start_column=1,
				end_row=row[0].row,
				end_column=4,
			)
		elif rt == "grand_total":
			for i, cell in enumerate(row):
				cell.border = border_thin
				cell.font = bold_font
				cell.fill = grand_fill
				cell.alignment = align_left if i in [0, 1, 2, 3] else align_right
			ws.merge_cells(
				start_row=row[0].row,
				start_column=1,
				end_row=row[0].row,
				end_column=4,
			)
		else:
			fill = None
			if rt == "no_order":
				fill = no_order_fill
			elif rt == "invoice":
				fill = invoice_fill
			for i, cell in enumerate(row):
				cell.border = border_thin
				if fill:
					cell.fill = fill
				cell.alignment = align_left if i in [0, 1, 2, 3] else (align_center if i == 8 else align_right)

	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=13)
	ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=13)
	ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=13)
	ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=13)
	ws.page_setup.orientation = "landscape"

	xlsx_file = BytesIO()
	wb.save(xlsx_file)
	return xlsx_file


def get_data(args):
	company = args.get("company")
	if not company:
		frappe.throw(_("Company is required"))

	report_date = getdate(args.get("to_date") or today())
	raw_rows = get_aging_data(args)
	data = []

	subtotal = {
		"invoiced": 0.0,
		"paid": 0.0,
		"return": 0.0,
		"outstanding": 0.0,
		"0_30": 0.0,
		"31_60": 0.0,
		"61_90": 0.0,
		"above_90": 0.0,
	}
	grand = {
		"invoiced": 0.0,
		"paid": 0.0,
		"return": 0.0,
		"outstanding": 0.0,
		"0_30": 0.0,
		"31_60": 0.0,
		"61_90": 0.0,
		"above_90": 0.0,
	}

	current_supplier_name = ""

	def append_subtotal():
		nonlocal current_supplier_name, subtotal, grand
		if current_supplier_name:
			data.append([
				"Subtotal: {0}".format(current_supplier_name),
				"",
				"",
				"",
				round(subtotal["invoiced"], 2),
				round(subtotal["paid"], 2),
				round(subtotal["return"], 2),
				round(subtotal["outstanding"], 2),
				"",
				round(subtotal["0_30"], 2),
				round(subtotal["31_60"], 2),
				round(subtotal["61_90"], 2),
				round(subtotal["above_90"], 2),
			])
			for k in grand:
				grand[k] += subtotal[k]

	for row in raw_rows:
		if not row:
			continue
		label = str(row[0] or "")

		if label.startswith("SUPPLIER:"):
			append_subtotal()
			parts = label[9:].strip().split(" - ", 1)
			supplier_code = parts[0].strip()
			current_supplier_name = parts[1].strip() if len(parts) > 1 else supplier_code
			data.append(["SUPPLIER: {0} - {1}".format(supplier_code, current_supplier_name)] + [""] * 12)
			subtotal = {
				"invoiced": 0.0,
				"paid": 0.0,
				"return": 0.0,
				"outstanding": 0.0,
				"0_30": 0.0,
				"31_60": 0.0,
				"61_90": 0.0,
				"above_90": 0.0,
			}
			continue

		if label.startswith("Subtotal:") or label == "GRAND TOTAL":
			continue

		if len(row) < 9 or not row[0]:
			continue

		po_no = row[1]
		invoice_no = row[2]
		date_str = row[3]
		debit = flt(row[5])
		paid = flt(row[6])
		ret = flt(row[7])
		balance = flt(row[8])

		if po_no and po_no != "No Order":
			po = po_no
			purchase_invoice_no = ""
			ref = po_no
		else:
			po = "No Order"
			purchase_invoice_no = invoice_no or "No Order"
			ref = po_no

		try:
			inv_date = datetime.strptime(str(date_str), "%d-%m-%Y").date()
		except (ValueError, TypeError):
			inv_date = report_date

		age = date_diff(report_date, inv_date)
		if age < 0:
			age = 0

		b0_30 = b31_60 = b61_90 = b90 = 0.0
		if balance != 0:
			if 0 <= age <= 30:
				b0_30 = balance
			elif 31 <= age <= 60:
				b31_60 = balance
			elif 61 <= age <= 90:
				b61_90 = balance
			else:
				b90 = balance

		data.append([
			date_str,
			po,
			purchase_invoice_no,
			ref,
			round(debit, 2),
			round(paid, 2),
			round(ret, 2),
			round(balance, 2),
			age,
			round(b0_30, 2),
			round(b31_60, 2),
			round(b61_90, 2),
			round(b90, 2),
		])

		subtotal["invoiced"] += debit
		subtotal["paid"] += paid
		subtotal["return"] += ret
		subtotal["outstanding"] += balance
		subtotal["0_30"] += b0_30
		subtotal["31_60"] += b31_60
		subtotal["61_90"] += b61_90
		subtotal["above_90"] += b90

	append_subtotal()

	data.append([
		"GRAND TOTAL",
		"",
		"",
		"",
		round(grand["invoiced"], 2),
		round(grand["paid"], 2),
		round(grand["return"], 2),
		round(grand["outstanding"], 2),
		"",
		round(grand["0_30"], 2),
		round(grand["31_60"], 2),
		round(grand["61_90"], 2),
		round(grand["above_90"], 2),
	])

	# Currency conversion
	base_currency = frappe.db.get_value('Company', company, 'default_currency') or 'SAR'
	target_currency = args.get('currency') or base_currency
	if target_currency and target_currency != base_currency:
		exchange_rate = _get_exchange_rate(base_currency, target_currency)
		if exchange_rate and exchange_rate != 1:
			# Amount columns: 5(invoice), 6(paid), 7(return), 8(outstanding), 9(0-30), 10(31-60), 11(61-90), 12(above_90)
			for row in data:
				if isinstance(row, list):
					for idx in [5, 6, 7, 8, 9, 10, 11, 12]:
						if idx < len(row) and isinstance(row[idx], (int, float)) and row[idx] != 0:
							row[idx] = round(row[idx] * exchange_rate, 2)

	return data


def _get_exchange_rate(from_currency, to_currency):
	"""Get exchange rate between any two currencies."""
	if from_currency == to_currency:
		return 1.0
	def _direct(frm, to):
		r = frappe.db.sql("SELECT exchange_rate FROM `tabCurrency Exchange` WHERE from_currency=%s AND to_currency=%s ORDER BY date DESC LIMIT 1", (frm, to))
		return flt(r[0][0]) if r and r[0][0] else None
	rate = _direct(from_currency, to_currency)
	if rate: return rate
	rate = _direct(to_currency, from_currency)
	if rate: return 1.0 / rate
	if from_currency != "SAR" and to_currency != "SAR":
		r1 = _direct(from_currency, "SAR"); r2 = _direct(to_currency, "SAR")
		if r1 and r2: return r1 / r2
	if from_currency != "USD" and to_currency != "USD":
		r1 = _direct(from_currency, "USD") or (_direct("USD", from_currency) and 1.0/_direct("USD", from_currency))
		r2 = _direct(to_currency, "USD") or (_direct("USD", to_currency) and 1.0/_direct("USD", to_currency))
		if r1 and r2: return r1 / r2
	return 1.0


def get_print_html(args):
	company = args.get("company") or ""
	supplier_filter = args.get("supplier") or ""
	to_date = args.get("to_date") or ""
	report_date = format_date(to_date) if to_date else datetime.now().strftime("%d-%m-%Y")

	rows = get_data(args)
	headers = [
		"Posting Date",
		"PO No",
		"Purchase Invoice Number",
		"Supplier LPO / Invoice Ref",
		"Invoiced",
		"Paid",
		"Return",
		"Outstanding",
		"Age(Days)",
		"0-30",
		"31-60",
		"61-90",
		"Above 90",
	]

	html_rows = []
	for row in rows:
		rt = _row_type(row)

		if rt == "supplier_header":
			html_rows.append('<tr><td colspan="13" class="supplier-header">{0}</td></tr>'.format(escape_html(row[0])))
		elif rt in ("subtotal", "grand_total"):
			label = escape_html(row[0])
			row_class = "grand-total" if rt == "grand_total" else "subtotal"
			cells = ['<td colspan="4" class="subtotal-label">{0}</td>'.format(label)]
			for idx, val in enumerate(row):
				if idx < 4:
					continue
				val_str = fmt_money(val) if isinstance(val, (int, float)) else escape_html(str(val))
				cells.append('<td class="text-right">{0}</td>'.format(val_str))
			html_rows.append('<tr class="{0}">'.format(row_class) + "".join(cells) + "</tr>")
		else:
			if rt == "no_order":
				row_class = "no-order-row"
			elif rt == "invoice":
				row_class = "invoice-row"
			else:
				row_class = ""
			cells = []
			for idx, val in enumerate(row):
				if idx in [0, 1, 2, 3]:
					css = "text-left"
				elif idx == 8:
					css = "text-center"
				else:
					css = "text-right"
				if idx >= 4 and idx != 8 and isinstance(val, (int, float)):
					val_str = fmt_money(val)
				else:
					val_str = escape_html(str(val))
				cells.append('<td class="{0}">{1}</td>'.format(css, val_str))
			html_rows.append('<tr class="{0}">'.format(row_class) + "".join(cells) + "</tr>")

	header_cells = "".join(['<th>{0}</th>'.format(escape_html(h)) for h in headers])
	html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
	body {{ font-family: Arial, sans-serif; font-size: 7pt; }}
	.header {{ text-align: center; margin-bottom: 10px; }}
	.header h2 {{ margin: 0; font-size: 14pt; }}
	.header p {{ margin: 2px 0; }}
	table {{ width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed; }}
	th, td {{ border: 1px solid #000; padding: 2px; }}
	th {{ background-color: #0F0F5C; color: #fff; text-align: center; font-size: 7pt; }}
	.text-right {{ text-align: right; }}
	.text-center {{ text-align: center; }}
	.text-left {{ text-align: left; }}
	.supplier-header {{ font-weight: bold; background-color: #E8ECF7; text-align: left; }}
	.subtotal-label {{ font-weight: bold; background-color: #D9E1F2; }}
	.subtotal td, .grand-total td {{ font-weight: bold; background-color: #D9E1F2; }}
	.grand-total .subtotal-label, .grand-total td {{ background-color: #D3D3D3; }}
	.no-order-row td {{ background-color: #FFF9E6; }}
	.invoice-row td {{ background-color: #E6F2FF; }}
</style>
</head>
<body>
	<div class="header">
		<h2>Accounts Payable Summary</h2>
		<p><strong>Company:</strong> {company}</p>
		<p><strong>Report Date:</strong> {report_date}</p>
		{supplier_line}
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
		supplier_line='<p><strong>Supplier:</strong> {0}</p>'.format(escape_html(supplier_filter)) if supplier_filter else "",
		header_cells=header_cells,
		rows="\n".join(html_rows),
	)
	return html
