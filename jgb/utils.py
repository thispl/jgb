import frappe
from frappe.utils.csvutils import read_csv_content
from frappe.utils import get_first_day, get_last_day, format_datetime, get_url_to_form, get_link_to_form
from frappe.utils import cint
from frappe.utils.data import date_diff, now_datetime, nowdate, today, add_days
import datetime
from frappe import _
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate
from frappe import throw, msgprint
from datetime import datetime
import erpnext
from frappe.utils import date_diff, add_months, today, add_days, nowdate,formatdate,flt
from frappe.utils.csvutils import read_csv_content
from frappe.utils.file_manager import get_file
import json
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc
from frappe.model.naming import make_autoname
from erpnext.setup.utils import get_exchange_rate
from frappe.query_builder.functions import Sum

from hrms.hr.doctype.leave_application.leave_application import get_leave_details

@frappe.whitelist()
def make_item_sheet():
	args = frappe.local.form_dict
	filename = args.name
	xlsx_file = build_xlsx_response(filename)
	return xlsx_file

@frappe.whitelist()
def make_item_sheet_1():
	args = frappe.local.form_dict
	filename = args.name
	xlsx_file = build_xlsx_response_1(filename)
	return xlsx_file

def make_xlsx(name, sheet_name="Item Details", wb=None, column_widths=None):
	import openpyxl
	from io import BytesIO

	column_widths = column_widths or []
	if wb is None:
		wb = openpyxl.Workbook()
	ws = wb.create_sheet(sheet_name, 0)

	doc = frappe.get_doc("Quotation", name)
	if doc:
		ws.append([
			"Item Code", "Item Name", "Qty", "UOM",
			"Discount %", "Discount Rate", "Discount Amount",
			"Unit Rate", "Amount"
		])
		for i in doc.items:
			discount_rate = i.discount_amount / i.qty if i.qty else 0
			ws.append([
				i.item_code,
				i.item_name,
				i.qty,
				i.uom,
				i.discount_percentage,   
				round(discount_rate, 2),
				i.discount_amount,        
				i.rate,
				i.amount
			])

	xlsx_file = BytesIO()
	wb.save(xlsx_file)
	return xlsx_file

def make_xlsx_1(name, sheet_name="Item Details", wb=None, column_widths=None):
	import openpyxl
	from io import BytesIO

	column_widths = column_widths or []
	if wb is None:
		wb = openpyxl.Workbook()
	ws = wb.create_sheet(sheet_name, 0)

	doc = frappe.get_doc("Purchase Order", name)
	if doc:
		ws.append([
			"Item Code", "Item Name", "Qty", "UOM",
			"Discount %", "Discount Rate", "Discount Amount",
			"Unit Rate", "Amount"
		])
		for i in doc.items:
			discount_rate = i.discount_amount / i.qty if i.qty else 0
			ws.append([
				i.item_code,
				i.item_name,
				i.qty,
				i.uom,
				i.discount_percentage,   
				round(discount_rate, 2),
				i.discount_amount,        
				i.rate,
				i.amount
			])

	xlsx_file = BytesIO()
	wb.save(xlsx_file)
	return xlsx_file


def build_xlsx_response_1(filename):
	xlsx_file = make_xlsx_1(filename)
	frappe.response['filename'] = filename + '.xlsx'
	frappe.response['filecontent'] = xlsx_file.getvalue()
	frappe.response['type'] = 'binary'
	frappe.response['content_type'] = (
		'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
	)


def build_xlsx_response(filename):
	xlsx_file = make_xlsx(filename)
	frappe.response['filename'] = filename + '.xlsx'
	frappe.response['filecontent'] = xlsx_file.getvalue()
	frappe.response['type'] = 'binary'
	frappe.response['content_type'] = (
		'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
	)


# def make_xlsx(name, sheet_name="Item Details", wb=None, column_widths=None):
#     import openpyxl
#     from io import BytesIO

#     if wb is None:
#         wb = openpyxl.Workbook()
#         ws = wb.active
#         ws.title = sheet_name
#     else:
#         ws = wb.create_sheet(sheet_name, 0)

#     ws.append([
#         "Tag", "Flow", "Ext.sp", "Drive", "KW",
#         "Fan RPM", "Volt", "Model", "Unit Size"
#     ])
#     column_widths = [15, 10, 10, 10, 10, 12, 10, 15, 12]
#     for i, width in enumerate(column_widths, start=1):
#         col_letter = openpyxl.utils.get_column_letter(i)
#         ws.column_dimensions[col_letter].width = width

#     xlsx_file = BytesIO()
#     wb.save(xlsx_file)
#     xlsx_file.seek(0)

#     return xlsx_file

@frappe.whitelist()
def margin_details(item_details, company, currency, exchange_rate, price_list, footer_discount):
	item_details = json.loads(item_details)
	
	data = ''
	data += '''
	
		<br><table>
		<style>
		td { text-align: left; }
		table, tr, td, th {
			padding: 5px;
			border: 1px solid black;
			font-size: 11px;
			border-collapse: collapse;
		}
	</style>
	<tr>
		<th colspan=13 style="padding:1px;font-size:14px;background-color:#5E3B63;color:white;">
			<center><b>MARGIN BY VALUE & MARGIN BY PERCENTAGE</b></center>
		</th>
	</tr>
	<tr style="background-color:lightgrey;text-align:center">
		<th width="150px">ITEM</th>
		<th width="400px;">ITEM NAME</th>
		<th>QTY</th>
		<th>Cost/Unit</th>
		<th>Cost</th>
		<th>Selling Price</th>
		<th>Margin Value</th>
		<th>Margin %</th>
	</tr>
	'''
	
	total_selling_price = 0
	total_cost = 0

	for i in item_details:
		item_code = i.get("item_code")
		item_name = i.get("item_name", "")
		qty = float(i.get("qty", 0))
		amount = float(i.get("amount", 0))
		sbu = frappe.get_value("Item Price", {"item_code": item_code,"price_list": "Cost Price"}, "price_list_rate") or 0
		cost = sbu * qty
		margin_value = amount - cost
		margin_percent = round((margin_value / amount * 100), 2) if amount else 0
		data += f'''
		<tr>
			<td>{item_code}</td>
			<td>{item_name}</td>
			<td style="text-align:right">{qty}</td>
			<td style="text-align:right">{frappe.utils.fmt_money(sbu)}</td>
			<td style="text-align:right">{frappe.utils.fmt_money(cost)}</td>
			<td style="text-align:right">{frappe.utils.fmt_money(amount)}</td>
			<td style="text-align:right">{frappe.utils.fmt_money(margin_value)}</td>
			<td style="text-align:right">{margin_percent}%</td>
		</tr>
		'''

		total_selling_price += amount
		total_cost += cost

	total_margin = total_selling_price - total_cost
	total_margin_percent = round((total_margin / total_selling_price * 100), 2) if total_selling_price else 0

	data += f'''
	<tr style="background-color:#f0f0f0;font-weight:bold;">
		<td colspan="4" style="text-align:center">TOTAL</td>
		<td style="text-align:right">{frappe.utils.fmt_money(total_cost)}</td>
		<td style="text-align:right">{frappe.utils.fmt_money(total_selling_price)}</td>
		<td style="text-align:right">{frappe.utils.fmt_money(total_margin)}</td>
		<td style="text-align:right">{total_margin_percent}%</td>
	</tr>
	</table>
	'''

	return data

@frappe.whitelist()
def packing_list(sales_invoice):
	data = frappe.db.sql("""
		SELECT 
			si.custom_exporter_iec, si.custom_gstin,
			sii.custom_pallet, sii.custom_pallet_length,
			sii.custom_pallet_breadth, sii.custom_pallet_height,
			SUM(sii.total_weight) as net_weight,
			SUM(sii.custom_gross_weight) as gross_weight,
			SUM(sii.custom_no_of_boxes) as total_boxes,
			SUM(sii.custom_no_of_pallets) as total_pallets,
			sii.item_code, sii.description, SUM(sii.qty) as qty
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
		WHERE si.name = %s
		GROUP BY sii.custom_pallet, sii.item_code
		ORDER BY sii.custom_pallet
	""", (sales_invoice,), as_dict=True)

	if not data:
		return "<p>No packing list data available.</p>"

	iec = data[0].custom_exporter_iec or ''
	gstin = data[0].custom_gstin or ''

	# Group by pallet
	pallet_map = {}
	for row in data:
		pallet_map.setdefault(row.custom_pallet, []).append(row)

	# Header and first table
	html = f"""
	<h3 class="text-center">Packing List</h3>
	<p style="margin-left: 70%;">Exporter IEC: <span style="font-weight: 100;">{iec}</span></p>
	<p style="margin-left: 70%;">GSTIN: <span style="font-weight: 100;">{gstin}</span></p>
	<table class="mt-2" border="1" cellspacing="0" cellpadding="4">
		<tr>
			<td class="background text-center">Pallet</td>
			<td class="background text-center">Item</td>
			<td class="background text-center">Description</td>
			<td class="background text-center">Qty (Nos)</td>
			<td class="background text-center">No. of Boxes (Nos)</td>
			<td class="background text-center">No. of Pallets (Nos)</td>
		</tr>
	"""
	total_qty = 0
	total_boxes = 0
	total_pallets = 0
	for pallet, items in pallet_map.items():
		rowspan = len(items)
		for idx, i in enumerate(items):
			html += "<tr>"
			if idx == 0:
				html += f'<td rowspan="{rowspan}">{pallet}</td>'
			total_qty += int(round(i.qty or 0))
			total_boxes += int(round(i.total_boxes or 0))
			total_pallets += int(round(i.total_pallets or 0))
			html += f"""
				<td>{i.item_code}</td>
				<td>{i.description}</td>
				<td class="text-right">{int(round(i.qty or 0))}</td>
				<td class="text-right">{int(round(i.total_boxes or 0))}</td>
				<td class="text-right">{int(round(i.total_pallets or 0))}</td>
			</tr>
			"""
	html += f"""
			<tr>
				<td colspan=3 class="text-right"><b>Total</b></td>
				<td class="text-right"><b>{total_qty}</b></td>
				<td class="text-right"><b>{total_boxes}</b></td>
				<td class="text-right"><b>{total_pallets}</b></td>
			</tr>"""
	html += "</table>"

	# Second table: Pallet summary
	html += f"""
	<div style="width: 70%;">
	<table class="mt-5" border="1" cellspacing="0" cellpadding="4" width=60%>
		<tr>
			<td rowspan="2" class="background text-center">Pallet</td>
			<td colspan="3" class="background text-center">Dimensions (mm)</td>
			<td colspan="2" class="background text-center">Weight (kg)</td>
		</tr>
		<tr>
			<td class="background text-center">L</td>
			<td class="background text-center">B</td>
			<td class="background text-center">H</td>
			<td class="background text-center">Net</td>
			<td class="background text-center">Gross</td>
		</tr>
	"""

	total_net = 0
	total_gross = 0

	for pallet, items in pallet_map.items():
		first = items[0]
		length = int(round(first.custom_pallet_length or 0))
		breadth = int(round(first.custom_pallet_breadth or 0))
		height = int(round(first.custom_pallet_height or 0))
		net_weight = int(round(first.net_weight or 0))
		gross_weight = int(round(first.gross_weight or 0))

		html += f"""
		<tr>
			<td class="text-left">{pallet}</td>
			<td class="text-right">{length}</td>
			<td class="text-right">{breadth}</td>
			<td class="text-right">{height}</td>
			<td class="text-right">{net_weight}</td>
			<td class="text-right">{gross_weight}</td>
		</tr>
		"""
		total_net += net_weight
		total_gross += gross_weight

	html += f"""
		<tr>
			<td colspan="4" class="text-right"><b>Total</b></td>
			<td class="text-right"><b>{total_net}</b></td>
			<td class="text-right"><b>{total_gross}</b></td>
		</tr>
		"""

	html += "</table></div>"
	return html


@frappe.whitelist()
def estimation_details(total,base_total,estimated,estimate,discount_amount=0,currency=None):
	try:
		# if discount_amount > 0:
		#     total=float(total)-float(discount_amount)
		total = float(total)-float(discount_amount)
		base_total=float(base_total)
		estimate=float(estimate)
		estimated = float(estimated)
		currency = currency or "SAR"
	except (TypeError, ValueError):
		return "<p style='color:red;'>Invalid input: total and estimated must be numeric.</p>"

	if estimated == 0:
		return "<p style='color:red;'>Estimated value cannot be zero (division by zero).</p>"

	

	# Conditional color for margin percentage
	
	if currency=="SAR":
		margin_value = total - estimated
		if total !=0:
			margin_percent = (margin_value / total) * 100
		else:
			margin_percent = 0
		percent_color = "green" if margin_percent >= 0 else "red"
		html = '''
		<br>
		<style>
			td, th {{
				text-align: center;
				padding: 5px;
				border: 1px solid black;
				font-size: 11px;
				border-collapse: collapse;
			}}
			table {{
				border-collapse: collapse;
				width: 100%;
			}}
		</style>
		<table>
			<tr>
				<th colspan="4" style="font-size:14px;background-color:#5E3B63;color:white;">
					<b>Estimated vs Quotation Value</b>
				</th>
			</tr>
			<tr style="background-color:lightgrey;">
				<th>Total Quoted Value</th>
				<th>Total Estimated Value</th>
				<th>Projected Margin in Value</th>
				<th>Profit on Cost</th>
			</tr>
			<tr>
				<td style="text-align:right;">{total:,.2f}</td>
				<td style="text-align:right;">{estimated:,.2f}</td>
				<td style="text-align:right;">{margin_value:,.2f}</td>
				<td style="text-align:right; color:{percent_color};"><b>{margin_percent:.2f}%</b></td>
			</tr>
		</table>
		'''.format(
			total=total,
			estimated=estimated,
			margin_value=margin_value,
			margin_percent=margin_percent,
			percent_color=percent_color
		)
	else:
		margin_value_quote = total - estimate
		if total !=0:
			margin_percent_quote = (margin_value_quote / total) * 100
		else:
			margin_percent_quote = 0
		margin_value_sar = base_total - estimated
		if base_total != 0:
			margin_percent_sar = (margin_value_sar / base_total) * 100
		else:
			margin_percent_sar = 0
		percent_color = "green" if margin_percent_quote >= 0 else "red"
		percent_color1 = "green" if margin_percent_sar >= 0 else "red"
		html = '''
	<br>
	<style>
		td, th {{
			text-align: center;
			padding: 5px;
			border: 1px solid black;
			font-size: 11px;
			border-collapse: collapse;
		}}
		table {{
			border-collapse: collapse;
			width: 100%;
		}}
	</style>
	<table>
		<tr>
			<th colspan="8" style="font-size:14px;background-color:#5E3B63;color:white;">
				<b>Estimated vs Quotation Value</b>
			</th>
		</tr>
		<tr style="background-color:lightgrey;">
			<th>Total Quoted Value({currency})</th>
			<th>Total Quoted Value(SAR)</th>
			<th>Total Estimated Value({currency})</th>
			<th>Total Estimated Value(SAR)</th>
			<th>Projected Margin in Value({currency})</th>
			<th>Profit on Cost({currency})</th>
			<th>Projected Margin in Value(SAR)</th>
			<th>Profit on Cost(SAR)</th>
		</tr>
		<tr>
			<td style="text-align:right;">{total:,.2f}</td>
			<td style="text-align:right;">{base_total:,.2f}</td>
			<td style="text-align:right;">{estimate:,.2f}</td>
			<td style="text-align:right;">{estimated:,.2f}</td>
			<td style="text-align:right;">{margin_value_quote:,.2f}</td>
			<td style="text-align:right; color:{percent_color};"><b>{margin_percent_quote:.2f}%</b></td>
			<td style="text-align:right;">{margin_value_sar:,.2f}</td>
			<td style="text-align:right; color:{percent_color1};"><b>{margin_percent_sar:.2f}%</b></td>
		</tr>
	</table>
	'''.format(
		total=total,
		base_total=base_total,
		estimate=estimate,
		estimated=estimated,
		currency=currency,
		margin_value_quote=margin_value_quote,
		margin_percent_quote=margin_percent_quote,
		percent_color=percent_color,
		margin_value_sar=margin_value_sar,
		margin_percent_sar=margin_percent_sar,
		percent_color1=percent_color1

	)

	return html


@frappe.whitelist()
def estimation_details_so(total,base_total,estimated,estimate,currency=None,discount_amount=0):
	try:
		total = float(total)-float(discount_amount)
		base_total=float(base_total)
		estimate=float(estimate)
		estimated = float(estimated)
		currency = currency or "SAR"
	except (TypeError, ValueError):
		return "<p style='color:red;'>Invalid input: total and estimated must be numeric.</p>"

	if estimated == 0:
		return "<p style='color:red;'>Estimated value cannot be zero (division by zero).</p>"

	

	# Conditional color for margin percentage
	
	if currency=="SAR":
		margin_value = total - estimated
		if total !=0:
			margin_percent = (margin_value / total) * 100
		else:
			margin_percent = 0
		percent_color = "green" if margin_percent >= 0 else "red"
		html = '''
		<br>
		<style>
			td, th {{
				text-align: center;
				padding: 5px;
				border: 1px solid black;
				font-size: 11px;
				border-collapse: collapse;
			}}
			table {{
				border-collapse: collapse;
				width: 100%;
			}}
		</style>
		<table>
			<tr>
				<th colspan="4" style="font-size:14px;background-color:#5E3B63;color:white;">
					<b>Estimated vs Sales Order Value</b>
				</th>
			</tr>
			<tr style="background-color:lightgrey;">
				<th>Total Ordered Value</th>
				<th>Total Estimated Value</th>
				<th>Projected Margin in Value</th>
				<th>Profit on Cost</th>
			</tr>
			<tr>
				<td style="text-align:right;">{total:,.2f}</td>
				<td style="text-align:right;">{estimated:,.2f}</td>
				<td style="text-align:right;">{margin_value:,.2f}</td>
				<td style="text-align:right; color:{percent_color};"><b>{margin_percent:.2f}%</b></td>
			</tr>
		</table>
		'''.format(
			total=total,
			estimated=estimated,
			margin_value=margin_value,
			margin_percent=margin_percent,
			percent_color=percent_color
		)
	else:
		margin_value_quote = total - estimate
		if total !=0:
			margin_percent_quote = (margin_value_quote / total) * 100
		else:
			margin_percent_quote = 0
		margin_value_sar = base_total - estimated
		if base_total != 0:
			margin_percent_sar = (margin_value_sar / base_total) * 100
		else:
			margin_percent_sar = 0
		percent_color = "green" if margin_percent_quote >= 0 else "red"
		percent_color1 = "green" if margin_percent_sar >= 0 else "red"
		html = '''
	<br>
	<style>
		td, th {{
			text-align: center;
			padding: 5px;
			border: 1px solid black;
			font-size: 11px;
			border-collapse: collapse;
		}}
		table {{
			border-collapse: collapse;
			width: 100%;
		}}
	</style>
	<table>
		<tr>
			<th colspan="8" style="font-size:14px;background-color:#5E3B63;color:white;">
				<b>Estimated vs Sales Order Value</b>
			</th>
		</tr>
		<tr style="background-color:lightgrey;">
			<th>Total Ordered Value({currency})</th>
			<th>Total Ordered Value(SAR)</th>
			<th>Total Estimated Value({currency})</th>
			<th>Total Estimated Value(SAR)</th>
			<th>Projected Margin in Value({currency})</th>
			<th>Profit on Cost({currency})</th>
			<th>Projected Margin in Value(SAR)</th>
			<th>Profit on Cost(SAR)</th>
		</tr>
		<tr>
			<td style="text-align:right;">{total:,.2f}</td>
			<td style="text-align:right;">{base_total:,.2f}</td>
			<td style="text-align:right;">{estimate:,.2f}</td>
			<td style="text-align:right;">{estimated:,.2f}</td>
			<td style="text-align:right;">{margin_value_quote:,.2f}</td>
			<td style="text-align:right; color:{percent_color};"><b>{margin_percent_quote:.2f}%</b></td>
			<td style="text-align:right;">{margin_value_sar:,.2f}</td>
			<td style="text-align:right; color:{percent_color1};"><b>{margin_percent_sar:.2f}%</b></td>
		</tr>
	</table>
	'''.format(
		total=total,
		base_total=base_total,
		estimate=estimate,
		estimated=estimated,
		currency=currency,
		margin_value_quote=margin_value_quote,
		margin_percent_quote=margin_percent_quote,
		percent_color=percent_color,
		margin_value_sar=margin_value_sar,
		margin_percent_sar=margin_percent_sar,
		percent_color1=percent_color1

	)

	return html


@frappe.whitelist()
def estimation_details_po(total,base_total,estimated,currency=None,custom_quote_value=None):
	try:
		custom_quote_value = float(custom_quote_value)
		total = float(total)
		base_total=float(base_total)
		estimated = float(estimated)
		currency = currency or "SAR"
	except (TypeError, ValueError):
		return "<p style='color:red;'>Invalid input: total and estimated must be numeric.</p>"

	if estimated == 0:
		return "<p style='color:red;'>Estimated value cannot be zero (division by zero).</p>"

	

	# Conditional color for margin percentage
	
	margin_value = float(custom_quote_value) - estimated
	
	margin_percent = (margin_value / estimated) * 100
	percent_color = "green" if margin_percent >= 0 else "red"
	html = '''
	<br>
	<style>
		td, th {{
			text-align: center;
			padding: 5px;
			border: 1px solid black;
			font-size: 11px;
			border-collapse: collapse;
		}}
		table {{
			border-collapse: collapse;
			width: 100%;
		}}
	</style>
	<table>
		<tr>
			<th colspan="4" style="font-size:14px;background-color:#5E3B63;color:white;">
				<b>Estimated vs Order Value</b>
			</th>
		</tr>
		<tr style="background-color:lightgrey;">
			<th>Total Order Value</th>
			<th>Total Estimated Value</th>
			<th>Profit on Cost</th>
		</tr>
		<tr>
			<td style="text-align:right;">{custom_quote_value:,.2f}</td>
			<td style="text-align:right;">{estimated:,.2f}</td>
			<td style="text-align:right; color:{percent_color};"><b>{margin_percent:.2f}%</b></td>
		</tr>
	</table>
	'''.format(
		custom_quote_value=custom_quote_value,
		estimated=estimated,
		margin_value=margin_value,
		margin_percent=margin_percent,
		percent_color=percent_color
	)
	return html



@frappe.whitelist()
def getstock_detail(item_details, company, docname):
	import json
	item_details = json.loads(item_details)

	# -----------------------------------
	# GET COMPANY WAREHOUSES
	# -----------------------------------
	warehouses = frappe.get_all(
		"Warehouse",
		filters={"company": company},
		pluck="name"
	)

	if not warehouses:
		return "<b>No Warehouses Found</b>"

	# -----------------------------------
	# STEP 1: COLLECT STOCK DATA
	# -----------------------------------
	warehouse_totals = {wh: 0 for wh in warehouses}
	item_stock_data = []

	for item in item_details:
		item_code = item.get("item_code")

		bin_data = frappe.db.sql("""
			SELECT warehouse,
				   SUM(actual_qty) as actual_qty,
				   SUM(reserved_stock) as reserved_stock
			FROM `tabBin`
			WHERE item_code = %s
			AND warehouse IN %s
			GROUP BY warehouse
		""", (item_code, tuple(warehouses)), as_dict=True)

		warehouse_stock_map = {
			d.warehouse: (d.actual_qty or 0) - (d.reserved_stock or 0)
			for d in bin_data
		}

		# accumulate totals
		for wh in warehouses:
			warehouse_totals[wh] += warehouse_stock_map.get(wh, 0)

		item_stock_data.append({
			"item": item,
			"warehouse_stock_map": warehouse_stock_map
		})

	# -----------------------------------
	# FILTER WAREHOUSES WITH STOCK
	# -----------------------------------
	filtered_warehouses = [
		wh for wh in warehouses if warehouse_totals.get(wh, 0) != 0
	]

	has_available_stock = len(filtered_warehouses) > 0

	# -----------------------------------
	# BUILD TABLE HEADER
	# -----------------------------------
	data = """
		<h4><center><b>STOCK DETAILS</b></center></h4>
		<table class="table table-bordered table-sm">
	"""

	# HEADER ROW 1
	data += """
		<tr>
			<th rowspan="2" style="background-color:#75506A;color:white;font-size:12px;">S#</th>
			<th rowspan="2" style="background-color:#75506A;color:white;font-size:12px;">ITEM CODE</th>
			<th rowspan="2" style="background-color:#75506A;color:white;font-size:12px;">ITEM NAME</th>
			<th rowspan="2" style="background-color:#75506A;color:white;font-size:12px;">TOTAL STOCK</th>
	"""

	if has_available_stock:
		data += f"""
			<th colspan="{len(filtered_warehouses)}"
				style="background-color:#75506A;color:white;font-size:12px;">
				Available
			</th>
		"""

	data += """
			<th colspan="2" style="background-color:#75506A;color:white;font-size:12px;">Completed</th>
			<th colspan="2" style="background-color:#75506A;color:white;font-size:12px;">Pending</th>
			<th rowspan="2" style="background-color:#75506A;color:white;font-size:12px;">Reserved</th>
			<th rowspan="2" style="background-color:#75506A;color:white;font-size:12px;">To Receive</th>
			<th rowspan="2" style="background-color:#75506A;color:white;font-size:12px;">To Sell</th>
		</tr>
	"""

	# HEADER ROW 2
	data += "<tr>"

	if has_available_stock:
		for wh in filtered_warehouses:
			data += f"""
				<th style="background-color:#75506A;color:white;font-size:12px;">
					{wh}
				</th>
			"""

	data += """
			<th style="background-color:#75506A;color:white;font-size:12px;">DN</th>
			<th style="background-color:#75506A;color:white;font-size:12px;">SI</th>
			<th style="background-color:#75506A;color:white;font-size:12px;">DN</th>
			<th style="background-color:#75506A;color:white;font-size:12px;">SI</th>
		</tr>
	"""

	# -----------------------------------
	# BUILD BODY ROWS
	# -----------------------------------
	for idx, entry in enumerate(item_stock_data, start=1):

		item = entry["item"]
		warehouse_stock_map = entry["warehouse_stock_map"]

		item_code = item.get("item_code")
		item_name = item.get("item_name")
		order_qty = item.get("qty", 0)

		total_stock = sum(warehouse_stock_map.get(wh, 0) for wh in warehouses)

		# Purchase Order
		po_data = frappe.db.sql("""
			SELECT
				SUM(poi.qty) as qty,
				SUM(poi.received_qty) as received_qty
			FROM `tabPurchase Order` po
			JOIN `tabPurchase Order Item` poi ON po.name = poi.parent
			WHERE poi.item_code = %s
			AND po.docstatus = 1
			AND po.status != 'Closed'
		""", (item_code,), as_dict=True)[0]

		to_receive = (po_data.qty or 0) - (po_data.received_qty or 0)

		# Sales Order
		so_data = frappe.db.sql("""
			SELECT
				SUM(soi.qty) as qty,
				SUM(soi.delivered_qty) as delivered_qty
			FROM `tabSales Order` so
			JOIN `tabSales Order Item` soi ON so.name = soi.parent
			WHERE soi.item_code = %s
			AND so.docstatus = 1
			AND so.status != 'Closed'
		""", (item_code,), as_dict=True)[0]

		to_sell = (so_data.qty or 0) - (so_data.delivered_qty or 0)

		# Delivery Note
		dn_completed = frappe.db.sql("""
			SELECT SUM(qty)
			FROM `tabDelivery Note Item`
			WHERE against_sales_order = %s
			AND item_code = %s
			AND docstatus = 1
		""", (docname, item_code))[0][0] or 0

		# Sales Invoice
		si_completed = frappe.db.sql("""
			SELECT SUM(qty)
			FROM `tabSales Invoice Item`
			WHERE sales_order = %s
			AND item_code = %s
			AND docstatus = 1
		""", (docname, item_code))[0][0] or 0

		dn_pending = order_qty - dn_completed
		si_pending = order_qty - si_completed

		# Reserved
		reserved_qty = sum(
			frappe.get_all(
				"Stock Reservation Entry",
				filters={
					"voucher_type": "Sales Order",
					"item_code": item_code,
					"docstatus": ["!=", 2]
				},
				pluck="reserved_qty"
			)
		)
		total_reserved_qty = frappe.db.sql("""
			SELECT 
				SUM(
					CASE
						WHEN status = 'Reserved'
							THEN reserved_qty

						WHEN status = 'Partially Reserved'
							THEN reserved_qty

						WHEN status = 'Partially Delivered'
							THEN (reserved_qty - delivered_qty)

						ELSE 0
					END
				) as total_reserved
			FROM `tabStock Reservation Entry`
			WHERE item_code = %s
			AND docstatus != 2
			AND status != 'Delivered'
		""", item_code, as_dict=True)[0]["total_reserved"] or 0
		# ROW
		data += "<tr>"
		data += f"<td>{idx}</td>"
		data += f"<td>{item_code}</td>"
		data += f"<td>{item_name}</td>"
		data += f"<td><b>{total_stock:.2f}</b></td>"

		if has_available_stock:
			for wh in filtered_warehouses:
				data += f"<td>{warehouse_stock_map.get(wh, 0):.2f}</td>"

		data += f"<td>{dn_completed:.2f}</td>"
		data += f"<td>{si_completed:.2f}</td>"
		data += f"<td>{dn_pending:.2f}</td>"
		data += f"<td>{si_pending:.2f}</td>"
		data += f"<td>{total_reserved_qty:.2f}</td>"
		data += f"<td>{to_receive:.2f}</td>"
		data += f"<td>{to_sell:.2f}</td>"
		data += "</tr>"

	data += "</table>"

	return data

@frappe.whitelist()
def update_qn_status(doc, name):

	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)

		# Check if a matching row exists
		exists = False
		for row in ref.table_gygr:
			if row.document_type_name == doc.opportunity:
				ref.remove(row)
				exists = True
				break  # Stop after finding and removing the first match

		ref.append("table_gygr", {
			"document_type": doc.doctype,
			"document_type_name": doc.name,
			"status": doc.status,
			"value":doc.total
		})

		ref.save(ignore_permissions=True)
		frappe.db.commit()


@frappe.whitelist()
def update_so_status(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)

		# Check if a matching row exists
		exists = False
		for row in ref.table_gygr:
			if row.document_type_name == doc.custom_quotation:
				ref.remove(row)
				exists = True
				break  # Stop after finding and removing the first match

		ref.append("table_gygr", {
			"document_type": doc.doctype,
			"document_type_name": doc.name,
			"status": doc.status,
			"value":doc.total
		})

		ref.save(ignore_permissions=True)
		frappe.db.commit()
@frappe.whitelist()
def update_po_status(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)

		# Check if a matching row exists
		exists = False
		for row in ref.table_gygr:
			if row.document_type_name == doc.name:
				ref.remove(row)
				exists = True
				break  # Stop after finding and removing the first match

		ref.append("table_gygr", {
			"document_type": doc.doctype,
			"document_type_name": doc.name,
			"status": doc.status,
			"value":doc.total
		})

		ref.save(ignore_permissions=True)
		frappe.db.commit()


@frappe.whitelist()
def update_si_status(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)
		exists = False
		for row in ref.table_gygr:
			if row.document_type_name == doc.custom_sales_order:
				ref.remove(row)
				exists = True
				break  # Stop after finding and removing the first match

		ref.append("table_gygr", {
			"document_type": doc.doctype,
			"document_type_name": doc.name,
			"status": doc.status,
			"value":doc.total,
			"projection": doc.total
		})

		ref.save(ignore_permissions=True)
		frappe.db.commit()



@frappe.whitelist()
def update_dn_status(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)

		# Check if a matching row exists
		exists = False
		for row in ref.table_gygr:
			for i in doc.items:
				if row.document_type_name == i.against_sales_order:
					ref.remove(row)
					exists = True
					break  # Stop after finding and removing the first match

				if row.document_type_name == i.against_sales_invoice:
					ref.remove(row)
					exists = True
					break 

		ref.append("table_gygr", {
			"document_type": doc.doctype,
			"document_type_name": doc.name,
			"status": doc.status,
			"value":doc.total
		})

		ref.save(ignore_permissions=True)
		frappe.db.commit()

@frappe.whitelist()
def update_dn_status_update(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc

	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)
		if doc.docstatus == 2:
			for row in ref.table_gygr:
				if row.document_type_name == doc.name:
					ref.table_gygr.remove(row) 
					ref.save(ignore_permissions=True)
					# frappe.db.commit()
					break
					
		else:
			updated = False

			for row in ref.table_gygr:
				if row.document_type_name == doc.name:
					row.status = doc.status
					updated = True
					break 
			if updated:
				ref.save(ignore_permissions=True)
				# frappe.db.commit()

# Doctypes cleaned up by the order's own on_cancel or by the ledger, so they
# must not block cancellation.
ORDER_CANCEL_IGNORE_DOCTYPES = (
	"GL Entry",
	"Stock Ledger Entry",
	"Payment Ledger Entry",
	"Stock Reservation Entry",
	"Repost Item Valuation",
	"Unreconcile Payment",
	"Unreconcile Payment Entries",
)


def restrict_order_cancel_if_linked(doc, method=None):
	"""Restrict cancelling an SO/PO while it has connected documents.

	Core only blocks submitted links, and runs after on_cancel has unlinked
	advances (unlink_advance_payment_on_cancelation_of_order). This runs on
	before_cancel, so draft documents and advance payments block too.
	"""
	from frappe.model.dynamic_links import get_dynamic_link_map
	from frappe.model.rename_doc import get_link_fields

	ignored = set(doc.get("ignore_linked_doctypes") or [])
	ignored.update(ORDER_CANCEL_IGNORE_DOCTYPES)
	ignored.update(frappe.get_hooks("ignore_links_on_delete"))

	linked = {}

	def add_link(dt, name, docstatus):
		if (
			dt in ignored
			or docstatus == 2
			or (dt == doc.doctype and name == doc.name)
			or not frappe.get_meta(dt).is_submittable
		):
			return
		linked.setdefault(dt, set()).add(name)

	for lf in get_link_fields(doc.doctype):
		link_dt, link_field = lf["parent"], lf["fieldname"]
		if lf["issingle"] or link_dt in ignored or link_field == "amended_from":
			continue
		try:
			meta = frappe.get_meta(link_dt)
		except frappe.DoesNotExistError:
			continue
		fields = ["name", "docstatus"] + (["parent", "parenttype"] if meta.istable else [])
		for row in frappe.db.get_values(link_dt, {link_field: doc.name}, fields, as_dict=True):
			add_link(
				row.parenttype if meta.istable else link_dt,
				row.parent if meta.istable else row.name,
				row.docstatus,
			)

	for df in get_dynamic_link_map().get(doc.doctype, []):
		if df.parent in ignored:
			continue
		try:
			meta = frappe.get_meta(df.parent)
		except frappe.DoesNotExistError:
			continue
		if meta.issingle:
			continue
		table = ", `parent`, `parenttype`" if meta.istable else ""
		for row in frappe.db.sql(
			"select `name`, `docstatus` {} from `tab{}` where `{}`=%s and `{}`=%s".format(
				table, df.parent, df.options, df.fieldname
			),
			(doc.doctype, doc.name),
			as_dict=True,
		):
			add_link(
				row.parenttype if meta.istable else df.parent,
				row.parent if meta.istable else row.name,
				row.docstatus,
			)

	if linked:
		details = "; ".join(
			"{0}: {1}".format(dt, ", ".join(get_link_to_form(dt, name) for name in sorted(names)))
			for dt, names in sorted(linked.items())
		)
		frappe.throw(
			_("Cannot cancel {0} {1} because it has connected documents. Remove or cancel them first: {2}").format(
				_(doc.doctype), doc.name, details
			),
			title=_("Linked Documents Exist"),
		)


@frappe.whitelist()
def update_so_status_cancel(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc

	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)
		if doc.docstatus == 2:
			for row in ref.table_gygr:
				if row.document_type_name == doc.name:
					ref.table_gygr.remove(row) 
					ref.save(ignore_permissions=True)
					# frappe.db.commit()
					break
					
		else:
			updated = False

			for row in ref.table_gygr:
				if row.document_type_name == doc.name:
					row.status = doc.status
					updated = True
					break 
			if updated:
				ref.save(ignore_permissions=True)
				# frappe.db.commit()

@frappe.whitelist()
def update_si_status_ref(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc

	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)
		if doc.docstatus == 2:
			for row in ref.table_gygr:
				if row.document_type_name == doc.name:
					ref.table_gygr.remove(row)  # ✅ Correct way to remove child row
					ref.save(ignore_permissions=True)
					frappe.db.commit()
					break
					
		else:
			updated = False

			for row in ref.table_gygr:
				if row.document_type_name == doc.custom_sales_order:
					# Match found: update existing row's status and value
					row.status = doc.status
					updated = True
					break  # Stop after updating one match for this item

			if updated:
				ref.save(ignore_permissions=True)
				frappe.db.commit()

@frappe.whitelist()
def update_pr_status_ref(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	ref_id=frappe.db.get_value("Purchase Order",doc.custom_purchase_receipt,"custom_project_reference")
	if ref_id:
		if doc.custom_purchase_receipt:
			ref = frappe.get_doc("Reference Project",ref_id)

			updated = False

			for row in ref.table_gygr:
				if row.document_type_name == doc.custom_purchase_receipt:
					
					ref.remove(row)
					exists = True
					break 

			ref.append("table_gygr", {
				"document_type": doc.doctype,
				"document_type_name": doc.name,
				"status": doc.status,
				"value":doc.total
			})

			ref.save(ignore_permissions=True)
			frappe.db.commit()


@frappe.whitelist()
def update_pr_status_update(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project",doc.custom_project_reference)
		if doc.docstatus == 2:
			for row in ref.table_gygr:
				if row.document_type_name == doc.name:
					ref.table_gygr.remove(row)  
					ref.save(ignore_permissions=True)
					break
					
		else:
			updated = False

			for row in ref.table_gygr:
				if row.document_type_name == doc.name:
					row.status = doc.status
					row.projection=doc.total
					updated = True
					break  
			if updated:     
				ref.save(ignore_permissions=True)

@frappe.whitelist()
def update_po_status_ref(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc

	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)
		if doc.docstatus == 2:
			for row in ref.table_gygr:
				if row.document_type_name == doc.name:
					ref.table_gygr.remove(row)  # ✅ Correct way to remove child row
					ref.save(ignore_permissions=True)
					frappe.db.commit()
					break
					
		else:
			updated = False

			for row in ref.table_gygr:
				if row.document_type_name == doc.name:
					# Match found: update existing row's status and value
					row.status = doc.status
					row.projection=doc.total
					updated = True
					break  # Stop after updating one match for this item

			if updated:
				ref.save(ignore_permissions=True)
				frappe.db.commit()


@frappe.whitelist()
def update_status_for_lead(name, status, project):
	ref = frappe.get_doc("Reference Project", project)
	updated = False

	for row in ref.table_gygr:
		if row.document_type_name == name:
			row.status = status
			updated = True
			break

	if updated:
		ref.save(ignore_permissions=True)


@frappe.whitelist()
def update_status_quotation(doc, method):
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)
		ref.reload()  # Optional: Ensures latest version

		projection_map = {
			"Open": 0.25,
			"Replied": 0.75,  # Assuming latest value intended
			"Ordered": 1.00,
			"Lost": 0.00
		}

		updated = False

		for row in ref.table_gygr:
			if row.document_type_name == doc.name:
				row.status = doc.status
				row.projection = row.value * projection_map.get(doc.status, 0)
				updated = True
				break

		if updated:
			ref.save(ignore_permissions=True)

@frappe.whitelist()
def update_status_so(doc,method):
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project",doc.custom_project_reference)
		updated = False

		for row in ref.table_gygr:
			if row.document_type_name == doc.name:
				row.status = doc.status
				updated = True
				if doc.per_billed == 100:
					row.projection = row.value * 1.00
				
				else:
					row.projection = 0
				
				break

		if updated:
			ref.save(ignore_permissions=True)

@frappe.whitelist()
def update_margin_html(margin):
	html = '''
	<div style="
		width: 220px;
		border: 1px solid #ccc;
		border-radius: 10px;
		box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
		font-family: Arial, sans-serif;
		overflow: hidden;
	">
		<div style="
			background-color: #5E3B63;
			color: white;
			text-align: center;
			font-size: 15px;
			padding: 10px;
			font-weight: bold;
		">
			Profit on Sales
		</div>
		<div style="
			text-align: center;
			padding: 30px;
			font-size: 18px;
			font-weight: 600;
			color: #333;
			background-color: #f9f9f9;
		">
			{margin:.2f} %
		</div>
	</div>
	'''.format(margin=float(margin))

	return html

@frappe.whitelist()
def update_margin_html_cost(margin):
	html = '''
	<div style="
		width: 220px;
		border: 1px solid #ccc;
		border-radius: 10px;
		box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
		font-family: Arial, sans-serif;
		overflow: hidden;
	">
		<div style="
			background-color: #5E3B63;
			color: white;
			text-align: center;
			font-size: 15px;
			padding: 10px;
			font-weight: bold;
		">
			Contribution Margin
		</div>
		<div style="
			text-align: center;
			padding: 30px;
			font-size: 18px;
			font-weight: 600;
			color: #333;
			background-color: #f9f9f9;
		">
			{margin:.2f} %
		</div>
	</div>
	'''.format(margin=float(margin))

	return html

@frappe.whitelist()
def update_estimation_table(so):
	sales = frappe.get_doc("Sales Order", so)
	return sales.custom_total_estimated_value , sales.custom_estimation_details,sales.custom_quote_value,sales.custom_estimation_margin,sales.custom_margin_on_cost
		
@frappe.whitelist()
def update_currency(doc,method):
	if doc.custom_logistic_request:
		lr_currency = frappe.db.get_value("Logistic Request", doc.custom_logistic_request, "currency")
		if lr_currency:
			doc.currency = lr_currency
			
@frappe.whitelist()
def update_rate(so,item):
	sales = frappe.get_doc("Sales Order", so)
	item_details = []
	for i in sales.items:
		if i.item_code == item:
			return i.custom_price_cost , sales.custom_estimation_margin , sales.custom_margin_on_cost
		

@frappe.whitelist()
def update_existing_po():
	updated_rows = 0

	pos = frappe.db.get_all(
		"Purchase Order",
		{"docstatus": ("!=", 2)},
		["name"]
	)

	for po_row in pos:
		po = frappe.get_doc("Purchase Order", po_row.name)

		if not po.custom_estimation_details:
			continue

		# Get first Sales Order linked in PO items
		sales_order = next(
			(item.sales_order for item in po.items if item.sales_order),
			None
		)

		if not sales_order:
			continue

		sales = frappe.get_doc("Sales Order", sales_order)

		if not sales.custom_estimation_details:
			continue

		# Map SO child table by title
		so_map = {
			row.title_of_estimation: row
			for row in sales.custom_estimation_details
		}

		for po_row in po.custom_estimation_details:
			if po_row.title_of_estimation in so_map:
				so_row = so_map[po_row.title_of_estimation]

				if (float(po_row.value or 0) == float(so_row.value or 0)
					and flt(po_row.percen) == flt(so_row.percen)):
					continue

				frappe.db.set_value(
					po_row.doctype,      # "Estimation Details"
					po_row.name,         # child row name
					{
						"title_of_estimation": so_row.title_of_estimation,
						"value": so_row.value,
						"percen": so_row.percen
					},
					update_modified=False
				)

				updated_rows += 1

	frappe.db.commit()
	return f"{updated_rows} estimation rows updated"

@frappe.whitelist()
def get_valuation_rate(
	item_code,
	warehouse,
	voucher_type,
	voucher_no,
	allow_zero_rate=False,
	currency=None,
	company=None,
	raise_error_if_no_rate=True,
	batch_no=None,
	serial_and_batch_bundle=None,
):
	from erpnext.stock.serial_batch_bundle import BatchNoValuation
	valuation_rate = 0
	if not company:
		company = frappe.get_cached_value("Warehouse", warehouse, "company")

	if warehouse and batch_no and frappe.db.get_value("Batch", batch_no, "use_batchwise_valuation"):
		table = frappe.qb.DocType("Stock Ledger Entry")
		query = (
			frappe.qb.from_(table)
			.select(Sum(table.stock_value_difference) / Sum(table.actual_qty))
			.where(
				(table.item_code == item_code)
				& (table.warehouse == warehouse)
				& (table.batch_no == batch_no)
				& (table.is_cancelled == 0)
				& (table.voucher_no != voucher_no)
				& (table.voucher_type != voucher_type)
			)
		)

		last_valuation_rate = query.run()
		if last_valuation_rate:
			return flt(last_valuation_rate[0][0])
	
	# Get moving average rate of a specific batch number
	if warehouse and serial_and_batch_bundle:
		sabb = frappe.db.get_value(
			"Serial and Batch Bundle", serial_and_batch_bundle, ["posting_date", "posting_time"], as_dict=True
		)
		batch_obj = BatchNoValuation(
			sle=frappe._dict(
				{
					"item_code": item_code,
					"warehouse": warehouse,
					"actual_qty": -1,
					"serial_and_batch_bundle": serial_and_batch_bundle,
					"posting_date": sabb.posting_date,
					"posting_time": sabb.posting_time,
				}
			)
		)

		return batch_obj.get_incoming_rate()

	# Get valuation rate from last sle for the same item and warehouse
	if last_valuation_rate := frappe.db.sql(  # nosemgrep
		"""select valuation_rate
		from `tabStock Ledger Entry` force index (item_warehouse)
		where
			item_code = %s
			AND warehouse = %s
			AND valuation_rate >= 0
			AND is_cancelled = 0
			AND NOT (voucher_no = %s AND voucher_type = %s)
		order by posting_datetime desc, creation desc limit 1""",
		(item_code, warehouse, voucher_no, voucher_type),
	):
		return flt(last_valuation_rate[0][0])
	
	# If negative stock allowed, and item delivered without any incoming entry,
	# system does not found any SLE, then take valuation rate from Item
	valuation_rate = frappe.db.get_value("Item", item_code, "valuation_rate")

	if not valuation_rate:
		# try Item Standard rate
		valuation_rate = frappe.db.get_value("Item", item_code, "standard_rate")

		if not valuation_rate:
			# try in price list
			valuation_rate = frappe.db.get_value(
				"Item Price", dict(item_code=item_code, buying=1, currency=currency), "price_list_rate"
			)
	return valuation_rate

def update_leave_salary(doc, method=None):
	if doc.leave_type == "Annual Vacation" and doc.custom_payment_type in ['Pay Now','Pay With Payroll',"Unpaid"] and not doc.is_new():
		from jgb.jgb.teampro.leave_application import calculate_vacation_pay_by_month
		result = calculate_vacation_pay_by_month(doc.name, cint(doc.custom_pay_hra_only or 0))
		doc.custom_leave_salary_amount = round(sum(flt(r["amount"]) for r in result), 2)


def get_salary_structure_assignment(employee, from_date):
	return frappe.db.get_value(
		"Salary Structure Assignment",
		{
			"employee": employee,
			"docstatus": 1,
			"from_date": ("<=", from_date)
		},
		["name", "salary_structure"],
		order_by="from_date desc"
	)


def get_applicable_promotion(employee, from_date, to_date):
	emp = frappe.get_doc("Employee", employee)

	promotions = [
		row for row in emp.custom_internal_work_historys
		if row.promotion_date
		and getdate(row.promotion_date) >= getdate(from_date)
		and getdate(row.promotion_date) <= getdate(to_date)
	]

	if not promotions:
		return None

	return sorted(promotions, key=lambda x: getdate(x.promotion_date))[0]


def get_latest_promotion(employee):
	emp = frappe.get_doc("Employee", employee)

	promotions = [
		row for row in emp.custom_internal_work_historys
		if row.promotion_date
	]

	if not promotions:
		return None

	return sorted(promotions, key=lambda x: getdate(x.promotion_date), reverse=True)[0]


def split_period(from_date, to_date):
	periods = []
	current = getdate(from_date)

	while current <= getdate(to_date):
		month_end = get_last_day(current)
		period_end = min(month_end, getdate(to_date))
		periods.append((current, period_end))
		current = add_days(period_end, 1)

	return periods


def get_month_days(date):
	return date_diff(get_last_day(date), get_first_day(date)) + 1


def prorate(amount, days, month_days):
	if not amount or not days:
		return 0
	return (amount / 30) * days


PROMOTION_FIELD_MAP = {
	"Basic": "basic",
	"HRA": "hra",
}

EMPLOYEE_FIELD_MAP = {
	"Basic": "custom_basic",
	"HRA": "custom_hra",
}

COMPONENT_OLD_DAYS_FIELD = {
	"Basic": "custom_old_salary_days",
	"HRA": "custom_old_hra_days",
}


@frappe.whitelist()
def calculate_leave_salary(name,hra):
	doc = frappe.get_doc("Leave Application", name)

	# if doc.leave_type != "Annual Vacation" or doc.custom_payment_type == "Pay With Payroll":
	# 	return {"total": 0, "components": []}
	if doc.leave_type != "Annual Vacation":
		return {"total": 0, "components": []}

	employee = frappe.get_doc("Employee", doc.employee)

	periods = split_period(doc.from_date, doc.to_date)

	from_date = getdate(doc.from_date)
	latest_promotion = get_latest_promotion(doc.employee)
	period_promotion = get_applicable_promotion(
		doc.employee,
		doc.from_date,
		doc.to_date,
	)

	total_amount = 0
	components = []

	for component, emp_field in EMPLOYEE_FIELD_MAP.items():
		emp_amt = float(employee.get(emp_field) or 0)

		old_days = float(doc.get(COMPONENT_OLD_DAYS_FIELD.get(component)) or 0)
		if hra == 1 and component == "Basic" and not old_days:
			continue
		if old_days > 0:
			promotion_row = latest_promotion
			promo_date = (
				add_days(from_date, old_days)
				if promotion_row or (hra == 1 and component == "Basic") else None
			)
		else:
			promotion_row = period_promotion
			promo_date = (
				getdate(period_promotion.promotion_date)
				if period_promotion else None
			)
		promo_frac = old_days % 1

		component_total = 0
		breakdown = []

		# Determine promotion values once per component
		old_amt = emp_amt
		new_amt = emp_amt

		if promotion_row and component in PROMOTION_FIELD_MAP:
			field = PROMOTION_FIELD_MAP[component]
			old_amt = float(promotion_row.get(field) or emp_amt)
			new_amt = float(promotion_row.get("new_" + field) or old_amt)

		if hra == 1 and component == "Basic":
			old_amt = emp_amt
			new_amt = 0

		for start, end in periods:
			month_days = get_month_days(start)
			days = date_diff(end, start) + 1

			# Promotion splits inside this period
			if promo_date and (start < promo_date <= end or (start == promo_date and promo_frac)) and old_amt != new_amt:

				before_days = date_diff(add_days(promo_date, -1), start) + 1 + promo_frac
				after_days = date_diff(end, promo_date) + 1 - promo_frac

				amt1 = prorate(old_amt, before_days, month_days)
				amt2 = prorate(new_amt, after_days, month_days)

				component_total += amt1 + amt2

				breakdown.append({
					"from": start,
					"to": promo_date if promo_frac else add_days(promo_date, -1),
					"days": before_days,
					"rate": "Previous Salary",
					"amount": round(amt1, 2)
				})

				breakdown.append({
					"from": promo_date,
					"to": end,
					"days": after_days,
					"rate": "Revised Salary",
					"amount": round(amt2, 2)
				})

			elif promo_date and end < promo_date:
				amt = prorate(old_amt, days, month_days)
				component_total += amt

				breakdown.append({
					"from": start,
					"to": end,
					"days": days,
					"rate": "Previous Salary",
					"amount": round(amt, 2)
				})

			elif promo_date and start >= promo_date:
				amt = prorate(new_amt, days, month_days)
				component_total += amt

				breakdown.append({
					"from": start,
					"to": end,
					"days": days,
					"rate": "Revised Salary",
					"amount": round(amt, 2)
				})

			else:
				amt = prorate(emp_amt, days, month_days)
				component_total += amt

				breakdown.append({
					"from": start,
					"to": end,
					"days": days,
					"rate": "No Change",
					"amount": round(amt, 2)
				})

		total_amount += component_total

		components.append({
			"component": component,
			"total": round(component_total, 2),
			"breakdown": breakdown
		})

	return {
		"total": round(total_amount, 2),
		"components": components
	}


@frappe.whitelist()
def return_leave_details(employee, from_date):
	data = get_leave_details(employee, from_date)
	if not data or not data.get("leave_allocation"):
		return "<p>No leave records found.</p>"
	leave_allocations = data.get("leave_allocation", {})
	html = """
	<table class="table table-bordered small">
		<thead>
			<tr>
				<th style="width:16%">Leave Type</th>
				<th style="width:16%; text-align:right;">Total Allocated Leaves</th>
				<th style="width:16%; text-align:right;">Used Leaves</th>
				<th style="width:16%; text-align:right;">Leaves Pending Approval</th>
				<th style="width:16%; text-align:right;">Available Leaves</th>
			</tr>
		</thead>
		<tbody>
	"""
	for leave_type, details in leave_allocations.items():
		total = flt(details.get("total_leaves"))
		taken = flt(details.get("leaves_taken"))
		pending = flt(details.get("leaves_pending_approval"))
		balance = flt(details.get("remaining_leaves"))
		balance_style = "color:red; font-weight:600;" if balance < 1 else ""
		html += f"""
			<tr>
				<td>{leave_type}</td>
				<td style="text-align:right;">{total:.2f}</td>
				<td style="text-align:right;">{taken:.2f}</td>
				<td style="text-align:right;">{pending:.2f}</td>
				<td style="text-align:right; {balance_style}">{balance:.2f}</td>
			</tr>
		"""
	html += """</tbody></table>"""
	return html



@frappe.whitelist()
def remove_paid_amount_during_delete(doc, method):
	if doc.docstatus==2:
		return
	if not doc.custom_pending_payment:
		return
	for i in doc.custom_pending_payment:
		if i.leave_application:
			if frappe.db.exists("Leave Application",{'name':i.leave_application}):
				la_doc=frappe.get_doc('Leave Application',i.leave_application)
				la_doc.custom_paid_amount=la_doc.custom_paid_amount-i.payable
				la_doc.save(ignore_permissions=True)



@frappe.whitelist()
def update_paid_amount_in_entry(doc, method):
	if not doc.custom_pay_now_reference:
		return
	la = frappe.get_doc("Leave Application", doc.custom_pay_now_reference)
	if not la.custom_pending_payment:
		return
	payable=0
	for row in la.custom_pending_payment:
		payable+=row.payable
		doc.append("custom_pending_payment", {
			"leave_application": row.leave_application,
			"payable": row.payable,
			"payable_type": row.payable_type,
			"payable_days": row.payable_days
		})
	if doc.paid_amount < payable:
		frappe.throw(f'Payable amount should be greater than {payable}')

@frappe.whitelist()
def update_paid_amount_in_la(doc, method):
	if not doc.custom_pay_now_reference:
		return
	
	payable=0
	if doc.custom_pending_payment:
		for i in doc.custom_pending_payment:
			if i.leave_application:
				if frappe.db.exists("Leave Application",{'name':i.leave_application}):
					la_doc=frappe.get_doc('Leave Application',i.leave_application)
					la_doc.custom_paid_amount=la_doc.custom_paid_amount+i.payable
					payable+=i.payable
					la_doc.save(ignore_permissions=True)
	if doc.paid_amount > payable:
		pay_now=doc.paid_amount-payable
		la_doc=frappe.get_doc('Leave Application',doc.custom_pay_now_reference)
		la_doc.custom_paid_amount=la_doc.custom_paid_amount+pay_now
		la_doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_unclaimed_leave(employee,vacation_from,vacation_to,name):
	paid_amount=0
	from_days = add_days(vacation_from, -1)
	balance = get_leave_details(employee, from_days)
	remaining = 0
	if balance.get("leave_allocation"):
		annual = balance["leave_allocation"].get("Annual Vacation")
		if annual:
			remaining = annual.get("remaining_leaves", 0)
	if remaining <= 0:
		return []
	claimed=0
	la=frappe.db.get_all('Leave Application',{'leave_type':'Annual Vacation','employee':employee,'custom_vacation_period_from_date':vacation_from,
	'name':('!=',name),'custom_vacation_period_to_date':vacation_to,'docstatus':1,'status':'Approved','workflow_state':'Approved'},['name'])
	for l in la:
		la_doc=frappe.get_doc('Leave Application',l.name)
		for p in la_doc.custom_pending_payment:
			if p.payable_type=='Unclaimed Leave':
				claimed+=p.payable_days or 0
	if claimed > 0:
		remaining=remaining-claimed
	if remaining <= 0:
		return []
	month_date=add_days(vacation_from,-1)
	month_start = get_first_day(month_date)
	month_end = get_last_day(month_date)

	emp = frappe.get_doc("Employee", employee)
	current_basic = emp.custom_basic or 0
	history = emp.custom_internal_work_historys or []
	leave_start = getdate(month_date)
	leave_end = add_days(leave_start, remaining - 1)
	promotion = None
	for row in history:
		if row.promotion_date and row.new_basic and row.new_basic > 0:
			promo_date = getdate(row.promotion_date)
			if getdate(month_start) <= promo_date <= getdate(month_end):
				promotion = row
				break
	month_days=date_diff(month_end,month_start)+1
	old_days = remaining
	new_days = 0
	old_basic = (current_basic/month_days)*old_days
	new_basic = 0

	if promotion:
		promo_date = getdate(promotion.promotion_date)
		if leave_start < promo_date <= leave_end:
			old_days = (promo_date - leave_start).days
			new_days = remaining - old_days
			old_basic = (promotion.basic/month_days)*old_days or 0
			new_basic = (current_basic/month_days)*new_days
	paid_amount=new_basic+old_basic
	return {
		"paid_amount": paid_amount,
		"paid_type": 'Unclaimed Leave',
		"total_days": remaining
	}

@frappe.whitelist()
def update_paid_amount(doc,method):
	if doc.custom_pay_now_reference:
		if frappe.db.exists('Leave Application',{'name':doc.custom_pay_now_reference}):
			la=frappe.get_doc('Leave Application',doc.custom_pay_now_reference)
			paid=la.custom_paid_amount+doc.paid_amount
			frappe.db.set_value("Leave Application",doc.custom_pay_now_reference,'custom_paid_amount',paid)
@frappe.whitelist()
# def remove_paid_amount_during_cancellation(doc,method):
#     if doc.custom_pay_now_reference:
#         if frappe.db.exists('Leave Application',{'name':doc.custom_pay_now_reference}):
#             la=frappe.get_doc('Leave Application',doc.custom_pay_now_reference)
#             paid=la.custom_paid_amount-doc.paid_amount
#             frappe.db.set_value("Leave Application",doc.custom_pay_now_reference,'custom_paid_amount',paid)
@frappe.whitelist()
def remove_paid_amount_during_deletion(doc,method):
	if doc.docstatus==0:
		pending=0
		if doc.custom_pending_payment:
			for d in doc.custom_pending_payment:
				if d.leave_application:
					la=frappe.get_doc('Leave Application',d.leave_application)
					paid=la.custom_paid_amount-d.payable
					pending+=paid
					frappe.db.set_value("Leave Application",d.leave_application,'custom_paid_amount',paid)
		if doc.custom_pay_now_reference:
			if frappe.db.exists('Leave Application',{'name':doc.custom_pay_now_reference}):
				la=frappe.get_doc('Leave Application',doc.custom_pay_now_reference)
				paid=doc.paid_amount-pending
				deduction=doc.paid_amount-paid
				frappe.db.set_value("Leave Application",doc.custom_pay_now_reference,'custom_paid_amount',deduction)
@frappe.whitelist()
def remove_paid_amount_during_cancel(doc,method):
	if doc.docstatus==2:
		pending=0
		if doc.custom_pending_payment:
			for d in doc.custom_pending_payment:
				if d.leave_application:
					la=frappe.get_doc('Leave Application',d.leave_application)
					paid=la.custom_paid_amount-d.payable
					pending+=paid
					frappe.db.set_value("Leave Application",d.leave_application,'custom_paid_amount',paid)
		if doc.custom_pay_now_reference:
			if frappe.db.exists('Leave Application',{'name':doc.custom_pay_now_reference}):
				la=frappe.get_doc('Leave Application',doc.custom_pay_now_reference)
				paid=doc.paid_amount-pending
				deduction=doc.paid_amount-paid
				frappe.db.set_value("Leave Application",doc.custom_pay_now_reference,'custom_paid_amount',deduction)  


def _payable_leave_salary(la, lwp_types):
	"""Leave salary payable for a pending-provision row: the stored amount,
	or the vacation-pay calculation for is_lwp leave types (whose
	custom_leave_salary_amount is left 0)."""
	leave_salary = la.custom_leave_salary_amount or 0
	if not leave_salary and la.leave_type in lwp_types:
		from jgb.jgb.teampro.leave_application import calculate_vacation_pay_by_month
		leave_salary = round(
			sum(flt(r["amount"]) for r in calculate_vacation_pay_by_month(la.name)),
			2,
		)
	return leave_salary


def _get_pending_leave_balances(employee, from_date, payment_type):
	lwp_types = set(frappe.get_all("Leave Type", {"is_lwp": 1}, pluck="name"))

	filters = {
		"docstatus": 1,
		"status": "Approved",
		"workflow_state": "Approved",
		"employee": employee,
		"to_date": ("<", from_date),
	}
	or_filters = None
	if payment_type == "Unpaid" and lwp_types:
		# Unpaid provision = (Annual Vacation + Unpaid) OR (any is_lwp leave
		# app, whatever its payment type). or_filters ORs the entries;
		# non-Annual-Vacation non-lwp rows are dropped in the loop below.
		or_filters = [
			{"custom_payment_type": "Unpaid"},
			{"leave_type": ["in", list(lwp_types)]},
		]
	else:
		filters["custom_payment_type"] = payment_type

	leaves = frappe.db.get_all(
		"Leave Application",
		filters=filters,
		or_filters=or_filters,
		fields=["name","leave_type","custom_payment_type","custom_leave_salary_amount",
			"custom_paid_amount"])

	# already queued/paid through another leave's Pending Payment rows
	linked_elsewhere = set(
		frappe.get_all(
			"Pending Payment",
			filters={"docstatus": ["!=", 2]},
			pluck="leave_application",
		)
	)

	data = []

	for la in leaves:
		if la.leave_type != "Annual Vacation" and la.leave_type not in lwp_types:
			continue
		if la.name in linked_elsewhere:
			continue
		balance = _payable_leave_salary(la, lwp_types) - (la.custom_paid_amount or 0)

		if balance > 0:
			data.append({
				"name": la.name,
				# lwp rows list under any payment type; show the leave
				# type so the row is identifiable in the dialog
				"custom_payment_type": (
					la.leave_type
					if la.leave_type != "Annual Vacation"
					else la.custom_payment_type
				),
				"balance_amount": balance
			})

	return data


@frappe.whitelist()
def get_unpaid_pay_now_amount(employee, from_date):
	return _get_pending_leave_balances(employee, from_date, "Pay Now")


@frappe.whitelist()
def get_unpaid_amount(employee, from_date):
	return _get_pending_leave_balances(employee, from_date, "Unpaid")

@frappe.whitelist()
def set_sent_for_approval(name,field_name,approve):
	if approve != "Rej":
		frappe.db.set_value(
			"Leave Application",
			name,
			field_name,
			1,
			update_modified=False
		)
		if field_name=='custom_sent_for_approval':
			frappe.db.set_value(
			"Leave Application",
			name,
			'custom_hod_approved',
			1,
			update_modified=False
		)
	if approve=='Yes':
		
		frappe.db.set_value(
		"Leave Application",
			name,
			'custom_approved_ticket',
			1,
			update_modified=False
		)
		if field_name=='custom_finance_approved_return':
			frappe.db.set_value(
			"Leave Application",
				name,
				'custom_approved_ticket_return',
				1,
				update_modified=False
			)
	if approve=='Rej':
		
		if field_name=='custom_hod_approved':
			reject_field='custom_hr_rejected'
		
		else:
			reject_field='custom_finance_rejected'
		frappe.db.set_value(
		"Leave Application",
			name,
			reject_field,
			1,
			update_modified=False
		)

	return 'Updated'

@frappe.whitelist()
def update_la_status(doc,method):
	if doc.custom_entry_and_exit_reference:
		if frappe.db.exists("Leave Application",doc.custom_entry_and_exit_reference):
			frappe.db.set_value("Leave Application",doc.custom_entry_and_exit_reference,"custom_entryexit_payment_status","Paid")

@frappe.whitelist()
def update_la_status_cancel(doc,method):
	if doc.custom_entry_and_exit_reference:
		if frappe.db.exists("Leave Application",doc.custom_entry_and_exit_reference):
			frappe.db.set_value("Leave Application",doc.custom_entry_and_exit_reference,"custom_entryexit_payment_status","Unpaid")


@frappe.whitelist()
def remove_paid_amount_during_cancel(doc,method):
	if doc.docstatus==2:
		pending=0
		if doc.custom_pending_payment:
			for d in doc.custom_pending_payment:
				if d.leave_application:
					la=frappe.get_doc('Leave Application',d.leave_application)
					paid=la.custom_paid_amount-d.payable
					pending+=paid
					frappe.db.set_value("Leave Application",d.leave_application,'custom_paid_amount',paid)
		if doc.custom_pay_now_reference:
			if frappe.db.exists('Leave Application',{'name':doc.custom_pay_now_reference}):
				la=frappe.get_doc('Leave Application',doc.custom_pay_now_reference)
				paid=doc.paid_amount-pending
				deduction=doc.paid_amount-paid
				frappe.db.set_value("Leave Application",doc.custom_pay_now_reference,'custom_paid_amount',deduction)  


@frappe.whitelist()
def getstock_detail_dn(item_details, company, docname):

	import json
	from frappe.utils import flt

	item_details = json.loads(item_details)

	data = ''
	data += '<h4><center><b>STOCK DETAILS</b></center></h4>'
	data += """
		<style>
		.table th, .table td{
			font-size:12px;
		}
		</style>
"""
	data += '<div style="overflow:auto; max-height:500px; border:1px solid #d1d8dd;">'
	data += '<table class="table table-bordered" style="min-width:2000px;">'
	warehouses = frappe.db.get_list(
		"Warehouse",
		filters={"company": company, "disabled": 0},
		fields=["name"],
		order_by="name asc"
	)

	warehouse_count = len(warehouses)

	data += '<tr>'

	data += '<td rowspan="2" style="width:5%;border:1px solid black;background:#75506A;color:white;text-align:center;"><b>S#</b></td>'
	data += '<td rowspan="2" style="width:12%;border:1px solid black;background:#75506A;color:white;text-align:center;"><b>ITEM CODE</b></td>'
	data += '<td rowspan="2" style="min-width:350px;border:1px solid black;background:#75506A;color:white;text-align:center;"><b>ITEM NAME</b></td>'
	data += '<td rowspan="2" style="border:1px solid black;background:#75506A;color:white;text-align:center;"><b>TOTAL STOCK</b></td>'

	data += f'<td colspan="{warehouse_count}" style="border:1px solid black;background:#75506A;color:white;text-align:center;"><b>AVAILABLE</b></td>'
	# data += f'<td colspan="{warehouse_count}" style="border:1px solid black;background:#75506A;color:white;text-align:center;"><b>INT HSI</b></td>'

	data += '<td style="border:1px solid black;background:#75506A;color:white;text-align:center;"><b>Completed</b></td>'
	data += '<td style="border:1px solid black;background:#75506A;color:white;text-align:center;"><b>Pending</b></td>'

	data += '</tr>'
	data += '<tr>'

	for wh in warehouses:
		wh_short = wh["name"].split(" - ")[0]
		data += f'<td style="border:1px solid black;background:#75506A;color:white;text-align:center;"><b>{wh["name"]}</b></td>'

	# for wh in warehouses:
	#     wh_short = wh["name"].split(" - ")[0]
	#     data += f'<td style="border:1px solid black;background:#75506A;color:white;text-align:center;"><b>{wh_short}</b></td>'

	data += '<td style="border:1px solid black;background:#75506A;color:white;text-align:center;"><b>SI</b></td>'
	data += '<td style="border:1px solid black;background:#75506A;color:white;text-align:center;"><b>SI</b></td>'

	data += '</tr>'

	def calculate_item(item_code, required_qty):

		total_stock = 0
		warehouse_stock_map = {}
		warehouse_in_transit = {}

		for wh in warehouses:

			bin_data = frappe.db.get_value(
				"Bin",
				{"item_code": item_code, "warehouse": wh["name"]},
				["actual_qty", "reserved_stock"],
				as_dict=1
			)

			actual = flt(bin_data.actual_qty) if bin_data else 0
			reserved = flt(bin_data.reserved_stock) if bin_data else 0

			available = actual - reserved

			warehouse_stock_map[wh["name"]] = available
			total_stock += available

			po_data = frappe.db.sql("""
				SELECT SUM(poi.qty) as qty, SUM(poi.received_qty) as r_qty
				FROM `tabPurchase Order` po
				JOIN `tabPurchase Order Item` poi ON po.name = poi.parent
				WHERE poi.warehouse=%s
				AND poi.item_code=%s
				AND po.docstatus=1
				AND po.status!='Closed'
			""", (wh["name"], item_code), as_dict=True)[0]

			in_transit = (po_data["qty"] or 0) - (po_data["r_qty"] or 0)

			warehouse_in_transit[wh["name"]] = in_transit

		si_qty_count = frappe.db.sql("""
			SELECT SUM(sii.qty)
			FROM `tabSales Invoice Item` sii
			INNER JOIN `tabDelivery Note Item` dni
			ON sii.dn_detail = dni.name
			WHERE dni.parent=%s
			AND sii.item_code=%s
			AND sii.docstatus IN (0,1)
		""", (docname, item_code))[0][0] or 0

		si_qty_pend = required_qty - si_qty_count

		return {
			"total_stock": total_stock,
			"warehouse_stock_map": warehouse_stock_map,
			"warehouse_in_transit": warehouse_in_transit,
			"si_count": si_qty_count,
			"si_pend": si_qty_pend
		}

	for idx, j in enumerate(item_details, start=1):

		bundle_items = frappe.db.get_all(
			"Product Bundle Item",
			filters={"parent": j["item_code"]},
			fields=["item_code", "qty"]
		)

		if not bundle_items:

			result = calculate_item(j["item_code"], j["qty"])

			data += '<tr>'
			data += f'<td style="border:1px solid black;text-align:center;">{idx}</td>'
			data += f'<td style="border:1px solid black;white-space:nowrap;">{j["item_code"]}</td>'
			data += f'<td style="border:1px solid black;">{j["item_name"]}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["total_stock"]:.2f}</td>'

			for wh in warehouses:
				data += f'<td style="border:1px solid black;text-align:center;">{result["warehouse_stock_map"][wh["name"]]:.2f}</td>'

			
			data += f'<td style="border:1px solid black;text-align:center;">{result["si_count"]:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["si_pend"]:.2f}</td>'

			data += '</tr>'
		else:

			parent_wh_stock = {}

			for wh in warehouses:

				ratios = []

				for b in bundle_items:

					child_res = calculate_item(b["item_code"], b["qty"])

					stock = child_res["warehouse_stock_map"][wh["name"]]

					ratio = stock // b["qty"] if b["qty"] else 0

					ratios.append(ratio)

				parent_wh_stock[wh["name"]] = min(ratios) if ratios else 0

			parent_total = sum(parent_wh_stock.values())

			parent_si = frappe.db.sql("""
				SELECT SUM(sii.qty)
				FROM `tabSales Invoice Item` sii
				INNER JOIN `tabDelivery Note Item` dni
				ON sii.dn_detail = dni.name
				WHERE dni.parent=%s
				AND sii.item_code=%s
				AND sii.docstatus IN (0,1)
			""", (docname, j["item_code"]))[0][0] or 0

			parent_si_pend = j["qty"] - parent_si

			data += '<tr style="background:#e6f2ff;font-weight:bold;">'
			data += f'<td style="border:1px solid black;text-align:center;">{idx}</td>'
			data += f'<td style="border:1px solid black;white-space:nowrap;">{j["item_code"]}</td>'
			data += f'<td style="border:1px solid black;">{j["item_name"]} (Bundle)</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{parent_total:.2f}</td>'

			for wh in warehouses:
				data += f'<td style="border:1px solid black;text-align:center;">{parent_wh_stock[wh["name"]]:.2f}</td>'

			
			data += f'<td style="border:1px solid black;text-align:center;">{parent_si:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{parent_si_pend:.2f}</td>'

			data += '</tr>'

			for b in bundle_items:

				child_required_qty = j["qty"] * b["qty"]

				child_result = calculate_item(b["item_code"], child_required_qty)

				item_name = frappe.db.get_value("Item", b["item_code"], "item_name")

				data += '<tr style="background:#f9f9f9;">'
				data += '<td style="border:1px solid black;"></td>'
				data += f'<td style="border:1px solid black;padding-left:25px;white-space:nowrap;">↳ {b["item_code"]}</td>'
				data += f'<td style="border:1px solid black;">{item_name}</td>'
				data += f'<td style="border:1px solid black;text-align:center;">{child_result["total_stock"]:.2f}</td>'

				for wh in warehouses:
					data += f'<td style="border:1px solid black;text-align:center;">{child_result["warehouse_stock_map"][wh["name"]]:.2f}</td>'

				# for wh in warehouses:
				#     data += f'<td style="border:1px solid black;text-align:center;">{child_result["warehouse_in_transit"][wh["name"]]:.2f}</td>'

				data += '<td colspan="2" style="border:1px solid black;text-align:center;">-</td>'
				data += '</tr>'

	data += '</table></div>'

	return data

@frappe.whitelist()
def getstock_detail_so(item_details, company, docname):

	import json
	item_details = json.loads(item_details)
	data = ''
	data += '<h4><center><b>STOCK DETAILS</b></center></h4>'
	data += '<div style="overflow:auto; max-height:500px; border:1px solid #d1d8dd;">'
	data += '<table class="table table-bordered" style="min-width:1900px;">'
	warehouses = frappe.db.get_list(
		"Warehouse",
		filters={"company": company,"disabled":0},
		fields=["name"],
		order_by="name asc"
	)
	warehouse_count = len(warehouses)
	data += '<tr>'
	data += '<th rowspan="2" style="width:4%;text-align:center;border:1px solid black;background:#75506A;color:white;">S#</th>'
	data += '<th rowspan="2" style="width:12%;text-align:center;border:1px solid black;background:#75506A;color:white;">ITEM CODE</th>'
	data += '<th rowspan="2" style="width:20%;text-align:center;border:1px solid black;background:#75506A;color:white;">ITEM NAME</th>'
	data += '<th rowspan="2" style="width:7%;text-align:center;border:1px solid black;background:#75506A;color:white;">SO QTY</th>'
	data += '<th rowspan="2" style="width:7%;text-align:center;border:1px solid black;background:#75506A;color:white;">TOTAL STOCK</th>'
	data += '<th rowspan="2" style="width:7%;text-align:center;border:1px solid black;background:#75506A;color:white;">RESERVED QTY (SO)</th>'
	data += '<th rowspan="2" style="width:7%;text-align:center;border:1px solid black;background:#75506A;color:white;">TOTAL RESERVED</th>'
	data += f'<th colspan="{warehouse_count}" style="text-align:center;border:1px solid black;background:#75506A;color:white;">AVAILABLE</th>'

	data += '<th colspan="2" style="text-align:center;border:1px solid black;background:#75506A;color:white;">COMPLETED</th>'
	data += '<th colspan="2" style="text-align:center;border:1px solid black;background:#75506A;color:white;">PENDING</th>'

	data += '<th rowspan="2" style="width:6%;text-align:center;border:1px solid black;background:#75506A;color:white;">TO RECEIVE</th>'
	data += '<th rowspan="2" style="width:6%;text-align:center;border:1px solid black;background:#75506A;color:white;">TO SELL</th>'
	data += '</tr>'
	data += '<tr>'
	for wh in warehouses:
		wh_short = wh["name"].split(" - ")[0]
		data += f'<th style="border:1px solid black;background:#75506A;color:white;text-align:center;">{wh["name"]}</th>'

	data += '<th style="border:1px solid black;background:#75506A;color:white;text-align:center;">DN</th>'
	data += '<th style="border:1px solid black;background:#75506A;color:white;text-align:center;">SI</th>'
	data += '<th style="border:1px solid black;background:#75506A;color:white;text-align:center;">DN</th>'
	data += '<th style="border:1px solid black;background:#75506A;color:white;text-align:center;">SI</th>'
	data += '</tr>'
	def calculate_item(item_code, required_qty):

		total_stock = 0
		reserved_qty = 0
		warehouse_stock_map = {}

		new_po = frappe.db.sql("""
			select sum(poi.qty) as qty, sum(poi.received_qty) as d_qty
			from `tabPurchase Order` po
			left join `tabPurchase Order Item` poi on po.name = poi.parent
			where poi.item_code = %s and po.docstatus = 1 and po.status != 'Closed'
		""", item_code, as_dict=True)[0]

		in_transit = (new_po["qty"] or 0) - (new_po["d_qty"] or 0)

		new_so = frappe.db.sql("""
			select sum(soi.qty) as qty, sum(soi.delivered_qty) as d_qty,soi.qty as so_qty
			from `tabSales Order` so
			left join `tabSales Order Item` soi on so.name = soi.parent
			where soi.item_code = %s and so.docstatus = 1 and so.status != 'Closed' 
		""", item_code, as_dict=True)[0]
		new_so_qty = frappe.db.sql("""
			select sum(soi.qty) as qty, sum(soi.delivered_qty) as d_qty
			from `tabSales Order` so
			left join `tabSales Order Item` soi on so.name = soi.parent
			where soi.item_code = %s
			and so.name = %s
		""", (item_code, docname), as_dict=True)[0]
		total_reserved_qty = frappe.db.sql("""
			SELECT 
				SUM(
					CASE
						WHEN status = 'Reserved'
							THEN reserved_qty

						WHEN status = 'Partially Reserved'
							THEN reserved_qty

						WHEN status = 'Partially Delivered'
							THEN (reserved_qty - delivered_qty)

						ELSE 0
					END
				) as total_reserved
			FROM `tabStock Reservation Entry`
			WHERE item_code = %s
			AND docstatus != 2
			AND status != 'Delivered'
		""", item_code, as_dict=True)[0]["total_reserved"] or 0
		so_qty = new_so_qty["qty"] or 0
		to_sell = (new_so["qty"] or 0) - (new_so["d_qty"] or 0)

		for wh in warehouses:

			st = frappe.db.get_value(
				"Bin",
				{"item_code": item_code, "warehouse": wh["name"]},
				"actual_qty"
			) or 0

			res = frappe.db.get_value(
				"Bin",
				{"item_code": item_code, "warehouse": wh["name"]},
				"reserved_stock"
			) or 0

			available_stock = st - res

			warehouse_stock_map[wh["name"]] = available_stock
			total_stock += available_stock

		res_qty = frappe.db.get_all(
			"Stock Reservation Entry",
			filters={
				"voucher_no": docname,
				"docstatus": ["!=", "2"],
				"item_code": item_code
			},
			pluck="reserved_qty"
		)

		reserved_qty = sum(res_qty)

		si_qty = frappe.db.sql("""
			SELECT SUM(qty)
			FROM `tabSales Invoice Item`
			WHERE sales_order=%s AND item_code=%s AND docstatus IN (0,1)
		""", (docname, item_code))[0][0] or 0

		dn_qty = frappe.db.sql("""
			SELECT SUM(qty)
			FROM `tabDelivery Note Item`
			WHERE against_sales_order=%s AND item_code=%s AND docstatus IN (0,1)
		""", (docname, item_code))[0][0] or 0

		si_pend = max(0, required_qty - si_qty)
		dn_pend = max(0, required_qty - dn_qty)

		return {
			"so_qty": so_qty,
			"total_stock": total_stock,
			"warehouse_stock_map": warehouse_stock_map,
			"dn_count": dn_qty,
			"si_count": si_qty,
			"dn_pend": dn_pend,
			"si_pend": si_pend,
			"reserved_qty": reserved_qty,
			"total_reserved_qty": total_reserved_qty,
			"in_transit": in_transit,
			"to_sell": to_sell
		}

	for idx, j in enumerate(item_details, start=1):

		bundle_items = frappe.db.get_all(
			"Product Bundle Item",
			filters={"parent": j["item_code"]},
			fields=["item_code", "qty"]
		)

		if not bundle_items:

			result = calculate_item(j["item_code"], j["qty"])

			data += '<tr>'
			data += f'<td style="border:1px solid black;text-align:center;padding:4px;">{idx}</td>'
			data += f'<td style="border:1px solid black;padding:4px;white-space:nowrap;">{j["item_code"]}</td>'
			data += f'<td style="border:1px solid black;padding:4px;">{j["item_name"]}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["so_qty"]:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["total_stock"]:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["reserved_qty"]:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["total_reserved_qty"]:.2f}</td>'
			
			for wh in warehouses:
				data += f'<td style="border:1px solid black;text-align:center;">{result["warehouse_stock_map"][wh["name"]]:.2f}</td>'

			data += f'<td style="border:1px solid black;text-align:center;">{result["dn_count"]:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["si_count"]:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["dn_pend"]:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["si_pend"]:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["in_transit"]:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{result["to_sell"]:.2f}</td>'
			data += '</tr>'

		else:

			parent_total = 0
			parent_wh_stock = {}

			for wh in warehouses:

				ratios = []

				for b in bundle_items:
					child_res = calculate_item(b["item_code"], b["qty"])
					stock = child_res["warehouse_stock_map"][wh["name"]]
					ratio = stock / b["qty"] if b["qty"] else 0
					ratios.append(ratio)

				min_stock = min(ratios) if ratios else 0
				parent_wh_stock[wh["name"]] = min_stock
				parent_total += min_stock

			parent_dn = frappe.db.sql("""
				SELECT SUM(qty)
				FROM `tabDelivery Note Item`
				WHERE against_sales_order=%s AND item_code=%s AND docstatus IN (0,1)
			""", (docname, j["item_code"]))[0][0] or 0

			parent_si = frappe.db.sql("""
				SELECT SUM(qty)
				FROM `tabSales Invoice Item`
				WHERE sales_order=%s AND item_code=%s AND docstatus IN (0,1)
			""", (docname, j["item_code"]))[0][0] or 0
			parent_calc = calculate_item(j["item_code"], j["qty"])
			parent_so_qty=frappe.db.sql("""select sum(soi.qty) from `tabSales Order` so left join `tabSales Order Item` soi on so.name=soi.parent where soi.item_code = %s and so.name = %s and so.docstatus = 1""", (j["item_code"], docname))[0][0] or 0
			parent_dn_pend = max(0, j["qty"] - parent_dn)
			parent_si_pend = max(0, j["qty"] - parent_si)
			
			data += '<tr style="background:#e6f2ff;font-weight:bold;">'
			data += f'<td style="border:1px solid black;text-align:center;">{idx}</td>'
			data += f'<td style="border:1px solid black;white-space:nowrap;">{j["item_code"]}</td>'
			data += f'<td style="border:1px solid black;">{j["item_name"]} (Bundle)</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{parent_so_qty:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{parent_total:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{parent_calc["reserved_qty"]:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{parent_calc["total_reserved_qty"]:.2f}</td>'
			for wh in warehouses:
				data += f'<td style="border:1px solid black;text-align:center;">{parent_wh_stock[wh["name"]]:.2f}</td>'

			data += f'<td style="border:1px solid black;text-align:center;">{parent_dn:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{parent_si:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{parent_dn_pend:.2f}</td>'
			data += f'<td style="border:1px solid black;text-align:center;">{parent_si_pend:.2f}</td>'
			data += '<td style="border:1px solid black;text-align:center;">-</td>'
			data += '<td style="border:1px solid black;text-align:center;">-</td>'
			data += '</tr>'

			for b in bundle_items:

				child_result = calculate_item(b["item_code"], b["qty"])
				item_name = frappe.db.get_value("Item", b["item_code"], "item_name")

				data += '<tr style="background:#f9f9f9;">'
				data += '<td style="border:1px solid black;"></td>'
				data += f'<td style="border:1px solid black;padding-left:25px;white-space:nowrap;">↳ {b["item_code"]}</td>'
				data += f'<td style="border:1px solid black;">{item_name}</td>'
				data += f'<td style="border:1px solid black;">-</td>'
				data += f'<td style="border:1px solid black;text-align:center;">{child_result["total_stock"]:.2f}</td>'
				data += f'<td style="border:1px solid black;text-align:center;">{child_result["reserved_qty"]:.2f}</td>'

				data += f'<td style="border:1px solid black;text-align:center;">{child_result["total_reserved_qty"]:.2f}</td>'
				for wh in warehouses:
					data += f'<td style="border:1px solid black;text-align:center;">{child_result["warehouse_stock_map"][wh["name"]]:.2f}</td>'

				data += '<td colspan="4" style="border:1px solid black;text-align:center;">-</td>'
				data += f'<td style="border:1px solid black;text-align:center;">{child_result["in_transit"]:.2f}</td>'
				data += f'<td style="border:1px solid black;text-align:center;">{child_result["to_sell"]:.2f}</td>'
				data += '</tr>'

	data += '</table></div>'

	return data



from jgb.jgb.doctype.accounts_report_dashboard.aging_report_summary_sales_person import accounts_aging
@frappe.whitelist()
def ageing_report_summary_sales_person(doc):
	import json, html
	from frappe.utils import cstr

	try:
		if isinstance(doc, str):
			doc = frappe._dict(json.loads(doc))

		if not doc.get("company"):
			frappe.throw("Kindly choose company")

		args = frappe._dict({
			"company": doc.get("company"),
			"sales_person": doc.get("sales_person") or None,
			"region": doc.get("region") or None,
			"to_date": doc.get("to_date") or None
		})

		data_rows = accounts_aging(args) or []

		html_output = """
		<table border='1' width='100%' style='border-collapse:collapse; table-layout:fixed;'>
		"""

		headers = [
			"Posting Date", "Voucher No", "Customer LPO",
			"Invoiced", "Paid", "Credit Note",
			"Outstanding", "Age", "0-30", "31-60", "61-90", "Above 90"
		]

		widths = ["9%", "12%", "15%", "8%", "8%", "8%", "8%", "4%", "7%", "7%", "7%", "7%"]

		html_output += "<thead><tr style='background:#0F0F5C;color:white;'>"

		for i, head in enumerate(headers):
			html_output += f"<th style='width:{widths[i]};text-align:center'>{head}</th>"

		html_output += "</tr></thead><tbody>"

		for row in data_rows:

			if not row:
				continue

			row_str = str(row[0]) if len(row) > 0 else ""

			if row_str.startswith("SALESPERSON:"):
				html_output += f"""
				<tr>
					<td colspan="12" style="background:#f5f5f5;font-weight:bold;font-size:14px;text-align:center;">
						{html.escape(row_str.replace("SALESPERSON:", "").strip())}
					</td>
				</tr>
				"""
				continue

			# subtotal / grand total
			if row_str.startswith("Subtotal:") or row_str == "GRAND TOTAL":

				html_output += "<tr style='font-weight:bold;background:#D9E1F2'>"
				html_output += f"<td colspan='3'>{html.escape(row_str)}</td>"

				for cell in row[3:]:
					html_output += f"<td style='text-align:right'>{html.escape(str(cell))}</td>"

			else:
				html_output += "<tr>"

				for i, cell in enumerate(row):
					align = "left" if i < 3 else "right"
					html_output += f"<td style='text-align:{align}'>{html.escape(str(cell))}</td>"

			html_output += "</tr>"

		html_output += "</tbody></table>"

		return cstr(html_output)

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Ageing Report Error")
		frappe.throw(f"Report Error: {str(e)}")

