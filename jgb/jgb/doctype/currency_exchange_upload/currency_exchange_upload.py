# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from openpyxl import Workbook
from frappe import _
from openpyxl import load_workbook
from frappe.utils.data import nowdate



class CurrencyExchangeUpload(Document):
	pass



@frappe.whitelist()
def download_product_excel():
	wb = Workbook()
	ws = wb.active
	ws.title = "Currency Template"
	headers = ["Valid from Date", "From Currency", "To Currency", "Exchange Rate (1 INR = [?] SAR)"]
	sample_values = ["DD-MM-YYYY", "Currency String - 3 Letters", "Currency String - 3 Letters", "Decimal - minimum 3 digits after decimal"]
	example_values = ["1-11-2025", "INR", "SAR", 0.043]
	ws.append(headers)
	ws.append(sample_values)
	ws.append(example_values)

	file_path = "/tmp/currency_template.xlsx"
	wb.save(file_path)
	with open(file_path, "rb") as f:
		frappe.local.response.filecontent = f.read()
		frappe.local.response.filename = "currency_template.xlsx"
		frappe.local.response.type = "download"





# @frappe.whitelist()
# def upload_currency_exchange_excel(file_path):
#     wb = load_workbook(file_path)
#     sheet = wb.active

#     for i, row in enumerate(sheet.iter_rows(min_row=3, values_only=True), start=3):
#         date,from_currency, to_currency, amount = row
#         existing = frappe.get_all("Currency Exchange",
#                                   filters={"from_currency": from_currency,
#                                            "to_currency": to_currency},
#                                   fields=["name", "date", "amount"])

#         if existing:
#             doc_name = existing[0]["name"]
#             if str(existing[0]["date"]) != str(date) or float(existing[0]["amount"]) != float(amount):
#                 doc = frappe.get_doc("Currency Exchange", doc_name)
#                 doc.date = date
#                 doc.exchange_rate = amount
#                 doc.save()
#                 frappe.msgprint(f"Row {i}: Updated {from_currency} → {to_currency}")
#         else:
#             frappe.get_doc({
#                 "doctype": "Currency Exchange",
#                 "from_currency": from_currency,
#                 "to_currency": to_currency,
#                 "date": date,
#                 "exchange_rate": amount
#             }).insert()
#             frappe.msgprint(f"Row {i}: Created {from_currency} to {to_currency}")
#     return {"status": "success", "message": "Currency exchange upload completed!"}



import frappe
from openpyxl import load_workbook
from frappe import _
from io import BytesIO
from datetime import datetime


@frappe.whitelist()
def upload_currency_exchange_excel(file_url):
	if not file_url:
		frappe.throw(_("No file URL provided."))

	try:
		file_doc = frappe.get_doc("File", {"file_url": file_url})
		file_content = file_doc.get_content()
	except Exception as e:
		frappe.throw(_("Failed to retrieve the file. Error: {0}").format(str(e)))

	try:
		wb = load_workbook(filename=BytesIO(file_content), data_only=True)
		ws = wb.active
	except Exception as e:
		frappe.throw(_("Unable to read Excel file: {0}").format(str(e)))

	headers = [cell.value for cell in ws[1]]
	created_or_updated = []

	for i, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
		row_data = dict(zip(headers, row))
		raw_date = row_data.get("Valid from Date")
		date = None
		date_id=None

		if raw_date:
			if isinstance(raw_date, datetime):
				date = raw_date.strftime("%Y-%m-%d")
				date_id = raw_date.strftime("%Y-%m-%d")
			elif isinstance(raw_date, str):
				try:
					date_obj = datetime.strptime(raw_date, "%d-%m-%Y")
				except ValueError:
					try:
						date_obj = datetime.strptime(raw_date, "%d/%m/%Y")
					except ValueError:
						frappe.msgprint(f"Row {i}: Invalid date format, skipping row")
						continue
				date = date_obj.strftime("%Y-%m-%d") 
				date_id = date_obj.strftime("%d-%m-%Y")

		from_currency = row_data.get("From Currency")
		to_currency = row_data.get("To Currency")
		amount = row_data.get("Exchange Rate (1 INR = [?] SAR)")

		if not from_currency or not to_currency or not amount:
			continue

		try:
			existing = frappe.get_all(
				"Currency Exchange",
				filters={"from_currency": from_currency, "to_currency": to_currency},
				fields=["name", "date", "exchange_rate"]
			)

			# if existing:
			# 	doc = frappe.get_doc("Currency Exchange", existing[0]["name"])
			# 	if str(doc.date) != str(date) or float(doc.exchange_rate) != float(amount):
			# 		doc.date = date
			# 		doc.exchange_rate = amount
			# 		doc.save(ignore_permissions=True)
			# 		# doc.name = date_id-doc.from_currency-to_currency-"Selling-Buying"
			# 		doc.name = f"{date_id}-{doc.from_currency}-{doc.to_currency}-Selling-Buying"
			# 		created_or_updated.append(f"Updated {from_currency} → {to_currency}")
			# else:
			doc = frappe.get_doc({
				"doctype": "Currency Exchange",
				"from_currency": from_currency,
				"to_currency": to_currency,
				"date": date,
				"exchange_rate": amount
			}).insert(ignore_permissions=True)
			created_or_updated.append(f"Created {from_currency} → {to_currency}")

		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Currency Exchange Upload Error")
			frappe.msgprint(_("Error processing row {0}: {1}").format(i, str(e)))


	return {
		"status": "success",
		"message": f"{len(created_or_updated)} rows processed successfully.",
		"details": created_or_updated
	}



# def update_all_invoice_stock():
	
#     invoices = frappe.get_all("Sales Invoice", filters={"docstatus":0, 'name':["not in",["JGB-HVA-SI-2025-00010","JGB-CMN-SI-2025-00005"]]}, fields=["name", "posting_date","posting_time"])

#     for inv in invoices:
#         si = frappe.get_doc("Sales Invoice", inv.name)

#         for item in si.items:
#             stock = frappe.db.sql("""
#                 SELECT SUM(actual_qty) AS qty
#                 FROM `tabStock Ledger Entry`
#                 WHERE item_code=%s 
#                 AND warehouse=%s
#                 AND posting_date = %s
# 				AND posting_time = %s
#                 AND is_cancelled = 0
#             """, (item.item_code, item.warehouse, si.posting_date, si.posting_time), as_dict=True)

#             available_qty = stock[0].qty or 0

#             item.custom_current_stock = available_qty

#         si.save()