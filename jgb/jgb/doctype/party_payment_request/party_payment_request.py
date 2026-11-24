# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.setup.utils import get_exchange_rate
from collections import defaultdict


class PartyPaymentRequest(Document):
	pass

@frappe.whitelist()
def get_currency_exchange(currency):
	conversion = get_exchange_rate(currency, "SAR")
	return conversion

#Check the same id in 2 row for Party Payment Request 
@frappe.whitelist()
def check_for_duplicate_payment(name,doc_type,doc_name):
	li = []
	dat = frappe.get_value(doc_type,name,["grand_total"])
	pos = frappe.db.sql("""select sum(`tabPurchase Invoice List`.payment_amount) as payment_amount,`tabPurchase Invoice List`.parent as name from `tabParty Payment Request`
	left join `tabPurchase Invoice List` on `tabParty Payment Request`.name = `tabPurchase Invoice List`.parent
	where `tabPurchase Invoice List`.name1 = '%s' """%(name),as_dict=True)[0]
	po = frappe.db.sql("""select `tabPurchase Invoice List`.parent as name from `tabParty Payment Request`
	left join `tabPurchase Invoice List` on `tabParty Payment Request`.name = `tabPurchase Invoice List`.parent
	where `tabPurchase Invoice List`.name1 = '%s' and `tabParty Payment Request`.docstatus = 0 """%(name),as_dict=True)
	for i in po:
		if i.name != doc_name:
			li.append(i.name)
	if not pos["payment_amount"]:
		pos["payment_amount"] = 0
	return pos["payment_amount"] or 0,li,dat or 0

#Append the values to match with given supplier if not creation of payment against PO and PI
from frappe.utils import flt
@frappe.whitelist()
def return_purchase_invoice(supplier):
	if supplier:
		existing_invoices = frappe.db.sql("""
			SELECT pil.name1
			FROM `tabPurchase Invoice List` pil
			LEFT JOIN `tabParty Payment Request` cpr 
				ON pil.parent = cpr.name
			WHERE cpr.supplier = %s
			AND cpr.docstatus = 1
		""", (supplier,), as_dict=False)

		existing_invoice_names = {inv[0] for inv in existing_invoices} if existing_invoices else set()

		purchase_invoice = frappe.get_list(
			"Purchase Invoice",
			filters={
				"status": ["not in", ["Paid", "Cancelled"]],
				"supplier": supplier,
				"name": ["not in", existing_invoice_names],
				"posting_date":[">=", "2026-01-01"]
			},
			fields=[
				"name", "posting_date", "supplier",
				"currency", "conversion_rate", "grand_total",
				"outstanding_amount", "company"
			],
		)
		filtered_pi = []

		for pi in purchase_invoice:
			linked_po = frappe.db.get_value(
				"Purchase Invoice Item",
				{"parent": pi["name"]},
				"purchase_order"
			)

			if linked_po:
				po_status = frappe.db.get_value("Purchase Order", linked_po, "status")

				if po_status in ["Closed", "Completed"]:
					continue

			filtered_pi.append(pi)

		purchase_invoice = filtered_pi

		pur_order = []
		po_list = frappe.db.get_list("Purchase Order", 
			filters={"supplier": supplier, "docstatus": 1,"transaction_date":[">=", "2026-01-01"],"status": ["not in", ["Closed", "Completed"]]},
			fields=['name', 'grand_total', 'currency', 'conversion_rate', 
					'transaction_date', 'advance_paid', 'supplier', 
					'company', 'project']
		)
		
		for po in po_list:
			total_invoiced = frappe.db.sql("""
				SELECT SUM(pii.amount)
				FROM `tabPurchase Invoice Item` pii
				INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
				WHERE pii.purchase_order = %s
				AND pi.docstatus = 1
			""", (po['name'],))[0][0] or 0
			if total_invoiced:
				total_invoiced =total_invoiced
			else:
				total_invoiced=0
			remaining_po_value = po['grand_total'] - total_invoiced
			remaining_po_values = flt(po['grand_total'] - total_invoiced - (po['advance_paid'] or 0),2)
			if remaining_po_values > 0:
				pur_order.append({
					'name': po['name'],
					'grand_total': remaining_po_value,
					'total_invoiced': total_invoiced,
					'currency': po['currency'],
					'conversion_rate': po['conversion_rate'],
					'transaction_date': po['transaction_date'],
					'advance_paid': po['advance_paid'],
					'supplier': po['supplier'],
					'company': po['company'],
					'project': po['project']
				})

		jv = frappe.db.sql("""select `tabJournal Entry`.name,`tabJournal Entry`.company,`tabJournal Entry`.title,`tabJournal Entry`.posting_date,`tabJournal Entry Account`.credit_in_account_currency as total_credit from `tabJournal Entry`
					left join `tabJournal Entry Account` on `tabJournal Entry`.name = `tabJournal Entry Account`.parent
					where `tabJournal Entry Account`.party = '%s' and `tabJournal Entry Account`.party_type = 'Supplier'  and `tabJournal Entry`.docstatus != 2 and `tabJournal Entry Account`.credit_in_account_currency > 0 and `tabJournal Entry`.posting_date >= '2026-01-01' ORDER BY
				`tabJournal Entry`.posting_date ASC"""%(supplier),as_dict=True)
		return purchase_invoice,pur_order,jv
# @frappe.whitelist()
# def return_purchase_invoice(supplier):
# 	if supplier:
# 		existing_invoices = frappe.db.sql("""
# 			SELECT pil.name1
# 			FROM `tabPurchase Invoice List` pil
# 			LEFT JOIN `tabParty Payment Request` cpr 
# 				ON pil.parent = cpr.name
# 			WHERE cpr.supplier = %s
# 			AND cpr.docstatus = 1
# 		""", (supplier,), as_dict=False)

# 		existing_invoice_names = {inv[0] for inv in existing_invoices} if existing_invoices else set()

# 		purchase_invoice = frappe.get_list(
# 			"Purchase Invoice",
# 			filters={
# 				"status": ["not in", ["Paid", "Cancelled"]],
# 				"supplier": supplier,
# 				"docstatus": 1,
# 				"name": ["not in", existing_invoice_names],
# 				"posting_date":[">=", "2026-01-01"]
# 			},
# 			fields=[
# 				"name", "posting_date", "supplier",
# 				"currency", "conversion_rate", "grand_total",
# 				"outstanding_amount", "company"
# 			],
# 		)


# 		pur_order = []
# 		po_list = frappe.db.get_list("Purchase Order", 
# 			filters={"supplier": supplier, "docstatus": 1,"transaction_date":[">=", "2026-01-01"]},
# 			fields=['name', 'grand_total', 'currency', 'conversion_rate', 
# 					'transaction_date', 'advance_paid', 'supplier', 
# 					'company', 'project']
# 		)
		
# 		for po in po_list:
# 			total_invoiced = frappe.db.sql("""
# 				SELECT SUM(`tabPurchase Invoice Item`.amount)
# 				FROM `tabPurchase Invoice Item`
# 				WHERE `tabPurchase Invoice Item`.purchase_order = %s
# 			""", (po['name'],))[0][0] or 0
# 			if total_invoiced:
# 				total_invoiced =total_invoiced
# 			else:
# 				total_invoiced=0
# 			remaining_po_value = po['grand_total'] - total_invoiced
# 			if remaining_po_value > 0:
# 				pur_order.append({
# 					'name': po['name'],
# 					'grand_total': remaining_po_value,
# 					'total_invoiced': total_invoiced,
# 					'currency': po['currency'],
# 					'conversion_rate': po['conversion_rate'],
# 					'transaction_date': po['transaction_date'],
# 					'advance_paid': po['advance_paid'],
# 					'supplier': po['supplier'],
# 					'company': po['company'],
# 					'project': po['project']
# 				})

# 		jv = frappe.db.sql("""select `tabJournal Entry`.name,`tabJournal Entry`.company,`tabJournal Entry`.title,`tabJournal Entry`.posting_date,`tabJournal Entry Account`.credit_in_account_currency as total_credit from `tabJournal Entry`
# 					left join `tabJournal Entry Account` on `tabJournal Entry`.name = `tabJournal Entry Account`.parent
# 					where `tabJournal Entry Account`.party = '%s' and `tabJournal Entry Account`.party_type = 'Supplier'  and `tabJournal Entry`.docstatus != 2 and `tabJournal Entry Account`.credit_in_account_currency > 0 and `tabJournal Entry`.posting_date >= '2026-01-01' ORDER BY
# 				`tabJournal Entry`.posting_date ASC"""%(supplier),as_dict=True)
# 		return purchase_invoice,pur_order,jv

#While enter the supplier in Party Payment Request get the supplier currency and set it
@frappe.whitelist()
def get_def_currency(supplier):
	supp = frappe.db.get_value("Supplier",supplier,['default_currency'])
	conversion = get_exchange_rate(supp, "SAR")
	return supp,conversion

#Get the below html table and show it Party Payment Request
@frappe.whitelist()
def pay_consolidated_req(name):
	con = frappe.db.sql("""SELECT * FROM `tabPurchase Invoice List` WHERE parent = '%s' """ % (name), as_dict=True)

	def calculate_outstanding_payment_difference(child_table):
		amounts_by_company = defaultdict(float)
		total = 0.0

		for row in child_table:
			company = row.get("company", "")
			outstanding_amount = row.get("outstanding_amount", 0.0)
			payment_amount = row.get("payment_amount", 0.0)
			amounts_by_company[company] += payment_amount
			total += payment_amount

		result = []

		for company, difference in amounts_by_company.items():
			result.append({"company": company, "value": difference})

		result.append({"company": "Total", "value": total})

		data = ''
		data += '<table width="61%"><tr><td style="color:white;background-color: #5E3B63;padding:1px;font-weight:bold;border: 1px solid black">Company</td><td style="font-weight:bold;color:white;background-color: #5E3B63;padding:1px;border: 1px solid black">Amount</td></tr>'

		for i in result:
			formatted_value = '{:,.2f}'.format(i["value"])
			data += '<tr><td style="padding:1px;border: 1px solid black">%s</td><td style="padding:1px;border: 1px solid black">%s</td></tr>' % (i["company"],formatted_value)

		data += '</table>'
		return data

	child_table = con
	amounts_difference_by_company = calculate_outstanding_payment_difference(child_table)
	return amounts_difference_by_company

import frappe
from collections import defaultdict

@frappe.whitelist()
def get_payment_entry_route_data(party_payment_request):
    doc = frappe.get_doc("Party Payment Request", party_payment_request)

    def calculate_outstanding_payment_difference(child_table):
        amounts_by_company = defaultdict(float)

        for row in child_table:
            company = row.get("company")
            payment_amount = row.get("payment_amount", 0.0)
            amounts_by_company[company] += payment_amount

        result = []
        for company, value in amounts_by_company.items():
            result.append({
                "company": company,
                "value": value
            })

        return result

    child_table = [
        {
            "company": i.company,
            "payment_amount": i.payment_amount,
            "type": i.type,
            "name1": i.name1,
            "grand_total": i.grand_total_company_currency,
            "outstanding_amount": i.outstanding_amount
        }
        for i in doc.purchase_invoice_list
    ]

    company_totals = calculate_outstanding_payment_difference(child_table)

    company = company_totals[0]["company"]
    paid_amount = company_totals[0]["value"]

    references = []
    for i in doc.purchase_invoice_list:
        if i.company == company:
            references.append({
                "reference_doctype": i.type,
                "reference_name": i.name1,
                "allocated_amount": i.payment_amount,
                "total_amount": i.grand_total_company_currency,
                "outstanding_amount": i.outstanding_amount,
            })

    return {
        "company": company,
        "paid_amount": paid_amount,
        "received_amount": paid_amount,
        "references": references,
        "supplier": doc.supplier,
        "mode_of_payment": doc.mode_of_payment,
        "paid_from": doc.account_paid_from,
        "paid_to": doc.account_paid_to,
        "paid_from_currency": doc.account_currency_from,
        "paid_to_currency": doc.account_currency_to,
    }
