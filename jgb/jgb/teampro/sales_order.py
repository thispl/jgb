import html

import frappe
from frappe.utils import flt
from frappe import _

@frappe.whitelist()
def create_logistics_request_for_sales_orders(so_names,cargo_type):
	import json

	if isinstance(so_names, str):
		so_names = json.loads(so_names)

	if not so_names:
		frappe.throw("No Sales Orders selected.")

	logistics_request = frappe.new_doc("Logistics Request")
	logistics_request.logistic_type = "Export"
	logistics_request.po_so = "Sales Order"
	total_amount = 0  # To accumulate grand total

	for po_name in so_names:
		po = frappe.get_doc("Sales Order", po_name)
		logistics_request.currency = po.currency
		logistics_request.conv_rate = po.conversion_rate
		logistics_request.cargo_type = cargo_type
		logistics_request.inventory_destination = "Direct to Customer"
		logistics_request.custom_customer_final_destination=po.customer
		for item in po.items:
			total_requested_qty = frappe.db.sql("""
				SELECT SUM(lri.qty)
				FROM `tabLogistics Request Item` lri
				JOIN `tabLogistics Request` lr ON lri.parent = lr.name
				WHERE lri.voucher_no = %s AND lri.item_code = %s AND lr.workflow_state != 'Draft'
			""", (po.name, item.item_code))[0][0] or 0
			pending_qty = item.qty - total_requested_qty

			if pending_qty > 0:
				rate = item.rate
				amount = pending_qty * rate
				base_rate = item.base_rate or rate * po.conversion_rate
				base_amount = item.base_amount or amount * po.conversion_rate

				logistics_request.append("product_description", {
					"item_code": item.item_code,
					"item_name": item.item_name,
					"description": item.description,
					"qty": pending_qty,
					"rate": rate,
					"uom": item.uom,
					"amount": amount,
					"conversion_factor": item.conversion_factor or 1,
					"base_rate": base_rate,
					"base_amount": base_amount,
					"voucher_no": po.name,
					"voucher_type": "Sales Order",
					"customer":po.customer,
					"requester_name":po.custom_sales_person,
					"box_name":item.custom_box_name,
					"pallet_name":item.custom_pallet_name,
					"no_of_boxes":item.custom_no_of_boxes,
					"no_of_pallets":item.custom_no_of_pallets,
					"total_box_weight_kg":item.custom_total_box_weight_kg,
					"total_pallet_weight_kg":item.custom_p_weight_per_unit_kg,
					"box_length_mm":item.custom_box_length_mm,
					"pallet_length_mm":item.custom_pallet_length_mm,
					"box_breadth_mm":item.custom_box_breadth_mm,
					"pallet_breadth_mm":item.custom_pallet_breadth_mm,
					"box_height_mm":item.custom_box_height_mm,
					"pallet_height_mm":item.custom_pallet_height_mm,
					"cbm":item.custom_cbm,
					"packing_weight_kg":item.custom_packing_weight_kg,
					"gross_weight_kg":item.custom_gross_weight_kg
				})

				total_amount += amount  # Accumulate amount
		box_data, pallet_data = get_box_summary_so(po_name)
		for row in box_data:
			logistics_request.append("box_summary_table", {
				"box": row.get("box"),
				"total_no_of_box": row.get("total_no_of_box"),
				"weight_per_unit": row.get("weight_per_unit"),
				"total_weight": row.get("total_weight"),
				"total_length": row.get("total_length"),
				"total_breadth": row.get("total_breadth"),
				"total_height": row.get("total_height")
			})

		for pal in pallet_data:
			logistics_request.append("pallet_summary", {
				"pallet": pal.get("box"),
				"total_no_of_pallet": pal.get("total_no_of_box"),
				"weight_per_unit": pal.get("weight_per_unit"),
				"total_weight": pal.get("total_weight"),
				"total_length": pal.get("total_length"),
				"total_breadth": pal.get("total_breadth"),
				"total_height": pal.get("total_height")
			})

	if not logistics_request.get("product_description"):
		frappe.throw("All selected Sales Orders are already fully included in previous Logistics Requests.")

	logistics_request.grand_total = total_amount  # Set computed grand total
	if total_amount>0:
		logistics_request.custom_duty =total_amount*0.45
	logistics_request.save(ignore_permissions=True)
	frappe.db.commit()

	return frappe.msgprint(f"Logistics Request <a href='/app/logistics-request/{logistics_request.name}'><b>{logistics_request.name}</b></a> created successfully.")




@frappe.whitelist()
def get_box_summary_so(po_name):
	if not frappe.db.exists("Sales Order", po_name):
		return [], []

	data = frappe.db.sql("""
	SELECT custom_box_name as box_name, custom_no_of_boxes as total_no,
		   SUM(IFNULL(custom_weight_per_unit_kg, 0)) as weight_per_unit,
		   SUM(IFNULL(custom_total_box_weight_kg, 0)) as total_weight,
		   SUM(IFNULL(custom_box_length_mm, 0)) as blength,
		   SUM(IFNULL(custom_box_height_mm, 0)) as bheight,
		   SUM(IFNULL(custom_box_breadth_mm, 0)) as bbreadth
	FROM `tabSales Order Item`
	WHERE parent = %s
	GROUP BY custom_box_name
""", (po_name,), as_dict=True)


	box_summary = [
		{
			"box": row.box_name,
			"total_no_of_box": row.total_no,
			"weight_per_unit": row.weight_per_unit,
			"total_weight": row.total_weight,
			"total_length": row.blength,
			"total_breadth": row.bbreadth,
			"total_height": row.bheight
		}
		for row in data if row.box_name and row.total_no
	]
	data2 = frappe.db.sql("""
		SELECT custom_pallet_name as pallet_name, custom_no_of_pallets as total_no,
			   SUM(custom_p_weight_per_unit_kg) as weight_per_unit,
			   SUM(custom_total_pallet_weight_kg) as total_weight,
			   SUM(custom_pallet_length_mm) as plength,
			   SUM(custom_pallet_breadth_mm) as pbreadth,
			   SUM(custom_pallet_height_mm) as pheight
		FROM `tabSales Order Item`
		WHERE parent = %s
		GROUP BY custom_pallet_name
	""", (po_name,), as_dict=True)

	pallet_summary = [
		{
			"box": row.pallet_name,
			"total_no_of_box": row.total_no,
			"weight_per_unit": row.weight_per_unit,
			"total_weight": row.total_weight,
			"total_length": row.plength,
			"total_breadth": row.pbreadth,
			"total_height": row.pheight
		}
		for row in data2 if row.pallet_name and row.total_no
	]
	return box_summary, pallet_summary



@frappe.whitelist()
def update_quote_value(estimation=None, margin=None):
	if estimation is None or margin is None:
		return 0
	value = 100 - float(margin)
	if value == 0:
		frappe.throw("Margin cannot be 100%: quoted value cannot be derived from the cost estimation.")
	quote_value = 100 * float(estimation) / float(value)
	return quote_value



import frappe
import re

@frappe.whitelist()
def get_cost_center_for_division(division=None, company=None):
	keyword = extract_keyword_from_division(division)

	if not keyword or not company:
		return ""

	cost_center = frappe.db.sql("""
		SELECT name FROM `tabCost Center`
		WHERE company = %s
		  AND is_group = 0
		  AND name LIKE %s
		LIMIT 1
	""", (
		company,
		f"%{keyword}%",
	), as_dict=0)

	return cost_center[0][0] if cost_center else ""



def extract_keyword_from_division(division):
	# Custom logic to extract from full name like "HVAC Division - (HVA)"
	match = re.search(r'([A-Za-z\s]+)\s+Division', division)
	if match:
		return match.group(1).strip()
	# fallback
	return division.split('-')[0].strip()




from frappe.utils import flt

@frappe.whitelist()
def get_so_qty_dashboard(sales_order):
    if not sales_order or not frappe.db.exists("Sales Order", sales_order):
        return {}

    so = frappe.get_doc("Sales Order", sales_order)
    item_map = {
        d.item_code: {
            "item_name": d.item_name or d.item_code,
            "description": html.unescape(frappe.utils.strip_html(d.description or "")).replace("\xa0", " "),
            "so_qty": 0.0,
            "delivered_qty": 0.0,
            "po_qty": 0.0,
            "received_qty": 0.0,
            "stock_qty": 0.0,
            "reserved_qty": 0.0,
        }
        for d in so.items
    }

    for d in so.items:
        item_map[d.item_code]["so_qty"] += flt(d.qty)
        item_map[d.item_code]["delivered_qty"] += flt(d.delivered_qty)

    for d in frappe.db.sql(
        """
        SELECT poi.item_code, SUM(poi.qty) as qty
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE po.docstatus = 1 AND poi.sales_order = %s
        GROUP BY poi.item_code
    """,
        (sales_order,),
        as_dict=1,
    ):
        if d.item_code in item_map:
            item_map[d.item_code]["po_qty"] += flt(d.qty)

    for d in frappe.db.sql(
        """
        SELECT pri.item_code, SUM(pri.qty) as qty
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
        JOIN `tabPurchase Order Item` poi ON poi.name = pri.purchase_order_item
        WHERE pr.docstatus = 1 AND poi.sales_order = %s
        GROUP BY pri.item_code
    """,
        (sales_order,),
        as_dict=1,
    ):
        if d.item_code in item_map:
            item_map[d.item_code]["received_qty"] += flt(d.qty)

    if item_map:
        item_codes = tuple(item_map.keys())
        for d in frappe.db.sql(
            """
            SELECT item_code, SUM(actual_qty) as actual_qty, SUM(reserved_qty) as reserved_qty
            FROM `tabBin`
            WHERE item_code IN %s
            GROUP BY item_code
        """,
            (item_codes,),
            as_dict=1,
        ):
            if d.item_code in item_map:
                item_map[d.item_code]["stock_qty"] += flt(d.actual_qty)
                item_map[d.item_code]["reserved_qty"] += flt(d.reserved_qty)

    totals = {
        "total_po_qty": sum(v["po_qty"] for v in item_map.values()),
        "total_received_qty": sum(v["received_qty"] for v in item_map.values()),
        "total_so_qty": sum(v["so_qty"] for v in item_map.values()),
        "total_delivered_qty": sum(v["delivered_qty"] for v in item_map.values()),
        "total_stock_qty": sum(v["stock_qty"] for v in item_map.values()),
        "total_reserved_qty": sum(v["reserved_qty"] for v in item_map.values()),
    }
    totals["balance_receive"] = totals["total_po_qty"] - totals["total_received_qty"]
    totals["balance_delivery"] = totals["total_so_qty"] - totals["total_delivered_qty"]
    totals["total_free_stock"] = totals["total_stock_qty"] - totals["total_reserved_qty"]

    items = []
    for item_code, data in item_map.items():
        items.append(
            {
                "item_code": item_code,
                "item_name": data["item_name"],
                "description": data["description"],
                "so_qty": data["so_qty"],
                "delivered_qty": data["delivered_qty"],
                "po_qty": data["po_qty"],
                "received_qty": data["received_qty"],
                "stock_qty": data["stock_qty"],
                "reserved_qty": data["reserved_qty"],
                "balance_receive": flt(data["po_qty"]) - flt(data["received_qty"]),
                "balance_delivery": flt(data["so_qty"]) - flt(data["delivered_qty"]),
                "free_stock": flt(data["stock_qty"]) - flt(data["reserved_qty"]),
            }
        )

    return {"items": items, "totals": totals}




@frappe.whitelist()
def download_so_qty_dashboard(sales_order):
    result = get_so_qty_dashboard(sales_order)
    if not result or not result.get("items"):
        frappe.throw("No data found for the selected Sales Order")

    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Font

    headers = [
        "Item",
        "Item Name",
        "Description",
        "Total Outgoing PO Qty",
        "Received Qty",
        "Balance to Receive",
        "SO Qty",
        "Delivered Qty",
        "Balance to Deliver",
        "Physical Stock",
        "Free Stock",
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "SO Qty Dashboard"
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])

    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for d in result["items"]:
        ws.append([
            d["item_code"],
            d["item_name"],
            d["description"],
            d["po_qty"],
            d["received_qty"],
            d["balance_receive"],
            d["so_qty"],
            d["delivered_qty"],
            d["balance_delivery"],
            d["stock_qty"],
            d["free_stock"],
        ])

    xlsx_file = BytesIO()
    wb.save(xlsx_file)

    frappe.response["filename"] = f"{sales_order}_qty_dashboard.xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"



import frappe
from frappe.utils.file_manager import save_file
from openpyxl import Workbook

@frappe.whitelist()
def get_item_template():

	wb = Workbook()
	ws = wb.active
	ws.title = "Item Template"

	# Add only headings
	ws.append(["Item Code", "Qty", "Rate"])

	# Save temporarily
	file_path = "/tmp/item_template.xlsx"
	wb.save(file_path)

	# Read file
	with open(file_path, "rb") as f:
		file = save_file(
			"Item_Template.xlsx",
			f.read(),
			None,   # dt → no doctype
			None,   # dn → no docname
			folder="Home/Attachments",
			is_private=0
		)

	return file.file_url



import frappe
import openpyxl
from openpyxl import Workbook
from io import BytesIO

@frappe.whitelist()
def get_item_without_code_template(brand=None, product=None):
	brand_doc = frappe.get_doc("Brand", brand)
	if brand_doc.custom_download_template:
		file_doc = frappe.get_doc(
			"File",
			{"file_url": brand_doc.custom_download_template}
		)
		file_content = file_doc.get_content()
		frappe.local.response.filename = file_doc.file_name
		frappe.local.response.filecontent = file_content
		frappe.local.response.type = "download"
		return
	headers = []
	if product:
		product_doc = frappe.get_doc("Product", product)
		for row in product_doc.product_naming:
			if row.title:
				headers.append(row.title)
	headers.extend(["Qty", "Rate"])
	wb = Workbook()
	ws = wb.active
	ws.title = "Template"
	for col_num, header in enumerate(headers, 1):
		ws.cell(row=1, column=col_num).value = header
	output = BytesIO()
	wb.save(output)
	frappe.local.response.filename = "Default_Template.xlsx"
	frappe.local.response.filecontent = output.getvalue()
	frappe.local.response.type = "download"



@frappe.whitelist()
def margin_tool(item_details, discount=None, per=None,total=None,tax=None):
	import json
	item_details = json.loads(item_details)

	data = ''
	data += """
		<br>
		<style>
			.margin-table {
				width: 100%;
				border-collapse: collapse;
				font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
				font-size: 12px;
				color: #333;
			}

			.margin-table th,
			.margin-table td {
				padding: 6px 8px;
				border: 1px solid #dcdcdc;
			}

			.margin-table thead th {
				background: linear-gradient(135deg, #75506A, #9A6C87);
				color: #fff;
				text-align: center;
				font-size: 13px;
				font-weight: 600;
			}

			.margin-table thead tr.title th {
				font-size: 15px;
				padding: 8px;
			}

			.margin-table tbody tr:nth-child(even) {
				background-color: #f9f9f9;
			}

			.margin-table tbody tr:hover {
				background-color: #f1edf0;
			}

			.text-right {
				text-align: right;
			}

			.text-center {
				text-align: center;
			}

			.summary-row td {
				font-weight: 600;
				background-color: #f4f4f4;
			}

			.net-total td {
				font-size: 13px;
				background-color: #75506A;
				color: #fff;
				font-weight: 700;
			}
			
		</style>

		<table class="margin-table">
			<thead>
				<tr class="title">
					<th colspan="10">ITEM DETAILS</th>
				</tr>
				<tr style="background: #e6e6e6; color: #333;">
					<th width="40" style="background: #e6e6e6; color: #333;">S#</th>
					<th width="250" style="background: #e6e6e6; color: #333;">Item Name</th>
					<th width="300" style="background: #e6e6e6; color: #333;">Description</th>
					<th width="70" style="background: #e6e6e6; color: #333;">Qty</th>
					<th width="70" style="background: #e6e6e6; color: #333;">UOM</th>
					<th width="70" style="background: #e6e6e6; color: #333;">Disc %</th>
					<th width="80" style="background: #e6e6e6; color: #333;">Disc Rate</th>
					<th width="90" style="background: #e6e6e6; color: #333;">Disc Amt</th>
					<th width="80" style="background: #e6e6e6; color: #333;">Unit Rate</th>
					<th width="90" style="background: #e6e6e6; color: #333;">Amount</th>
				</tr>
			</thead>
			<tbody>
		"""

	dis = 0
	amount = 0
	discount = float(discount) if discount else 0.0
	per = float(per) if per else 0.0
	total = float(total) if total else 0.0
	tax = float(tax) if tax else 0.0
	for idx, i in enumerate(item_details, start=1):
		dis += i["discount_amount"]
		amount += i["amount"]

		data += '''
		<tr>
			<td style="text-align:center;">{}</td>
			<td>{}</td>
			<td>{}</td>
			<td style="text-align:right;">{}</td>
			<td>{}</td>
			<td style="text-align:right;">{}</td>
			<td style="text-align:right;">{:.2f}</td>
			<td style="text-align:right;">{:.2f}</td>
			<td style="text-align:right;">{:.2f}</td>
			<td style="text-align:right;">{:.2f}</td>
		</tr>
		'''.format(
			idx,
			i["item_name"],
			i["description"],
			i["qty"],
			i["uom"],
			i["discount_percentage"],
			i["discount_rate"],
			i["discount_amount"],
			i["rate"],
			i["amount"]
		)

	data += """
		<tr class="summary-row">
			<td colspan="7" class="text-right">Total</td>
			<td class="text-right">{:.2f}</td>
			<td></td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="summary-row">
			<td colspan="9" class="text-right">Additional Percentage</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="summary-row">
			<td colspan="9" class="text-right">Additional Discount</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="summary-row">
			<td colspan="9" class="text-right">Tax</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="net-total">
			<td colspan="9" class="text-right">Net Total</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		</tbody>
		</table>
		""".format(dis, amount, per, discount, tax, total)
	return data



from frappe.utils import today
@frappe.whitelist()
def process_uploaded_file_so(file_url, salesorder_name):
	import frappe, os
	from io import BytesIO
	from frappe.utils.file_manager import get_file
	from openpyxl import load_workbook

	file_doc = frappe.get_doc("File", {"file_url": file_url})
	content = None
	file_path = None

	try:
		file_path = frappe.utils.get_site_path(file_doc.file_url.strip("/"))
		if not os.path.exists(file_path):
			raise FileNotFoundError
	except Exception:
		content = file_doc.get_content()

	try:
		if content:
			wb = load_workbook(filename=BytesIO(content), data_only=True)
		else:
			wb = load_workbook(filename=file_path, data_only=True)
		sheet = wb.active
	except Exception as e:
		frappe.throw(f"Unable to read Excel file: {str(e)}")

	rows = list(sheet.iter_rows(values_only=True))
	if not rows:
		frappe.throw("Excel file is empty.")

	data_rows = rows[2:]

	salesorder = frappe.get_doc("Sales Order", salesorder_name)
	division_code = salesorder.custom_division_short_code
	product_short = salesorder.custom_product_short_code
	cost_center = salesorder.cost_center
	brand = salesorder.custom_brand
	quo = salesorder.custom_brand_exchange_rate
	conver = salesorder.conversion_rate

	if salesorder.custom_brand == "Pennbarry":
		salesorder.items = [row for row in salesorder.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[9] or 0
			rate = row_vals[10] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:min(8, len(row_vals))] if v]

			if brand:
				item_name_parts.append(str(brand).strip())


			item_name = "-".join(item_name_parts)

			item_description_data = [str(v).strip() for v in row_vals[:min(8, len(row_vals))] if v]
			item_description = "-".join(item_description_data)
			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["item_name"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()
	
	elif salesorder.custom_brand == "Antec Controls":
		salesorder.items = [row for row in salesorder.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[4] or 0
			rate = row_vals[5] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:3] if v]
			item_description_data=[str(v).strip() for v in row_vals[:4] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description= "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()
	elif salesorder.custom_brand == "EH Price-VAV":
		salesorder.items = [row for row in salesorder.items if row.item_code]
		data_rows = rows[1:]
		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[1] or 0
			rate = row_vals[11] or 0


			item_name_parts = [str(v).strip() for v in row_vals[2:11] if v]
			item_description_data = [str(v).strip() for v in row_vals[2:11] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())
			# item_description_data.append("""Variable Air Volume - Pressure Independent Type
			#         Casing : - 20mm Ga Galvanized Steel Sheet (Double skin)
			#         Insulation : - 1" Insulation (48kg/m³, WGF)
			#         Controls : - Neptronic – Bacnet  MS/TP - (EVCB14NIT0S Actuator + TDU00-100 -Thermostat)
			#         Electric Heater : - Neptronic - Modulating Type.
			#         Attenuator : - ATTSP(Where Mentioned)
			#         Accessories : HB - Hanger Bracket, GT - Gauge taps, DSW - Disconnect switch, Transformer """)
			item_name = "-".join(item_name_parts)
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()
	elif salesorder.custom_brand == "EH Price-SA":
		salesorder.items = [row for row in salesorder.items if row.item_code]
		data_rows = rows[1:]
		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[8] or 0
			rate = row_vals[9] or 0


			item_name_parts = [str(v).strip() for v in row_vals[1:8] if v]
			item_description_data = [str(v).strip() for v in row_vals[1:8] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()
	elif salesorder.custom_brand == "EH Price-Dampers":
		salesorder.items = [row for row in salesorder.items if row.item_code]
		data_rows = rows[1:]
		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[7] or 0
			rate = row_vals[8] or 0


			item_name_parts = [str(v).strip() for v in row_vals[1:7] if v]
			item_description_data = [str(v).strip() for v in row_vals[1:7] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			# item_description_data.append("""Motorised Smoke & Fire Damper
			#     Model : FSD-3V-S-231 ( UL Classified) - Class I - (3 Hrs.)
			#     Frame : 16 gauge galvanized steel construction
			#     Blade : 16 gauge triple V grove galvanized steel construction
			#     Fusible Link : UL Listed , Electro-thermal fusible link with 165°F temperature tripping point.
			#     Actuator : Honeywell ,  Spring return Complies with UL873 standard.""")
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()

	elif salesorder.custom_brand == "Vortice":
		salesorder.items = [row for row in salesorder.items if row.item_code]
		data_rows = rows[1:]
		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[5] or 0
			rate = row_vals[6] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:5] if v]
			item_description_data=[str(v).strip() for v in row_vals[:5] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description= "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()

	elif salesorder.custom_brand == "MÜPRO":
		data_rows = rows[1:]
		created_items = []

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[5] or 0
			rate = row_vals[6] or 0

			item_name_parts = [str(v).strip() for v in row_vals[:4] if v]
			item_description_data = [str(v).strip() for v in row_vals[:5] if v]
			if brand:
				item_name_parts.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost": rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost": rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo
			})

		if not created_items:
			frappe.throw("No data rows found in the uploaded file.")

		salesorder.set("items", [])

		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division
		income_account = division_settings.get(div, {}).get("income_account")

		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost": it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost": it["custom_price_cost"],
				"custom_total_cost": it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount": it["custom_total_cost"],
				"custom_cost_amount_sar": it["custom_custom_total_costcompany_currency"]
			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()

	return "Items created successfully"



import math
@frappe.whitelist()
def set_box_weight(item,box,item_qty):
	box_qty = frappe.db.get_value("Box Table",{'parent':item,'box':box},['qty'])
	no_of_boxes = 0
	if box_qty:
		no_of_boxes = math.ceil(float(item_qty) / float(box_qty))
	box_weight = frappe.db.get_value("Box",{'name':box},['weight'])
	total_weight_of_boxes = no_of_boxes * box_weight
	total_box_length = frappe.db.get_value("Box",{'name':box},['length']) * no_of_boxes
	total_box_breadth = frappe.db.get_value("Box",{'name':box},['breadth']) * no_of_boxes
	total_box_height = frappe.db.get_value("Box",{'name':box},['height']) * no_of_boxes
	return no_of_boxes, total_weight_of_boxes, total_box_length, total_box_breadth, total_box_height



@frappe.whitelist()
def set_pallet_weight(item,box,pallet,box_qty):
	pallet_qty = frappe.db.get_value("Pallet Table",{'parent':item,'box':box,'pallet':pallet},['qty'])
	no_of_pallets = 0
	if pallet_qty:
		no_of_pallets = math.ceil(float(box_qty) / float(pallet_qty))
	pallet_weight = frappe.db.get_value("Pallet",{'name':pallet},['weight'])
	total_weight_of_pallets = no_of_pallets * pallet_weight
	total_pallet_length = frappe.db.get_value("Pallet",{'name':pallet},['length']) * no_of_pallets
	total_pallet_breadth = frappe.db.get_value("Pallet",{'name':pallet},['breadth']) * no_of_pallets
	total_pallet_height = frappe.db.get_value("Pallet",{'name':pallet},['height']) * no_of_pallets
	return no_of_pallets, total_weight_of_pallets, total_pallet_length, total_pallet_breadth, total_pallet_height




import frappe
from frappe.model.document import Document

def create_project_on_so_submit(doc, method):
	existing = frappe.db.exists("Project", {"sales_order": doc.name})
	if existing:
		return

	project_name = f"{doc.name}_{doc.customer}"
	if doc.po_no:
		series = f"{doc.customer}-{doc.po_no}-{doc.name}"
	else:
		series = f"{doc.customer}-{doc.name}"

	project = frappe.get_doc({
		"doctype": "Project",
		"naming_series": series,
		"project_name": project_name,
		"sales_order": doc.name,
		"customer": doc.customer,
		"company": doc.company,
	})

	project.insert(ignore_permissions=True)

	# link the project back to the sales order
	doc.db_set("project", project.name)
	frappe.msgprint(f"Project '{project.project_name}' created.")




def so_amend_history(doc, method):

	if not doc.amended_from:
		return

	old_total = frappe.db.get_value(
		"Sales Order",
		doc.amended_from,
		"total"
	) or 0

	create_so_history(
		doc,
		remarks=f"Sales Order Amended from {doc.amended_from}",
		value_from=old_total,
		value_to=doc.total
	)



import frappe
from frappe.utils import now_datetime
from frappe.utils.data import flt

def create_so_history(doc, remarks, value_from=0, value_to=0):
	last_idx = frappe.db.sql("""
		SELECT IFNULL(MAX(idx), 0)
		FROM `tabSales Order History`
		WHERE parent=%s
	""", doc.name)[0][0]

	row = frappe.new_doc("Sales Order History")
	row.parent = doc.name
	row.parenttype = "Sales Order"
	row.parentfield = "custom_sales_order_history"
	row.idx = last_idx + 1
	row.user = frappe.session.user
	row.date = now_datetime()
	row.value_from = value_from
	row.value_to = value_to
	row.remarks = remarks
	row.insert(ignore_permissions=True)





def send_agm_dm_notification(doc, method):

	if doc.workflow_state != "AGM/DM Pending":
		return

	if not doc.custom_division:
		return

	division = frappe.get_doc("Division", doc.custom_division)

	email_list = []

	for row in division.division_managers:
		if row.division_manager:
			email_list.append(row.division_manager)

	if email_list:
		frappe.sendmail(
			recipients=email_list,
			subject=f"{doc.name} - Pending for AGM/DM",
			message=f"""
			<p>Dear Sir/Madam,</p>

				<p>
				This is to inform you that the Sales Order 
				<strong>
					<a href="{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }" target="_blank">
						{ doc.name }
					</a>
				</strong> 
				is currently pending your approval.
				</p>

				<p>
				Please review the details and take the necessary action.
				</p>

			"""
		)





import frappe
@frappe.whitelist()
def set_so_series(doc, method):
	prefix = "SOJGBKSA"
	latest = frappe.db.sql("""
		SELECT name FROM `tabSales Order`
		WHERE name LIKE %s and amended_from is null
		ORDER BY name DESC
		LIMIT 1
	""", (prefix + "%",), as_dict=True)

	if latest:
		last_number = int(latest[0].name.replace(prefix, ""))
		new_number = last_number + 1
	else:
		new_number = 2001

	doc.custom_so_naming_series = f"{prefix}{new_number}"
	# doc.naming_series = prefix



@frappe.whitelist()
def validate_sow_amount(doc, method):
	if doc.custom_sow_as_item == 1:
		total_sow_amount = sum(item.sow_amount for item in doc.custom_sow if item.sow_amount)
		if doc.base_total != total_sow_amount:
			frappe.throw(f"Total SOW Amount ({total_sow_amount}) does not match the Quotation Item Amount ({doc.base_total}). Please correct the amounts in the items.")



@frappe.whitelist()
def validate_so_mandatory(doc,method):
	if doc.has_value_changed("workflow_state") and doc.workflow_state=="S.E Pending":
		if not doc.po_no:
			frappe.throw("Customer Purchase Order is mandatory before proceeding to the next approval level.")
		if not doc.custom_sales_personuser:
			frappe.throw("Sales Person User must be specified before proceeding to the next approval level.")
		if not doc.payment_terms_template:
			frappe.throw("Payment Terms Template is required before proceeding to the next approval level.")
		if not doc.custom_delivery_terms:
			frappe.throw("Kindly enter the Delivery Terms before move to next level")
		if not doc.custom_support_engineer:
			frappe.throw("Support Engineer must be specified before proceeding to the next approval level.")


import json
import frappe
import time
from frappe.utils import now_datetime


def capture_so_changes(doc, method):
	frappe.enqueue("jgb.jgb.custom.create_so_history_from_version",queue="short",docname=doc.name)



@frappe.whitelist()
def send_payment_terms_notification(doc, method):
	old_doc = doc.get_doc_before_save()

	if not old_doc:
		return

	if old_doc.payment_terms_template == doc.payment_terms_template:
		return

	cfo_emails = frappe.db.sql_list("""
		SELECT u.email
		FROM `tabHas Role` hr
		INNER JOIN `tabUser` u
			ON u.name = hr.parent
		WHERE hr.role = 'CFO'
		AND u.enabled = 1
	""")

	if not cfo_emails:
		return
	
	user_name = frappe.db.get_value(
		"User",
		frappe.session.user,
		"full_name"
	) or frappe.session.user

	frappe.sendmail(
		recipients=cfo_emails,
		subject=f"Payment Terms Updated for Sales Order {doc.name}",
		message=f"""
		<p>Dear Sir/Madam,</p>

		<p>The Payment Terms for Sales Order <b>{doc.name}</b> have been updated after submission by <b>{user_name}</b>.</p>

		<p>The Payment Terms have been changed from <b>{old_doc.payment_terms_template or 'None'}</b> to <b>{doc.payment_terms_template or 'None'}</b>.</p>

		<p>Please review the updated Payment Terms at your convenience.</p>

		<p>Regards,<br>ERP System</p>
		"""
	)



import os
import tempfile
import openpyxl
from frappe.utils.csvutils import read_csv_content
from frappe.utils.file_manager import get_file

SO_ESTIMATION_TITLES = [
	"Cost of Item",
	"Customs Duty",
	"Freight & Delivery - 5% Calculated Default , value can be edited for more or less",
	"Customs Clearance Charges",
	"SABER Charges",
	"Bank Charges",
	"Installation Charges - Manpower",
	"Installation Charges - Equipment",
	"Installation Charges - Materials / Consumables",
	"Installation Charges - Food - Transportation & Accommodation",
	"Installation Charges - Others",
]


@frappe.whitelist()
def upload_item_sheet_so(docname, file_url):
	"""Import SO items from xlsx/csv (Item Code, Qty, Currency, Cost, Rate) and
	refresh item cost fields + estimation table, mirroring the SO client script."""
	try:
		file_doc, file_content_or_path = get_file(file_url)
		if os.path.exists(file_content_or_path):
			filepath = file_content_or_path
		else:
			suffix = ".xlsx" if file_url.endswith(".xlsx") else ".csv"
			tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
			tmp.write(file_content_or_path if isinstance(file_content_or_path, bytes) else file_content_or_path.encode())
			tmp.close()
			filepath = tmp.name

		ext = os.path.splitext(filepath)[1].lower()
		doc = frappe.get_doc("Sales Order", docname)

		if ext == ".xlsx":
			ws = openpyxl.load_workbook(filepath, data_only=True).active
			rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if any(r)]
		elif ext == ".csv":
			with open(filepath, encoding="utf-8-sig") as f:
				rows = [r for r in read_csv_content(f.read())[1:] if any(r)]
		else:
			frappe.throw(f"Unsupported file format: {ext}")

		brand_rate = flt(doc.custom_brand_exchange_rate) or 1
		mult = flt(doc.custom_multiplier_percentage) or 1
		company_currency = frappe.db.get_value("Company", doc.company, "default_currency")

		def rate_to_sar(currency):
			# cost is entered in the row's Currency; prefer the SO's brand rate
			if currency == doc.custom_brand_currency and brand_rate:
				return brand_rate
			if not currency or currency == company_currency:
				return 1
			from erpnext.setup.utils import get_exchange_rate
			return flt(get_exchange_rate(currency, company_currency)) or 1

		for r in rows:
			vals = r[:5] + [None] * (5 - len(r[:5]))
			item_code, qty, currency, cost, rate = vals
			qty, cost, rate = flt(qty), flt(cost), flt(rate)
			to_sar = rate_to_sar(currency)
			disc = cost * mult / 100 if mult > 1 else 0
			net = cost - disc
			doc.append("items", {
				"item_code": item_code,
				"qty": qty,
				"rate": rate,
				"custom_cost": cost,
				"custom_discount_cost_amount": disc,
				"custom_discount_cost_amount_sar": disc * to_sar,
				"custom_net_cost_amount": net,
				"custom_net_cost_amount_sar": net * to_sar,
				"custom_price_cost": cost * to_sar,
				"custom_cost_amount": net * qty,
				"custom_cost_amount_sar": net * qty * to_sar,
				"custom_total_cost": net * qty,
				"custom_custom_total_costcompany_currency": net * qty * to_sar,
			})

		total_cost = sum(flt(d.custom_cost_amount) for d in doc.items)
		total_cost_sar = sum(flt(d.custom_cost_amount_sar) for d in doc.items)
		doc.custom_total_cost_amount = flt(total_cost, 2)
		doc.custom_total_cost_amount_sar = flt(total_cost_sar, 2)

		existing = {r.title_of_estimation for r in doc.custom_estimation_details}
		for t in SO_ESTIMATION_TITLES:
			if t not in existing:
				doc.append("custom_estimation_details", {
					"title_of_estimation": t,
					"value": 0,
					"value_quotation_currency": 0,
				})

		est = 0
		for r in doc.custom_estimation_details:
			t = (r.title_of_estimation or "").lower().strip()
			if t in ("cost of item", "cost of items"):
				r.value = total_cost_sar
				doc.custom_cost_of_item = total_cost_sar
			if (r.title_of_estimation or "").startswith("Freight & Delivery - 5%") and not flt(r.value):
				r.percen = 5
				r.value = total_cost_sar * 5 / 100
			est += flt(r.value)

		doc.custom_total_estimated_value = flt(est, 2)
		doc.custom_other_cost = flt(est - total_cost_sar, 2)

		conv = flt(doc.conversion_rate) or 1
		quote = sum(flt(d.qty) * flt(d.rate) * conv for d in doc.items) - flt(doc.discount_amount)
		doc.custom_quote_value = flt(quote, 2)
		doc.custom_estimation_margin = flt((quote - est) / quote * 100, 2) if quote else 0
		doc.custom_margin_on_cost = flt((quote - est) / est * 100, 2) if est else 0

		doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {"status": "success", "message": "Items and estimation imported successfully."}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "SO Item Sheet Import Failed")
		return {"status": "error", "message": str(e)}
