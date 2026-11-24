import frappe
from frappe.utils import flt
from frappe import _


@frappe.whitelist()
def get_series(company,doctype):
	series = frappe.db.get_value("Company",{"name":company},["abbr"])
	return f"{series}-{"RET"}-.YYYY."


@frappe.whitelist()
def update_advance_money(advance):
	words=frappe.utils.money_in_words(advance)
	return words


@frappe.whitelist()
def cancel_journal_entry_retention(doc,method):
	jv = frappe.db.get_value("Journal Entry",{"cheque_no":doc.name},["name"])
	if jv:
		jv_cancel=frappe.get_doc("Journal Entry",jv)
		if jv_cancel.docstatus == 1:
			jv_cancel.cancel()



@frappe.whitelist()
def create_new_journal_entry_retention(doc,method):
	document = frappe.get_doc("Retention Invoice", doc.name)
	sales=frappe.get_doc("Sales Order",doc.sales_order)
	jv = frappe.new_doc("Journal Entry")
	jv.voucher_type = "Journal Entry"
	jv.company = document.company
	jv.posting_date = doc.transaction_date
	jv.user_remark = f"Customer Name : {sales.customer} Order No : {doc.sales_order} Order Date : {sales.transaction_date} Project : {sales.project}"
	jv.cheque_no = doc.name
	jv.custom_advance_invoice=doc.name
	jv.cheque_date = document.transaction_date
	advance_account = frappe.db.get_value("Company", {"name": document.company}, "custom_default_retention_account")
	receivable_account = frappe.db.get_value("Company", {"name": document.company}, "default_receivable_account")
	accounts = [
		{
			'account': advance_account,
			'credit_in_account_currency': document.advance_amount1
		},
		{
			'account': receivable_account,
			'debit_in_account_currency': document.advance_amount1,
			'party_type': 'Customer',
			'party': document.customer
		}
	]

	for account in accounts:
		jv.append('accounts', account)

	jv.save(ignore_permissions=True)
	jv.submit()
	custom_invoice = jv.custom_advance_invoice
	existing_docs = frappe.db.sql("""
		SELECT name FROM `tabJournal Entry`
		WHERE name LIKE %s
		ORDER BY name DESC
	""", (custom_invoice + '%'), as_dict=True)
	if not existing_docs:
		new_name = f"{custom_invoice}-01"
	else:
		last_doc = existing_docs[0]
		last_number = int(last_doc.name.split('-')[-1])
		new_sequence = last_number + 1
		new_name = f"{custom_invoice}-{new_sequence}"
	frappe.rename_doc("Journal Entry", jv.name, new_name, force=1)
	
	