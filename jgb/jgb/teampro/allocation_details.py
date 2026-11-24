import frappe
from frappe.utils import flt
from frappe.utils import flt
@frappe.whitelist()
def get_detail_so(item_code, company):
	date = frappe.db.get_value("Custom Settings", "Custom Settings", "date")
	so_details = []
	
	sa = frappe.db.sql("""
		SELECT `tabSales Order Item`.parent AS parent,
			SUM(`tabSales Order Item`.qty) AS qty,
			`tabSales Order Item`.delivered_qty AS delivered_qty
		FROM `tabSales Order`
		LEFT JOIN `tabSales Order Item` ON `tabSales Order`.name = `tabSales Order Item`.parent
		WHERE `tabSales Order Item`.item_code = '%s'
		AND `tabSales Order`.docstatus != 2
		AND `tabSales Order`.company = '%s'
		AND `tabSales Order`.transaction_date >= '%s'
		GROUP BY `tabSales Order Item`.parent
		ORDER BY `tabSales Order`.transaction_date
	""" % (item_code, company, date), as_dict=True)
	sa_names = {i.parent for i in sa}
	for i in sa:
		reser_qty = frappe.db.sql("""
			SELECT SUM(reserved_qty) AS total_reserved_qty
			FROM `tabStock Reservation Entry`
			WHERE voucher_no = '%s'
			AND docstatus = 1
			AND item_code = '%s'
			AND status IN ('Reserved', 'Partially Reserved')
		""" % (i.parent, item_code), as_dict=True)[0].total_reserved_qty or 0

		prq = frappe.db.sql("""
			SELECT (reserved_qty - delivered_qty) AS partially_delivered
			FROM `tabStock Reservation Entry`
			WHERE item_code = '%s' AND voucher_no = '%s' AND status = 'Partially Delivered'
		""" % (item_code, i.parent), as_dict=True)
		
		if prq:
			reser_qty = flt(prq[0]['partially_delivered']) or 0
		
		i.qty = i.qty or 0
		i.delivered_qty = i.delivered_qty or 0
		pending_qty = i.qty - i.delivered_qty
		sb = frappe.get_doc("Sales Order", i.parent)

		so_details.append(frappe._dict({
			"parent": i.parent,
			"qty": i.qty,
			"reserved_qty": reser_qty,
			"pending_qty": pending_qty,
			"rate": i.rate,
			"delivered_qty": i.delivered_qty,
			"transaction_date": sb.transaction_date,
			"customer": sb.customer,
			"po_no": sb.po_no,
			# "status": sb.custom_reservation_status
		}))
	
	additional_entries = frappe.db.sql("""
		SELECT 
			`tabStock Reservation Entry`.voucher_no AS voucher_no,
			`tabStock Reservation Entry`.reserved_qty,
			`tabSales Order`.transaction_date,
			`tabSales Order`.customer,
			`tabSales Order`.po_no
		FROM `tabStock Reservation Entry`
		LEFT JOIN `tabSales Order` ON `tabSales Order`.name = `tabStock Reservation Entry`.voucher_no
		LEFT JOIN `tabSales Order Item` ON `tabSales Order Item`.parent = `tabSales Order`.name
		WHERE `tabStock Reservation Entry`.item_code = %s
		AND  `tabStock Reservation Entry`.status IN ('Reserved', 'Partially Reserved')
		AND (`tabSales Order Item`.item_code != %s OR `tabSales Order Item`.item_code IS NULL)
		AND (`tabSales Order`.name IS NULL 
			OR (`tabSales Order`.docstatus != 2 
				AND `tabSales Order`.company = %s 
				AND `tabSales Order`.transaction_date >= %s))
		GROUP BY `tabStock Reservation Entry`.voucher_no
		ORDER BY `tabStock Reservation Entry`.creation
	""", (item_code, item_code, company, date), as_dict=True)

#  `tabSales Order`.custom_reservation_status   

	for entry in additional_entries:
		if entry.voucher_no not in sa_names:
			so_details.append(frappe._dict({
				"parent": entry.voucher_no,
				"qty": 0,  
				"reserved_qty": entry.reserved_qty or 0,
				"pending_qty": 0,  
				"rate": 0,  
				"delivered_qty": 0,
				"transaction_date": entry.transaction_date, 
				"customer": entry.customer, 
				"po_no": entry.po_no, 
				# "status": entry.custom_reservation_status
			}))
	
	return so_details



@frappe.whitelist()
def get_detail_po(item_code,company):
	date = frappe.db.get_value("Custom Settings","Custom Settings","date")
	po_details = []
	bal_qty = 0
	# pending_qty = 0
	sa = frappe.db.sql(""" select `tabPurchase Order Item`.parent as parent,`tabPurchase Order Item`.qty as qty from `tabPurchase Order`
	left join `tabPurchase Order Item` on `tabPurchase Order`.name = `tabPurchase Order Item`.parent
	where `tabPurchase Order Item`.item_code = '%s' and `tabPurchase Order`.docstatus = 1 and `tabPurchase Order`.company = '%s' and `tabPurchase Order`.transaction_date >= '%s'  order by transaction_date""" %(item_code,company,date),as_dict=True)
	for i in sa:
	# 	pending_qty = i.qty - i.delivered_qty
		pos = frappe.db.sql("""select sum(`tabPurchase Receipt Item`.received_qty) as received_qty from `tabPurchase Receipt`
		left join `tabPurchase Receipt Item` on `tabPurchase Receipt`.name = `tabPurchase Receipt Item`.parent
		where `tabPurchase Receipt Item`.item_code = '%s' and `tabPurchase Receipt Item`.purchase_order = '%s' and `tabPurchase Receipt`.company = '%s'  and `tabPurchase Receipt`.docstatus = 1 """ % (item_code,i.parent,company), as_dict=True)
		req=0
		for j in pos:
			req=j.received_qty
		po = frappe.db.get_value("Item Inspection",{"po_number":i.parent,"item_code":item_code},["sample"])
		if not po:
			po = 0
		if not req:
			req =0
		bal_qty = i.qty - req
		bal = 0
		if bal_qty >0:
			bal = bal_qty
		sb = frappe.get_doc("Purchase Order", i.parent)
		po_details.append(frappe._dict({"mr":req,"qc":po,"parent":i.parent,"qty":i.qty,"bal_qty":bal,"transaction_date":sb.transaction_date,"supplier":sb.supplier}))
	return po_details



@frappe.whitelist()
def get_item_price_dt(item_code):
	# item_code = "114-40002104GY"
	use = frappe.session.user
	role = frappe.get_roles(use)
	data = []
	row = []
	user = frappe.get_all("User Permission",{"user":use,"allow":"Price List"},["*"])
	item = frappe.get_all("Item",{"name":item_code},["*"])
	for i in item:
		if "Cost Viewer" in role:
			std = frappe.get_value("Item Price",{"item_code":i.item_code,"price_list":"STANDARD BUYING-USD"},["price_list_rate"])
			if std:
				row.append(frappe._dict({"price_list":"STANDARD BUYING-USD","price_list_rate":std}))
			if not std:
				std = 0
				row.append(frappe._dict({"price_list":"STANDARD BUYING-USD","price_list_rate":std}))
		for s in user:
			item = frappe.db.sql(""" select price_list_rate from `tabItem Price` where price_list = '%s' and item_code = '%s' """%(s.for_value,i.item_code),as_dict=True)
			if item:
				row.append(frappe._dict({"price_list":s.for_value,"price_list_rate":item[0]["price_list_rate"]}))
		data.append(row)
	return data	
