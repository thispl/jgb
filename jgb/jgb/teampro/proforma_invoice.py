import frappe
from frappe.utils import getdate
from frappe.utils import money_in_words
from frappe.utils import flt, fmt_money

@frappe.whitelist()
def money_in_words_advance_invoice(amt):
	
	if amt:
		amt_word = money_in_words(flt(amt))
		return amt_word



@frappe.whitelist()
def make_payment_entry_from_advance_invoice(advance_invoice):
    ai = frappe.get_doc("Advance Invoice", advance_invoice)

    pe = frappe.new_doc("Payment Entry")

   
    pe.payment_type = "Receive"
    pe.party_type = "Customer"
    pe.party = ai.customer
    pe.party_name = ai.customer
    pe.company = ai.company
    pe.posting_date = frappe.utils.nowdate()

    pe.paid_amount = ai.advance_amount1
    pe.received_amount = ai.advance_amount1

    pe.custom_sales_order = ai.sales_order
    pe.custom_advance_invoice = ai.name
    pe.custom_is_advance = 1
    pe.custom_outstanding_amount = ai.advance_amount1
    
    pe.project = ai.project

    
    receivable_account = (
        frappe.get_cached_value("Customer", ai.customer, "default_receivable_account")
        or frappe.get_cached_value("Company", ai.company, "default_receivable_account")
    )

    cash_or_bank_account = (
        frappe.get_cached_value("Company", ai.company, "default_cash_account")
        or frappe.get_cached_value("Company", ai.company, "default_bank_account")
    )

    pe.paid_from = receivable_account
    pe.paid_to = cash_or_bank_account

    
    pe.party_account = receivable_account

   
    pe.append("references", {
        "reference_doctype": "Sales Order",
        "reference_name": ai.sales_order,
        "total_amount": ai.grand_total,
        "outstanding_amount": ai.advance_amount1,
        "allocated_amount": ai.advance_amount1
    })

   
    pe.set_missing_values()
    pe.set_amounts()

    return pe
    
	