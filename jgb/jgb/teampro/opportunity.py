import frappe
import json

@frappe.whitelist()
def update_opp_status(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)

		# Check if a matching row exists
		exists = False
		for row in ref.table_gygr:
			if row.document_type_name == doc.custom_sales_follow_up:
				ref.remove(row)
				exists = True
				break  # Stop after finding and removing the first match
			if row.document_type_name == doc.party_name:
				ref.remove(row)
				exists = True
				break 

		ref.append("table_gygr", {
			"document_type": doc.doctype,
			"document_type_name": doc.name,
			"status": doc.status
		})

		ref.save(ignore_permissions=True)
		frappe.db.commit()
