import frappe

@frappe.whitelist()
def create_logistics_request_for_delivery(lr_names):
	import json

	if isinstance(lr_names, str):
		lr_names = json.loads(lr_names)

	if not lr_names:
		frappe.throw("No Delivery Note selected.")

	logistics_request = frappe.new_doc("Logistics Request")
	logistics_request.logistic_type = "Local Delivery"
	logistics_request.po_so = "Delivery Note"
	
	total_amount = 0 

	for po_name in lr_names:
		po = frappe.get_doc("Delivery Note", po_name)
		logistics_request.currency = po.currency
		logistics_request.conv_rate = po.conversion_rate
		logistics_request.cargo_type = "Road"
		logistics_request.inventory_destination = "Direct to Customer"
		logistics_request.customer=po.customer
		for item in po.items:
			# total_requested_qty = frappe.db.sql("""
			#     SELECT SUM(qty)
			#     FROM `tabLogistics Request Item`
			#     WHERE voucher_no = %s AND item_code = %s
			# """, (po.name, item.item_code))[0][0] or 0
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
					"voucher_type": "Delivery Note",
					"customer":po.customer,
					"requester_name":frappe.session.user,
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
		box_data, pallet_data = get_box_summary_dn(po_name)
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
		frappe.throw("All selected Delivery Note are already fully included in previous Logistics Requests.")

	logistics_request.grand_total = total_amount  # Set computed grand total
	if total_amount>0:
		logistics_request.custom_duty =total_amount*0.45
	logistics_request.save(ignore_permissions=True)
	frappe.db.commit()

	return frappe.msgprint(f"Logistics Request <a href='/app/logistics-request/{logistics_request.name}'><b>{logistics_request.name}</b></a> created successfully.")



@frappe.whitelist()
def get_box_summary_dn(po_name):
	if not frappe.db.exists("Delivery Note", po_name):
		return [], []

	data = frappe.db.sql("""
	SELECT custom_box_name as box_name, custom_no_of_boxes as total_no,
		   SUM(IFNULL(custom_weight_per_unit_kg, 0)) as weight_per_unit,
		   SUM(IFNULL(custom_total_box_weight_kg, 0)) as total_weight,
		   SUM(IFNULL(custom_box_length_mm, 0)) as blength,
		   SUM(IFNULL(custom_box_height_mm, 0)) as bheight,
		   SUM(IFNULL(custom_box_breadth_mm, 0)) as bbreadth
	FROM `tabDelivery Note Item`
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
		FROM `tabDelivery Note Item`
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


@frappe.whitelist()
def get_inventory_account_for_division(division=None,company=None ):
	if not division:
		return
	inventory_account = frappe.db.get_value(
		"Division Account Details", {"parent": division,"company": company},"inventory_account")
	if inventory_account:
		return inventory_account

@frappe.whitelist()
def get_expense_account_for_division(division=None, company=None):
	if not division:
		return
	expense_account = frappe.db.get_value("Division Account Details",{"parent": division,"company": company},"expense_account")
	if not expense_account:
		return
	if expense_account:
		return expense_account



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



@frappe.whitelist()
def get_lr_from_dn(dn):
	if not dn:
		return []

	data = frappe.db.sql("""
		SELECT DISTINCT parent AS lr_id
		FROM `tabLogistics Request Item`
		WHERE voucher_type = 'Delivery Note'
		AND voucher_no = %s
	""", dn, as_dict=1)

	return data



@frappe.whitelist()
def set_expense_account_from_division(doc, method):
	company = doc.company
	division = doc.custom_division
	if not division:
		return
	
	# Get COG, SRBNB and COS from Division Account Details
	div_details = frappe.db.get_value("Division Account Details", 
		{"parent": division, "company": company}, 
		["expense_account", "snrb_account", "cos_account"], as_dict=True)
	
	if not div_details:
		return
	
	# Check if update_stock is disabled on the PI
	update_stock_disabled = doc.update_stock == 0 if hasattr(doc, 'update_stock') else False
	
	for item in doc.items:
		if not item.item_code:
			continue
		
		# Check if item is a stock item
		is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
		
		# Check if item has a linked Purchase Receipt
		pr_field = None
		if hasattr(item, 'purchase_receipt_item') and item.purchase_receipt_item:
			pr_field = item.purchase_receipt_item
		elif hasattr(item, 'purchase_receipt') and item.purchase_receipt:
			pr_field = item.purchase_receipt
		
		has_pr = frappe.db.exists("Purchase Receipt Item", {"name": pr_field}) if pr_field else False
		
		# Stock items without PR and without update_stock should use SRBNB
		if is_stock_item and not has_pr and update_stock_disabled:
			if div_details.snrb_account:
				item.expense_account = div_details.snrb_account
		elif is_stock_item:
			# Stock items with PR/update_stock use COG
			if div_details.expense_account:
				item.expense_account = div_details.expense_account
		else:
			# Non-stock items: default to COS, but respect manual override
			# Replace COG-type accounts (auto-filled from Item Default) with COS,
			# but keep any other account the user set (e.g. Saber Charges, COS)
			cos_acc = div_details.cos_account or div_details.expense_account
			if not cos_acc:
				continue
			if not item.expense_account:
				item.expense_account = cos_acc
			elif item.expense_account != cos_acc:
				# Check if current account is a COG-type account (auto-filled default)
				current_type = frappe.db.get_value("Account", item.expense_account, "account_type")
				if current_type == "Cost of Goods Sold":
					item.expense_account = cos_acc




@frappe.whitelist()
def enqueue_lr_update_dn(doc, method):
	frappe.enqueue(
		"jgb.jgb.teampro.delivery_note.update_logistics_status_from_dn",
		doc_name=doc.name, 
		queue="long",
		timeout=600
	)



@frappe.whitelist()
def update_logistics_status_from_dn(doc_name):
	doc = frappe.get_doc("Delivery Note", doc_name) 
	if not doc.items:
		return

	status_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
	current_status = status_map.get(doc.docstatus, "Unknown")

	for item in doc.items:
		linked_docs = []

		if item.against_sales_order:
			linked_docs.append(("Sales Order", item.against_sales_order))

		if item.against_sales_invoice:
			linked_docs.append(("Sales Invoice", item.against_sales_invoice))

		if not linked_docs:
			continue
				
		lr_docs = frappe.get_all("Logistics Request", fields=["name"])
		for lr in lr_docs:
			lr_doc = frappe.get_doc("Logistics Request", lr.name)

			matched = False
			for voucher_type, voucher_no in linked_docs:
				for row in lr_doc.product_description:
					if row.voucher_type == voucher_type and row.voucher_no == voucher_no:
						matched = True
						break
				if matched:
					break

			if not matched:
				continue

			if doc.docstatus == 2:  # Cancelled
				to_remove = []
				for row in lr_doc.lr_status_details:
					if row.voucher_type == "Delivery Note" and row.voucher_name == doc.name:
						to_remove.append(row)

				for row in to_remove:
					lr_doc.lr_status_details.remove(row)


			else:
				updated = False
				for lr_status in lr_doc.lr_status_details:
					if lr_status.voucher_type == "Delivery Note" and lr_status.voucher_name == doc.name:
						lr_status.status = current_status
						updated = True
						break

				if not updated:
					lr_doc.append("lr_status_details", {
						"voucher_type": "Delivery Note",
						"voucher_name": doc.name,
						"status": current_status
					})

			lr_doc.save(ignore_permissions=True)




@frappe.whitelist()
def update_dn_so_qty(doc, method):
	if not doc.items:
		return
	for item in doc.items:
		if item.against_sales_order and item.so_detail:
			current_delivered = frappe.db.get_value("Sales Order Item",item.so_detail,"delivered_qty") or 0
			zoho_delivered = frappe.db.get_value("Sales Order Item",item.so_detail,"custom_zoho_delivered_qty") or 0
			new_qty = current_delivered + zoho_delivered
			frappe.db.set_value("Sales Order Item",item.so_detail,"delivered_qty",new_qty)




import frappe
from frappe.utils import today, date_diff, formatdate, fmt_money, cstr

def send_dn_submission_mail(doc, method):
	sales_order = None
	for item in doc.items:
		if item.against_sales_order:
			sales_order = item.against_sales_order
			break
	if not sales_order:
		return
	so_owner = frappe.db.get_value("Sales Order", sales_order, "owner")
	if not so_owner:
		return
	email_id = frappe.db.get_value("User", so_owner, "email")
	if not email_id:
		return
	posting_date = formatdate(doc.posting_date, "dd-MM-yyyy")
	subject = f"Delivery Note Submitted for Sales Order {sales_order}"
	message = f"""
	Dear User,<br><br>
	Delivery Note <b>{doc.name}</b> has been submitted against
	Sales Order <b>{sales_order}</b>.<br><br>
	<b>Customer:</b> {doc.customer}<br>
	<b>Posting Date:</b> {posting_date}<br><br>
	Kindly check and proceed further if required.<br><br>
	Regards,<br>
	ERP System
	"""

	frappe.sendmail(
		recipients=[email_id],
		subject=subject,
		message=message,
		reference_doctype="Delivery Note",
		reference_name=doc.name
	)
