import frappe
from frappe.utils import flt
import json

@frappe.whitelist()
def get_so_pending_details(division=None):
	item_list = frappe.get_all("Item", {"disabled": 0}, ["name", "item_name"])
	data = []

	for i in item_list:
		# Get actual stock
		actual_stock_data = frappe.db.sql("""
			SELECT SUM(actual_qty) AS actual_qty
			FROM `tabBin`
			WHERE item_code = %s
		""", (i.name,), as_dict=True)

		actual_qty = flt(actual_stock_data[0].actual_qty) if actual_stock_data else 0

		# Filter Sales Orders
		division_condition = "AND so.custom_division = %s" if division else ""
		params = (i.name, division) if division else (i.name,)

		sales_orders = frappe.db.sql(f"""
			SELECT
				soi.item_code AS item_code,
				so.name AS name,
				SUM(soi.qty) AS qty,
				SUM(soi.delivered_qty) AS delivered_qty,
				SUM(soi.qty - soi.delivered_qty) AS pending_qty
			FROM `tabSales Order` so
			LEFT JOIN `tabSales Order Item` soi ON so.name = soi.parent
			WHERE soi.item_code = %s AND so.docstatus = 1
			AND (soi.qty - soi.delivered_qty) > 0
			{division_condition}
			GROUP BY so.name, soi.item_code
		""", params, as_dict=True)

		if not sales_orders:
			continue

		reserved_qty_total = []

		for so in sales_orders:
			reserved_qty = 0.0

			# Reserved and Partially Reserved
			rs1 = frappe.db.sql("""
				SELECT SUM(reserved_qty) AS reserved_qty
				FROM `tabStock Reservation Entry`
				WHERE item_code = %s AND voucher_no = %s
				AND status IN ('Reserved', 'Partially Reserved')
			""", (i.name, so['name']), as_dict=True)

			if rs1 and rs1[0].reserved_qty:
				reserved_qty += flt(rs1[0].reserved_qty)

			# Partially Delivered
			rs2 = frappe.db.sql("""
				SELECT SUM(reserved_qty - delivered_qty) AS reserved_qty
				FROM `tabStock Reservation Entry`
				WHERE item_code = %s AND voucher_no = %s
				AND status = 'Partially Delivered'
			""", (i.name, so['name']), as_dict=True)

			if rs2 and rs2[0].reserved_qty:
				reserved_qty += flt(rs2[0].reserved_qty)

			reserved_qty_total.append(reserved_qty)

		pending_so_names = [so["name"] for so in sales_orders]
		pending_qtys = [flt(so["pending_qty"]) for so in sales_orders]
		qty = [flt(so["qty"]) for so in sales_orders]
		dn_qty = [flt(so["delivered_qty"]) for so in sales_orders]

		total_pending_qty = sum(pending_qtys)

		if total_pending_qty > actual_qty:
			data.append([
				i.name,
				i.item_name,
				actual_qty,
				pending_so_names,
				pending_qtys,
				qty,
				dn_qty,
				reserved_qty_total
			])

	return data

@frappe.whitelist()
def reservation_creation(allocations, division=None):
	if isinstance(allocations, str):
		allocations = json.loads(allocations)

	if not isinstance(allocations, list):
		frappe.throw("Invalid allocations format")

	created_reservations = []

	for row in allocations:
		so = row.get("sales_order")
		item_code = row.get("item_code")
		qty = flt(row.get("qty"))

		if not so or not item_code or qty <= 0:
			continue

		voucher = frappe.db.get_value("Sales Order Item", {"parent": so, "item_code": item_code}, "name")
		voucher_qty = frappe.db.get_value("Sales Order Item", {"parent": so, "item_code": item_code}, "qty")
		actual_stock_data = frappe.db.sql("""
			SELECT SUM(actual_qty) AS actual_qty FROM `tabBin` WHERE item_code = %s
		""", (item_code,), as_dict=True)

		actual_qty = flt(actual_stock_data[0].actual_qty) if actual_stock_data else 0

		reser = frappe.new_doc("Stock Reservation Entry")
		reser.voucher_no = so
		reser.voucher_type = "Sales Order"
		reser.item_code = item_code
		reser.voucher_detail_no = voucher
		reser.voucher_qty = voucher_qty
		reser.reserved_qty = qty
		reser.available_qty = actual_qty
		reser.company = frappe.db.get_value("Sales Order", so, "company")
		reser.warehouse = frappe.db.get_value("Sales Order Item", {"parent": so, "item_code": item_code}, "warehouse")
		reser.insert(ignore_permissions=True)
		created_reservations.append(reser.name)

	return created_reservations
