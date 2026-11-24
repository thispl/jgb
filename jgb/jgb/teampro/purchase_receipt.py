import frappe
import re
from frappe import _

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



import re
import frappe

@frappe.whitelist()
def get_srbnb_account_for_division(division=None, company=None):
	if not division:
		return
	snrb_account = frappe.db.get_value(
		"Division Account Details", {"parent": division,"company": company},"snrb_account")
	if snrb_account:
		return snrb_account


@frappe.whitelist()
def update_logistic_request(doc,method):
	if doc.custom_logistics_request:
		if frappe.db.exists('Logistics Request',{'name':doc.custom_logistics_request}):
			logistics=frappe.get_doc('Logistics Request',{'name':doc.custom_logistics_request})
			if logistics.workflow_state=='Out for Delivery':
				logistics.workflow_state='Arrived'
			logistics.save(ignore_permissions=True)
			# frappe.db.commit()  



import frappe
from frappe.utils import nowtime
@frappe.whitelist()
def update_excess_qty_pr(doc, method):
	if not doc.items:
		return
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type = "Material Receipt"
	stock_entry.company = doc.company
	stock_entry.posting_date = doc.posting_date
	stock_entry.posting_time = doc.posting_time or nowtime()
	stock_entry.custom_purchase_receipt=doc.name
	target_warehouse = doc.set_warehouse or frappe.db.get_value("Warehouse", {
		"warehouse_name": "Transit Warehouse",
		"company": doc.company
	}, "name")

	if not target_warehouse:
		frappe.throw(f"Target warehouse not found for company {doc.company}")

	for item in doc.items:
			if item.custom_excess_quantity > 0:
				# Only allow excess qty when received qty actually exceeds PO qty
				po_qty = 0
				if item.purchase_order and item.purchase_order_item:
					po_qty = frappe.db.get_value(
						"Purchase Order Item",
						item.purchase_order_item,
						"qty",
					) or 0
				if po_qty and item.received_qty <= po_qty:
					frappe.throw(
						_(
							"Row {0}: Excess Quantity cannot be set for item {1}. "
							"Received qty ({2}) does not exceed PO qty ({3}). "
							"Please clear the Excess Quantity field."
						).format(item.idx, item.item_code, item.received_qty, po_qty)
					)
				stock_entry.append("items", {
					"item_code": item.item_code,
					"qty": item.custom_excess_quantity,
					"t_warehouse": target_warehouse,
					"uom": item.uom,
					"stock_uom": item.stock_uom,
					"conversion_factor": item.conversion_factor,
					"basic_rate": item.rate,
					"expense_account": item.expense_account or "",
					"cost_center": item.cost_center or "",
				})

	if stock_entry.items:
		stock_entry.insert()
		stock_entry.submit()
		frappe.msgprint(f"Stock Entry {stock_entry.name} created for excess quantity.")




@frappe.whitelist()
def update_pr_in_lr_submit(doc,method):
	if doc.custom_logistics_request:
		if frappe.db.exists('Logistics Request',{'name':doc.custom_logistics_request}):
			docs=frappe.get_doc("Logistics Request",doc.custom_logistics_request)
			if docs.lr_status_details:
				for i in docs.lr_status_details:
					if i.voucher_name==doc.name:
						frappe.db.set_value("LR Status Details", i.name, "status", "Submitted", update_modified=False)



#On first save of PR, PR  ID is set in LR
@frappe.whitelist()
def update_pr_in_lr_draft(doc,method):
	if doc.custom_logistics_request:
		if frappe.db.exists('Logistics Request',{'name':doc.custom_logistics_request}):
			docs=frappe.get_doc("Logistics Request",doc.custom_logistics_request)
			docs.append("lr_status_details",{
				"voucher_type":"Purchase Receipt",
				"voucher_name":doc.name,
				"status":"Draft"
			})
			docs.has_purchase_receipt=1
			docs.save(ignore_permissions=True)


import frappe

@frappe.whitelist()
def send_notification_to_sales(doc, method):
	po_list = list(set([item.purchase_order for item in doc.items if item.purchase_order]))

	if not po_list:
		return

	for po in po_list:
		so = frappe.db.get_value(
			"Purchase Order Item",
			{"parent": po},
			"sales_order"
		)
		if not so:
			continue

		sales_persons = frappe.db.get_all(
			"Sales Order",
			{'name': so},
			['custom_sales_person']
		)

		if not sales_persons:
			continue

		for sp in sales_persons:
			email = sp.custom_sales_person

			if not email:
				continue

			frappe.sendmail(
				recipients=[email],
				subject=f"Purchase Receipt Created for Sales Order {so}",
				message=f"""
					Dear Sales Person,<br><br>
					Purchase Receipt <b>{doc.name}</b> has been created for Sales Order <b>{so}</b>.<br><br>
					Regards,<br>
					ERP
				"""
			)



#On first save of PR, PR  ID is set in LR
@frappe.whitelist()
def update_pr_in_lr_cancel(doc,method):
	if doc.custom_logistics_request:
		if frappe.db.exists('Logistics Request',{'name':doc.custom_logistics_request}):
			docs=frappe.get_doc("Logistics Request",doc.custom_logistics_request)
			if docs.lr_status_details:
				for i in docs.lr_status_details:
					if i.voucher_name==doc.name:
						docs.remove(i)
			docs.save(ignore_permissions=True)



def update_pr_currency_validate(doc,method):
	if doc.custom_logistics_request and doc.items:
		if doc.items[0].purchase_order:
			po = frappe.get_doc("Purchase Order", doc.items[0].purchase_order)
			doc.currency = po.currency
			doc.conversion_rate = po.conversion_rate



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




def set_inventory_account_from_division(doc, method):
	company = doc.company
	division = doc.custom_division

	if not division:
		return
	inventory_account = frappe.db.get_value(
		"Division Account Details", {"parent": division,"company": company},"inventory_account")
	if inventory_account:
		doc.custom_inventory_account = inventory_account



def update_pr_currency_validate(doc,method):
	if doc.custom_logistics_request and doc.items:
		if doc.items[0].purchase_order:
			po = frappe.get_doc("Purchase Order", doc.items[0].purchase_order)
			doc.currency = po.currency
			doc.conversion_rate = po.conversion_rate


from frappe.utils import flt, nowdate, nowtime as _nowtime


@frappe.whitelist()
def make_manufacture_stock_entry(purchase_receipt, bom_no, fg_qty, target_warehouse=None):
	"""Build a Manufacture Stock Entry from a submitted Purchase Receipt.

	Returns the unsaved doc (open_mapped_doc style) so the user reviews and
	saves it from the UI. BOM raw materials get s_warehouse from the PR row
	that received them (fallback: PR set_warehouse); the finished good row
	gets t_warehouse from target_warehouse. PR items that are not BOM
	components are simply not part of the entry — they remain received stock.
	"""
	if not frappe.has_permission("Stock Entry", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	pr = frappe.get_doc("Purchase Receipt", purchase_receipt)
	if pr.docstatus != 1:
		frappe.throw(_("Purchase Receipt {0} must be submitted.").format(purchase_receipt))

	fg_qty = flt(fg_qty)
	if fg_qty <= 0:
		frappe.throw(_("Manufacturing Quantity must be greater than zero."))

	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Manufacture"
	se.purpose = "Manufacture"
	se.company = pr.company
	se.posting_date = nowdate()
	se.posting_time = _nowtime()
	se.bom_no = bom_no
	se.from_bom = 1
	se.fg_completed_qty = fg_qty
	se.custom_purchase_receipt = pr.name

	# Project-tagged GL keeps manufacture cost in project profitability
	for row in pr.items:
		if row.sales_order:
			project = frappe.db.get_value("Sales Order", row.sales_order, "project")
			if project:
				se.project = project
				break

	# Standard BOM explosion: raw material rows + finished good + scrap rows
	se.get_items()

	# get_items copies the item's sales COGS into expense_account -> ERPNext's
	# COGS-type Difference Account warning. Stock Adjustment is the right sink.
	stock_adj = frappe.get_cached_value("Company", pr.company, "stock_adjustment_account")

	pr_warehouse = {row.item_code: row.warehouse for row in pr.items}
	for d in se.items:
		if d.is_finished_item or d.is_scrap_item:
			d.t_warehouse = target_warehouse
		else:
			d.s_warehouse = pr_warehouse.get(d.item_code) or pr.set_warehouse
		if stock_adj:
			d.expense_account = stock_adj
		if se.project:
			d.project = se.project

	return se


@frappe.whitelist()
def auto_manufacture_stock_entries(purchase_receipt):
	"""Create one draft Manufacture Stock Entry per active BOM whose raw
	materials are fully covered by this PR's items.

	Returns list of created Stock Entry names (empty when nothing matches, so
	the caller can fall back to the manual BOM dialog). PR quantities are
	allocated greedily across matches, default BOMs first.
	"""
	if not frappe.has_permission("Stock Entry", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	pr = frappe.get_doc("Purchase Receipt", purchase_receipt)
	if pr.docstatus != 1:
		frappe.throw(_("Purchase Receipt {0} must be submitted.").format(purchase_receipt))

	remaining = {}
	for d in pr.items:
		remaining[d.item_code] = remaining.get(d.item_code, 0) + flt(d.stock_qty or d.qty)

	boms = frappe.db.sql(
		"""
		SELECT b.name
		FROM `tabBOM` b
		WHERE b.docstatus = 1 AND b.is_active = 1 AND b.company = %(company)s
		  AND NOT EXISTS (
			  SELECT 1 FROM `tabBOM Item` bi
			  WHERE bi.parent = b.name AND bi.item_code NOT IN %(codes)s
		  )
		  AND EXISTS (SELECT 1 FROM `tabBOM Item` bi2 WHERE bi2.parent = b.name)
		ORDER BY b.is_default DESC, b.name
		""",
		{"company": pr.company, "codes": tuple(remaining)},
		pluck=True,
	)

	created = []
	for bom_name in boms:
		req = frappe.get_all(
			"BOM Item", filters={"parent": bom_name}, fields=["item_code", "qty"]
		)
		if not req:
			continue
		fg_qty = min(int(remaining.get(r.item_code, 0) // flt(r.qty)) for r in req)
		if fg_qty < 1:
			continue
		se = make_manufacture_stock_entry(pr.name, bom_name, fg_qty, pr.set_warehouse)
		se.insert()
		created.append(se.name)
		for r in req:
			remaining[r.item_code] -= fg_qty * flt(r.qty)

	return created