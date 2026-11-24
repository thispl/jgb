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
	filename = "Accounts Payable Aging Report PO wise"
	build_xlsx_response(filename)


@frappe.whitelist()
def download_pdf():
	args = frappe.local.form_dict
	html = get_print_html(args)
	pdf = get_pdf(html)
	frappe.response["filename"] = "Accounts Payable Aging Report PO wise.pdf"
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
	sheet_name = sheet_name or "AP Aging PO wise"
	ws = wb.create_sheet(sheet_name, 0)
	if "Sheet" in wb.sheetnames:
		wb.remove(wb["Sheet"])

	widths = [25, 18, 18, 14, 22, 14, 14, 14, 14]
	for i, w in enumerate(widths, 1):
		ws.column_dimensions[get_column_letter(i)].width = w

	ws.append([args.get("company") or ""])
	ws.append(["Accounts Payable Aging Report PO wise"])
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
		"Supplier",
		"PO No",
		"Invoice No",
		"Order/Invoice Date",
		"Supplier LPO / Invoice Ref",
		"Debit",
		"Paid",
		"Return",
		"Balance",
	]
	ws.append(headers)

	report_data = get_data(args)
	for row in report_data:
		ws.append(row)

	num_cols = 9
	text_cols = 5

	# --- Apply title styling (rows 1-4) ---
	for cell in ws[1]:
		cell.font = company_font
		cell.alignment = align_center
	for cell in ws[2]:
		cell.font = title_font
		cell.alignment = align_center
	for cell in ws[3]:
		cell.font = date_font
		cell.alignment = align_center
	for cell in ws[4]:
		cell.font = date_font
		cell.alignment = align_center

	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
	ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
	ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=num_cols)
	ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=num_cols)

	ws.row_dimensions[1].height = 22
	ws.row_dimensions[2].height = 28
	ws.row_dimensions[3].height = 20

	# --- Header row styling (row 5) ---
	header_row_idx = 5
	for cell in ws[header_row_idx]:
		cell.font = header_font
		cell.fill = header_fill
		cell.alignment = align_center
		cell.border = border_thin
	ws.row_dimensions[header_row_idx].height = 25

	# --- Data rows styling ---
	data_start_row = 6
	data_end_row = data_start_row + len(report_data) - 1
	alt_row = False

	for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=num_cols):
		row_label = str(row[0].value or "")
		is_supplier = row_label.startswith("SUPPLIER:")
		is_subtotal = row_label.startswith("Subtotal:")
		is_grand_total = row_label == "GRAND TOTAL"

		for i, cell in enumerate(row):
			cell.border = border_thin

			if is_supplier:
				cell.font = salesperson_font
				cell.fill = salesperson_fill
				cell.alignment = align_center

			elif is_grand_total:
				cell.font = grand_total_font
				cell.fill = grand_total_fill
				cell.alignment = align_left if i < text_cols else align_right
				if i >= text_cols:
					cell.number_format = currency_format

			elif is_subtotal:
				cell.font = subtotal_font
				cell.fill = subtotal_fill
				cell.alignment = align_left if i < text_cols else align_right
				if i >= text_cols:
					cell.number_format = currency_format

			else:
				cell.font = data_font
				cell.alignment = align_left if i in [0, 1, 2, 4] else (align_center if i == 3 else align_right)
				if i >= text_cols:
					cell.number_format = currency_format
				if alt_row:
					cell.fill = alt_row_fill

		if is_supplier:
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
				end_column=text_cols,
			)
			alt_row = False

		else:
			alt_row = not alt_row

	# --- Page setup ---
	ws.page_setup.orientation = "landscape"
	ws.page_setup.fitToWidth = 1
	ws.page_setup.fitToHeight = 0
	ws.sheet_properties.pageSetUpPr.fitToPage = True

	xlsx_file = BytesIO()
	wb.save(xlsx_file)
	return xlsx_file



def get_data(args):
	company = args.get("company")
	if not company:
		frappe.throw(_("Company is required"))

	supplier = args.get("supplier")
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	purchase_order = args.get("purchase_order")
	division = args.get("division")
	account = args.get("account")

	conditions = ["company = %s", "docstatus = 1"]
	values = [company]

	if supplier:
		conditions.append("supplier = %s")
		values.append(supplier)
	if purchase_order:
		conditions.append("name = %s")
		values.append(purchase_order)
	if division:
		conditions.append("custom_division = %s")
		values.append(division)
	if from_date:
		conditions.append("transaction_date >= %s")
		values.append(from_date)
	if to_date:
		conditions.append("transaction_date <= %s")
		values.append(to_date)

	po_list = frappe.db.sql(
		"""
		SELECT name, transaction_date, supplier, supplier_name, title, custom_division, grand_total
		FROM `tabPurchase Order`
		WHERE {0}
		ORDER BY supplier, transaction_date
		""".format(" AND ".join(conditions)),
		tuple(values),
		as_dict=True,
	)

	po_names = [po.name for po in po_list]

	invoice_map = defaultdict(list)
	all_invoice_names = set()

	if po_names:
		invoice_query = """
			SELECT pii.purchase_order, pi.name, pi.grand_total, pi.is_return, pi.bill_no
			FROM `tabPurchase Invoice` pi
			INNER JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
			WHERE (
		"""
		if frappe.db.has_column("Purchase Invoice", "purchase_order"):
			invoice_query += "pii.purchase_order IN %s OR pi.purchase_order IN %s) AND pi.docstatus = 1"
			invoice_params = [tuple(po_names), tuple(po_names)]
		else:
			invoice_query += "pii.purchase_order IN %s) AND pi.docstatus = 1"
			invoice_params = [tuple(po_names)]

		if account:
			invoice_query += " AND pi.credit_to = %s"
			invoice_params.append(account)

		invoice_list = frappe.db.sql(invoice_query, tuple(invoice_params), as_dict=True)

		for inv in invoice_list:
			invoice_map[inv.purchase_order].append(inv)
			all_invoice_names.add(inv.name)

		if account:
			po_list = [po for po in po_list if po.name in invoice_map]
			po_names = [po.name for po in po_list]

	standalone_list = []
	if not purchase_order:
		pi_conditions = ["pi.company = %s", "pi.docstatus = 1"]
		pi_values = [company]

		if supplier:
			pi_conditions.append("pi.supplier = %s")
			pi_values.append(supplier)
		if division:
			pi_conditions.append("pi.custom_division = %s")
			pi_values.append(division)
		if from_date:
			pi_conditions.append("pi.posting_date >= %s")
			pi_values.append(from_date)
		if to_date:
			pi_conditions.append("pi.posting_date <= %s")
			pi_values.append(to_date)
		if account:
			pi_conditions.append("pi.credit_to = %s")
			pi_values.append(account)

		not_exists = """
			AND NOT EXISTS (
				SELECT 1 FROM `tabPurchase Invoice Item` pii2
				WHERE pii2.parent = pi.name AND pii2.purchase_order IS NOT NULL AND pii2.purchase_order != ''
			)
		"""
		if frappe.db.has_column("Purchase Invoice", "purchase_order"):
			not_exists += " AND (pi.purchase_order IS NULL OR pi.purchase_order = '')"

		standalone_list = frappe.db.sql(
			"""
			SELECT pi.name, pi.supplier, pi.supplier_name, pi.posting_date, pi.bill_no, pi.grand_total, pi.is_return
			FROM `tabPurchase Invoice` pi
			WHERE {0} {1}
			ORDER BY pi.supplier, pi.posting_date
			""".format(" AND ".join(pi_conditions), not_exists),
			tuple(pi_values),
			as_dict=True,
		)
		for pi in standalone_list:
			all_invoice_names.add(pi.name)

	payment_map = defaultdict(float)
	if all_invoice_names:
		payments = frappe.db.sql(
			"""
			SELECT per.reference_name, per.allocated_amount
			FROM `tabPayment Entry Reference` per
			INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
			WHERE per.reference_name IN %s AND pe.company = %s AND pe.docstatus = 1
			AND per.reference_doctype = 'Purchase Invoice'
			""",
			(tuple(all_invoice_names), company),
			as_dict=True,
		)
		for p in payments:
			payment_map[p.reference_name] += flt(p.allocated_amount)

	po_payment_map = defaultdict(float)
	if po_names:
		po_payments = frappe.db.sql(
			"""
			SELECT per.reference_name, per.allocated_amount
			FROM `tabPayment Entry Reference` per
			INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
			WHERE per.reference_doctype = 'Purchase Order' AND per.reference_name IN %s
			AND pe.company = %s AND pe.docstatus = 1
			""",
			(tuple(po_names), company),
			as_dict=True,
		)
		for p in po_payments:
			po_payment_map[p.reference_name] += flt(p.allocated_amount)

	grouped = defaultdict(list)

	for po in po_list:
		invs = invoice_map.get(po.name, [])
		returns = 0.0
		inv_paid = 0.0

		for inv in invs:
			if inv.is_return:
				returns += abs(flt(inv.grand_total))
			else:
				inv_paid += payment_map.get(inv.name, 0.0)

		po_paid = po_payment_map.get(po.name, 0.0)
		paid = inv_paid + po_paid
		debit = flt(po.grand_total)
		balance = debit - paid - returns
		age = date_diff(today(), po.transaction_date) if po.transaction_date else 0

		if round(balance, 2) == 0:
			continue

		grouped[po.supplier].append({
			"type": "order",
			"supplier_code": po.supplier,
			"supplier_name": po.supplier_name or po.supplier,
			"po_no": po.name,
			"invoice_no": "",
			"date": po.transaction_date,
			"ref": po.name,
			"debit": debit,
			"paid": paid,
			"return": returns,
			"balance": balance,
			"age": age,
			"a0_30": balance if 0 <= age <= 30 else 0,
			"a31_60": balance if 31 <= age <= 60 else 0,
			"a61_90": balance if 61 <= age <= 90 else 0,
			"a90": balance if age > 90 else 0,
		})

	for pi in standalone_list:
		debit = flt(pi.grand_total) if not pi.is_return else 0.0
		returns = abs(flt(pi.grand_total)) if pi.is_return else 0.0
		paid = payment_map.get(pi.name, 0.0)
		balance = debit - paid - returns
		age = date_diff(today(), pi.posting_date) if pi.posting_date else 0

		if round(balance, 2) == 0:
			continue

		ref = pi.bill_no or pi.name
		grouped[pi.supplier].append({
			"type": "no_order",
			"supplier_code": pi.supplier,
			"supplier_name": pi.supplier_name or pi.supplier,
			"po_no": "No Order",
			"invoice_no": pi.name,
			"date": pi.posting_date,
			"ref": ref,
			"debit": debit,
			"paid": paid,
			"return": returns,
			"balance": balance,
			"age": age,
			"a0_30": balance if 0 <= age <= 30 else 0,
			"a31_60": balance if 31 <= age <= 60 else 0,
			"a61_90": balance if 61 <= age <= 90 else 0,
			"a90": balance if age > 90 else 0,
		})

	data = []
	grand_debit = grand_paid = grand_return = grand_balance = 0.0

	for supplier_code in sorted(grouped.keys()):
		rows = grouped[supplier_code]
		if not rows:
			continue
		supplier_name = rows[0]["supplier_name"]
		rows.sort(key=lambda x: (0 if x["type"] == "order" else 1, x["date"] or ""))
		data.append([f"SUPPLIER: {supplier_code} - {supplier_name}"] + [""] * 8)

		sup_debit = sup_paid = sup_return = sup_balance = 0.0

		for r in rows:
			data.append([
				r["supplier_code"],
				r["po_no"],
				r["invoice_no"],
				r["date"].strftime("%d-%m-%Y") if hasattr(r["date"], "strftime") else r["date"],
				r["ref"],
				round(r["debit"], 2),
				round(r["paid"], 2),
				round(r["return"], 2),
				round(r["balance"], 2),
			])
			sup_debit += r["debit"]
			sup_paid += r["paid"]
			sup_return += r["return"]
			sup_balance += r["balance"]

		data.append([
			"Subtotal:", "", "", "", "",
			round(sup_debit, 2),
			round(sup_paid, 2),
			round(sup_return, 2),
			round(sup_balance, 2),
		])

		grand_debit += sup_debit
		grand_paid += sup_paid
		grand_return += sup_return
		grand_balance += sup_balance

	data.append([
		"GRAND TOTAL", "", "", "", "",
		round(grand_debit, 2),
		round(grand_paid, 2),
		round(grand_return, 2),
		round(grand_balance, 2),
	])

	# Currency conversion
	base_currency = frappe.db.get_value('Company', company, 'default_currency') or 'SAR'
	target_currency = args.get('currency') or base_currency
	if target_currency and target_currency != base_currency:
		exchange_rate = _get_exchange_rate(base_currency, target_currency)
		if exchange_rate and exchange_rate != 1:
			# Amount columns: 5(Credit), 6(Received), 7(CreditNote), 8(Outstanding)
			for row in data:
				if isinstance(row, list):
					for idx in [5, 6, 7, 8]:
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
		"Supplier",
		"PO No",
		"Invoice No",
		"Order/Invoice Date",
		"Supplier LPO / Invoice Ref",
		"Debit",
		"Paid",
		"Return",
		"Balance",
	]

	html_rows = []
	for row in rows:
		label = str(row[0] or "")
		if label.startswith("SUPPLIER:"):
			html_rows.append(
				'<tr><td colspan="9" class="supplier-header">{0}</td></tr>'.format(escape_html(label))
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
	.supplier-header {{ font-weight: bold; background-color: #E8ECF7; font-size: 10pt; }}
	.subtotal-label {{ font-weight: bold; background-color: #D9E1F2; }}
	.grand-total {{ font-weight: bold; background-color: #D3D3D3; }}
</style>
</head>
<body>
	<div class="header">
		<h2>Accounts Payable Aging Report PO wise</h2>
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
