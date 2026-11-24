import frappe
from frappe.model.document import Document
from frappe.utils import flt

@frappe.whitelist()
def create_logistics_request_for_purchase_orders(po_names,cargo_type,inventory_destination):
	import json

	if isinstance(po_names, str):
		po_names = json.loads(po_names)

	if not po_names:
		frappe.throw("No Purchase Orders selected.")

	logistics_request = frappe.new_doc("Logistics Request")
	logistics_request.logistic_type = "Import"
	logistics_request.po_so = "Purchase Order"
	total_amount = 0  
	for po_name in po_names:
		po = frappe.get_doc("Purchase Order", po_name)
		logistics_request.currency = po.currency
		logistics_request.conv_rate = po.conversion_rate
		logistics_request.cargo_type = cargo_type
		logistics_request.inventory_destination = inventory_destination
		for item in po.items:
			# total_requested_qty = frappe.db.sql("""
			#     SELECT SUM(lri.qty)
			#     FROM `tabLogistics Request Item` lri
			#     JOIN `tabLogistics Request` lr ON lri.parent = lr.name
			#     WHERE lri.voucher_no = %s AND lri.item_code = %s AND lr.workflow_state != 'Draft'
			# """, (po.name, item.item_code))[0][0] or 0
			total_requested_qty = frappe.db.sql("""
				SELECT COALESCE(SUM(lri.qty), 0)
				FROM `tabLogistics Request Item` lri
				INNER JOIN `tabLogistics Request` lr
					ON lr.name = lri.parent
				WHERE lri.voucher_no = %s
				AND lri.po_item = %s
				AND lr.workflow_state != 'Draft'
			""", (po.name, item.name))[0][0]
			pending_qty = item.qty - total_requested_qty

			if pending_qty > 0:
				rate = item.rate
				amount = pending_qty * rate
				base_rate = item.base_rate or rate * po.conversion_rate
				base_amount = item.base_amount or amount * po.conversion_rate

				logistics_request.append("product_description", {
					"item_code": item.item_code,
					"item_name": item.item_name,
					"po_item":item.name,
					"description": item.description,
					"qty": pending_qty,
					"rate": rate,
					"uom": item.uom,
					"amount": amount,
					"currency":po.currency,
					"conversion_factor": item.conversion_factor or 1,
					"base_rate": base_rate,
					"base_amount": base_amount,
					"voucher_no": po.name,
					"voucher_type": "Purchase Order",
					"supplier":po.supplier,
					"requester_name":po.custom_sales_person,
					"box_name":item.custom_box_name,
					"pallet_name":item.custom_pallet_name,
					"no_of_boxes":item.custom_no_of_boxes,
					"no_of_pallets":item.custom_no_of_pallets,
					"total_box_weight_kg":item.custom_total_box_weight_kg,
					"total_pallet_weight_kg":item.custom_total_pallet_weight_kg,
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
		box_data, pallet_data = get_box_summary_po(po_name)
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
		frappe.throw("All selected Purchase Orders are already fully included in previous Logistics Requests.")

	logistics_request.grand_total = total_amount  # Set computed grand total
	if total_amount>0:
		logistics_request.custom_duty =total_amount*0.45
	logistics_request.save(ignore_permissions=True)
	frappe.db.commit()

	return frappe.msgprint(f"Logistics Request <a href='/app/logistics-request/{logistics_request.name}'><b>{logistics_request.name}</b></a> created successfully.")


@frappe.whitelist()
def get_box_summary_po(po_name):
	if not frappe.db.exists("Purchase Order", po_name):
		return [], []

	data = frappe.db.sql("""
	SELECT custom_box_name as box_name, custom_no_of_boxes as total_no,
		   SUM(IFNULL(custom_weight_per_unit_kg, 0)) as weight_per_unit,
		   SUM(IFNULL(custom_total_box_weight_kg, 0)) as total_weight,
		   SUM(IFNULL(custom_box_length_mm, 0)) as blength,
		   SUM(IFNULL(custom_box_height_mm, 0)) as bheight,
		   SUM(IFNULL(custom_box_breadth_mm, 0)) as bbreadth
	FROM `tabPurchase Order Item`
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
		FROM `tabPurchase Order Item`
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


import frappe
import random

@frappe.whitelist()
def get_unique_random_number(doctype):
	while True:
		number = random.randint(10000000, 99999999)  # 8-digit random number
		exists = frappe.db.exists(doctype, {"custom_po_name": number})
		if not exists:
			return number


import frappe
import os
import openpyxl
import tempfile
from frappe.utils.csvutils import read_csv_content
from frappe.utils.file_manager import get_file

@frappe.whitelist()
def upload_item_sheet_po(docname, file_url):
	try:
		file_doc, file_content_or_path = get_file(file_url)
		if os.path.exists(file_content_or_path):
			filepath = file_content_or_path
		else:
			suffix = ".xlsx" if file_url.endswith(".xlsx") else ".csv"
			tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
			if isinstance(file_content_or_path, bytes):
				tmp.write(file_content_or_path)
			else:
				tmp.write(file_content_or_path.encode())
			tmp.close()
			filepath = tmp.name

		ext = os.path.splitext(filepath)[1].lower()

		doc = frappe.get_doc("Purchase Order", docname)

		if ext == ".xlsx":
			wb = openpyxl.load_workbook(filepath, data_only=True)
			ws = wb.active
			for row in ws.iter_rows(min_row=2, values_only=True):
				if not any(row): 
					continue
				item_code, qty, rate = row
				doc.append("items", {
					"item_code": item_code,
					"qty": qty,
					"rate": rate
				})

		elif ext == ".csv":
			with open(filepath, "r", encoding="utf-8-sig") as f:
				rows = read_csv_content(f.read())
			for row in rows[1:]:
				if not any(row):
					continue
				item_code, qty, rate = row
				doc.append("items", {
					"item_code": item_code,
					"qty": qty,
					"rate": rate
				})
				# item_code, item_name, qty, uom, discount_per, discount_rate, discount_amount, rate, amount = row
				# doc.append("items", {
				#     "item_code": item_code,
				#     "item_name": item_name,
				#     "qty": qty,
				#     "uom": uom,
				#     "discount_percentage": discount_per,
				#     "discount_amount": discount_amount,
				#     "rate": rate,
				#     "amount": amount
				# })

		else:
			frappe.throw(f"Unsupported file format: {ext}")

		doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {"status": "success", "message": "Items imported successfully."}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Item Sheet Import Failed")
		return {"status": "error", "message": str(e)}


@frappe.whitelist()
def process_uploaded_file_po_create(file_url, division_code, product_short, division, product, po_name, brand = None):
	"""
	Process Excel file, create Item documents if not exist, 
	and return item data for appending to PO.
	"""
	import frappe
	from io import BytesIO
	from openpyxl import load_workbook
	from frappe.utils import today

	file_doc = frappe.get_doc("File", {"file_url": file_url})
	content = file_doc.get_content()

	wb = load_workbook(filename=BytesIO(content), data_only=True)
	sheet = wb.active
	rows = list(sheet.iter_rows(values_only=True))
	if len(rows) <= 2:
		frappe.throw("Excel is empty or missing data rows")

	data_rows = rows[2:]  # skip header
	items = []

	prefix = f"{division_code}-{product_short}"

	for idx, row in enumerate(data_rows, start=3):
		if not any(row): continue

		row_vals = list(row)
		qty = float(row_vals[9] or 1)
		rate = float(row_vals[10] or 0)
		item_name_parts = [str(v).strip() for v in row_vals[:min(8, len(row_vals))] if v]

		if brand:
			item_name_parts.append(str(brand).strip())


		if not item_name_parts:
			frappe.throw(f"Row #{idx}: Item name is empty")

		item_name = "-".join(item_name_parts)

		# Check if Item exists
		existing_item = frappe.db.get_value(
			"Item",
			{"item_name": item_name, "item_code": ["like", f"{prefix}%"]},
			"name"
		)

		if existing_item:
			item_code = existing_item
		else:
			# Generate new item_code
			last_item = frappe.db.sql("""
				SELECT item_code FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)
			num = 0
			if last_item:
				try:
					num = int(last_item[0]["item_code"].split("-")[-1])
				except: num = 0
			item_code = f"{prefix}-{num + 1:06d}"

			# Create Item document
			item_doc = frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_name,
				"description": item_name,
				"item_group": division,
				"custom_product":product,
				"custom_auto_created_item": 1,
				"custom_purchase_order_reference":po_name
			})
			item_doc.insert(ignore_permissions=True)
			frappe.db.commit()

		# Add to list for PO
		items.append({
			"item_code": item_code,
			"item_name": item_name,
			"qty": qty,
			"rate": rate
		})

	return items

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


from frappe.utils import flt, fmt_money
@frappe.whitelist()
def get_po_so_qty_dashboard(purchase_order):
    if not purchase_order or not frappe.db.exists("Purchase Order", purchase_order):
        return {}

    po_items = frappe.get_all(
        "Purchase Order Item",
        filters={"parent": purchase_order},
        fields=["name", "item_code", "sales_order_item"],
        order_by="idx",
    )

    so_item_names = [d.sales_order_item for d in po_items if d.sales_order_item]
    so_item_data = {}
    if so_item_names:
        for d in frappe.db.sql(
            """
            SELECT name, qty, delivered_qty
            FROM `tabSales Order Item`
            WHERE name IN %s
        """,
            (tuple(so_item_names),),
            as_dict=1,
        ):
            so_item_data[d.name] = {
                "so_qty": flt(d.qty),
                "delivered_qty": flt(d.delivered_qty),
            }

    items = []
    for d in po_items:
        so = so_item_data.get(d.sales_order_item, {"so_qty": 0, "delivered_qty": 0})
        so_qty = so["so_qty"]
        delivered_qty = so["delivered_qty"]
        items.append(
            {
                "item_code": d.item_code,
                "so_qty": so_qty,
                "delivered_qty": delivered_qty,
                "balance_so_qty": so_qty - delivered_qty,
            }
        )

    return {"items": items}



@frappe.whitelist()
def download_po_so_qty_dashboard(purchase_order):
    result = get_po_so_qty_dashboard(purchase_order)
    if not result or not result.get("items"):
        frappe.throw("No data found for the selected Purchase Order")

    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Font

    headers = [
        "Item",
        "Sales Order Qty",
        "Delivered Qty",
        "Balance SO Qty",
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "PO SO Qty Dashboard"
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])

    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for d in result["items"]:
        ws.append([
            d["item_code"],
            d["so_qty"],
            d["delivered_qty"],
            d["balance_so_qty"],
        ])

    xlsx_file = BytesIO()
    wb.save(xlsx_file)

    frappe.response["filename"] = f"{purchase_order}_po_so_qty_dashboard.xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"


@frappe.whitelist()
def check_purchase_order_connection(po_name):
    return has_connected_document(po_name)


def has_connected_document(po_name):
    """
    Check whether the Purchase Order is connected
    to a Purchase Receipt or Purchase Invoice.
    """

    purchase_receipt = frappe.db.exists(
        "Purchase Receipt Item",
        {
            "purchase_order": po_name,
            "docstatus": ["!=", 2]
        }
    )

    if purchase_receipt:
        return True

    purchase_invoice = frappe.db.exists(
        "Purchase Invoice Item",
        {
            "purchase_order": po_name,
            "docstatus": ["!=", 2]
        }
    )

    if purchase_invoice:
        return True

    return False




@frappe.whitelist()
def update_advance_po(doc,method):
	sales_orders = list({item.sales_order for item in doc.items if item.sales_order})

	if not sales_orders:
		doc.custom_so_advance_paid = 0
		return

	total_advance = 0

	for so in sales_orders:
		advance_paid = frappe.db.sql("""
			SELECT SUM(pe.paid_amount)
			FROM `tabPayment Entry Reference` per
			JOIN `tabPayment Entry` pe ON per.parent = pe.name
			WHERE per.reference_doctype = 'Sales Order'
			AND per.reference_name = %s
			AND pe.docstatus = 1
		""", (so,), as_list=1)[0][0] or 0

		total_advance += advance_paid

	doc.custom_so_advance_paid = total_advance



@frappe.whitelist()
def set_estimation_margins(doc, method=None):
	# The Sales Order's profit-on-sales field is `custom_estimation_margin`, but the
	# Purchase Order's is `custom_margin_on_quote`. The SO -> PO mapper copies the
	# same-named quote/estimate/margin-on-cost fields and leaves margin-on-quote at 0.
	# Derive both here so every creation path (UI, mapper, API, Data Import) is consistent.
	quote = flt(doc.custom_quote_value)
	estimate = flt(doc.custom_total_estimated_value)
	if quote and estimate:
		doc.custom_margin_on_quote = (quote - estimate) / quote * 100
		doc.custom_margin_on_cost = (quote - estimate) / estimate * 100


@frappe.whitelist()
def validate_po_mandatory(doc,method):
	if doc.has_value_changed("workflow_state") and doc.workflow_state=="S.E Pending":
		if not doc.custom_purchase_type:
			frappe.throw("Purchase Type is mandatory before proceeding to the next approval level.")
		if not doc.payment_terms_template:
			frappe.throw("Payment Terms Template is required before proceeding to the next approval level.")
		if not doc.custom_delivery_terms:
			frappe.throw("Kindly enter the Delivery Terms before move to next level")
		if not doc.custom_support_engineer:
			frappe.throw("Support Engineer must be specified before proceeding to the next approval level.")
	if doc.has_value_changed("workflow_state") and doc.workflow_state=="Regional Accountant Pending":
		if not doc.custom_purchase_type:
			frappe.throw("Purchase Type is mandatory before proceeding to the next approval level.")
		if not doc.payment_terms_template:
			frappe.throw("Payment Terms Template is required before proceeding to the next approval level.")
		if not doc.custom_delivery_terms:
			frappe.throw("Kindly enter the Delivery Terms before move to next level")
		if not doc.custom_support_engineer:
			frappe.throw("Support Engineer must be specified before proceeding to the next approval level.")




@frappe.whitelist()
def send_agm_dm_notification_po(doc, method):

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
			subject=f"Purchase Order {doc.name} Awaiting Approval",
			message=f"""
			<p>Dear Sir/Madam,</p>

				<p>
				This is to inform you that the Purchase Order 
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
def set_po_series(doc, method):
	prefix = "POJGBKSA"
	latest = frappe.db.sql("""
		SELECT name FROM `tabPurchase Order`
		WHERE name LIKE %s and amended_from is null
		ORDER BY name DESC
		LIMIT 1
	""", (prefix + "%",), as_dict=True)

	if latest:
		last_number = int(latest[0].name.replace(prefix, ""))
		new_number = last_number + 1
	else:
		new_number = 2001

	doc.custom_po_naming_series = f"{prefix}{new_number}"

	# doc.naming_series = prefix