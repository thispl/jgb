# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AccountsReportDashboard(Document):
	def get_customer_order_wise_data(self):
		from jgb.jgb.doctype.accounts_report_dashboard.customer_order_wise_ar_summary import get_data
		return get_data({
			"company": self.company,
			"customer": self.customer,
			"from_date": self.from_date,
			"to_date": self.to_date,
			"sales_order": self.sales_order,
			"division": self.division,
			"account": self.account,
		})

	def get_customer_order_wise_html(self):
		from jgb.jgb.doctype.accounts_report_dashboard.customer_order_wise_ar_summary import get_print_html
		return get_print_html({
			"company": self.company,
			"customer": self.customer,
			"from_date": self.from_date,
			"to_date": self.to_date,
			"sales_order": self.sales_order,
			"division": self.division,
			"account": self.account,
		})

	def get_accounts_payable_aging_data(self):
		from jgb.jgb.doctype.accounts_report_dashboard.accounts_payable_aging_report_po_wise import get_data
		return get_data({
			"company": self.company,
			"supplier": self.supplier,
			"from_date": self.from_date,
			"to_date": self.to_date,
			"purchase_order": self.purchase_order,
			"division": self.division,
			"account": self.account,
		})

	def get_accounts_payable_aging_html(self):
		from jgb.jgb.doctype.accounts_report_dashboard.accounts_payable_aging_report_po_wise import get_print_html
		return get_print_html({
			"company": self.company,
			"supplier": self.supplier,
			"from_date": self.from_date,
			"to_date": self.to_date,
			"purchase_order": self.purchase_order,
			"division": self.division,
			"account": self.account,
		})

	def get_accounts_payable_summary_data(self):
		from jgb.jgb.doctype.accounts_report_dashboard.accounts_payable_summary import get_data
		return get_data({
			"company": self.company,
			"supplier": self.supplier,
			"to_date": self.to_date,
			"purchase_order": self.purchase_order,
			"division": self.division,
			"account": self.account,
		})

	def get_accounts_payable_summary_html(self):
		from jgb.jgb.doctype.accounts_report_dashboard.accounts_payable_summary import get_print_html
		return get_print_html({
			"company": self.company,
			"supplier": self.supplier,
			"to_date": self.to_date,
			"purchase_order": self.purchase_order,
			"division": self.division,
			"account": self.account,
		})

	def get_advance_sales_tax_invoice_data(self):
		from jgb.jgb.doctype.accounts_report_dashboard.advance_sales_tax_invoice import get_data
		return get_data({
			"company": self.company,
			"customer": self.customer,
			"from_date": self.from_date,
			"to_date": self.to_date,
		})

	def get_advance_sales_tax_invoice_html(self):
		from jgb.jgb.doctype.accounts_report_dashboard.advance_sales_tax_invoice import get_print_html
		return get_print_html({
			"company": self.company,
			"customer": self.customer,
			"from_date": self.from_date,
			"to_date": self.to_date,
		})

	def get_fixed_asset_register_html(self):
		from jgb.jgb.doctype.accounts_report_dashboard.fixed_asset_register_report import get_fixed_asset_register_html
		return get_fixed_asset_register_html(self)



from frappe.utils import flt, fmt_money
@frappe.whitelist()
def return_account_total(from_date, to_date, account):
	font_style = "font-family: 'Times New Roman', Times, serif;"
	data = f'''
	<table border="1" style="border-collapse: collapse; width: 100%;">
	<tr style="background-color: #0F0F5C;">
		<td colspan="1" style="{font_style}"></td>
		<td colspan="1" style="{font_style}"></td>
		<td colspan="3" style="text-align:center;color:white;font-weight: bold; {font_style}">Opening</td>
		<td colspan="3" style="text-align:center;color:white;font-weight: bold; {font_style}">Movement</td>
		<td colspan="3" style="text-align:center;color:white;font-weight: bold; {font_style}">Closing</td>
	</tr>
	<tr style="background-color: lightgray; color: black;">
		<td style="text-align:center; font-weight:bold; {font_style}">Party</td>
		<td style="text-align:center; font-weight:bold; {font_style}">Party Name</td>
		<td style="text-align:center; font-weight:bold; {font_style}">Debit</td>
		<td style="text-align:center; font-weight:bold; {font_style}">Credit</td>
		<td style="text-align:center; font-weight:bold; {font_style}">Balance</td>
		<td style="text-align:center; font-weight:bold; {font_style}">Debit</td>
		<td style="text-align:center; font-weight:bold; {font_style}">Credit</td>
		<td style="text-align:center; font-weight:bold; {font_style}">Balance</td>
		<td style="text-align:center; font-weight:bold; {font_style}">Debit</td>
		<td style="text-align:center; font-weight:bold; {font_style}">Credit</td>
		<td style="text-align:center; font-weight:bold; {font_style}">Balance</td>
	</tr>
	'''

	employee = frappe.get_all("Employee", ["name", "employee_name"])

	t_op_debit = t_op_credit = t_mov_debit = t_mov_credit = t_clo_debit = t_clo_credit = 0
	has_data = False  # Track if we added any data rows

	for j in employee:
		gle = frappe.db.sql("""
			SELECT sum(debit) as debit_amount, sum(credit) as credit_amount
			FROM `tabGL Entry` 
			WHERE account = %s AND posting_date < %s AND is_opening = 'No'
			AND party = %s AND party_type = 'Employee' AND is_cancelled = 0
		""", (account, from_date, j.name), as_dict=True)

		for g in gle:
			g.debit_amount = g.debit_amount or 0
			g.credit_amount = g.credit_amount or 0

			sq = frappe.db.sql("""
				SELECT sum(debit_in_account_currency) AS debit, sum(credit_in_account_currency) AS credit
				FROM `tabGL Entry`
				WHERE account = %s AND party = %s AND party_type = 'Employee'
				AND posting_date BETWEEN %s AND %s AND is_opening = 'No' AND is_cancelled = 0
			""", (account, j.name, from_date, to_date), as_dict=True)

			for i in sq:
				i.debit = i.debit or 0
				i.credit = i.credit or 0

				op_debit = g.debit_amount
				op_credit = g.credit_amount
				mov_debit = i.debit
				mov_credit = i.credit
				clo_debit = op_debit + mov_debit
				clo_credit = op_credit + mov_credit

				if op_debit or op_credit or mov_debit or mov_credit:
					has_data = True
					data += '<tr>'
					data += f'<td style="{font_style}">{j.name}</td><td style="{font_style}">{j.employee_name}</td>'
					data += f'<td style="text-align:right; {font_style}">{fmt_money(op_debit)}</td>'
					data += f'<td style="text-align:right; {font_style}">{fmt_money(op_credit)}</td>'
					data += f'<td style="text-align:right; {font_style}">{fmt_money(op_debit - op_credit)}</td>'
					data += f'<td style="text-align:right; {font_style}">{fmt_money(mov_debit)}</td>'
					data += f'<td style="text-align:right; {font_style}">{fmt_money(mov_credit)}</td>'
					data += f'<td style="text-align:right; {font_style}">{fmt_money(mov_debit - mov_credit)}</td>'
					data += f'<td style="text-align:right; {font_style}">{fmt_money(clo_debit)}</td>'
					data += f'<td style="text-align:right; {font_style}">{fmt_money(clo_credit)}</td>'
					data += f'<td style="text-align:right; {font_style}">{fmt_money(clo_debit - clo_credit)}</td>'
					data += '</tr>'

					t_op_debit += op_debit
					t_op_credit += op_credit
					t_mov_debit += mov_debit
					t_mov_credit += mov_credit
					t_clo_debit += clo_debit
					t_clo_credit += clo_credit

	if has_data:
		t_op_balance = t_op_debit - t_op_credit
		t_mov_balance = t_mov_debit - t_mov_credit
		t_clo_balance = t_clo_debit - t_clo_credit

		data += '<tr style="text-align:right; font-weight:bold;">'
		data += f'<td colspan="2" style="text-align:center; {font_style}">Total</td>'
		data += f'<td style="{font_style}">{fmt_money(t_op_debit)}</td>'
		data += f'<td style="{font_style}">{fmt_money(t_op_credit)}</td>'
		data += f'<td style="{font_style}">{fmt_money(t_op_balance)}</td>'
		data += f'<td style="{font_style}">{fmt_money(t_mov_debit)}</td>'
		data += f'<td style="{font_style}">{fmt_money(t_mov_credit)}</td>'
		data += f'<td style="{font_style}">{fmt_money(t_mov_balance)}</td>'
		data += f'<td style="{font_style}">{fmt_money(t_clo_debit)}</td>'
		data += f'<td style="{font_style}">{fmt_money(t_clo_credit)}</td>'
		data += f'<td style="{font_style}">{fmt_money(t_clo_balance)}</td>'
		data += '</tr>'
	else:
		data += f'''
		<tr>
			<td colspan="11" style="text-align:center; font-style:italic; {font_style}">No data available</td>
		</tr>
		'''

	data += '</table>'
	return data




@frappe.whitelist()
def get_sales_person(doc, name, from_date, to_date, company, sales_person_user):
	data = "<table width=100% border=1px solid black><tr style='background-color:#0F0F5C;font-size:12px;text-align:center;'>"
	data += "<td><b style='color:white;'>SL.NO</b></td><td colspan='2'><b style='color:white;'>Date</b></td><td><b style='color:white;'>Invoice Number</b></td>"
	data += "<td><b style='color:white;'>Customer Name</b></td><td><b style='color:white;'>LPO NO</b></td><td><b style='color:white;'>Gross Amount</b></td>"
	data += "<td><b style='color:white;'>Discount</b></td><td><b style='color:white;'>Ret. Amount</b></td><td><b style='color:white;'>Net</b></td>"
	data += "<td><b style='color:white;'>Collected</b></td><td><b style='color:white;'>Balance</b></td></tr>"

	full_data = ""

	if not doc.company and not sales_person_user:
		sales_person = frappe.get_all("Sales Person", fields=["name"])
		for s in sales_person:
			full_data += get_sales_data_by_salesperson(s.name, from_date, to_date)

	elif not doc.company and sales_person_user:
		full_data += get_sales_data_by_salesperson(sales_person_user, from_date, to_date)

	elif doc.company and not sales_person_user:
		sales_person = frappe.get_all("Sales Person", fields=["name"])
		for s in sales_person:
			full_data += get_sales_data_by_salesperson(s.name, from_date, to_date, doc.company)

	else:
		full_data += get_sales_data_by_salesperson(sales_person_user, from_date, to_date, doc.company)

	# Show only one no-data row if full_data is empty
	if not full_data.strip():
		data += '<tr><td colspan="12" style="text-align:center;font-style:italic;color:gray;">No data available</td></tr>'
	else:
		data += full_data

	data += "</table>"
	return data




def get_sales_data_by_salesperson(sales_person_user, from_date, to_date, company=None):
	data = ""
	j = 1
	company_totals = {}
	salesperson_totals = {
		"total": 0, "discount_amount": 0, "convert_float": 0,
		"net_total": 0, "collected_total": 0, "balance": 0
	}

	filters = {
		"custom_sales_personuser": sales_person_user,
		"posting_date": ("between", (from_date, to_date)),
		"docstatus": ("not in", [0, 2])
	}
	if company:
		filters["company"] = company

	sales_invoice = frappe.get_all("Sales Invoice", filters=filters,
		fields=["name", "customer", "total", "discount_amount", "posting_date", "outstanding_amount", "po_no", "company"],
		order_by="posting_date"
	)

	if not sales_invoice:
		return ""  # ← Don't show "no data" here

	data += f'<tr><td colspan="12" style="border: 1px solid black; background-color:lightgray;"><b style="color:black;font-size:12px">{sales_person_user}</b></td></tr>'

	prev_company = None
	for i in sales_invoice:
		comp = i.company
		if prev_company != comp:
			data += f'<tr><td colspan="12" style="border: 1px solid black; background-color:lightgray;"><b style="color:black;font-size:12px">{comp}</b></td></tr>'
			prev_company = comp

		net = i.total - i.discount_amount
		convert_float = int(i.total - net)
		net_int = int(net)
		collected = net - i.outstanding_amount
		collected_int = int(collected)
		customer_name = frappe.db.get_value("Customer",i.customer,"customer_name")
		data += f"<tr style='font-size:12px;'>"
		data += f"<td>{j}</td><td colspan='2' nowrap>{i.posting_date.strftime('%d-%m-%Y')}</td><td>{i.name}</td>"
		data += f"<td>{customer_name}</td><td>{i.po_no}</td><td style='text-align:right;'>{i.total}</td><td style='text-align:right;'>{i.discount_amount}</td>"
		data += f"<td style='text-align:right;'>{convert_float}</td><td style='text-align:right;'>{net_int}</td><td style='text-align:right;'>{collected_int}</td><td style='text-align:right;'>{i.outstanding_amount}</td></tr>"

		if comp not in company_totals:
			company_totals[comp] = {
				"total": 0, "discount_amount": 0, "convert_float": 0,
				"net_total": 0, "collected_total": 0, "balance": 0
			}

		company_totals[comp]["total"] += i.total
		company_totals[comp]["discount_amount"] += i.discount_amount
		company_totals[comp]["convert_float"] += convert_float
		company_totals[comp]["net_total"] += net_int
		company_totals[comp]["collected_total"] += collected_int
		company_totals[comp]["balance"] += i.outstanding_amount

		salesperson_totals["total"] += i.total
		salesperson_totals["discount_amount"] += i.discount_amount
		salesperson_totals["convert_float"] += convert_float
		salesperson_totals["net_total"] += net_int
		salesperson_totals["collected_total"] += collected_int
		salesperson_totals["balance"] += i.outstanding_amount

		j += 1

	for comp, totals in company_totals.items():
		data += f'<tr style="font-size:12px"><td colspan="6"><b>Total for {comp}</b></td>'
		data += f'<td style="text-align:right;">{round(totals["total"], 2)}</td><td style="text-align:right;">{round(totals["discount_amount"], 2)}</td>'
		data += f'<td style="text-align:right;">{round(totals["convert_float"], 2)}</td><td style="text-align:right;">{round(totals["net_total"], 2)}</td>'
		data += f'<td style="text-align:right;">{round(totals["collected_total"], 2)}</td><td style="text-align:right;">{round(totals["balance"], 2)}</td></tr>'

	data += f'<tr style="font-size:12px"><td colspan="6"><b>Total for {sales_person_user}</b></td>'
	data += f'<td style="text-align:right;">{round(salesperson_totals["total"], 2)}</td><td style="text-align:right;">{round(salesperson_totals["discount_amount"], 2)}</td>'
	data += f'<td style="text-align:right;">{round(salesperson_totals["convert_float"], 2)}</td><td style="text-align:right;">{round(salesperson_totals["net_total"], 2)}</td>'
	data += f'<td style="text-align:right;">{round(salesperson_totals["collected_total"], 2)}</td><td style="text-align:right;">{round(salesperson_totals["balance"], 2)}</td></tr>'

	return data



@frappe.whitelist()
def receivable_report(doc):
	# if doc.project:
		data = "<table width=100% border=1px solid black><tr style=background-color:#0F0F5C;font-size:8px><td colspan=1 ><b style=color:white; text-align:center;width:320px>Date</b></td><td colspan=2  style=color:white><b style=color:white; text-align:center;>Referance No</b></td><td colspan=1  style=color:white><b style=color:white; text-align:center;>Voucher Type</b></td><td colspan=1  style=color:white><b style=color:white; text-align:center;>Particulars</b></td><td colspan=1 style=color:white><b style=color:white; text-align:center;>Invoice Amount</b></td><td  style=color:white><b style=color:white; text-align:center;>Received</b></td><td colspan=1  style=color:white><b style=color:white; text-align:center;>Balance Due</b></td></tr>"
		pay = frappe.get_all("Payment Entry Reference",{"reference_name":doc.sales_order},['parent'])
		for i in pay:
			pay_entry = frappe.get_all("Payment Entry",{"name":i.parent},["posting_date","paid_amount","remarks","status"],order_by="posting_date")
			for j in pay_entry:
				if j.status =="Submitted":
					data += f'<tr><td colspan=1 style="border: 1px solid black; font-size:8px" nowrap>{j.posting_date.strftime("%d-%m-%Y")}</td><td colspan=2 style="border: 1px solid black; font-size:8px" nowrap>{i.parent}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >Payment Entry</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{j.remarks}</td><td colspan=1 style="border: 1px solid black; font-size:8px">-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{j.paid_amount}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td></tr>'
		si  = frappe.get_all("Sales Invoice",{"sales_order":doc.sales_order},['name','posting_date','total'],order_by="posting_date")
		for k in si:
			data += f'<tr><td colspan=1 style="border: 1px solid black; font-size:8px" nowrap>{k.posting_date.strftime("%d-%m-%Y")}</td><td colspan=2 style="border: 1px solid black; font-size:8px" nowrap>{k.name}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >Sales Invoice</td><td colspan=1 style="border: 1px solid black; font-size:8px">{k.total}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{k.ret_amount}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td></tr>'
			si_pay= frappe.get_all("Payment Entry Reference",{"reference_name":k.name},['parent'])
			for s in si_pay:
				si_pay_entry = frappe.get_all("Payment Entry",{"name":s.parent},["posting_date","paid_amount","remarks","status"],order_by="posting_date")
				for v in si_pay_entry:
					if v.status =="Submitted":
						data += f'<tr><td colspan=1 style="border: 1px solid black; font-size:8px" nowrap>{v.posting_date.strftime("%d-%m-%Y")}</td><td colspan=2 style="border: 1px solid black; font-size:8px" nowrap>{s.parent}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >Payment Entry</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{v.remarks}</td><td colspan=1 style="border: 1px solid black; font-size:8px">-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{v.paid_amount}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td></tr>'
	# else:
	#     data = "<table width=100% border=1px solid black><tr style=background-color:#e35310;font-size:10px;text-align:center><td colspan=1 ><b style=color:white; text-align:center;width:320px>Sales Order Documents Not Avaliable</b></td></tr>"
		data += '</table>'
		return data

from frappe.utils.data import date_diff

@frappe.whitelist()
def get_accounts_ledger(doc):
	total_amount = 0
	total_paid = 0
	total_credit_note = 0
	total_outstanding = 0
	total_0_30 = 0
	total_31_60 = 0
	total_61_90 = 0
	total_91_above = 0

	sales_invoices = frappe.db.get_all(
		"Sales Invoice",
		{'company': doc.company, 'customer': doc.customer},
		['posting_date', 'name', 'total', 'outstanding_amount'],
		order_by="posting_date"
	)
	currency = frappe.db.get_value('Company',doc.company,'default_currency')
	header_style = "style='background-color:#0F0F5C; color:white; font-size:12px; text-align:center; padding:6px; border:1px solid black;'"
	style = "style='border:1px solid black; font-size:12px; text-align:center; padding:4px;'"

	data = "<table width='100%' style='border-collapse: collapse;'>"
	data += "<tr>"
	headers = ["Invoice No", "Date", "Age", f"Amount {currency}", f"Paid {currency}", f"Credit Note {currency}", f"Outstanding {currency}", "0-30", "31-60", "61-90", "91-Above"]
	for h in headers:
		data += f"<td {header_style}>{h}</td>"
	data += "</tr>"

	if sales_invoices:
		for i in sales_invoices:
			days = date_diff(i.posting_date, doc.from_date)
			if 0 <= days <= 120:
				total_amount += i.total
				total_outstanding += i.outstanding_amount

				bucket_0_30 = bucket_31_60 = bucket_61_90 = bucket_91_above = "-"

				if 0 <= days <= 30:
					total_0_30 += i.total
					bucket_0_30 = i.total
				elif 31 <= days <= 60:
					total_31_60 += i.total
					bucket_31_60 = i.total
				elif 61 <= days <= 90:
					total_61_90 += i.total
					bucket_61_90 = i.total
				elif 91 <= days <= 120:
					total_91_above += i.total
					bucket_91_above = i.total

				data += "<tr>"
				data += f"<td {style}>{i.name}</td>"
				data += f"<td {style}>{i.posting_date.strftime('%d-%m-%Y')}</td>"
				data += f"<td {style}>{days}</td>"
				data += f"<td {style}>{i.total}</td>"
				data += f"<td {style}>-</td>"
				data += f"<td {style}>-</td>"
				data += f"<td {style}>{i.outstanding_amount}</td>"
				data += f"<td {style}>{bucket_0_30}</td>"
				data += f"<td {style}>{bucket_31_60}</td>"
				data += f"<td {style}>{bucket_61_90}</td>"
				data += f"<td {style}>{bucket_91_above}</td>"
				data += "</tr>"
			

		# Total row
		data += "<tr>"
		data += f"<td {style}><b>Total</b></td>"   # Invoice No
		data += f"<td {style}></td>"               # Date
		data += f"<td {style}></td>"               # Age
		data += f"<td {style}><b>{total_amount}</b></td>"  # Amount QR
		data += f"<td {style}>-</td>"              # Paid QR
		data += f"<td {style}>-</td>"              # Credit Note QR
		data += f"<td {style}><b>{total_outstanding}</b></td>"  # Outstanding QR
		data += f"<td {style}><b>{total_0_30}</b></td>"    # 0-30
		data += f"<td {style}><b>{total_31_60}</b></td>"   # 31-60
		data += f"<td {style}><b>{total_61_90}</b></td>"   # 61-90
		data += f"<td {style}><b>{total_91_above}</b></td>"# 91-Above
		data += "</tr>"
	else:
		# Show "No Data Available" row across all 11 columns
		data += f"<tr><td colspan='11' {style}>No Data Available</td></tr>"

	data += "</table>"

	return data


@frappe.whitelist()
def statement_of_account(company, from_date, to_date, customer):
	currency = frappe.db.get_value('Company',company,'default_currency')
	data = ''
	data += f"""
	<style>
		.soa-table {{ width: 100%; border-collapse: collapse; font-family: 'Calibri', Arial, sans-serif; font-size: 11px; }}
		.soa-table thead th {{ background: #1F3864; color: #FFFFFF; font-weight: bold; text-align: center; padding: 8px 4px; border: 1px solid #1F3864; font-size: 12px; }}
		.soa-table tbody td {{ padding: 5px 4px; border: 1px solid #D0D0D0; }}
		.soa-table tbody tr.alt-row {{ background: #F7F9FC; }}
		.soa-table tbody tr.subtotal-row td {{ background: #D9E1F2; font-weight: bold; color: #1F3864; font-size: 12px; }}
		.soa-table tbody tr.grand-total-row td {{ background: #1F3864; color: #FFFFFF; font-weight: bold; font-size: 12px; }}
		.soa-table tbody td.text-left {{ text-align: left; }}
		.soa-table tbody td.text-right {{ text-align: right; }}
		.soa-table tbody td.currency {{ text-align: right; font-variant-numeric: tabular-nums; }}
	</style>
	<table class="soa-table">
	<thead><tr>
		<th style='width:8%'>Date</th>
		<th style='width:10%'>Voucher Type</th>
		<th style='width:8%'>Voucher No</th>
		<th style='width:25%'>Remarks</th>
		<th style='width:10%'>Debit({currency})</th>
		<th style='width:8%'>Credit({currency})</th>
		<th style='width:5%'>Balance({currency})</th>
	</tr></thead><tbody>
	"""

	# Customer statement = true receivables (Asset root) + the company's
	# unapplied advance account (e.g. 2201). Excludes "invoiced" advance
	# liability accounts (e.g. 2202) which double-count amounts already
	# billed through the invoice's AR debit.
	receivable_accounts = """(account IN (
		SELECT name FROM `tabAccount`
		WHERE company = %s AND account_type = 'Receivable' AND root_type = 'Asset'
	) OR account = (
		SELECT default_advance_received_account FROM `tabCompany` WHERE name = %s
	))"""

	if customer:
		gl_entry = frappe.db.sql("""
			SELECT voucher_type, voucher_no, posting_date,party_type, party, SUM(debit) AS debit, SUM(credit) AS credit
			FROM `tabGL Entry`
			WHERE company = %s AND posting_date BETWEEN %s AND %s
			AND is_cancelled = 0 AND party = %s AND party_type = 'Customer'
			AND {0}
			GROUP BY voucher_no
			ORDER BY posting_date
		""".format(receivable_accounts), (company, from_date, to_date, customer, company, company), as_dict=True)

		gle = frappe.db.sql("""
			SELECT SUM(debit) AS opening_debit, SUM(credit) AS opening_credit
			FROM `tabGL Entry`
			WHERE company = %s
			AND (posting_date < %s OR (IFNULL(is_opening, 'No') = 'Yes' AND posting_date >= %s))
			AND party = %s AND is_cancelled = 0 AND party_type = 'Customer'
			AND {0}
		""".format(receivable_accounts), (company, from_date, to_date, customer, company, company), as_dict=True)
	else:
		gl_entry = frappe.db.sql("""
			SELECT voucher_type, voucher_no, posting_date,party_type, party, SUM(debit) AS debit, SUM(credit) AS credit
			FROM `tabGL Entry`
			WHERE company = %s AND posting_date BETWEEN %s AND %s
			AND is_cancelled = 0
			AND {0}
			GROUP BY voucher_no
			ORDER BY posting_date
		""".format(receivable_accounts), (company, from_date, to_date, company, company), as_dict=True)

		gle = frappe.db.sql("""
			SELECT SUM(debit) AS opening_debit, SUM(credit) AS opening_credit
			FROM `tabGL Entry`
			WHERE company = %s
			AND (posting_date < %s OR (IFNULL(is_opening, 'No') = 'Yes' AND posting_date >= %s))
			AND is_cancelled = 0
			AND {0}
		""".format(receivable_accounts), (company, from_date, to_date, company, company), as_dict=True)

	# If no gl_entry data found, only show headers and "No Data Available"
	if not gl_entry:
		data += '<tr><td colspan="7" style="text-align:center;font-size:12px;">No Data Available</td></tr>'
		data += '</tbody></table>'
		return data

	# Else proceed with balance calculation
	opening_balance = 0
	t_p_debit = 0
	t_p_credit = 0

	for g in gle:
		g.opening_debit = g.opening_debit or 0
		g.opening_credit = g.opening_credit or 0
		t_p_debit += g.opening_debit
		t_p_credit += g.opening_credit
		opening_balance = t_p_debit - t_p_credit

	data += f'<tr class="subtotal-row"><td colspan="6" style="text-align:right;">Opening Balance</td><td class="currency">{fmt_money(round(opening_balance, 2))}</td></tr>'

	balance = opening_balance
	alt_row = False

	for i in gl_entry:
		balance += (i.debit - i.credit)
		remarks = ''
		check_no = ''
		voucher_type_display = i.voucher_type
		if i.voucher_type == "Payment Entry":
			ref_no = frappe.db.get_value("Payment Entry", {"name": i.voucher_no}, ['reference_no'])
			check_no = ref_no or ''
			payment_entry = frappe.db.get_all("Payment Entry",{"name": i.voucher_no},["party_type", "party_name"])
			if payment_entry:
				r = payment_entry[0]
				if r.get("party_type") == "Employee":
					party_name = r.get("party_name") or ''
					remarks = f"{party_name}"
		elif i.voucher_type == "Sales Invoice":
			remark = frappe.db.get_all("Sales Invoice", filters={"name": i.voucher_no}, fields=['*'])

			if remark:
				r = remark[0]
				dn = r.get('delivery_note', '')
				po = r.get('po_no', '')
				return_doc=r.get('is_return', '')
				ref_no = r.get('custom_supplier_ref_') or ''
				if return_doc:
					voucher_type_display = "Credit Note"
				if dn and po:
					remarks = f"DN No.{dn} & LPO No.{po}"
				elif dn:
					remarks = f" DN No.{dn}"
				elif po:
					remarks = f"{ref_no} LPO No.{po}"
				else:
					remarks=f"{ref_no}"
		elif i.voucher_type == "Journal Entry":
			remark = frappe.db.get_value("Journal Entry", {"name": i.voucher_no}, "user_remark")
			other_remark=frappe.db.get_value("Journal Entry", {"name": i.voucher_no}, "remark")
			cheque_no = frappe.db.get_value("Journal Entry", {"name": i.voucher_no}, "cheque_no")
			po_no = frappe.db.get_value("Advance Invoice", {"name": cheque_no}, "po_no") if cheque_no else None
			if remark and cheque_no:
				remarks = f"LPO No.{po_no} {remark}" if po_no else remark
				check_no = cheque_no
			elif remark:
				remarks = remark
			elif cheque_no:
				remarks = f"LPO No.{po_no}" if po_no else ''
				check_no = cheque_no
			else:
				if other_remark:
					remarks=other_remark
				else:
					if i.party:
						account = frappe.db.get_value("GL Entry",{"voucher_no": i.voucher_no,"party": i.party},"account")
						if account and "salary" in account.lower():
							remarks = "Salary"
		elif i.voucher_type == "Expense Claim":
			employee_name = frappe.db.get_value("Expense Claim",i.voucher_no,"employee")
			remarks = employee_name or ''
		elif i.party:
			account = frappe.db.get_value("GL Entry",{"voucher_no": i.voucher_no,"party": i.party},"account")
			if account and "salary" in account.lower():
				remarks = "Salary"
		row_class = ' class="alt-row"' if alt_row else ''
		data += f'''
			<tr{row_class}>
				<td nowrap>{i.posting_date.strftime("%d-%m-%Y")}</td>
				<td>{voucher_type_display}</td>
				<td nowrap>{i.voucher_no}</td>
				<td style="max-width: 150px; word-wrap: break-word; overflow-wrap: break-word; white-space: normal;">
					{remarks} {check_no}
				</td>
				<td class="currency">{fmt_money(round(i.debit, 2)) or "-"}</td>
				<td class="currency">{fmt_money(round(i.credit, 2)) or "-"}</td>
				<td class="currency">{fmt_money(round(balance, 2))}</td>
			</tr>
		'''
		alt_row = not alt_row

	tp_credit = sum(i.credit for i in gl_entry)
	tp_debit = sum(i.debit for i in gl_entry)

	data += f'<tr class="subtotal-row"><td colspan=4 style="text-align:right">Total</td>'
	data += f'<td class="currency">{fmt_money(round(tp_debit, 2))}</td>'
	data += f'<td class="currency">{fmt_money(round(tp_credit, 2))}</td>'
	data += f'<td class="currency"></td></tr>'

	data += f'<tr class="grand-total-row"><td colspan="6" style="text-align:right;">Closing Balance</td><td class="currency">{fmt_money(round(balance, 2))}</td></tr>'
	data += '</tbody></table>'

	return data


@frappe.whitelist()
def supplier_statement_of_account(company, from_date, to_date, supplier, currency=None):
	data = ''
	base_currency = frappe.db.get_value('Company',company,'default_currency') or 'SAR'
	display_currency = currency or base_currency

	# Get exchange rate for conversion
	exchange_rate = 1.0
	if display_currency and display_currency != base_currency:
		exchange_rate = get_payable_exchange_rate(base_currency, display_currency)

	def _convert(amt):
		if exchange_rate and exchange_rate != 1 and amt and amt != 0:
			return round(amt * exchange_rate, 2)
		return amt

	data += f"""
	<style>
		.soa-table {{ width: 100%; border-collapse: collapse; font-family: 'Calibri', Arial, sans-serif; font-size: 10px; }}
		.soa-table thead th {{ background: #1F3864; color: #FFFFFF; font-weight: bold; text-align: center; padding: 8px 4px; border: 1px solid #1F3864; font-size: 11px; }}
		.soa-table tbody td {{ padding: 5px 4px; border: 1px solid #D0D0D0; }}
		.soa-table tbody tr.alt-row {{ background: #F7F9FC; }}
		.soa-table tbody tr.subtotal-row td {{ background: #D9E1F2; font-weight: bold; color: #1F3864; font-size: 11px; }}
		.soa-table tbody tr.grand-total-row td {{ background: #1F3864; color: #FFFFFF; font-weight: bold; font-size: 12px; }}
		.soa-table tbody td.currency {{ text-align: right; font-variant-numeric: tabular-nums; }}
	</style>
	<table class="soa-table">
	<thead><tr>
		<th style='width:10%'>Date</th>
		<th style='width:10%'>Voucher Type</th>
		<th style='width:10%'>Voucher No</th>
		<th style='width:25%'>Remarks</th>
		<th style='width:10%'>Debit({display_currency})</th>
		<th style='width:10%'>Credit({display_currency})</th>
		<th style='width:10%'>Balance({display_currency})</th>
	</tr></thead><tbody>
	"""

	if supplier:
		gl_entry = frappe.db.sql("""
			SELECT voucher_type, voucher_no, posting_date,party_type, party, SUM(debit) AS debit, SUM(credit) AS credit
			FROM `tabGL Entry`
			WHERE company = %s
			AND posting_date BETWEEN %s AND %s
			AND is_cancelled = 0
			AND party = %s
			GROUP BY voucher_no
			ORDER BY posting_date
		""", (company, from_date, to_date, supplier), as_dict=True)

		gle = frappe.db.sql("""
			SELECT SUM(debit) AS opening_debit, SUM(credit) AS opening_credit
			FROM `tabGL Entry`
			WHERE company = %s AND (posting_date < %s OR (IFNULL(is_opening, 'No') = 'Yes' AND posting_date >= %s))
			AND party = %s AND is_cancelled = 0 AND party_type='Supplier'
		""", (company, from_date, to_date, supplier), as_dict=True)
	else:
		gl_entry = frappe.db.sql("""
			SELECT voucher_type, voucher_no, posting_date,party_type, party, SUM(debit) AS debit, SUM(credit) AS credit
			FROM `tabGL Entry`
			WHERE company = %s AND posting_date BETWEEN %s AND %s AND is_cancelled = 0
			GROUP BY voucher_no
			ORDER BY posting_date
		""", (company, from_date, to_date), as_dict=True)

		gle = frappe.db.sql("""
			SELECT SUM(debit) AS opening_debit, SUM(credit) AS opening_credit
			FROM `tabGL Entry`
			WHERE company = %s AND (posting_date < %s OR (IFNULL(is_opening, 'No') = 'Yes' AND posting_date >= %s))
			AND is_cancelled = 0 AND party_type='Supplier'
		""", (company, from_date, to_date), as_dict=True)

	if gl_entry:
		opening_balance = 0
		t_p_debit = 0
		t_p_credit = 0

		for g in gle:
			g.opening_debit = g.opening_debit or 0
			g.opening_credit = g.opening_credit or 0
			t_p_debit += g.opening_debit
			t_p_credit += g.opening_credit
			opening_balance = t_p_credit - t_p_debit

		data += f'<tr class="subtotal-row"><td colspan=6 style="text-align:right">Opening Balance</td><td class="currency">{fmt_money(round(_convert(opening_balance),2))}</td></tr>'

		balance = opening_balance
		alt_row = False

		for i in gl_entry:
			balance += (i.credit - i.debit)
			if i.voucher_type == "Payment Entry":
				ref_no = frappe.db.get_value("Payment Entry", {"name": i.voucher_no}, ['reference_no'])
				check_no = ref_no if ref_no else ''
			else:
				check_no = ''

			if i.voucher_type == "Purchase Invoice":
				remarks = ''
				invoice = frappe.get_doc("Purchase Invoice", i.voucher_no)
				for k in invoice.items:
					dn = frappe.db.get_value("Purchase Receipt", {"name": k.purchase_receipt}, ["supplier_delivery_note"])
					po = k.purchase_order
					if dn and po:
						remarks = f"DN No.{dn} & PO No.{po}"
					elif dn:
						remarks = f"DN No.{dn}"
					elif po:
						remarks = f"PO No.{po}"
			elif i.voucher_type == "Journal Entry":
				remarks = ''
				remark = frappe.db.get_value("Journal Entry", {"name": i.voucher_no}, ['user_remark'])
				cheque_no = frappe.db.get_value("Journal Entry", {"name": i.voucher_no}, ['cheque_no'])
				other_remark=frappe.db.get_value("Journal Entry", {"name": i.voucher_no}, "remark")
				if remark:
					remarks = remark
				elif cheque_no:
					check_no = cheque_no
				else:
					if other_remark:
						remarks=other_remark
			else:
				remarks = ''

			row_class = ' class="alt-row"' if alt_row else ''
			data += f'''
				<tr{row_class}>
					<td nowrap>{i.posting_date.strftime("%d-%m-%Y")}</td>
					<td>{i.voucher_type}</td>
					<td nowrap>{i.voucher_no}</td>
					<td style="max-width: 150px; word-wrap: break-word; overflow-wrap: break-word; white-space: normal;">
						{remarks}{check_no}
					</td>
					<td class="currency">{fmt_money(round(_convert(i.debit), 2)) or "-"}</td>
					<td class="currency">{fmt_money(round(_convert(i.credit), 2)) or "-"}</td>
					<td class="currency">{fmt_money(round(_convert(balance), 2))}</td>
				</tr>
			'''
			alt_row = not alt_row

		tp_credit = sum(i.credit for i in gl_entry)
		tp_debit = sum(i.debit for i in gl_entry)

		data += f'<tr class="subtotal-row"><td colspan=4 style="text-align:right">Total</td><td class="currency">{fmt_money(round(_convert(tp_debit),2))}</td><td class="currency">{fmt_money(round(_convert(tp_credit),2))}</td><td class="currency"></td></tr>'
		data += f'<tr class="grand-total-row"><td colspan=6 style="text-align:right">Closing Balance</td><td class="currency">{fmt_money(round(_convert(balance),2))}</td></tr>'
	else:
		data += '''<tr><td colspan="7" style="text-align:center;">No data available</td></tr>'''

	data += '</tbody></table>'
	return data





def get_payable_exchange_rate(from_currency, to_currency):
	"""Get exchange rate between any two currencies.
	Tries: direct rate -> reverse rate -> cross rate via SAR -> cross rate via USD."""
	if from_currency == to_currency:
		return 1.0

	def _get_direct_rate(frm, to):
		r = frappe.db.sql("""
			SELECT exchange_rate FROM `tabCurrency Exchange`
			WHERE from_currency = %s AND to_currency = %s
			ORDER BY date DESC LIMIT 1
		""", (frm, to))
		return flt(r[0][0]) if r and r[0][0] else None

	rate = _get_direct_rate(from_currency, to_currency)
	if rate:
		return rate

	rate = _get_direct_rate(to_currency, from_currency)
	if rate:
		return 1.0 / rate

	if from_currency != "SAR" and to_currency != "SAR":
		rate_from_sar = _get_direct_rate(from_currency, "SAR")
		rate_to_sar = _get_direct_rate(to_currency, "SAR")
		if rate_from_sar and rate_to_sar:
			return rate_from_sar / rate_to_sar

	if from_currency != "USD" and to_currency != "USD":
		rate_from_usd = _get_direct_rate(from_currency, "USD") or (_get_direct_rate("USD", from_currency) and 1.0 / _get_direct_rate("USD", from_currency))
		rate_to_usd = _get_direct_rate(to_currency, "USD") or (_get_direct_rate("USD", to_currency) and 1.0 / _get_direct_rate("USD", to_currency))
		if rate_from_usd and rate_to_usd:
			return rate_from_usd / rate_to_usd

	frappe.msgprint(f"No exchange rate found for {from_currency} -> {to_currency}. Using 1.0")
	return 1.0


from frappe.utils import nowdate, getdate, add_years, formatdate
@frappe.whitelist()
def receipt_report(doc):
	data = """
	<style>
		.rr-table { width: 100%; border-collapse: collapse; font-family: 'Calibri', Arial, sans-serif; font-size: 11px; }
		.rr-table thead th { background: #1F3864; color: #FFFFFF; font-weight: bold; text-align: center; padding: 8px 4px; border: 1px solid #1F3864; font-size: 12px; }
		.rr-table tbody td { padding: 5px 4px; border: 1px solid #D0D0D0; }
		.rr-table tbody tr.alt-row { background: #F7F9FC; }
		.rr-table tbody tr.subtotal-row td { background: #D9E1F2; font-weight: bold; color: #1F3864; font-size: 12px; }
		.rr-table tbody td.text-left { text-align: left; }
		.rr-table tbody td.currency { text-align: right; font-variant-numeric: tabular-nums; }
	</style>
	<table class="rr-table">
	<thead><tr>
		<th style='width:10%'>Posting Date</th>
		<th style='width:10%'>Voucher No</th>
		<th style='width:20%'>Party Name</th>
		<th style='width:20%'>Received Amount</th>
		<th style='width:10%'>Sales Person</th>
		<th style='width:30%'>Remarks</th>
	</tr></thead><tbody>
	"""

	total = 0
	data_rows = ""
	alt_row = False

	# --- Journal Entry (Bank Entry / Cash Entry) ---
	journal = frappe.db.sql("""
		SELECT * 
		FROM `tabJournal Entry`
		WHERE 
			company = %s 
			AND posting_date BETWEEN %s AND %s 
			AND docstatus = 1 
			AND voucher_type IN ("Bank Entry", "Cash Entry")
		ORDER BY posting_date ASC
	""", (doc.company, doc.from_date, doc.to_date), as_dict=True)

	for journ in journal:
		doc_journal = frappe.get_all("Journal Entry Account", {"parent": journ.name, "party_type": "Customer"}, ["party", "credit_in_account_currency"])
		for c in doc_journal:
			if c.credit_in_account_currency > 0:
				total += c.credit_in_account_currency
				row_class = ' class="alt-row"' if alt_row else ''
				data_rows += f"<tr{row_class}><td nowrap>{formatdate(journ.posting_date, 'dd-MM-yyyy')}</td>"
				data_rows += f"<td>{journ.name}</td>"
				data_rows += f"<td>{c.party}</td>"
				data_rows += f"<td class='currency'>{fmt_money(round(c.credit_in_account_currency, 2))}</td>"
				data_rows += f"<td></td>"
				data_rows += f"<td class='text-left'>{journ.remarks or ''}</td></tr>"
				alt_row = not alt_row

	# --- Payment Entries ---
	sa = frappe.db.sql("""
		SELECT * 
		FROM `tabPayment Entry`
		WHERE 
			company = %s 
			AND posting_date BETWEEN %s AND %s 
			AND payment_type = 'Receive' 
			AND party_type = 'Customer' 
			AND docstatus = 1 
		ORDER BY posting_date ASC
	""", (doc.company, doc.from_date, doc.to_date), as_dict=True)

	for i in sa:
		sales_person = ''
		document = frappe.get_all("Payment Entry Reference", {"parent": i.name}, ["reference_doctype", "reference_name"])
		if document:
			for j in document:
				if j.reference_doctype == "Sales Order":
					sales_person = frappe.db.get_value("Sales Order", {"name": j.reference_name}, "custom_sales_personuser")
				elif j.reference_doctype == "Sales Invoice":
					sales_person = frappe.db.get_value("Sales Invoice", {"name": j.reference_name}, "custom_sales_personuser")
		total += i.received_amount
		row_class = ' class="alt-row"' if alt_row else ''
		data_rows += f"<tr{row_class}><td nowrap>{formatdate(i.posting_date, 'dd-MM-yyyy')}</td>"
		data_rows += f"<td>{i.name}</td>"
		data_rows += f"<td>{i.party_name}</td>"
		data_rows += f"<td class='currency'>{fmt_money(round(i.received_amount, 2))}</td>"
		data_rows += f"<td class='text-left'>{sales_person or ''}</td>"
		data_rows += f"<td class='text-left'>{i.remarks or ''}</td></tr>"
		alt_row = not alt_row

	# Final output: if no data rows, show "No Data Available"
	if not data_rows:
		data += f"<tr><td colspan='6' style='text-align:center; font-size:12px;'>No Data Available</td></tr>"
	else:
		data += data_rows
		data += f"<tr class='subtotal-row'><td></td><td></td><td style='text-align:right'>Total</td><td class='currency'>{fmt_money(round(total, 2))}</td><td></td><td></td></tr>"

	data += "</tbody></table>"
	return data


import json, html
from frappe.utils import cstr
@frappe.whitelist()
def payable_aging_report(doc):
	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))

	if not doc.get("company"):
		frappe.msgprint("Kindly choose Company")
		return ""

	args = frappe._dict({
		"company": doc.company,
		"supplier": doc.get("supplier"),
		"currency": doc.get("currency")
	})

	data_rows = get_payable_aging_data(args)

	data = "<table border='1' width='100%' style='border-collapse:collapse;table-layout:fixed;font-size:8px;'>"
	data += "<thead><tr style='font-size:9px;background-color:#0F0F5C;'>"

	headers = [
		("Posting Date", "8%"),
		("Voucher No", "20%"),
		("Supplier Invoice No", "12%"),
		("Invoice Amount", "9%"),
		("Paid Amount", "9%"),
		("Debit Note", "8%"),
		("Outstanding Amount", "9%"),
		("Age (Days)", "7%"),
		("0-30", "6%"),
		("31-60", "6%"),
		("61-90", "6%"),
		("Above 90", "6%")
	]

	for head, width in headers:
		data += f"<td style='color:white;font-weight:bold;text-align:center;width:{width};padding:4px 2px;word-wrap:break-word;'>" + html.escape(str(head)) + "</td>"

	data += "</tr></thead><tbody>"

	if not data_rows or len(data_rows) == 0:
		data += f"<tr><td colspan='{len(headers)}' style='text-align:center;'>No Data Available</td></tr>"

	elif len(data_rows) == 1 and data_rows[0][0] == "Total":
		data += f"<tr><td colspan='{len(headers)}' style='text-align:center;'>No Data Available</td></tr>"

	else:
		detail_rows = data_rows[:-1] if data_rows[-1][0] == "Total" else data_rows

		for row in detail_rows:
			row_label = str(row[0]) if row[0] else ""
			if row_label.startswith("Supplier Subtotal:"):
				data += "<tr style='font-size:8px;font-weight:bold;background-color:#D9E1F2;color:#1F3864;'>"
				# Merge first 3 columns for the label, then show numeric cells
				data += f"<td colspan='3' style='text-align:left;padding:3px 2px;word-wrap:break-word;'>" + html.escape(str(row[0])) + "</td>"
				for i, cell in enumerate(row):
					if i >= 3:
						cell_html = html.escape(str(cell)).replace("\n", "<br>") if i == 1 else html.escape(str(cell))
						data += f"<td style='text-align:right;padding:3px 2px;word-wrap:break-word;'>" + cell_html + "</td>"
				data += "</tr>"
			else:
				data += "<tr style='font-size:8px'>"
				for cell in row:
					cell_html = html.escape(str(cell)).replace("\n", "<br>")
					data += f"<td style='text-align:right;padding:3px 2px;word-wrap:break-word;'>" + cell_html + "</td>"
				data += "</tr>"

		if data_rows[-1][0] == "Total":
			total_row = data_rows[-1]

			data += "<tr style='font-size:8px;font-weight:bold;background-color:#eaeaea;'>"

			for i, cell in enumerate(total_row):
				align = "left" if i < 3 else "right"
				data += f"<td style='text-align:{align};padding:3px 2px;word-wrap:break-word;'>" + html.escape(str(cell)) + "</td>"

			data += "</tr>"

	data += "</tbody></table>"

	return cstr(data)




from frappe.utils.data import date_diff, now_datetime, nowdate, today

def get_payable_aging_data(args):
	data = []

	invoice_amount = 0
	paid_amount = 0
	debit_note = 0
	outstanding_amount = 0

	age_0_30 = 0
	age_31_60 = 0
	age_61_90 = 0
	age_above_90 = 0

	combined_data = []

	supplier = args.supplier
	company = args.company

	# Forex Gain/Loss account for the company (deductions against this account
	# should not be treated as unallocated advance payments in the aging report)
	forex_gl_account = frappe.db.get_value(
		"Account",
		{"company": company, "account_name": "Forex Gain/Loss"},
		"name",
	)

	if supplier:
		suppliers = [frappe._dict({"name": supplier, "supplier_name": frappe.db.get_value("Supplier", supplier, "supplier_name")})]
	else:
		suppliers = frappe.db.sql("""
			SELECT DISTINCT pi.supplier AS name, s.supplier_name
			FROM `tabPurchase Invoice` pi
			LEFT JOIN `tabSupplier` s ON s.name = pi.supplier
			WHERE pi.company = %s AND pi.docstatus = 1 AND pi.is_return = 0
			ORDER BY s.supplier_name
		""", (company,), as_dict=True)

	for sup in suppliers:

		sup_invoice_amount = 0
		sup_paid_amount = 0
		sup_debit_note = 0
		sup_outstanding_amount = 0
		sup_age_0_30 = 0
		sup_age_31_60 = 0
		sup_age_61_90 = 0
		sup_age_above_90 = 0
		sup_has_data = False

		pi_list = frappe.db.sql("""
			SELECT *
			FROM `tabPurchase Invoice`
			WHERE company=%s
			AND supplier=%s
			AND docstatus=1
			AND is_return=0
			ORDER BY posting_date ASC
		""", (company, sup.name), as_dict=True)

		for pi in pi_list:

			# Purchase Return Amount
			return_amount = frappe.db.sql("""
				SELECT SUM(base_grand_total)
				FROM `tabPurchase Invoice`
				WHERE company=%s
				AND return_against=%s
				AND docstatus=1
			""", (company, pi.name))[0][0] or 0

			# Purchase Return Document
			return_docs = frappe.db.sql("""
				SELECT name
				FROM `tabPurchase Invoice`
				WHERE company=%s
				AND return_against=%s
				AND docstatus=1
			""", (company, pi.name), as_dict=True)

			return_payments = []

			if return_docs:
				return_payments = frappe.db.sql("""
					SELECT per.allocated_amount
					FROM `tabPayment Entry Reference` per
					LEFT JOIN `tabPayment Entry` pe
						ON pe.name = per.parent
					WHERE pe.company=%s
					AND per.reference_name=%s
					AND pe.docstatus=1
				""", (company, return_docs[0]["name"]), as_dict=True)

			# PI Payments
			payments = frappe.db.sql("""
				SELECT per.allocated_amount
				FROM `tabPayment Entry Reference` per
				LEFT JOIN `tabPayment Entry` pe
					ON pe.name = per.parent
				WHERE pe.company=%s
				AND per.reference_name=%s
				AND pe.docstatus=1
			""", (company, pi.name), as_dict=True)

			value = (
				sum(d["allocated_amount"] for d in payments)
				+ sum(d["allocated_amount"] for d in return_payments)
			)

			# Journal Entries
			jv_entries = frappe.db.sql("""
				SELECT
					debit_in_account_currency,
					credit_in_account_currency
				FROM `tabJournal Entry Account` jea
				LEFT JOIN `tabJournal Entry` je
					ON je.name = jea.parent
				WHERE je.company=%s
				AND jea.reference_name=%s
				AND je.docstatus=1
			""", (company, pi.name), as_dict=True)

			for jv in jv_entries:

				if jv.debit_in_account_currency:
					value += jv.debit_in_account_currency

				if jv.credit_in_account_currency:
					value -= jv.credit_in_account_currency

			# Outstanding
			if value and return_amount:
				outstanding = pi.base_grand_total - value + return_amount

			elif value:
				outstanding = pi.base_grand_total - value

			elif return_amount:
				outstanding = pi.base_grand_total + return_amount

			else:
				outstanding = pi.base_grand_total

			outstanding_amount += outstanding

			age = date_diff(today(), pi.posting_date) if pi.posting_date else 0

			if round(outstanding, 2) != 0:

				invoice_amount += pi.base_grand_total
				sup_invoice_amount += pi.base_grand_total

				if value:
					paid_amount += value
					sup_paid_amount += value

				if return_amount:
					debit_note += return_amount
					sup_debit_note += return_amount

				if 0 <= age <= 30:
					age_0_30 += outstanding
					sup_age_0_30 += outstanding

				elif 31 <= age <= 60:
					age_31_60 += outstanding
					sup_age_31_60 += outstanding

				elif 61 <= age <= 90:
					age_61_90 += outstanding
					sup_age_61_90 += outstanding

				else:
					age_above_90 += outstanding
					sup_age_above_90 += outstanding

				sup_outstanding_amount += outstanding
				sup_has_data = True

				combined_data.append({
					"posting_date": pi.posting_date,
					"name": pi.name,
					"bill_no": pi.bill_no or "-",
					"invoice_amount": pi.base_grand_total,
					"paid_amount": value,
					"debit_note": return_amount,
					"outstanding": outstanding,
					"age": age,
					"out_0_30": outstanding if 0 <= age <= 30 else 0,
					"out_31_60": outstanding if 31 <= age <= 60 else 0,
					"out_61_90": outstanding if 61 <= age <= 90 else 0,
					"out_above_90": outstanding if age > 90 else 0
				})

		# Fetch advance Payment Entries (unallocated payments to this supplier)
		pe_advances = frappe.db.sql("""
			SELECT pe.name, pe.posting_date, pe.reference_no, pe.paid_from,
			       pe.base_paid_amount,
			       (SELECT COALESCE(SUM(per.allocated_amount), 0)
			        FROM `tabPayment Entry Reference` per
			        WHERE per.parent = pe.name) as allocated
			FROM `tabPayment Entry` pe
			WHERE pe.company = %s
			AND pe.docstatus = 1
			AND pe.payment_type = 'Pay'
			AND pe.party_type = 'Supplier'
			AND pe.party = %s
			HAVING allocated < pe.base_paid_amount
			ORDER BY pe.posting_date ASC
		""", (company, sup.name), as_dict=True)

		for pe in pe_advances:
			# Skip Payment Entries that have a deduction against the
			# Forex Gain/Loss account (e.g. 4101 - Forex Gain/Loss - JGB).
			# These are not real advance payments and should not appear
			# as outstanding rows in the aging report.
			if forex_gl_account and frappe.db.exists(
				"Payment Entry Deduction",
				{"parent": pe.name, "account": forex_gl_account},
			):
				continue

			unallocated = pe.base_paid_amount - pe.allocated
			if round(unallocated, 2) == 0:
				continue

			# Get bank name from Account paid_from -> account_name
			bank_name = ""
			if pe.paid_from:
				acc_name = frappe.db.get_value("Account", pe.paid_from, "account_name") or ""
				if acc_name:
					bank_name = acc_name.replace("Bank- ", "").strip() if "Bank-" in acc_name else acc_name

			voucher_no = f"{pe.name}\n{bank_name} - {pe.reference_no or ''}" if bank_name else f"{pe.name}\n{pe.reference_no or ''}"

			age = date_diff(today(), pe.posting_date) if pe.posting_date else 0
			outstanding = -unallocated  # negative = advance/credit with supplier

			paid_amount += unallocated
			sup_paid_amount += unallocated
			outstanding_amount += outstanding
			sup_outstanding_amount += outstanding
			sup_has_data = True

			if 0 <= age <= 30:
				age_0_30 += outstanding
				sup_age_0_30 += outstanding
			elif 31 <= age <= 60:
				age_31_60 += outstanding
				sup_age_31_60 += outstanding
			elif 61 <= age <= 90:
				age_61_90 += outstanding
				sup_age_61_90 += outstanding
			else:
				age_above_90 += outstanding
				sup_age_above_90 += outstanding

			combined_data.append({
				"posting_date": pe.posting_date,
				"name": voucher_no,
				"bill_no": pe.name,
				"invoice_amount": 0,
				"paid_amount": unallocated,
				"debit_note": 0,
				"outstanding": outstanding,
				"age": age,
				"out_0_30": outstanding if 0 <= age <= 30 else 0,
				"out_31_60": outstanding if 31 <= age <= 60 else 0,
				"out_61_90": outstanding if 61 <= age <= 90 else 0,
				"out_above_90": outstanding if age > 90 else 0
			})

		# Add supplier subtotal row (only when showing all suppliers)
		if not supplier and sup_has_data:
			combined_data = sorted(
				combined_data,
				key=lambda x: x["posting_date"]
			)

			for row in combined_data:

				data.append([
					row["posting_date"].strftime("%d-%m-%Y"),
					row["name"],
					row["bill_no"],
					round(row["invoice_amount"], 2),
					round(row["paid_amount"], 2),
					round(row["debit_note"], 2),
					round(row["outstanding"], 2),
					row["age"],
					round(row["out_0_30"], 2),
					round(row["out_31_60"], 2),
					round(row["out_61_90"], 2),
					round(row["out_above_90"], 2)
				])

			data.append([
				f"Supplier Subtotal: {sup.supplier_name}",
				"",
				"",
				round(sup_invoice_amount, 2),
				round(sup_paid_amount, 2),
				round(sup_debit_note, 2),
				round(sup_outstanding_amount, 2),
				"",
				round(sup_age_0_30, 2),
				round(sup_age_31_60, 2),
				round(sup_age_61_90, 2),
				round(sup_age_above_90, 2)
			])

			combined_data = []

	# Single supplier case - just output the rows
	if supplier:
		combined_data = sorted(
			combined_data,
			key=lambda x: x["posting_date"]
		)

		for row in combined_data:

			data.append([
				row["posting_date"].strftime("%d-%m-%Y"),
				row["name"],
				row["bill_no"],
				round(row["invoice_amount"], 2),
				round(row["paid_amount"], 2),
				round(row["debit_note"], 2),
				round(row["outstanding"], 2),
				row["age"],
				round(row["out_0_30"], 2),
				round(row["out_31_60"], 2),
				round(row["out_61_90"], 2),
				round(row["out_above_90"], 2)
			])

	data.append([
		"Total",
		"",
		"",
		round(invoice_amount, 2),
		round(paid_amount, 2),
		round(debit_note, 2),
		round(outstanding_amount, 2),
		"",
		round(age_0_30, 2),
		round(age_31_60, 2),
		round(age_61_90, 2),
		round(age_above_90, 2)
	])

	# Currency conversion: if target currency is not base currency, convert amounts
	base_currency = frappe.db.get_value('Company', company, 'default_currency') or 'SAR'
	target_currency = args.get('currency') or base_currency

	if target_currency and target_currency != base_currency:
		exchange_rate = get_payable_exchange_rate(base_currency, target_currency)
		if exchange_rate and exchange_rate != 1:
			amount_indices = [3, 4, 5, 6, 8, 9, 10, 11]
			for row in data:
				for idx in amount_indices:
					if isinstance(row[idx], (int, float)) and row[idx] != 0:
						row[idx] = round(row[idx] * exchange_rate, 2)

	return data



@frappe.whitelist()
def return_total_amt_consolidate(from_date,to_date,account):
	acct = account.split(' - ')
	acc=''
	if len(acct) == 2:
		acc = acct[0]
	if len(acct) == 3:
		acc = f"{acct[0]} - {acct[1]}"
	if len(acct) == 4:
		acc = f"{acct[1]} - {acct[2]}"
	ac = '%'+acc+'%'
	data = '<table  border= 1px solid black width = 100%>'
	# data += '<tr style = "background-color:#D9E2ED"><td colspan =1><b></b></td><td colspan =1 style = "text-align:center"><b>Opening</b></td><td colspan =2 style = "text-align:center"><b>Movement</b></td><td colspan =1 style = "text-align:center"><b>Closing</b></td></tr>'
	data += '<tr style = "background-color:#0F0F5C;;color:white"><td  style = "text-align:center;font-weight:bold;color:white"></td><td  colspan= 2 style = "text-align:center;font-weight:bold;color:white">Opening</td><td  colspan = 2 style = "text-align:center;font-weight:bold;color:white">Movement</td><td  colspan = 2 style = "text-align:center;font-weight:bold;color:white">Closing</td></tr>'
	data += '<tr style = "background-color:lightgray;color:black"><td  style = "text-align:center;font-weight:bold;color:black">Company</td><td  style = "text-align:center;font-weight:bold;color:black">Opening Debit</td><td  style = "text-align:center;font-weight:bold;color:black">Opening Credit</td><td  style = "text-align:center;font-weight:bold;color:black">Movement Debit</td><td  style = "text-align:center;font-weight:bold;color:black">Movement Credit</td><td  style = "text-align:center;font-weight:bold;color:black">Closing Debit</td><td  style = "text-align:center;font-weight:bold;color:black">Closing Credit</td></tr>'
	op_credit = 0
	op_debit = 0
	total_op_debit = 0
	total_op_credit = 0
	t_c_credit = 0
	t_p_credit = 0
	t_c_debit = 0
	t_p_debit = 0
	
	li = []
	company = frappe.db.sql(""" select name from `tabCompany`""",as_dict=1)
	for com in company:
		li.append(com.name)
		comp = frappe.db.get_list("Company",{"parent_company":com.name},['name'])
		for j in comp:
			li.append(j.name)
	for c in li:
		gle = frappe.db.sql("""select account, sum(debit) as opening_debit, sum(credit) as opening_credit from `tabGL Entry` where company = '%s'	and (posting_date < '%s' or (ifnull(is_opening, 'No') = 'Yes' and posting_date > '%s')) and account like '%s' and is_cancelled = 0  """%(c,from_date,to_date,ac),as_dict=True)
		for g in gle:
			if not g.opening_debit:
				g.opening_debit = 0
			if not g.opening_credit:
				g.opening_credit = 0
			t_p_debit += g.opening_debit
			t_p_credit += g.opening_credit
			balance_op = t_p_debit - t_p_credit
			data += '<tr><td>%s</td><td style = text-align:right >%s</td><td style = text-align:right >%s</td>'%(c,fmt_money(g.opening_debit) ,fmt_money(g.opening_credit))
			sq = frappe.db.sql(""" select company,sum(debit_in_account_currency) as debit,sum(credit_in_account_currency) as credit from `tabGL Entry` where company = '%s' and account like '%s' and posting_date between '%s' and '%s' and is_opening = 'No' and is_cancelled = 0 """%(c,ac,from_date,to_date),as_dict=True)
			for i in sq:
				if not i.credit:
					i.credit = 0
				if not i.debit:
					i.debit = 0
				op_credit = g.opening_credit + i.credit
				op_debit = g.opening_debit + i.debit
				total_op_debit += i.debit
				total_op_credit += i.credit
				t_c_credit += op_credit
				t_c_debit += op_debit
				balance_cl = t_c_debit - t_c_credit
				balance_move=total_op_debit-total_op_credit
				data += '<td style = text-align:right >%s</td><td style = text-align:right >%s</td><td style = text-align:right >%s</td><td style = text-align:right >%s</td></tr>'%(fmt_money(i.debit),fmt_money(i.credit),fmt_money(op_debit),fmt_money(op_credit))
	data += '<tr style = "text-align:right;font-weight:bold"><td style = "text-align:center;font-weight:bold">Total</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'%(fmt_money(t_p_debit),fmt_money(t_p_credit),fmt_money(total_op_debit),fmt_money(total_op_credit),fmt_money(t_c_debit),fmt_money(t_c_credit))
	# data += '<tr style = "text-align:right;font-weight:bold"><td style = "text-align:center;font-weight:bold">Balance</td><td colspan =3>%s</td><td colspan =3></td><td colspan=3>%s</td></tr>'%(fmt_money(balance_op),fmt_money(balance_cl))
	data += '</table>'
	return data






import json
import html
import frappe
from frappe.utils import today, date_diff, formatdate, fmt_money, cstr

@frappe.whitelist()
def ageing_report_test(doc):
	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))

	if not doc.get("company") or not doc.get("customer"):
		# return "<p style='color:black;text-align:center;'>Missing company or customer information.</p>"
		frappe.msgprint("Kindly choose company")
	# Inline the accounts_aging() logic here
	args = frappe._dict({
		"company": doc.company,
		"customer": doc.customer
	})
	data_rows = get_accounts_aging_data(args)  # function defined below

	# Build HTML table
	data = "<table border='1' width='100%' style='border-collapse:collapse;'>"
	data += "<thead><tr style='font-size:12px;background-color:#0F0F5C;'>"
	headers = [
		"Posting Date", "Voucher No", "Customer LPO", "Invoiced Amount",
		"Paid Amount", "Credit Note", "Outstanding Amount", "Age (Days)",
		"0-30", "31-60", "61-90", "Above 90"
	]
	for head in headers:
		data += f"<td style='color:white; font-weight:bold; text-align:center'>{head}</td>"
	data += "</tr></thead><tbody>"

	if not data_rows or len(data_rows) == 0:
		# No data at all
		data += f"<tr><td colspan='{len(headers)}' style='text-align:center; font-size:12px; color:black;'>No Data Available</td></tr>"
	elif len(data_rows) == 1 and data_rows[0][0] == "Total":
		# Only total row present, no invoice data
		data += f"<tr><td colspan='{len(headers)}' style='text-align:center; font-size:12px; color:black;'>No Data Available</td></tr>"
	else:
		# Show all data rows (excluding total if present)
		for row in data_rows[:-1] if data_rows[-1][0] == "Total" else data_rows:
			data += "<tr style='font-size:10px'>"
			for cell in row:
				data += f"<td style='text-align:right'>{html.escape(str(cell))}</td>"
			data += "</tr>"

		# Add total row only if real data exists
		if data_rows[-1][0] == "Total" and len(data_rows) > 1:
			total_row = data_rows[-1]
			data += "<tr style='font-size:10px; font-weight:bold; background-color:#eaeaea;'>"
			for i, cell in enumerate(total_row):
				align = "left" if i < 3 else "right"
				data += f"<td style='text-align:{align}'>{html.escape(str(cell))}</td>"
			data += "</tr>"

	data += "</tbody></table>"
	return cstr(data)




def get_accounts_aging_data(args):
	data = []
	in_amount = paid_amount = credit_note = out_amount = 0
	age_0_30 = age_31_60 = age_61_90 = age_above_90 = 0
	combined_data = []

	customer = args.customer
	company = args.company

	si_list = frappe.db.sql("""
		SELECT * FROM `tabSales Invoice` 
		WHERE company = %s AND customer = %s AND docstatus = 1 
		AND is_return = 0 AND status != 'Paid' 
		ORDER BY posting_date ASC
	""", (company, customer), as_dict=True)

	for i in si_list:
		return_amount = frappe.db.sql("""
			SELECT sum(grand_total) FROM `tabSales Invoice` 
			WHERE company = %s AND return_against = %s AND docstatus = 1
		""", (company, i.name))[0][0] or 0

		result_doc = frappe.db.sql("""
			SELECT name FROM `tabSales Invoice` 
			WHERE company = %s AND return_against = %s AND docstatus = 1
		""", (company, i.name), as_dict=True)

		pay_doc = []
		if result_doc:
			pay_doc = frappe.db.sql("""
				SELECT per.allocated_amount 
				FROM `tabPayment Entry Reference` per
				LEFT JOIN `tabPayment Entry` pe ON per.parent = pe.name
				WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
			""", (company, result_doc[0]["name"]), as_dict=True)

		pay = frappe.db.sql("""
			SELECT per.allocated_amount 
			FROM `tabPayment Entry Reference` per
			LEFT JOIN `tabPayment Entry` pe ON per.parent = pe.name
			WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
		""", (company, i.name), as_dict=True)

		value = sum(j["allocated_amount"] for j in pay) + sum(r["allocated_amount"] for r in pay_doc)

		jv = frappe.db.sql("""
			SELECT credit_in_account_currency 
			FROM `tabJournal Entry Account` per
			LEFT JOIN `tabJournal Entry` pe ON per.parent = pe.name
			WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
		""", (company, i.name), as_dict=True)

		value += sum(k.credit_in_account_currency for k in jv)

		if value and return_amount:
			outstanding = i.grand_total - value + return_amount
		elif value:
			outstanding = i.grand_total - value
		elif return_amount:
			outstanding = i.grand_total + return_amount
		else:
			outstanding = i.grand_total

		out_amount += outstanding
		age = date_diff(today(), i.posting_date) if i.posting_date else 0

		if round(outstanding) != 0:
			if value:
				paid_amount += value
			if return_amount:
				credit_note += return_amount
			in_amount += i.grand_total

			if 0 <= age <= 30:
				age_0_30 += outstanding
			elif 31 <= age <= 60:
				age_31_60 += outstanding
			elif 61 <= age <= 90:
				age_61_90 += outstanding
			else:
				age_above_90 += outstanding

			combined_data.append({
				'posting_date': i.posting_date,
				'name': i.name,
				'po_no': i.po_no or '-',
				'grand_total': i.grand_total,
				'paid_amount': value,
				'credit_note': return_amount,
				'outstanding': outstanding,
				'age': age,
				'out_0_30': outstanding if 0 <= age <= 30 else 0,
				'out_31_60': outstanding if 31 <= age <= 60 else 0,
				'out_61_90': outstanding if 61 <= age <= 90 else 0,
				'out_above_90': outstanding if age > 90 else 0
			})

	combined_data = sorted(combined_data, key=lambda x: x['posting_date'])

	for entry in combined_data:
		if entry['outstanding'] != 0:
			data.append([
				entry['posting_date'].strftime("%d-%m-%Y"),
				entry['name'],
				entry['po_no'],
				round(entry['grand_total'], 2),
				round(entry['paid_amount'], 2),
				round(entry['credit_note'], 2),
				round(entry['outstanding'], 2),
				entry['age'],
				round(entry['out_0_30'], 2),
				round(entry['out_31_60'], 2),
				round(entry['out_61_90'], 2),
				round(entry['out_above_90'], 2)
			])

	# Add totals row
	data.append([
		'Total', '', '', round(in_amount, 2),
		round(paid_amount, 2),
		round(credit_note, 2),
		round(out_amount, 2), '',
		round(age_0_30, 2),
		round(age_31_60, 2),
		round(age_61_90, 2),
		round(age_above_90, 2)
	])

	return data

from jgb.jgb.doctype.accounts_report_dashboard.aging_report_summary import accounts_aging

@frappe.whitelist()
def ageing_report_summary(doc):
	import json, html
	from frappe.utils import cstr

	if isinstance(doc, str): doc = frappe._dict(json.loads(doc))
	if not doc.get("company"): frappe.throw("Kindly choose company")

	data_rows = accounts_aging(frappe._dict({"company": doc.company, "customer": doc.customer, "to_date": doc.get("to_date")}))

	def fmt_currency(val):
		try:
			num = float(val)
			return f"{num:,.2f}"
		except (ValueError, TypeError):
			return str(val)

	html_output = """
	<style>
		.ar-table { width: 100%; border-collapse: collapse; font-family: 'Calibri', Arial, sans-serif; font-size: 10px; table-layout: fixed; }
		.ar-table thead th { background: #1F3864; color: #FFFFFF; font-weight: bold; text-align: center; padding: 8px 2px; border: 1px solid #1F3864; font-size: 11px; }
		.ar-table tbody td { padding: 4px 2px; border: 1px solid #D0D0D0; }
		.ar-table tbody tr.alt-row { background: #F7F9FC; }
		.ar-table tbody tr.subtotal-row td { background: #D9E1F2; font-weight: bold; color: #1F3864; font-size: 11px; }
		.ar-table tbody tr.grand-total-row td { background: #1F3864; color: #FFFFFF; font-weight: bold; font-size: 12px; }
		.ar-table tbody td.text-left { text-align: left; }
		.ar-table tbody td.text-right { text-align: right; }
		.ar-table tbody td.currency { text-align: right; font-variant-numeric: tabular-nums; }
	</style>
	<table class="ar-table">
	"""

	html_output += "<thead><tr>"
	headers = ["Posting Date", "Voucher No", "Customer", "Sales Engineer", "Invoiced", "Paid", "Credit Note", "Outstanding", "Age", "0-30", "31-60", "61-90", "Above 90"]
	widths = ["7%", "10%", "20%", "10%", "8%", "8%", "8%", "8%", "4%", "6%", "6%", "6%", "6%"]
	for i, head in enumerate(headers):
		html_output += f"<th style='width:{widths[i]}'>{head}</th>"
	html_output += "</tr></thead><tbody>"

	alt_row = False
	for row in data_rows:
		row_str = str(row[0])
		if row_str == "GRAND TOTAL":
			html_output += "<tr class='grand-total-row'>"
			html_output += f"<td colspan='4' style='text-align:left'>{html.escape(row_str)}</td>"
			for cell in row[4:]:
				html_output += f"<td class='currency'>{html.escape(fmt_currency(cell))}</td>"
			html_output += "</tr>"
			alt_row = False
		elif row_str.startswith("Subtotal:"):
			html_output += "<tr class='subtotal-row'>"
			html_output += f"<td colspan='4' style='text-align:left'>{html.escape(row_str)}</td>"
			for cell in row[4:]:
				html_output += f"<td class='currency'>{html.escape(fmt_currency(cell))}</td>"
			html_output += "</tr>"
			alt_row = False
		else:
			row_class = " class='alt-row'" if alt_row else ""
			html_output += f"<tr{row_class}>"
			for i, cell in enumerate(row):
				align = "text-left" if i < 4 else "currency"
				html_output += f"<td class='{align}'>{html.escape(str(cell))}</td>"
			html_output += "</tr>"
			alt_row = not alt_row

	html_output += "</tbody></table>"
	return cstr(html_output)



@frappe.whitelist()
def return_account_summary_total(from_date, to_date, account=None, company=None):
	data = '<table border="1" style="border-collapse: collapse; width: 100%;">'
	data += '<tr style="background-color: #0F0F5C;"><td colspan="1"><b></b></td><td colspan="1"><b></b></td>'
	data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Opening</td>'
	data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Movement</td>'
	data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Closing</td></tr>'

	data += '<tr style="background-color: lightgray; color: white;">'
	data += '<td style="text-align:center; font-weight:bold; color:black;">Account Code</td>'
	data += '<td style="text-align:center; font-weight:bold; color:black;">Account Name</td>'
	data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
	data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td>'
	data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
	data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td>'
	data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
	data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td></tr>'

	has_data = False  # Flag to track if any data row is added

	if account:
		main_account = frappe.db.get_value("Account", account, ["name", "account_number"], as_dict=True)
		if not main_account:
			frappe.throw(f"Account '{account}' not found")

		def get_all_accounts(account_code):
			accounts = frappe.db.get_all("Account", filters={"parent_account": account_code, "disabled": 0}, fields=["name", "account_number"])
			all_accounts = accounts[:]
			for acc in accounts:
				child_accounts = get_all_accounts(acc["name"])
				all_accounts.extend(child_accounts)
			return all_accounts

		accounts = [main_account] + get_all_accounts(account)
	else:
		accounts = frappe.db.get_all(
			"Account",
			filters={"is_group": 0, "disabled": 0, "company": company},
			fields=["name", "account_number"]
		)

	total_op_debit = total_op_credit = t_c_credit = t_p_credit = t_c_debit = t_p_debit = 0

	for acc in accounts:
		gle = frappe.db.sql("""
			SELECT SUM(debit) AS debit_amount, SUM(credit) AS credit_amount
			FROM `tabGL Entry`
			WHERE account = %s AND posting_date < %s AND is_opening = 'No' AND is_cancelled = 0 AND company = %s
		""", (acc.name, from_date, company), as_dict=True)

		for g in gle:
			g.debit_amount = g.debit_amount or 0
			g.credit_amount = g.credit_amount or 0
			t_p_debit += g.debit_amount
			t_p_credit += g.credit_amount

			sq = frappe.db.sql("""
				SELECT SUM(debit_in_account_currency) AS debit, SUM(credit_in_account_currency) AS credit
				FROM `tabGL Entry`
				WHERE account = %s AND posting_date BETWEEN %s AND %s
				AND is_opening = 'No' AND is_cancelled = 0 AND company = %s
			""", (acc.name, from_date, to_date, company), as_dict=True)

			for i in sq:
				i.credit = i.credit or 0
				i.debit = i.debit or 0
				op_credit = g.credit_amount + i.credit
				op_debit = g.debit_amount + i.debit
				total_op_debit += i.debit
				total_op_credit += i.credit
				t_c_credit += op_credit
				t_c_debit += op_debit

				if g.debit_amount or g.credit_amount or i.credit or i.debit:
					has_data = True
					data += f'<tr><td>{acc.account_number or "-"}</td><td>{acc.name}</td>'
					data += f'<td style="text-align:right">{fmt_money(g.debit_amount)}</td>'
					data += f'<td style="text-align:right">{fmt_money(g.credit_amount)}</td>'
					data += f'<td style="text-align:right">{fmt_money(i.debit)}</td>'
					data += f'<td style="text-align:right">{fmt_money(i.credit)}</td>'
					data += f'<td style="text-align:right">{fmt_money(op_debit)}</td>'
					data += f'<td style="text-align:right">{fmt_money(op_credit)}</td></tr>'

	if has_data:
		data += '<tr style="text-align:right; font-weight:bold;"><td colspan="2" style="text-align:center;">Total</td>'
		data += f'<td>{fmt_money(t_p_debit)}</td><td>{fmt_money(t_p_credit)}</td>'
		data += f'<td>{fmt_money(total_op_debit)}</td><td>{fmt_money(total_op_credit)}</td>'
		data += f'<td>{fmt_money(t_c_debit)}</td><td>{fmt_money(t_c_credit)}</td></tr>'
	else:
		data += '<tr><td colspan="8" style="text-align:center; font-style: italic; color: black;">No data available</td></tr>'

	data += '</table>'
	return data



@frappe.whitelist()
def return_total_amt1(from_date,to_date,account):
	acct = account.split(' - ')
	acc=''
	if len(acct) == 2:
		acc = acct[0]
	if len(acct) == 3:
		acc = f"{acct[0]} - {acct[1]}"
	if len(acct) == 4:
		acc = f"{acct[1]} - {acct[2]}"
	ac = '%'+acc+'%'
	data = '<table  border= 1px solid black width = 100%>'
	data += '<tr style = "background-color:#0F0F5C;"><td colspan =1><b></b></td><td colspan =1 style = "text-align:center;font-weight:bold;color:white;">Opening</td><td colspan =2 style = "text-align:center;font-weight:bold;color:white;">Movement</td><td colspan =1 style = "text-align:center;font-weight:bold;color:white;">Closing</td></tr>'

	data += '<tr style = "background-color:lightgray;color:black"><td  style = "text-align:center;font-weight:bold;color:black">Company</td><td  style = "text-align:center;font-weight:bold;color:black">Balance</td><td  style = "text-align:center;font-weight:bold;color:black">Debit</td><td  style = "text-align:center;font-weight:bold;color:black">Credit</td><td  style = "text-align:center;font-weight:bold;color:black">Balance</td></tr>'
	op_credit = 0
	op_debit = 0
	total_op_debit = 0
	total_op_credit = 0
	t_c_credit = 0
	t_p_credit = 0
	t_c_debit = 0
	t_p_debit = 0
	
	li = []
	company = frappe.db.sql(""" select name from `tabCompany` where is_group = 0""",as_dict=1)
	for com in company:
		li.append(com.name)
		# comp = frappe.db.get_list("Company",{"parent_company":com.name},['name'])
		# for j in comp:
		# 	li.append(j.name)
	for c in li:
		gle = frappe.db.sql("""select account, sum(debit_in_account_currency) as opening_debit, sum(credit_in_account_currency) as opening_credit from `tabGL Entry` where company = '%s'	and (posting_date < '%s' or (ifnull(is_opening, 'No') = 'Yes' and posting_date > '%s')) and account like '%s' and is_cancelled = 0  """%(c,from_date,to_date,ac),as_dict=True)
		for g in gle:
			if not g.opening_debit:
				g.opening_debit = 0
			if not g.opening_credit:
				g.opening_credit = 0
			t_p_debit += g.opening_debit
			t_p_credit += g.opening_credit
			balance_op = t_p_debit - t_p_credit
			data += '<tr><td>%s</td><td style = text-align:right >%s</td>'%(c,fmt_money(g.opening_debit - g.opening_credit,2))
			sq = frappe.db.sql(""" select company,sum(debit_in_account_currency) as debit,sum(credit_in_account_currency) as credit from `tabGL Entry` where company = '%s' and account like '%s' and posting_date between '%s' and '%s' and is_opening = 'No' and is_cancelled = 0 """%(c,ac,from_date,to_date),as_dict=True)
			for i in sq:
				if not i.credit:
					i.credit = 0
				if not i.debit:
					i.debit = 0
				op_credit = g.opening_credit + i.credit
				op_debit = g.opening_debit + i.debit
				total_op_debit += i.debit
				total_op_credit += i.credit
				t_c_credit += op_credit
				t_c_debit += op_debit
				balance_cl = round(t_c_debit,2) - round(t_c_credit,2)
				balance_move=total_op_debit-total_op_credit
				data += '<td style = text-align:right >%s</td><td style = text-align:right >%s</td><td style = text-align:right >%s</td></tr>'%(fmt_money(i.debit,2),fmt_money(i.credit,2),fmt_money(round(op_debit,2) - round(op_credit,2),2))
	data += '<tr style = "text-align:right;font-weight:bold"><td style = "text-align:right;font-weight:bold">Total</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'%(fmt_money(balance_op,2),fmt_money(total_op_debit,2),fmt_money(total_op_credit,2),fmt_money(balance_cl,2))
	# data += '<tr style = "text-align:right;font-weight:bold"><td style = "text-align:center;font-weight:bold">Balance</td><td colspan =3>%s</td><td colspan =3></td><td colspan=3>%s</td></tr>'%(fmt_money(balance_op),fmt_money(balance_cl))
	data += '</table>'
	return data
