import frappe

@frappe.whitelist()
def update_lead_name(doc,method):
	frappe.db.set_value('Lead',doc.name,'party_name',doc.name)
	doc.reload()