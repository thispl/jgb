import frappe
from frappe.utils import flt
from frappe import _
from frappe.utils import add_months, nowdate, getdate
from erpnext.accounts.party import get_party_account, get_party_bank_account
from erpnext.accounts.doctype.payment_entry.payment_entry import get_bank_cash_account, get_payment_entry

@frappe.whitelist()
def make_payment_entry_from_advance_sales_invoice(advance_invoice):
	ai = frappe.get_doc("Advance Sales Invoice", advance_invoice)

	if not ai.sales_order:
		frappe.throw(_("Sales Order is not linked to this Advance Sales Invoice"))

	if not flt(ai.grand_total):
		frappe.throw(_("Grand Total is required to create Payment Entry"))

	existing_pe = frappe.db.sql(
		"""
		SELECT DISTINCT pe.name
		FROM `tabPayment Entry` pe
		LEFT JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
		WHERE pe.docstatus = 1
			AND pe.party = %s
			AND pe.company = %s
			AND (
				(per.reference_doctype = 'Sales Order' AND per.reference_name = %s)
				OR IFNULL(pe.custom_sales_order, '') = %s
			)
			AND ROUND(pe.paid_amount, 2) = ROUND(%s, 2)
		""",
		(ai.party, ai.company, ai.sales_order, ai.sales_order, flt(ai.grand_total)),
		as_dict=1,
	)
	if existing_pe:
		return {
			"payment_entry": existing_pe[0].name,
			"is_existing": True,
		}

	# Build a new Payment Entry and return it so the client can open it in creation mode.
	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Receive"
	pe.party_type = "Customer"
	pe.party = ai.party
	pe.party_name = ai.party_name
	pe.company = ai.company
	pe.posting_date = ai.posting_date or nowdate()
	pe.reference_date = ai.posting_date or nowdate()
	pe.paid_from = ai.paid_from or get_party_account("Customer", ai.party, ai.company)
	if ai.paid_to:
		pe.paid_to = ai.paid_to
		pe.bank_account = frappe.db.get_value(
			"Bank Account",
			{"account": ai.paid_to, "is_company_account": 1, "company": ai.company},
			"name",
		)
	else:
		bank = get_bank_cash_account(frappe._dict({"company": ai.company}), None)
		if bank:
			pe.paid_to = bank.account
			pe.bank_account = bank.name
	pe.paid_amount = flt(ai.grand_total)
	pe.received_amount = flt(ai.grand_total)

	if ai.project:
		pe.project = ai.project

	if pe.meta.has_field("custom_sales_order"):
		pe.custom_sales_order = ai.sales_order
	if pe.meta.has_field("custom_is_advance"):
		pe.custom_is_advance = 1

	pe.append("references", {
		"reference_doctype": "Sales Order",
		"reference_name": ai.sales_order,
		"total_amount": flt(ai.grand_total),
		"outstanding_amount": flt(ai.grand_total),
		"allocated_amount": flt(ai.grand_total),
	})

	pe.setup_party_account_field()
	pe.set_missing_values()
	pe.set_exchange_rate()
	pe.set_amounts()

	return {
		"payment_entry": None,
		"is_existing": False,
		"doc": pe.as_dict(convert_dates_to_str=True),
	}

	

@frappe.whitelist()
def validate_advance_sales_invoice(doc, method):
	# Validation removed: Advance Sales Invoice can now be submitted before the Payment Entry is created.
	# Payment Entry creation is provided via the "Create Payment Entry" button on the form.
	pass


def fill_address_contact(doc, method=None):
	from frappe.contacts.doctype.address.address import get_address_display
	from frappe.contacts.doctype.contact.contact import get_contact_details

	if doc.get("customer_address") and not doc.get("address_display"):
		doc.address_display = get_address_display(doc.customer_address)

	if doc.get("contact_person"):
		details = get_contact_details(doc.contact_person) or {}
		if not doc.get("contact_display"):
			doc.contact_display = details.get("contact_display")
		if not doc.get("contact_mobile"):
			doc.contact_mobile = details.get("contact_mobile")
		if not doc.get("contact_email"):
			doc.contact_email = details.get("contact_email")




# @frappe.whitelist()
# def validate_advance_sales_invoice(doc, method):
# 	if not doc.custom_is_historical_import:
# 		if doc.sales_order:
# 			pe_details = frappe.db.sql("""
# 				SELECT pe.name, pe.paid_amount
# 				FROM `tabPayment Entry Reference` per
# 				INNER JOIN `tabPayment Entry` pe
# 					ON per.parent = pe.name
# 				WHERE per.reference_doctype = 'Sales Order'
# 				AND per.reference_name = %s
# 				AND pe.docstatus = 1
# 			""", (doc.sales_order,), as_dict=1)
# 			if not pe_details:
# 				frappe.throw("No Payment Entry found against the Sales Order. Please create a Payment Entry first.")
# 			match_found = False
# 			for d in pe_details:
# 				if round(flt(d.paid_amount), 2) == round(flt(doc.grand_total), 2):
# 					match_found = True
# 					break
# 			if not match_found:
# 				frappe.throw(f"No Payment Entry amount matches the Advance Invoice total ({doc.grand_total}).")