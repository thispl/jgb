# Division Account Details gains a "Delivery Charges Account" so a Logistics
# Request charge allocated across Delivery Notes posts each split line to the
# division's own delivery account (5023 VLP, 5013 HVA, ...) instead of the
# single general 5093 that the Book Invoice button used to hardcode.
#
# The seed values are the accounts the accounts team already uses on the
# Purchase Invoices booked against Logistics Requests; they stay editable on
# the Division form afterwards.

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

FIELD = "delivery_charges_account"
COMPANY = "Joint Global Business Co LLC"

DIVISION_ACCOUNTS = {
	"Valves and Pipeline (VLP)": "5023 - Delivery & Distribution Charges - Valves & Pipelines - JGB",
	"HVAC Division - (HVA)": "5013 - Delivery & Distribution Charges  - HVAC - JGB",
	"Filtration Division (FRD)": "5043 - Delivery & Distribution Charges - Filtration - JGB",
	"Waterworks Division (WTR)": "5033 - Delivery & Distribution Charges - Waterworks - JGB",
	"Misting (MST)": "5053 - Delivery & Distribution Charges - Misting - JGB",
}


def execute():
	create_custom_fields(
		{
			"Division Account Details": [
				dict(
					fieldname=FIELD,
					label="Delivery Charges Account",
					fieldtype="Link",
					options="Account",
					insert_after="cos_account",
					description="Expense account used for Logistics Request delivery charges allocated across Delivery Notes",
				)
			]
		}
	)

	for division, account in DIVISION_ACCOUNTS.items():
		row = frappe.db.get_value(
			"Division Account Details", {"parent": division, "company": COMPANY}, "name"
		)
		if not row or frappe.db.get_value("Division Account Details", row, FIELD):
			continue
		if frappe.db.exists("Account", account):
			frappe.db.set_value("Division Account Details", row, FIELD, account)
