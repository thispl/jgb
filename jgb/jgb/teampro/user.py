
import frappe
@frappe.whitelist()
def update_full_name_hook(doc, method):
	first = doc.first_name or ""
	middle = doc.middle_name or ""
	last = doc.last_name or ""
	doc.full_name = " ".join(filter(None, [first, middle, last]))