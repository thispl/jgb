
import frappe
from frappe.model.document import Document

@frappe.whitelist()
def create_logistics_request_for_sales_invoice(so_names,cargo_type):
	import json

	if isinstance(so_names, str):
		so_names = json.loads(so_names)

	if not so_names:
		frappe.throw("No Sales Invoices selected.")

	logistics_request = frappe.new_doc("Logistics Request")
	logistics_request.logistic_type = "Export"
	logistics_request.po_so = "Sales Invoice"
	

	total_amount = 0  # To accumulate grand total

	for po_name in so_names:
		po = frappe.get_doc("Sales Invoice", po_name)
		logistics_request.currency = po.currency
		logistics_request.conv_rate = po.conversion_rate
		logistics_request.cargo_type = cargo_type
		logistics_request.custom_customer_final_destination=po.customer
		logistics_request.inventory_destination = "Direct to Customer"
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
					"voucher_type": "Sales Invoice",
					"customer":po.customer,
					"requester_name":po.custom_sales_person,
					"box_name":item.custom_box,
					"pallet_name":item.custom_pallet,
					"no_of_boxes":item.custom_no_of_boxes,
					"no_of_pallets":item.custom_no_of_pallets,
					"total_box_weight_kg":item.custom_total_weight_of_boxes,
					"total_pallet_weight_kg":item.custom_total_weight_of_pallets,
					"box_length_mm":item.custom_box_length,
					"pallet_length_mm":item.custom_pallet_length,
					"box_breadth_mm":item.custom_box_breadth,
					"pallet_breadth_mm":item.custom_pallet_breadth,
					"box_height_mm":item.custom_box_height,
					"pallet_height_mm":item.custom_pallet_height,
					"cbm":item.custom_cbm,
					"packing_weight_kg":item.custom_packing_weight,
					"gross_weight_kg":item.custom_gross_weight
				})

				total_amount += amount  # Accumulate amount
		box_data, pallet_data = get_box_summary_si(po_name)
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
		frappe.throw("All selected Sales Invoices are already fully included in previous Logistics Requests.")

	logistics_request.grand_total = total_amount  # Set computed grand total
	if total_amount>0:
		logistics_request.custom_duty =total_amount*0.45
	logistics_request.save(ignore_permissions=True)
	frappe.db.commit()

	return frappe.msgprint(f"Logistics Request <a href='/app/logistics-request/{logistics_request.name}'><b>{logistics_request.name}</b></a> created successfully.")



@frappe.whitelist()
def get_box_summary_si(po_name):
	if not frappe.db.exists("Sales Invoice", po_name):
		return [], []

	data = frappe.db.sql("""
	SELECT custom_box as box_name, custom_no_of_boxes as total_no,
		   SUM(IFNULL(custom_weight_per_unit_b, 0)) as weight_per_unit,
		   SUM(IFNULL(custom_total_weight_of_boxes, 0)) as total_weight,
		   SUM(IFNULL(custom_box_length, 0)) as blength,
		   SUM(IFNULL(custom_box_height, 0)) as bheight,
		   SUM(IFNULL(custom_box_breadth, 0)) as bbreadth
	FROM `tabSales Invoice Item`
	WHERE parent = %s
	GROUP BY custom_box
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
		SELECT custom_pallet as pallet_name, custom_no_of_pallets as total_no,
			   SUM(custom_weight_per_unit_p) as weight_per_unit,
			   SUM(custom_total_weight_of_pallets) as total_weight,
			   SUM(custom_pallet_length) as plength,
			   SUM(custom_pallet_breadth) as pbreadth,
			   SUM(custom_pallet_height) as pheight
		FROM `tabSales Invoice Item`
		WHERE parent = %s
		GROUP BY custom_pallet
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
def cost_center_from_division(division=None, company=None):
	if not division:
		return  
	cost_center = frappe.db.get_value(
		"Division Account Details", {"parent": division,"company": company}, "cost_center")
	if cost_center:
		return cost_center


@frappe.whitelist()
def update_ipc_values_ipc(ipc):
	sales_order = frappe.get_doc("Interim Payment Certificate", ipc)
	return sales_order.items , sales_order.retention_percentage , sales_order.advance_percentage , sales_order.previously_certified_value


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



import frappe
@frappe.whitelist()
def set_income_account_from_division(doc, method):
	company = doc.company
	division = doc.custom_division
	if not division:
		return
	income_account = frappe.db.get_value("Division Account Details",{"parent": division,"company": company},"income_account")
	if not income_account:
		return
	for item in doc.items:
		if not item.item_code:
			continue
		item.income_account = income_account



import re

@frappe.whitelist()
def set_zatca_exemption_from_category(doc, method):
	"""Auto-set exemption reason code and export flag based on ZATCA tax category."""
	category = doc.get("custom_zatca_tax_category")
	if not category:
		return
	if category == "Services outside scope of tax / Not subject to VAT":
		doc.custom_exemption_reason_code = "VATEX-SA-OOS"
		doc.custom_zatca_export_invoice = 1
	elif category == "Zero Rated":
		if not doc.get("custom_exemption_reason_code") or doc.get("custom_exemption_reason_code") == "Standard 15%":
			doc.custom_exemption_reason_code = "VATEX-SA-29"
	elif category == "Standard":
		if not doc.get("custom_exemption_reason_code"):
			doc.custom_exemption_reason_code = "Standard 15%"



@frappe.whitelist()
def reduce_ipc_qty_sold(doc,method):
	qty_ipc = 0
	if doc.custom_interim_payment_certificate:
		dn = frappe.get_doc("Interim Payment Certificate", doc.custom_interim_payment_certificate)
		for d in dn.items:
			for i in doc.items:
				if d.item_code == i.item_code and d.name == i.custom_ipc_details:
					qty_ipc += i.qty
					qty = qty_ipc - d.inv_qty
				frappe.db.set_value("IPC Item", d.name, "inv_qty", qty)


def allow_payment_terms_update_after_submit(doc, method=None):
	"""Let the payment terms be changed on a submitted Sales Invoice.

	``payment_terms_template`` is allow_on_submit, so ERPNext keeps it editable after
	submit; its client controller then rebuilds ``payment_schedule`` as brand-new rows.
	Frappe's ``validate_update_after_submit`` loads every child row from the database by
	name, so those not-yet-inserted rows raise "Payment Schedule <hash> not found"
	(shown as "The resource you are looking for is not available"). Wrap the instance's
	validation so it runs against the persisted schedule, then restore the new rows.
	"""
	if not doc.has_value_changed("payment_terms_template"):
		return

	original_validate = doc.validate_update_after_submit

	def validate_against_persisted_schedule():
		if doc.flags.ignore_validate_update_after_submit:
			return
		new_schedule = doc.get("payment_schedule")
		persisted_schedule = frappe.get_doc(doc.doctype, doc.name).get("payment_schedule")
		doc.set("payment_schedule", persisted_schedule)
		try:
			original_validate()
		finally:
			doc.set("payment_schedule", new_schedule)

	doc.validate_update_after_submit = validate_against_persisted_schedule



@frappe.whitelist()
def update_ipc_qty_sold(doc,method):
	qty_ipc = 0
	if doc.custom_interim_payment_certificate:
		dn = frappe.get_doc("Interim Payment Certificate", doc.custom_interim_payment_certificate)
		for d in dn.items:
			for i in doc.items:
				if d.item_code == i.item_code and d.name == i.custom_ipc_details:
					qty_ipc += i.qty
					qty = qty_ipc + d.inv_qty 
				frappe.db.set_value("IPC Item", d.name, "inv_qty", qty)