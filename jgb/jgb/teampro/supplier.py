import frappe

@frappe.whitelist()
def set_supplier_series(doc,method):
	doc.naming_series = "S-.#####"