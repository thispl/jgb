import frappe
from frappe.utils import flt
@frappe.whitelist()
def update_ipc_values(dn):
	delivery_note = frappe.get_doc("Delivery Note", dn)
	return delivery_note.items



@frappe.whitelist()
def update_previously_certified_value(so):
	result = frappe.db.sql(
		"""
		SELECT SUM(balance_amount)
		FROM `tabInterim Payment Certificate`
		WHERE sales_order = %s
		AND docstatus = 1
		""",
		so,
	)

	net_certified_to_date = result[0][0] or 0
	return net_certified_to_date


@frappe.whitelist()
def update_ipc_values_so(so):
	sales_order = frappe.get_doc("Sales Order", so)
	return sales_order.items



@frappe.whitelist()
def update_advance_percentage(so):
	advance = frappe.db.sql(
		"""
		SELECT SUM(asi.custom_advance_percentage)
		FROM `tabAdvance Sales Invoice` asi
		INNER JOIN `tabPayment Entry Reference` pre
			ON pre.parent = asi.name
		WHERE
			asi.docstatus = 1
			AND pre.reference_name = %s
		""",
		(so,),
	)[0][0] or 0
	return advance