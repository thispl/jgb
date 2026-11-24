import frappe
import re
from erpnext.setup.utils import get_exchange_rate

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



def extract_keyword_from_division(division):
	# Custom logic to extract from full name like "HVAC Division - (HVA)"
	match = re.search(r'([A-Za-z\s]+)\s+Division', division)
	if match:
		return match.group(1).strip()
	# fallback
	return division.split('-')[0].strip()



@frappe.whitelist()
def update_currency_amount(currency, amount, company=None):
	if not amount:
		return 0

	if not company:
		company = frappe.db.get_default("company") 

	default_currency = frappe.db.get_value("Company", company, "default_currency")

	if currency == default_currency or not currency:
		amount_value = amount
	else:
		conversion = get_exchange_rate(currency, default_currency)
		amount_value = float(conversion) * float(amount)

	return amount_value



import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def create_new_pi(
	expense_claim,
	supplier,
	description,
	amount,
	vat,
	account,
	company,
	name,
	row_name,
	division=None,
	project=None,
	currency=None,
	
):
	if frappe.db.exists("Purchase Invoice", {"custom_expense_claim": expense_claim,"custom_expense_claim_number": row_name}):
		return frappe.db.get_value(
			"Purchase Invoice",
			{"custom_expense_claim": expense_claim,"custom_expense_claim_number": row_name},
			"name"
		)
	else:
		VAT_PERCENT = 15

		amount = float(amount or 0)
		vat = float(vat or 0)

		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.posting_date = nowdate()
		pi.due_date = nowdate()
		pi.company = company
		pi.custom_division = division
		pi.project = project
		pi.currency = currency
		pi.update_stock = 0
		pi.custom_expense_claim = expense_claim
		pi.custom_expense_claim_number = row_name
		# ---------------- Item ----------------
		item = pi.append("items", {})
		item.item_code = "NST-OTH-000022"
		item.item_name = frappe.db.get_value("Item", item.item_code, "item_name")
		item.description = description
		item.qty = 1

		# Amount logic
		if vat == 0:
			item.rate = amount
			net_amount = amount
		else:
			net_amount = amount - (amount * VAT_PERCENT / 100)
			item.rate = net_amount

		expense_account = frappe.db.get_value(
			"Expense Claim Account",
			{"parent": account},
			"default_account"
		)

		if not expense_account:
			frappe.throw(f"No Expense Account found for {account}")

		item.expense_account = expense_account

		# ---------------- VAT Tax ----------------
		tax = pi.append("taxes", {})
		tax.charge_type = "Actual"
		tax.account_head = expense_account
		tax.description = "VAT 15%"
		tax.rate = VAT_PERCENT
		tax.tax_amount = amount * VAT_PERCENT / 100

		pi.insert(ignore_permissions=True)

		return pi.name



@frappe.whitelist()
def update_currency_amount_advance(currency, amount, company=None):
	if not amount:
		return 0

	if not company:
		company = frappe.db.get_default("company") 

	default_currency = frappe.db.get_value("Company", company, "default_currency")

	if currency == default_currency or not currency:
		amount_value = amount
	else:
		conversion = get_exchange_rate(currency, default_currency)
		amount_value = float(conversion) * float(amount)

	return amount_value


@frappe.whitelist()
def get_expense_claim_payments(expense_claim):
	payment_entries = frappe.db.sql("""
		SELECT
			pe.name,
			pe.posting_date,
			pe.paid_amount
		FROM
			`tabPayment Entry Reference` per
		INNER JOIN
			`tabPayment Entry` pe
			ON pe.name = per.parent
		WHERE
			per.reference_doctype = 'Expense Claim'
			AND per.reference_name = %s
	""", (expense_claim,), as_dict=True)

	return payment_entries



import frappe
from frappe.utils import flt

def expense_claim_before_insert(doc, method=None):
	if not doc.is_new():
		return

	if doc.advances:
		for d in doc.get("advances"):
			if flt(d.unclaimed_amount) > 0:
				d.unclaimed_amount = flt(d.unclaimed_amount, 2)



@frappe.whitelist()
def update_payment_status_submission(doc, method):
	status = "Paid" if doc.is_paid else "Unpaid"
	frappe.db.set_value("Expense Claim",doc.name,"custom_payment_status",status)


@frappe.whitelist()
def update_payment_status_cancel(doc, method):
	frappe.db.set_value("Expense Claim",doc.name,"custom_payment_status","Cancelled")




@frappe.whitelist()
def on_update_expense_claim(doc, method=None):
	VAT_RATE = 1.15
	VAT_ACCOUNT = "2401 - VAT - 15 % - JGB"

	# -------------------------------
	# 1. Parent Totals (AFTER SUBMIT)
	# -------------------------------
	total_advance = sum(flt(d.advance_paid) for d in doc.advances or [])

	frappe.db.set_value(
		doc.doctype,
		doc.name,
		{
			"custom_total_advance_amount": total_advance,
			"custom_total_claimed_amount_with_tax":
				flt(doc.total_claimed_amount) + flt(doc.total_taxes_and_charges)
		}
	)

	# -------------------------------
	# 2. Expense Rows (AFTER SUBMIT)
	# -------------------------------
	for d in doc.expenses or []:

		if not d.custom_include_vat:
			if doc.custom_currency != "SAR":
				converted = update_currency_amount(
					doc.custom_currency, d.amount, doc.company
				)
				base = converted
				tax = 0
				claim_currency = d.amount
			else:
				base = d.amount
				tax = 0
				claim_currency = d.amount
		else:
			if doc.custom_currency != "SAR":
				converted = update_currency_amount(
					doc.custom_currency, d.amount, doc.company
				)
				base = converted / VAT_RATE
				tax = converted - base
				claim_currency = base * VAT_RATE
			else:
				base = d.custom_claim_amount_in_selected_currency / VAT_RATE
				tax = d.custom_claim_amount_in_selected_currency - base
				claim_currency = base * VAT_RATE

		frappe.db.set_value(
			d.doctype,
			d.name,
			{
				"amount": base,
				"sanctioned_amount": base,
				"custom_claim_amount_in_selected_currency": claim_currency,
				"custom_tax_amount": tax,
				"cost_center": doc.cost_center
			}
		)

	# -------------------------------
	# 3. Rebuild Taxes Table (AFTER SUBMIT)
	# -------------------------------
	frappe.db.sql(
		"DELETE FROM `tabExpense Taxes and Charges` WHERE parent=%s",
		doc.name
	)

	for d in doc.expenses or []:
		if d.custom_include_vat:
			frappe.get_doc({
				"doctype": "Expense Taxes and Charges",
				"parent": doc.name,
				"parenttype": doc.doctype,
				"parentfield": "taxes",
				"custom_supplier": d.custom_supplier,
				"custom_supplier_name": d.custom_supplier_name,
				"tax_amount": d.custom_tax_amount,
				"account_head": VAT_ACCOUNT,
				"description": VAT_ACCOUNT,
				"cost_center": doc.cost_center
			}).insert(ignore_permissions=True)
