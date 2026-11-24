import frappe
from frappe.model.naming import make_autoname

@frappe.whitelist()
def set_customer_series(doc, method):
	doc.naming_series = "C-.#####"


@frappe.whitelist()
def create_new_address(doc, method):
	# Find existing billing address linked to this customer (by Dynamic Link,
	# not by address_title, so renaming the customer doesn't create duplicates)
	existing_address_name = frappe.db.get_value(
		"Dynamic Link",
		{
			"parenttype": "Address",
			"link_doctype": "Customer",
			"link_name": doc.name,
			"parentfield": "links",
		},
		"parent",
	)

	if not existing_address_name:
		add = frappe.new_doc("Address")
		add.address_type = "Billing"
		add.address_title = doc.customer_name

		add.address_line1 = doc.custom_street_name
		add.custom_address_line_1street_arabic = doc.custom_street_name_in_arabic

		add.address_line2 = doc.custom_district
		add.custom_street_in_arabic = doc.custom_district_in_arabic
		add.custom_area = doc.custom_district
		add.address_in_arabic = doc.custom_district_in_arabic

		add.custom_building_number = doc.custom_building_number
		add.city = doc.custom_city
		add.custom_city_in_arabic   = doc.custom_city_in_arabic
		add.state = doc.custom_state
		add.custom_state_in_arabic = doc.custom_state_in_arabic
		add.custom_additional_number = doc.custom_additional_number
		add.pincode = doc.custom_zippostal_code
		add.email_id = doc.custom_email
		add.phone = doc.custom_contact_no
		add.fax = doc.custom_fax_number_
		add.phone = doc.custom_phone
		add.country = doc.custom_country
		add.custom_country_in_arabic = doc.custom_country_in_arabic
		# Add link to customer
		add.append("links", {
			"link_doctype": "Customer",
			"link_name": doc.name
		})
	else:
		add = frappe.get_doc("Address", existing_address_name)
		if not add.address_type == "Billing":
			add.address_type = "Billing"
		if not add.address_title == doc.customer_name:
			add.address_title = doc.customer_name
		if not add.address_line1 == doc.custom_street_name:
			add.address_line1 = doc.custom_street_name
		if not add.custom_address_line_1street_arabic == doc.custom_street_name_in_arabic:
			add.custom_address_line_1street_arabic = doc.custom_street_name_in_arabic
		if not add.address_line2 == doc.custom_district:
			add.address_line2 = doc.custom_district
		if not add.custom_street_in_arabic == doc.custom_district_in_arabic:
			add.custom_street_in_arabic = doc.custom_district_in_arabic
		if not add.custom_area == doc.custom_district:
			add.custom_area = doc.custom_district
		if not add.address_in_arabic == doc.custom_district_in_arabic:
			add.address_in_arabic = doc.custom_district_in_arabic
		if not add.custom_building_number == doc.custom_building_number:
			add.custom_building_number = doc.custom_building_number
		if not add.city == doc.custom_city:
			add.city = doc.custom_city
		if not add.custom_city_in_arabic == doc.custom_city_in_arabic:
			add.custom_city_in_arabic   = doc.custom_city_in_arabic
		if add.state != doc.custom_state:
			add.state = doc.custom_state
		if add.custom_state_in_arabic != doc.custom_state_in_arabic:
			add.custom_state_in_arabic = doc.custom_state_in_arabic
		if not add.pincode == doc.custom_zippostal_code:
			add.pincode = doc.custom_zippostal_code
		if add.email_id != doc.custom_email:
			add.email_id = doc.custom_email
		if add.phone != doc.custom_contact_no:
			add.phone = doc.custom_contact_no
		if add.fax != doc.custom_fax_number_:
			add.fax = doc.custom_fax_number_
		if add.custom_additional_number != doc.custom_additional_number:
			add.custom_additional_number = doc.custom_additional_number
		if add.phone != doc.custom_phone:
			add.phone = doc.custom_phone
		if add.country != doc.custom_country:
			add.country = doc.custom_country
		if add.custom_country_in_arabic != doc.custom_country_in_arabic:
			add.custom_country_in_arabic = doc.custom_country_in_arabic

		# Ensure the customer link exists on this address
		already_linked = any(
			l.link_doctype == "Customer" and l.link_name == doc.name
			for l in add.links
		)
		if not already_linked:
			add.append("links", {
				"link_doctype": "Customer",
				"link_name": doc.name
			})
	add.save(ignore_permissions=True)
	if not doc.customer_primary_address:
		# doc.customer_primary_address=add.name
		frappe.db.set_value("Customer",doc.name,"customer_primary_address",add.name)
	frappe.db.commit()




@frappe.whitelist()
def create_new_customer_address(doc, method):
	# Find existing billing address linked to this customer (by Dynamic Link,
	# not by address_title, so renaming the customer doesn't create duplicates)
	existing_address_name = frappe.db.get_value(
		"Dynamic Link",
		{
			"parenttype": "Address",
			"link_doctype": "Customer",
			"link_name": doc.name,
			"parentfield": "links",
		},
		"parent",
	)

	if not existing_address_name:
		add = frappe.new_doc("Address")
		add.address_type = "Billing"
		add.address_title = doc.customer_name

		add.address_line1 = doc.custom_street_name
		add.custom_address_line_1street_arabic = doc.custom_street_name_in_arabic

		add.address_line2 = doc.custom_district
		add.custom_street_in_arabic = doc.custom_district_in_arabic
		add.custom_area = doc.custom_district
		add.address_in_arabic = doc.custom_district_in_arabic

		add.custom_building_number = doc.custom_building_number
		add.city = doc.custom_city
		add.custom_city_in_arabic   = doc.custom_city_in_arabic
		add.state = doc.custom_state
		add.custom_state_in_arabic = doc.custom_state_in_arabic
		add.custom_additional_number = doc.custom_additional_number
		add.pincode = doc.custom_zippostal_code
		add.email_id = doc.custom_email
		add.phone = doc.custom_contact_no
		add.fax = doc.custom_fax_number_
		add.phone = doc.custom_phone
		add.country = doc.custom_country
		add.custom_country_in_arabic = doc.custom_country_in_arabic
		# Add link to customer
		add.append("links", {
			"link_doctype": "Customer",
			"link_name": doc.name
		})
	else:
		add = frappe.get_doc("Address", existing_address_name)
		if not add.address_type == "Billing":
			add.address_type = "Billing"
		if not add.address_title == doc.customer_name:
			add.address_title = doc.customer_name
		if not add.address_line1 == doc.custom_street_name:
			add.address_line1 = doc.custom_street_name
		if not add.custom_address_line_1street_arabic == doc.custom_street_name_in_arabic:
			add.custom_address_line_1street_arabic = doc.custom_street_name_in_arabic
		if not add.address_line2 == doc.custom_district:
			add.address_line2 = doc.custom_district
		if not add.custom_street_in_arabic == doc.custom_district_in_arabic:
			add.custom_street_in_arabic = doc.custom_district_in_arabic
		if not add.custom_area == doc.custom_district:
			add.custom_area = doc.custom_district
		if not add.address_in_arabic == doc.custom_district_in_arabic:
			add.address_in_arabic = doc.custom_district_in_arabic
		if not add.custom_building_number == doc.custom_building_number:
			add.custom_building_number = doc.custom_building_number
		if not add.city == doc.custom_city:
			add.city = doc.custom_city
		if not add.custom_city_in_arabic == doc.custom_city_in_arabic:
			add.custom_city_in_arabic   = doc.custom_city_in_arabic
		if add.state != doc.custom_state:
			add.state = doc.custom_state
		if add.custom_state_in_arabic != doc.custom_state_in_arabic:
			add.custom_state_in_arabic = doc.custom_state_in_arabic
		if not add.pincode == doc.custom_zippostal_code:
			add.pincode = doc.custom_zippostal_code
		if add.email_id != doc.custom_email:
			add.email_id = doc.custom_email
		if add.phone != doc.custom_contact_no:
			add.phone = doc.custom_contact_no
		if add.fax != doc.custom_fax_number_:
			add.fax = doc.custom_fax_number_
		if add.custom_additional_number != doc.custom_additional_number:
			add.custom_additional_number = doc.custom_additional_number
		if add.phone != doc.custom_phone:
			add.phone = doc.custom_phone
		if add.country != doc.custom_country:
			add.country = doc.custom_country
		if add.custom_country_in_arabic != doc.custom_country_in_arabic:
			add.custom_country_in_arabic = doc.custom_country_in_arabic

		# Ensure the customer link exists on this address
		already_linked = any(
			l.link_doctype == "Customer" and l.link_name == doc.name
			for l in add.links
		)
		if not already_linked:
			add.append("links", {
				"link_doctype": "Customer",
				"link_name": doc.name
			})
	add.save(ignore_permissions=True)
	if not doc.customer_primary_address:
		doc.customer_primary_address=add.name
	doc.save()
	frappe.db.commit()

