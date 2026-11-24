import frappe
from frappe.utils import flt
from frappe import _
from frappe.utils import add_months, nowdate, getdate

@frappe.whitelist()
def make_employee_advance_journal_entry(employee_advance):
	doc = frappe.get_doc("Employee Advance", employee_advance)
	division = doc.custom_division
	cost_center = ""
	if division:
		cost_center = get_cost_center_for_division(division, doc.company)

	loan_account = "1401 - Employee Loans & Advance - JGB"
	if not loan_account:
		frappe.throw(_("Employee Loan Account not found for company {0}").format(doc.company))

	# if loan_account == doc.advance_account:
	# 	frappe.throw(_("Employee Loan Account cannot be the same as the Advance Account"))

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.company = doc.company
	je.posting_date = nowdate()
	je.custom_division = division
	je.custom_cost_center = cost_center
	je.remark = "Employee Advance - " + doc.name

	amount, exchange_rate, account_currency = get_employee_advance_je_amount(loan_account, doc)
	je.append(
		"accounts",
		{
			"account": loan_account,
			"account_currency": account_currency,
			"exchange_rate": flt(exchange_rate),
			"cost_center": cost_center,
			"debit_in_account_currency": flt(amount),
			"party_type": "Employee",
			"party": doc.employee,
			"reference_type": "Employee Advance",
			"reference_name": doc.name,
		},
	)

	return je.as_dict()



import frappe
import re

@frappe.whitelist()
def get_cost_center_for_division(division=None, company=None):
	keyword = extract_keyword_from_division(division)

	if not keyword or not company:
		return ""

	cost_center = frappe.db.sql("""
		SELECT name FROM `tabCost Center`
		WHERE company = %s
		  AND is_group = 0
		  AND name LIKE %s
		LIMIT 1
	""", (
		company,
		f"%{keyword}%",
	), as_dict=0)

	return cost_center[0][0] if cost_center else ""



def get_employee_advance_je_amount(account, doc):
	account_currency = frappe.db.get_value("Account", account, "account_currency")
	if account_currency != doc.currency:
		amount = flt(doc.paid_amount) * flt(doc.exchange_rate)
		exchange_rate = 1
	else:
		amount = doc.paid_amount
		exchange_rate = doc.exchange_rate
	return amount, exchange_rate, account_currency


def extract_keyword_from_division(division):
	# Custom logic to extract from full name like "HVAC Division - (HVA)"
	match = re.search(r'([A-Za-z\s]+)\s+Division', division)
	if match:
		return match.group(1).strip()
	# fallback
	return division.split('-')[0].strip()