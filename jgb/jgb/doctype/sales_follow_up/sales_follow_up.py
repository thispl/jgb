# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SalesFollowUP(Document):
	pass

@frappe.whitelist()
def customer_contacts(customer):
	customer_contacts=[]

	customer_contact = frappe.get_doc("Customer", customer)
	for i in customer_contact.custom_customer_contact_details:
		contact_data = {
			"person_name": i.person_name or '',
			"mobile": i.mobile or '',
			"is_primary": i.is_primary or False,
			"has_whatsapp": i.has_whatsapp or False,
			"email_id": i.email_id or '',
			"is_primaryemail": i.is_primaryemail or False,
			"service":i.service or ''
		}
		customer_contacts.append(frappe._dict(contact_data))
	return customer_contacts

@frappe.whitelist()
def organization_update_sp(customer):
	customer=frappe.db.get_value("Customer",{"name":customer},["name"])
	return customer

@frappe.whitelist()
def organization_update_sp_lead(lead):
	company_name=frappe.db.get_value("Lead",{"name":lead},["company_name"])
	return company_name

@frappe.whitelist()
def add_custom_appointment_details_in_lead(name, lead, visted_date, visted_by, appointment_remarks):
	lead_doc = frappe.get_doc("Lead", lead)

	if lead_doc:
		if lead_doc.custom_visit_status_details:  # Ensure it exists
			lead_doc.append("custom_visit_status_details", {
				"sales_follow_up": name,
				"visit_date": visted_date,
				"visit_by": visted_by,
				"remarks": appointment_remarks
			})
				
		else:
			# If the child table is empty, add a new entry
			lead_doc.append("custom_visit_status_details", {
				"sales_follow_up": name,
				"visit_date": visted_date,
				"visit_by": visted_by,
				"remarks": appointment_remarks
			})

		lead_doc.save()
		frappe.db.commit()  # Not necessary, but keeping it here if needed

@frappe.whitelist()
def update_spf_status(doc,method):
	if doc.lead_name:
		sfp_name = frappe.db.get_all("Sales Follow UP", {"party_name": doc.lead_name}, "name")
		if sfp_name:
			for i in sfp_name:
				sfp_doc = frappe.get_doc("Sales Follow UP", i.name) 
				sfp_doc.status = "Converted"
				sfp_doc.party_from="Customer"
				sfp_doc.party_name=doc.name
				sfp_doc.save()  
				sfp_doc.reload() 
				frappe.db.commit() 

from datetime import datetime
from frappe.utils.data import date_diff, now_datetime, nowdate, today, add_days

@frappe.whitelist()
def update_spf_details_lead(doc,method):
	created_on=now_datetime()
	if doc.party_from=="Lead":
		lead=frappe.get_doc("Lead",doc.party_name)
		lead.append("custom_sfp_details", {"sfp_id": doc.name,"sfp_owner":doc.account_manager_lead_owner,"created_on":created_on,"service":doc.service})
		lead.save()
		frappe.db.commit()  
	if doc.party_from=="Customer":
		customer=frappe.get_doc("Customer",doc.party_name)
		customer.append("custom_sales_follow_up", {"sfp_id": doc.name,"sfp_owner":doc.account_manager_lead_owner,"created_on":created_on,"service":doc.service})
		customer.save()
		frappe.db.commit() 
	
@frappe.whitelist()
def set_quotation(doc,method):
	frappe.db.set_value("Opportunity",doc.opportunity,"custom_quotation",doc.name)

@frappe.whitelist()
def update_sfp_opportunity(doc,method):
	if doc.custom_sales_follow_up and doc.custom_quotation and doc.status=="Lost":
		frappe.db.set_value("Sales Follow UP",doc.custom_sales_follow_up,"status","Replied")

@frappe.whitelist()
def update_lead_contacts_sfp(doc,method):
    if doc.party_from=="Lead" and doc.party_name:
        lead_contact = frappe.get_doc("Lead", doc.party_name)
        for i in lead_contact.custom_lead_contacts:
            doc.append("contacts", {
                'person_name': i.person_name,
                'mobile': i.mobile,
                'is_primary': i.is_primary,
                'has_whatsapp': i.has_whatsapp,
                'email_id': i.email_id,
                'is_primaryemail': i.is_primaryemail,
                'service':i.service
            })
            doc.append("custom_contact_details", {
                'person_name': i.person_name,
                'mobile': i.mobile,
                'is_primary': i.is_primary,
                'has_whatsapp': i.has_whatsapp,
                'email_id': i.email_id,
                'is_primaryemail': i.is_primaryemail,
                'service':i.service
            })
    elif doc.party_from=="Customer" and doc.party_name:
        lead_contact = frappe.get_doc("Customer", doc.party_name)
        for i in lead_contact.custom_customer_contacts:
            doc.append("custom_customer_contacts", {
                "person_name": i.person_name or '',
                "mobile": i.mobile or '',
                "is_primary": i.is_primary or False,
                "has_whatsapp": i.has_whatsapp or False,
                "email_id": i.email_id or '',
                "is_primaryemail": i.is_primaryemail or False,
                "service":i.service or ''
            })
    doc.save()
    frappe.db.commit()  


@frappe.whitelist()
def update_dnc(name):
    sfp_name = frappe.db.get_all("Sales Follow UP", {"party_name":name}, "name")
    if sfp_name:
        for i in sfp_name:
            sfp_doc = frappe.get_doc("Sales Follow UP", i.name) 
            sfp_doc.status = "Do Not Contact"
            sfp_doc.save()  
            sfp_doc.reload() 
            frappe.db.commit() 

@frappe.whitelist()
def update_dnc_converted(name):
    sfp_name = frappe.db.get_all("Sales Follow UP", {"party_name":name}, "name")
    if sfp_name:
        for i in sfp_name:
            sfp_doc = frappe.get_doc("Sales Follow UP", i.name) 
            sfp_doc.status = "Converted"
            sfp_doc.save()  
            sfp_doc.reload() 
            frappe.db.commit() 

@frappe.whitelist()
def update_app_visit_status(lead,visit):
    doc=frappe.get_doc('Lead',lead)
    doc.visit_status=visit
    doc.save()
    doc.reload()