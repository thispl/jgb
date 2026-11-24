import frappe
from frappe.utils import flt
from frappe import _

@frappe.whitelist()
def get_pi_items(invoice):
	pi = frappe.get_doc("Purchase Invoice", invoice)

	data = []
	for item in pi.items:
		data.append({
			"description": item.item_name,
			"amount": item.amount,
			"expense_account": item.expense_account
		})
	

	return data



@frappe.whitelist()
def update_rate_and_total(doc,method):
	total_amount = 0

	for row in doc.items:  
		amount = row.amount or 0
		applicable_charges = row.applicable_charges or 0

		# Total Amount
		row.custom_total_amount = amount + applicable_charges

		if row.qty:
			row.custom_new_item_rate = row.custom_total_amount / row.qty
		else:
			row.rate = 0



from frappe.utils import flt
import frappe

@frappe.whitelist()
def update_total_table(doc, method=None):

	grand_total = 0

	for i in doc.purchase_receipts:
		grand_total += flt(i.grand_total or 0)
	doc.custom_total_receipt_value = grand_total
	
	qty=0
	applicable_charges=0
	amount_1 =0
	custom_total_amount=0
	for item in doc.items:
		qty += flt(item.qty or 0)
		amount_1 += flt(item.amount or 0)
		applicable_charges += flt(item.applicable_charges or 0)
		custom_total_amount += flt(item.custom_total_amount or 0)
	doc.set("custom_purchase_receipt_item_total", [])

	doc.append("custom_purchase_receipt_item_total", {
		"total": "Total",
		"total_quantity": qty,
		"total_amount": amount_1,
		"total_applicable_charges": applicable_charges,
		"total_total_amount": custom_total_amount
	})

