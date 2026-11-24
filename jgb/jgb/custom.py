import frappe
from frappe.utils.csvutils import read_csv_content
from frappe.utils import get_first_day, get_last_day, format_datetime, get_url_to_form
from frappe.utils import cint
from frappe.utils.data import date_diff, now_datetime, nowdate, today, add_days
import datetime
from frappe.utils import money_in_words
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate
from frappe import throw, msgprint
from frappe.model.naming import make_autoname
from frappe import throw, _
from datetime import date, timedelta
import frappe
from frappe.utils import add_months, nowdate, getdate
from frappe.utils import flt, fmt_money
import json
from erpnext.setup.utils import get_exchange_rate
import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_bank_cash_account, get_payment_entry
from erpnext.accounts.party import get_party_account, get_party_bank_account
from jgb.jgb.doctype.accounts_report_dashboard.aging_report_summary import accounts_aging
from jgb.jgb.doctype.accounts_report_dashboard.aging_report_summary_sales_person import accounts_aging as accounts_aging_sales_person
from jgb.jgb.doctype.accounts_report_dashboard.receivable_summary_salesperson import accounts_receivable_summary
# Update the total cost estimation value in quotation
@frappe.whitelist()
def update_total_est_value(doc,method):
	total_value= 0
	total_quotaion=0
	if doc.custom_estimation_details:
		for i in doc.custom_estimation_details:
			if i.value:
				total_value+=i.value
			if i.value_quotation_currency:
				total_quotaion+=i.value_quotation_currency
		doc.custom_total_estimated_value=total_value
		doc.custom_total_estimated_value_quotation_currency=total_quotaion


# @frappe.whitelist()
# def create_item_series(item_group, product):
#     item_group_short_code = frappe.db.get_value("Item Group", {"name": item_group}, "custom_short_code")
#     product_short_code = frappe.db.get_value("Product", {"name": product}, "short_code")

#     if not item_group_short_code or not product_short_code:
#         frappe.throw("Missing short code for Item Group or Product.")

#     prefix = f"{item_group_short_code}-{product_short_code}-."
#     series = make_autoname(prefix + "#####")
#     return series


#completed
import re
import frappe

@frappe.whitelist()
def create_item_series(item_group, product):
	item_group_short_code = frappe.db.get_value("Item Group", {"name": item_group}, "custom_short_code")
	product_short_code = frappe.db.get_value("Product", {"name": product}, "short_code")

	if not item_group_short_code or not product_short_code:
		frappe.throw("Missing short code for Item Group or Product.")

	prefix = f"{item_group_short_code}-{product_short_code}-"

	existing_items = frappe.db.get_all("Item", filters={
		"item_code": ["like", f"{prefix}%"]
	}, fields=["item_code"])

	max_num = 0
	pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$") 
	for item in existing_items:
		item_code = item["item_code"]
		match = pattern.match(item_code)
		if match:
			num_part = int(match.group(1))
			if num_part > max_num:
				max_num = num_part

	next_num = max_num + 1
	next_code = f"{prefix}{str(next_num).zfill(6)}" 

	return next_code

#completed
@frappe.whitelist()
def set_asset_naming(asset_category):
	item_group_short_code = "AST"
	product_short_code =frappe.db.get_value("Asset Category",asset_category,"custom_short_code")
	if not product_short_code:
		frappe.throw("Short code is missing in Asset category")
	prefix = f"{item_group_short_code}-{product_short_code}-"

	existing_items = frappe.db.get_all("Item", filters={
		"item_code": ["like", f"{prefix}%"]
	}, fields=["item_code"])

	max_num = 0
	pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$") 
	for item in existing_items:
		item_code = item["item_code"]
		match = pattern.match(item_code)
		if match:
			num_part = int(match.group(1))
			if num_part > max_num:
				max_num = num_part

	next_num = max_num + 1
	next_code = f"{prefix}{str(next_num).zfill(6)}" 

	return next_code

#completed
@frappe.whitelist()
def set_parameters(type):
	product = frappe.get_doc("Product",type)
	return product.product_naming

#completed
@frappe.whitelist()
def set_pallet_weight(item,box,pallet,box_qty):
	pallet_qty = frappe.db.get_value("Pallet Table",{'parent':item,'box':box,'pallet':pallet},['qty'])
	no_of_pallets = 0
	if pallet_qty:
		no_of_pallets = math.ceil(float(box_qty) / float(pallet_qty))
	pallet_weight = frappe.db.get_value("Pallet",{'name':pallet},['weight'])
	total_weight_of_pallets = no_of_pallets * pallet_weight
	total_pallet_length = frappe.db.get_value("Pallet",{'name':pallet},['length']) * no_of_pallets
	total_pallet_breadth = frappe.db.get_value("Pallet",{'name':pallet},['breadth']) * no_of_pallets
	total_pallet_height = frappe.db.get_value("Pallet",{'name':pallet},['height']) * no_of_pallets
	return no_of_pallets, total_weight_of_pallets, total_pallet_length, total_pallet_breadth, total_pallet_height


#completed
import math
@frappe.whitelist()
def set_box_weight(item,box,item_qty):
	box_qty = frappe.db.get_value("Box Table",{'parent':item,'box':box},['qty'])
	no_of_boxes = 0
	if box_qty:
		no_of_boxes = math.ceil(float(item_qty) / float(box_qty))
	box_weight = frappe.db.get_value("Box",{'name':box},['weight'])
	total_weight_of_boxes = no_of_boxes * box_weight
	total_box_length = frappe.db.get_value("Box",{'name':box},['length']) * no_of_boxes
	total_box_breadth = frappe.db.get_value("Box",{'name':box},['breadth']) * no_of_boxes
	total_box_height = frappe.db.get_value("Box",{'name':box},['height']) * no_of_boxes
	return no_of_boxes, total_weight_of_boxes, total_box_length, total_box_breadth, total_box_height


#completed
import json
import frappe
from bs4 import BeautifulSoup
@frappe.whitelist()
def create_item_name(parameter, description=None):
	import json
	if isinstance(parameter, str):
		parameter = json.loads(parameter)
	item_name = "-".join(i["value"] for i in parameter if i.get("value"))
	if not item_name and description:
		description = BeautifulSoup(description, "html.parser").get_text(strip=True)
		item_name = description
	item_name = item_name[:140]
	return item_name

@frappe.whitelist()
def create_logistics_request(doc, method):
	lr = frappe.new_doc("Logistics Request")
	lr.logistic_type = "Local Delivery"
	lr.po_so = "Delivery Note"
	lr.order_no = doc.name
	lr.requester_name = doc.owner
	lr.cargo_type = "Road"
	lr.inventory_destination = "Direct to Customer"
	lr.date_of_shipment = today()
	lr.source = doc.source
	lr.shipping_address_name = doc.shipping_address_name
	lr.shipping_address = doc.shipping_address
	lr.etd = today()
	lr.grand_total = doc.grand_total
	lr.custom_duty = 0.45 * doc.grand_total

	for row in doc.items:
		lr.append("product_description_dn", row.as_dict())


	lr.insert()
	frappe.db.commit()



#completed
@frappe.whitelist()
def check_leave_validations(doc, method):
	if doc.leave_type=='Marriage Leave':
		if frappe.db.exists('Leave Application',{'leave_type':doc.leave_type,'name':('!=',doc.name),'docstatus':['!=',2],'employee':doc.employee}) :
			frappe.throw(f'Already another application found.Marriage leave only allowed once.') 
	# if doc.leave_type == "Sick Leave":
	#     today = getdate(nowdate())
	#     fdate = getdate(doc.from_date)
	#     month_start = date(fdate.year, fdate.month, 1)
	#     if fdate.month == 12:
	#         next_month_start = date(fdate.year + 1, 1, 1)
	#     else:
	#         next_month_start = date(fdate.year, fdate.month + 1, 1)
	#     max_monthly_allowance = 2.5
	#     taken_leave_this_month = frappe.db.sql("""
	#         SELECT SUM(total_leave_days)
	#         FROM `tabLeave Application`
	#         WHERE employee = %s
	#         AND leave_type = 'Sick Leave'
	#         AND status NOT IN ('Rejected', 'Cancelled')
	#         AND from_date >= %s AND from_date < %s
	#         AND name != %s
	#     """, (doc.employee, month_start, next_month_start, doc.name))[0][0] or 0
	#     total_requested = taken_leave_this_month + doc.total_leave_days
	#     if total_requested > max_monthly_allowance:
	#         frappe.throw(
	#             f"You are allowed only 2.5 Sick Leave days in {today.strftime('%B')}. "
	#             f"Already requested: {taken_leave_this_month}."
	#         )
	elif doc.leave_type=='Pilgrimage Leave':
		if frappe.db.exists('Leave Application',{'leave_type':doc.leave_type,'name':('!=',doc.name),'docstatus':['!=',2],'custom_pilgrimage_for':doc.custom_pilgrimage_for,'employee':doc.employee}) :
			frappe.throw(f'Already another application found for {doc.custom_pilgrimage_for}.') 
	elif doc.leave_type=='Maternity Leave':
		gender=frappe.db.get_value('Employee',{'name':doc.employee},['gender'])
		if gender!='Female':
			frappe.throw('Maternity leave is applicable for <b>Female</b> employees only.') 
	elif doc.leave_type=="Relative's Death":
		if doc.custom_death_in=='Family Member':
			family = frappe.db.get_value("Leave Type",{'name':"Relative's Death"},"custom_maximum_leave_allowed_for_family_member")
			if doc.total_leave_days > float(family):
				frappe.throw(f'Maximum of {family} Days is applicable for death of <b>{doc.custom_death_in}</b>.') 
		else:
			close_relative = frappe.db.get_value("Leave Type",{'name':"Relative's Death"},"custom_maximum_leave_allowed_for_close_relative")
			if doc.total_leave_days > float(close_relative):
				frappe.throw(f'Maximum of {close_relative} Days is applicable for death of <b>{doc.custom_death_in}</b>.') 
	# elif doc.leave_type=="Injury Leave":
	#     current_year_start = date(getdate(nowdate()).year, 1, 1)
	#     current_year_end = date(getdate(nowdate()).year, 12, 31)

	#     total_injury_leave = frappe.db.sql("""
	#         SELECT SUM(total_leave_days)
	#         FROM `tabLeave Application`
	#         WHERE employee = %s
	#         AND leave_type = 'Injury Leave'
	#         AND status NOT IN ('Rejected', 'Cancelled')
	#         AND from_date BETWEEN %s AND %s
	#         AND name != %s
	#     """, (doc.employee, current_year_start, current_year_end, doc.name))[0][0] or 0
	#     total_requested = total_injury_leave + doc.total_leave_days
	#     if total_requested > 10:
	#         frappe.throw(f"Injury Leave cannot exceed 10 days per year. Already requested: {total_injury_leave}")
	elif doc.leave_type=="Child Birth Leave":
		total_leave = frappe.db.sql("""
			SELECT SUM(total_leave_days)
			FROM `tabLeave Application`
			WHERE employee = %s
			AND leave_type = 'Child Birth Leave'
			AND status NOT IN ('Rejected', 'Cancelled')
			AND name != %s
		""", (doc.employee, doc.name))[0][0] or 0
		total_requested = total_leave + doc.total_leave_days
		child_birth_leave = frappe.db.get_value("Leave Type",{'name':"Child Birth Leave"},'custom_maximum_leave_allowed')
		if total_requested > child_birth_leave:
			frappe.throw(f"Child Birth Leave only applicable for {child_birth_leave} days per employee .")
	elif doc.leave_type=="Annual Vacation":
		today = getdate(nowdate())
		doj = frappe.db.get_value("Employee", {'name': doc.employee}, 'date_of_joining')
		eligible_date = getdate(add_months(doj, 6))  
		# if today < eligible_date:
		#     frappe.throw("Employees who completed 6 months are only eligible to apply <b>Annual Vacation</b>")
		if doc.custom_ticket_required==1:
			anniversary = getdate(add_years(doj, 1))
			if today < anniversary:
				frappe.throw("Employees who completed 1 year are only eligible to apply along with ticket")
			from_year = getdate(doc.from_date).year
			existing_with_ticket = frappe.db.exists(
				"Leave Application",
				{
					"employee": doc.employee,
					"leave_type": "Annual Vacation",
					"custom_ticket_required": 1,
					"docstatus": ["!=", 2], 
					"name": ["!=", doc.name],  
				},
			)

			if existing_with_ticket:
				existing_doc = frappe.get_doc("Leave Application", existing_with_ticket)
				if getdate(existing_doc.from_date).year == from_year:
					frappe.throw("An Annual Vacation with ticket has already been applied for this year.")
		spouse_count=0
		child_count=0
		for f in doc.custom_family_details:
			if f.relation not in ['Spouse','Child']:
				frappe.throw('Ticket only applicable for <b>Spouse</b> and <b>Child</b> ')
			if f.relation=='Spouse':
				spouse_count+=1
			if f.relation=='Child':
				child_count+=1
			if spouse_count>1:
				frappe.throw('Ticket only applicable for one <b>Spouse</b>')
			if child_count>2:
				frappe.throw('Ticket only applicable for 2 <b>Children</b>')

		start = add_days(doc.from_date, -1)
		end = add_days(doc.to_date, 1)

		# Normalize to date objects
		start_date = ensure_date(start)
		end_date = ensure_date(end)

		start_hh = check_holiday(start_date, doc.employee)
		end_hh = check_holiday(end_date, doc.employee)

		if start_hh:
			frappe.throw(
				f"<b>{start_date.strftime('%d-%m-%Y')}</b> is holiday. Annual Vacation is not allowed to club with holidays."
			)

		if end_hh:
			frappe.throw(
				f"<b>{end_date.strftime('%d-%m-%Y')}</b> is holiday. Annual Vacation is not allowed to club with holidays."
			)


#completed
def ensure_date(val):
	if isinstance(val, str):
		return datetime.datetime.strptime(val, "%Y-%m-%d").date()
	return val

import frappe
from frappe.utils import nowdate, getdate, add_years, formatdate

@frappe.whitelist()
def allocate_pilgrimage():
	today = getdate(nowdate())
	employees = frappe.db.get_all("Employee", {'status':'Active'}, ['name', 'date_of_joining'])
	for emp in employees:
		doj = emp.get("date_of_joining")
		fifth_anniversary = add_years(doj, 5)
		retirement_date = add_years(doj, 60)
		if today >= fifth_anniversary:
			from_date = fifth_anniversary
			to_date = getdate(f"{retirement_date.year}-12-31")
			existing = frappe.db.exists("Leave Allocation", {
				"employee": emp.name,
				"leave_type": "Pilgrimage Leave",
				"docstatus": ["!=", 2], 
			})

			if not existing:
				allocation = frappe.new_doc("Leave Allocation")
				allocation.employee = emp.name
				allocation.leave_type = "Pilgrimage Leave"
				allocation.from_date = from_date
				allocation.to_date = to_date
				allocation.new_leaves_allocated = 6  
				allocation.docstatus = 1
				allocation.save(ignore_permissions=True)
				frappe.db.commit()     


@frappe.whitelist()
def check_allocations(doc,method):
	today = getdate(nowdate())
	if doc.leave_type=='Pilgrimage Leave':
		employees = frappe.db.get_value("Employee", {'name':doc.employee}, [ 'date_of_joining'])
		fifth_anniversary = add_years(employees, 1)
		retirement_date = add_years(employees, 60)
		if today < fifth_anniversary:
			frappe.throw("Employees who completed 1 years of service only eligible for <b>Pilgrimage Leave</b>")
		pilgrimage_leave = frappe.db.get_value("Leave Type",{'name':'Pilgrimage Leave'},"custom_maximum_leave_allowed")
		# if doc.new_leaves_allocated > float(pilgrimage_leave):
		#     frappe.throw(f"<b>Pilgrimage Leave</b> allocation should not exceed {pilgrimage_leave}")
		if frappe.db.exists('Leave Allocation',{'employee':doc.employee,'docstatus':['!=',2],'leave_type':doc.leave_type,'name':['!=',doc.name]}):
			docs=frappe.db.get_all('Leave Allocation',{'employee':doc.employee,'docstatus':['!=',2],'leave_type':doc.leave_type,'name':['!=',doc.name]})
			tot=0
			for i in docs:
				tot+=i.new_leaves_allocated
			tot=tot+doc.new_leaves_allocated
			if tot > float(pilgrimage_leave):
				frappe.throw(f"<b>Pilgrimage Leave</b> allocation should not exceed {pilgrimage_leave}.Already another allocation present.Kindly check.")
	elif doc.leave_type == 'Marriage Leave':

		allocations = frappe.db.get_all(    
			"Leave Allocation",
			filters={
				"employee": doc.employee,
				"leave_type": doc.leave_type,
				"docstatus": ["!=", 2],
				"name": ["!=", doc.name],
			},
			fields=["new_leaves_allocated"]
		)

		# Safe summing: None → 0
		previous_total = sum([(a.new_leaves_allocated or 0) for a in allocations])

		# Total after adding current allocation
		combined_total = previous_total + (doc.new_leaves_allocated or 0)
		marriage_leave = frappe.db.get_value("Leave Type",{'name':'Marriage Leave'},"custom_maximum_leave_allowed")
		if combined_total > marriage_leave:
			frappe.throw(
				f"<b>Marriage Leave</b> allocation cannot exceed {marriage_leave} days in total. "
				"Another allocation already exists. Kindly check."
			)

		if (doc.new_leaves_allocated or 0) > marriage_leave:
			frappe.throw(f"<b>Marriage Leave</b> allocation cannot exceed {marriage_leave} days.")

	elif doc.leave_type=='Annual Vacation':    
		employees = frappe.db.get_value("Employee", {'name':doc.employee}, [ 'date_of_joining'])
		anniversary = add_years(employees, 1)
		# if getdate(doc.from_date) < anniversary:
		#     frappe.throw("<b>Annual Vacation</b> is eligible only for employees completed 1 year.")

@frappe.whitelist()
def allocate_annual_leave():
	today = getdate(nowdate())
	employees = frappe.db.get_all('Employee', {'status': 'Active'},['name', 'date_of_joining'])
	for emp in employees:
		doj = getdate(emp.date_of_joining)
		if today < add_months(doj, 1):
			continue
		months_completed = (today.year - doj.year) * 12 + (today.month - doj.month)
		expected_date = add_months(doj, months_completed)
		if expected_date != today:
			continue
		existing_alloc = frappe.db.get_value(
			'Leave Allocation',
			{
				'employee': emp.name,
				'leave_type': 'Annual Vacation',
				'from_date': ['<=', today],
				'to_date': ['>=', today],
				'docstatus':1
			},
			['name']
		)

		if existing_alloc:
			alloc_doc = frappe.get_doc('Leave Allocation', existing_alloc)
			alloc_doc.new_leaves_allocated += 2.5
			alloc_doc.save(ignore_permissions=True)
			frappe.db.commit()
		else:
			current_anniversary = add_months(doj, (months_completed // 12) * 12)
			next_anniversary = add_months(current_anniversary, 12) - timedelta(days=1)
			alloc_doc = frappe.new_doc('Leave Allocation')
			alloc_doc.employee = emp.name
			alloc_doc.leave_type = 'Annual Vacation'
			alloc_doc.from_date = current_anniversary
			alloc_doc.to_date = next_anniversary
			alloc_doc.new_leaves_allocated = 2.5
			alloc_doc.save(ignore_permissions=True)
			alloc_doc.submit()

		
#completed
@frappe.whitelist()
def check_holiday(date,emp):
	holiday_list = frappe.db.get_value('Employee',emp,'holiday_list')
	company = frappe.db.get_value('Employee',emp,'company')
	if not holiday_list:
		holiday_list = frappe.db.get_value('Company',company,'default_holiday_list')
	holiday = frappe.db.sql("""select `tabHoliday`.holiday_date,`tabHoliday`.weekly_off from `tabHoliday List` 
	left join `tabHoliday` on `tabHoliday`.parent = `tabHoliday List`.name where `tabHoliday List`.name = '%s' and holiday_date = '%s' """%(holiday_list,date),as_dict=True)
	if holiday:
		return 'H'


#completed
@frappe.whitelist()
def update_family_table(employee,family):
	fam=[]
	if family=='Yes':
		emp=frappe.get_doc('Employee',employee)
		for e in emp.custom_family:
			fam.append({
				'relation': e.relation,
				'name1': e.name1
			})
	return fam


#completed
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

# @frappe.whitelist()
# def get_accounts_ledger(doc):
#     total_amount = 0
#     total_paid = 0
#     total_credit_note = 0
#     total_outstanding = 0
#     total_0_30 = 0
#     total_31_60 = 0
#     total_61_90 = 0
#     total_91_above = 0
#     sales_invoices = frappe.get_all("Sales Invoice", {'company': doc.company, 'customer': doc.customer}, ['posting_date', 'name', 'total', 'outstanding_amount'],order_by="posting_date")
#     data = "<table width='100%' border=1px solid black><tr style=background-color:#0F0F5C;;font-size:12px;text-align:center;><td colspan=1 ><b style=color:white; text-align:center;width:320px>Invoice No</b></td><td colspan=2  style=color:white><b style=color:white; text-align:center;>Date</b></td><td colspan=1  style=color:white><b style=color:white; text-align:center;>Age</b></td><td colspan=1  style=color:white><b style=color:white; text-align:center;>Amount QR</b></td><td colspan=1 style=color:white><b style=color:white; text-align:center;>Paid QR</b></td><td colspan=1  style=color:white><b style=color:white; text-align:center;>Credit Note QR</b></td><td colspan=1  style=color:white><b style=color:white; text-align:center;>Outstanding QR</b></td><td colspan=1  style=color:white><b style=color:white; text-align:center;>0-30</b></td><td  style=color:white;width:30%><b style=color:white; text-align:center;>31-60</b></td><td colspan=1  style=color:white;width:30%><b style=color:white; text-align:center;>61-90</b></td><td colspan=1  style=color:white><b style=color:white; text-align:center;>91-Above</b></td></tr>"
#     if sales_invoices:
#         for i in sales_invoices:
#             days = date_diff(doc.from_date, i.posting_date)
#             if 0 <= days <= 120:
#                 total_amount += i.total
#                 total_outstanding += i.outstanding_amount
#                 data += f'<tr style="text-align:center"><td colspan=1 style="border: 1px solid black; font-size:12px" >{i.name}</td><td colspan=2 style="border: 1px solid black; font-size:8px" >{i.posting_date.strftime("%d-%m-%Y")}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{days}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{i.total}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{i.outstanding_amount}</td>'
#                 if 0 <= days <= 30:
#                     total_0_30 += i.total
#                     data += f'<td colspan=1 style="border: 1px solid black; font-size:12px;text-align:center;" >{i.total}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td>'
#                 if 31 <= days <= 60:
#                     total_31_60 += i.total
#                     data += f'<td colspan=1 style="border: 1px solid black; font-size:12px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{i.total}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td>'
#                 if 61 <= days <= 90:
#                     total_61_90 += i.total
#                     data += f'<td colspan=1 style="border: 1px solid black; font-size:12px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{i.total}</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td>'
#                 if 91 <= days <= 120:
#                     total_91_above += i.total
#                     data += f'<td colspan=1 style="border: 1px solid black; font-size:12px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >-</td><td colspan=1 style="border: 1px solid black; font-size:8px" >{i.total}</td>'					
#         data += '</tr>'
#         data += f'<tr><td colspan=4 style="border: 1px solid black; font-size:12px" >Total</td><td style="border: 1px solid black; font-size:8px" >{total_amount}</td><td style="border: 1px solid black; font-size:8px" >-</td><td style="border: 1px solid black; font-size:8px" >-</td><td style="border: 1px solid black; font-size:8px" >{total_outstanding}</td><td style="border: 1px solid black; font-size:8px" >{total_0_30}</td><td style="border: 1px solid black; font-size:8px" >{total_31_60}</td><td style="border: 1px solid black; font-size:8px" >{total_61_90}</td><td style="border: 1px solid black; font-size:8px" >{total_91_above}</td></tr>'
#         data += '</table>'
#     else:
#         data += f'<tr><td colspan=4 style="border: 1px solid black; font-size:12px" >Total</td><td style="border: 1px solid black; font-size:12px" >0.0</td><td style="border: 1px solid black; font-size:12px" >-</td><td style="border: 1px solid black; font-size:12px" >-</td><td style="border: 1px solid black; font-size:12px" >0.0</td><td style="border: 1px solid black; font-size:12px" >0.0</td><td style="border: 1px solid black; font-size:12px" >0.0</td><td style="border: 1px solid black; font-size:12px" >0.0</td><td style="border: 1px solid black; font-size:12px" >0.0</td></tr>'
#         # data = "<table width='100%' border=1px solid black><tr style=background-color:#0F0F5C;;font-size:12px;text-align:center><td colspan=1 ><b style=color:white; text-align:center;width:320px>Sales Invoice Documents Not Avaliable</b></td></tr>"

#     return data




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

	if customer:
		gl_entry = frappe.db.sql("""
			SELECT voucher_type, voucher_no, posting_date,party_type, party, SUM(debit) AS debit, SUM(credit) AS credit 
			FROM `tabGL Entry` 
			WHERE company = %s AND posting_date BETWEEN %s AND %s 
			AND is_cancelled = 0 AND party = %s AND party_type = 'Customer' 
			GROUP BY voucher_no 
			ORDER BY posting_date
		""", (company, from_date, to_date, customer), as_dict=True)

		gle = frappe.db.sql("""
			SELECT SUM(debit) AS opening_debit, SUM(credit) AS opening_credit 
			FROM `tabGL Entry` 
			WHERE company = %s 
			AND (posting_date < %s OR (IFNULL(is_opening, 'No') = 'Yes' AND posting_date >= %s)) 
			AND party = %s AND is_cancelled = 0 AND party_type = 'Customer'
		""", (company, from_date, to_date, customer), as_dict=True)
	else:
		gl_entry = frappe.db.sql("""
			SELECT voucher_type, voucher_no, posting_date,party_type, party, SUM(debit) AS debit, SUM(credit) AS credit 
			FROM `tabGL Entry` 
			WHERE company = %s AND posting_date BETWEEN %s AND %s 
			AND is_cancelled = 0 
			GROUP BY voucher_no 
			ORDER BY posting_date
		""", (company, from_date, to_date), as_dict=True)

		gle = frappe.db.sql("""
			SELECT SUM(debit) AS opening_debit, SUM(credit) AS opening_credit 
			FROM `tabGL Entry` 
			WHERE company = %s 
			AND (posting_date < %s OR (IFNULL(is_opening, 'No') = 'Yes' AND posting_date >= %s)) 
			AND is_cancelled = 0
		""", (company, from_date, to_date), as_dict=True)

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


# @frappe.whitelist()
# def receipt_report(doc):
#     data = "<table border='1px solid black' width='100%'><tr style=background-color:#0F0F5C><td style='text-align:center;background-color:#0F0F5C;'width='10%'><p style=color:white;font-weight:bold>Posting Date</p></td><td style='text-align:center;'width='10%'><p style=color:white;font-weight:bold>Voucher No</p></td><td style='text-align:center;'width='20%'><p style=color:white;font-weight:bold>Party Name</p></td><td style='text-align:center;'width='20%'><p style=color:white;font-weight:bold>Received Amount</p></td><td style='text-align:center;overflow-wrap: break-word;'width='10%'><p style=color:white;font-weight:bold>Sales Person</p></td><td style='text-align:center;overflow-wrap: break-word;'width='30%'><p style=color:white;font-weight:bold>Remarks</p></td></tr>"
#     sales_person = []
#     total = 0
#     ind = 0
#     sa = frappe.db.sql("""
#         SELECT * 
#         FROM `tabPayment Entry`
#         WHERE company = %s AND posting_date BETWEEN %s AND %s AND payment_type ='Receive' AND party_type = 'Customer' AND docstatus = 1 order by posting_date  ASC
#     """, (doc.company, doc.from_date, doc.to_date), as_dict=True)
	
#     journal = frappe.db.sql("""
#         SELECT * 
#         FROM `tabJournal Entry`
#         WHERE 
#             company = %s 
#             AND posting_date BETWEEN %s AND %s 
#             AND docstatus = 1 
#             AND voucher_type IN ("Bank Entry", "Cash Entry")
#         ORDER BY posting_date ASC
#     """, (doc.company, doc.from_date, doc.to_date), as_dict=True)
	
#     for journ in journal:
#         doc_journal = frappe.get_all("Journal Entry Account", {"parent": journ.name,"party_type":"customer"}, ["party", "credit_in_account_currency"])
#         for c in doc_journal:
#             if c.credit_in_account_currency>0:
#                 ind += 1
#                 total += c.credit_in_account_currency
#                 data += f"<tr><td width='10%' nowrap>{formatdate(journ.posting_date, 'dd-MM-yyyy')}</td><td width='10%'>{journ.name}</td><td width='20%'>{c.party}</td><td style='text-align:right;'width='20%'>{fmt_money(round(c.credit_in_account_currency, 2))}</td><td style='overflow-wrap: break-word;'width='10%'></td><td style='text-align:left;overflow-wrap: break-word;'width='30%'>{journ.remarks or ''}</td></tr>"

#     for i in sa:
#         document = frappe.get_all("Payment Entry Reference", {"parent": i.name}, ["reference_doctype", "reference_name"])
#         if document:
#             for j in document:
#                 if j.reference_doctype == "Sales Order":
#                     sales_person = frappe.db.get_value("Sales Order", {"name": j.reference_name}, ["custom_sales_personuser"])
#                 elif j.reference_doctype == "Sales Invoice":
#                     sales_person = frappe.db.get_value("Sales Invoice", {"name": j.reference_name}, ["custom_sales_personuser"])
#         else:
#             sales_person =''
#         ind += 1
#         total += i.received_amount
#         data += f"<tr><td width='10%' nowrap>{formatdate(i.posting_date, 'dd-MM-yyyy')}</td><td width='10%'>{i.name}</td><td width='20%'>{i.party_name}</td><td style='text-align:right;'width='20%'>{fmt_money(round(i.received_amount, 2))}</td><td  style='text-align:left;overflow-wrap: break-word'width='10%'>{sales_person or ''}</td><td style='text-align:left;overflow-wrap: break-word;'width='30%'>{i.remarks or ''}</td></tr>"
#     data += f"<tr><td width='10%'> </td><td width='10%'> </td><td width='20%'>Total</td><td style='text-align:right;'width='20%'>{fmt_money(round(total, 2))}</td><td style='overflow-wrap: break-word;'width='10%'></td><td width='30%'></td></tr>"
#     data += '</table>'
#     return data

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


# @frappe.whitelist()
# def ageing_report_test(doc):
#     in_amount = 0
#     paid_amount = 0
#     credit_note = 0
#     out_amount = 0
#     age_0_30 = 0
#     age_31_60 = 0
#     age_61_90 = 0
#     # age_91_120 = 0
#     # age_above_121 = 0
#     age_above_90=0
#     paid = 0
#     combined_data =[]
#     data = "<table border='1px solid black' width='100%'><tr style='font-size:12px;background-color:#0F0F5C;'><td width=10%><p style=color:white;font-weight:bold>Posting Date</p></td><td width=10%><p style='text-align:center;color:white;font-weight:bold'>Voucher No</p></td><td width=10%><p style='text-align:center;color:white;font-weight:bold'>Customer LPO</p></td><td width=10%><p style='text-align:center;color:white;font-weight:bold'>Invoiced Amount</p></td><td width=10%><p style='text-align:center;color:white;font-weight:bold'>Paid Amount</p></td><td width=10%><p style='text-align:center;color:white;font-weight:bold'>Credit Note</p></td><td width=10%><p style='text-align:center;color:white;font-weight:bold'>Outstanding Amount</p></td><td width=5%><p style='text-align:center;color:white;font-weight:bold'>Age (Days)</p></td><td width=5%><p style='text-align:center;color:white;font-weight:bold'>0- 30</p></td><td width=5%><p style='text-align:center;color:white;font-weight:bold'>31-  60</p></td><td width=5%><p style='text-align:center;color:white;font-weight:bold'>61-  90</p></td><td width=5%><p style='text-align:center;color:white;font-weight:bold'>Above 90</p></td></tr>"
#     for c in doc.company:
#         if doc.customer:
#             si_list = frappe.db.sql(
#                 """SELECT * FROM `tabSales Invoice` WHERE company = %s and customer = %s and docstatus = 1 and is_return = 0 and invoice_type='Credit' and status !='Paid'  order by posting_date  ASC""",
#                 (c.company, doc.customer),
#                 as_dict=True
#             )
#             for i in si_list:
#                 result= frappe.db.sql("""
#                     SELECT sum(grand_total) as total
#                     FROM `tabSales Invoice` 
#                     WHERE company = %s AND return_against = %s AND docstatus = 1
#                 """, (c.company, i.name))
#                 return_amount = result[0][0] if result and result[0][0] else 0
				
#                 result_doc = frappe.db.sql("""
#                     SELECT name
#                     FROM `tabSales Invoice` 
#                     WHERE company = %s AND return_against = %s AND docstatus = 1
#                 """, (c.company, i.name), as_dict=True)
				
#                 pay_doc = []
#                 if result_doc:
#                     pay_doc = frappe.db.sql("""
#                         SELECT per.allocated_amount 
#                         FROM `tabPayment Entry Reference` AS per
#                         LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                         WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                     """, (c.company, result_doc[0]["name"]), as_dict=True)
#                 pay = frappe.db.sql("""
#                     SELECT per.allocated_amount 
#                     FROM `tabPayment Entry Reference` AS per
#                     LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                     WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                 """, (c.company, i.name), as_dict=True)
#                 value = sum(j["allocated_amount"] for j in pay) + sum(r["allocated_amount"] for r in pay_doc)

#                 jv = frappe.db.sql("""
#                     SELECT credit_in_account_currency 
#                     FROM `tabJournal Entry Account` AS per
#                     LEFT JOIN `tabJournal Entry` AS pe ON per.parent = pe.name
#                     WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                 """, (c.company, i.name), as_dict=True)
#                 for k in jv:
#                     value += k.credit_in_account_currency
				

#                 if value and return_amount:
#                     outstanding = i.grand_total - value + return_amount
#                 elif value:
#                     outstanding = i.grand_total - value
#                 elif return_amount:
#                     outstanding = i.grand_total + return_amount
#                 else:
#                     outstanding = i.grand_total
				
#                 out_amount += outstanding
#                 age = date_diff(today(), i.posting_date) if i.posting_date else 0

#                 if round(outstanding) != 0:
#                     if value:
#                         paid_amount += value
#                     if return_amount:
#                         credit_note += return_amount
#                     in_amount += i.grand_total
#                     if 0 <= age <= 30:
#                         age_0_30 += outstanding
#                     elif 31 <= age <= 60:
#                         age_31_60 += outstanding
#                     elif 61 <= age <= 90:
#                         age_61_90 += outstanding
#                     else:
#                         age_above_90 += outstanding
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 += outstanding
#                     # else:
#                     #     age_above_121 += outstanding
#                     combined_data.append({
#                         'posting_date': i.posting_date,
#                         'name': i.name,
#                         'po_no': i.po_no if i.po_no else '-',
#                         'grand_total': i.grand_total,
#                         'paid_amount': value if value else 0,
#                         'credit_note': return_amount if return_amount else 0,
#                         'outstanding': outstanding if outstanding else 0,
#                         'age': age,
#                         'oustanding_0_30':outstanding if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':outstanding if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':outstanding if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':outstanding if age > 90 else 0,
#                         # 'oustanding_91_120':outstanding if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':outstanding if age > 120 else 0,
#                     })

#             sales = frappe.db.sql(
#                 """SELECT * FROM `tabSales Invoice` WHERE company = %s and customer = %s and docstatus = 1 and is_return = 1 and invoice_type='Credit' and status !='Paid' AND (return_against IS NULL OR return_against = '')  order by posting_date  ASC""",
#                 (c.company, doc.customer),
#                 as_dict=True
#             )
#             for a in sales:
#                 pay = frappe.db.sql(""" SELECT per.allocated_amount FROM `tabPayment Entry Reference` AS per
#                 LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                 WHERE per.reference_name = '%s' AND pe.docstatus = 1 and pe.company = '%s' """ % (a.name, c.company), as_dict=True)
#                 value = sum(j.allocated_amount for j in pay)

#                 jv = frappe.db.sql(""" SELECT credit_in_account_currency FROM `tabJournal Entry Account` AS per
#                 LEFT JOIN `tabJournal Entry` AS pe ON per.parent = pe.name
#                 WHERE per.reference_name = '%s' AND pe.docstatus = 1 and pe.company = '%s'""" % (a.name, c.company), as_dict=True)
#                 value += sum(k.credit_in_account_currency for k in jv)

#                 outstanding = a.grand_total - value if value else a.grand_total
#                 out_amount += outstanding
#                 age = date_diff(today(), a.posting_date) if a.posting_date else 0

#                 if round(outstanding) != 0:
#                     if value:
#                         paid_amount += value
#                     if a.grand_total:
#                         credit_note += a.grand_total
#                     in_amount += a.grand_total
#                     if 0 <= age <= 30:
#                         age_0_30 += outstanding
#                     elif 31 <= age <= 60:
#                         age_31_60 += outstanding
#                     elif 61 <= age <= 90:
#                         age_61_90 += outstanding
#                     else:
#                         age_above_90 += outstanding
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 += outstanding
#                     # else:
#                     #     age_above_121 += outstanding
#                     combined_data.append({
#                         'posting_date': a.posting_date,
#                         'name': a.name,
#                         'po_no':a.po_no if i.po_no else '-',
#                         'grand_total': a.grand_total,
#                         'paid_amount': value if value else 0,
#                         'credit_note': a.grand_total if a.grand_total else 0,
#                         'outstanding': outstanding if outstanding else 0,
#                         'age': age,
#                         'oustanding_0_30':outstanding if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':outstanding if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':outstanding if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':outstanding if age > 90 else 0,
#                         # 'oustanding_91_120':outstanding if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':outstanding if age > 120 else 0,
#                     })

#             payment = frappe.db.sql("""
#                 SELECT * FROM `tabPayment Entry` 
#                 WHERE company = %s AND party = %s AND docstatus = 1 
#                 AND payment_type = 'Receive' 
#                 ORDER BY posting_date ASC
#             """, (c.company, doc.customer), as_dict=True)
#             for v in payment:
#                 unallocated_amount = v.unallocated_amount
#                 paid_amount += unallocated_amount
#                 out_amount -= unallocated_amount
#                 age = date_diff(today(), v.posting_date)
#                 if unallocated_amount != 0:
#                     if 0 <= age <= 30:
#                         age_0_30 -= unallocated_amount
#                     elif 31 <= age <= 60:
#                         age_31_60 -= unallocated_amount
#                     elif 61 <= age <= 90:
#                         age_61_90 -= unallocated_amount
#                     else:
#                         age_above_90 -= unallocated_amount
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 -= unallocated_amount
#                     # else:
#                     #     age_above_121 -= unallocated_amount
#                     combined_data.append({
#                         'posting_date': v.posting_date,
#                         'name': v.name,
#                         'po_no': v.reference_no if v.reference_no else '-',
#                         'grand_total': 0,
#                         'paid_amount': unallocated_amount if unallocated_amount else 0,
#                         'credit_note': 0,
#                         'outstanding': -unallocated_amount if unallocated_amount else 0,
#                         'age': age,
#                         'oustanding_0_30':-unallocated_amount if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':-unallocated_amount if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':-unallocated_amount if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':-unallocated_amount if age > 90 else 0,
#                         # 'oustanding_91_120':-unallocated_amount if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':-unallocated_amount if age > 120 else 0,
#                     })

#             journal = frappe.db.sql("""
#                 SELECT per.credit_in_account_currency, per.debit_in_account_currency, pe.name, pe.posting_date 
#                 FROM `tabJournal Entry Account` AS per
#                 LEFT JOIN `tabJournal Entry` AS pe ON per.parent = pe.name
#                 WHERE pe.company = %s AND per.account LIKE %s AND pe.docstatus = 1 
#                 AND party_type = 'Customer' AND party = %s AND per.reference_name IS NULL
#             """, (c.company, '%Debtors -%', doc.customer), as_dict=True)
#             for jour in journal:
#                 pay_journ = frappe.db.sql("""
#                     SELECT per.allocated_amount 
#                     FROM `tabPayment Entry Reference` AS per
#                     LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                     WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                 """, (c.company, jour.name), as_dict=True)
#                 value_journ = sum(jo["allocated_amount"] for jo in pay_journ)
#                 if value_journ:
#                     value_journ = value_journ
#                 else:
#                     value_journ = 0
#                 if jour.credit_in_account_currency:
#                     journ_amount_credit = jour.credit_in_account_currency
#                     paid_amount += journ_amount_credit - value_journ
#                     in_amount -= journ_amount_credit - value_journ
#                     out_amount -= journ_amount_credit - value_journ
#                     age = date_diff(today(), jour.posting_date)
#                     if 0 <= age <= 30:
#                         age_0_30 -= (jour.credit_in_account_currency -value_journ)
#                     elif 31 <= age <= 60:
#                         age_31_60 -= (jour.credit_in_account_currency -value_journ)
#                     elif 61 <= age <= 90:
#                         age_61_90 -= (jour.credit_in_account_currency -value_journ)
#                     else:
#                         age_above_90 -= (jour.credit_in_account_currency -value_journ)
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 -= (jour.credit_in_account_currency -value_journ)
#                     # else:
#                     #     age_above_121 -= (jour.credit_in_account_currency -value_journ)
#                     combined_data.append({
#                         'posting_date': jour.posting_date,
#                         'name': jour.name,
#                         'po_no':'-',
#                         'grand_total': -jour.credit_in_account_currency,
#                         'paid_amount': 0,
#                         'credit_note': '-',
#                         'outstanding': -(jour.credit_in_account_currency-value_journ) or 0,
#                         'age': age,
#                         'oustanding_0_30':-(jour.credit_in_account_currency-value_journ) if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':-(jour.credit_in_account_currency-value_journ) if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':-(jour.credit_in_account_currency-value_journ) if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':-(jour.credit_in_account_currency-value_journ) if age > 90 else 0,
#                         # 'oustanding_91_120':-(jour.credit_in_account_currency-value_journ) if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':-(jour.credit_in_account_currency-value_journ) if age > 120 else 0,
#                     })
	
#                 elif jour.debit_in_account_currency:
#                     journ_amount_debit = jour.debit_in_account_currency
#                     in_amount += journ_amount_debit - value_journ
#                     out_amount += journ_amount_debit - value_journ
#                     age = date_diff(today(), jour.posting_date)

#                     if 0 <= age <= 30:
#                         age_0_30 += (jour.debit_in_account_currency -value_journ)
#                     elif 31 <= age <= 60:
#                         age_31_60 += (jour.debit_in_account_currency -value_journ)
#                     elif 61 <= age <= 90:
#                         age_61_90 += (jour.debit_in_account_currency -value_journ)
#                     else:
#                         age_above_90 += (jour.debit_in_account_currency -value_journ)
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 += (jour.debit_in_account_currency -value_journ)
#                     # else:
#                     #     age_above_121 += (jour.debit_in_account_currency -value_journ)
	
#                     combined_data.append({
#                         'posting_date': jour.posting_date,
#                         'name': jour.name,
#                         'po_no':'-',
#                         'grand_total': jour.debit_in_account_currency,
#                         'paid_amount':value_journ or 0,
#                         'credit_note': 0,
#                         'outstanding': (jour.debit_in_account_currency -value_journ) or 0,
#                         'age': age,
#                         'oustanding_0_30':jour.debit_in_account_currency -value_journ if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':jour.debit_in_account_currency -value_journ if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':jour.debit_in_account_currency -value_journ if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':jour.debit_in_account_currency -value_journ if age > 90 else 0,
#                         # 'oustanding_91_120':jour.debit_in_account_currency -value_journ if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':jour.debit_in_account_currency -value_journ if age > 120 else 0,
#                     })
#     combined_data = sorted(combined_data, key=lambda x: x['posting_date'])
#     for entry in combined_data:
#         if entry['outstanding'] != 0:
#             data += f"""<tr style='font-size:10px'>
#             <td>{formatdate(entry['posting_date'],'dd-mm-yyyy')}</td>
#             <td>{entry['name']}</td>
#             <td>{entry['po_no']}</td>
#             <td>{fmt_money(round(entry['grand_total'], 2))}</td>
#             <td>{fmt_money(round(entry['paid_amount'], 2)) if entry['paid_amount']  else '-'}</td>
#             <td>{fmt_money(entry['credit_note'], 2) if entry['credit_note'] else '-'}</td>
#             <td>{fmt_money(round(entry['outstanding'], 2)) if entry['outstanding'] else 0}</td>
#             <td>{entry['age']}</td>
#             <td>{fmt_money(round(entry['oustanding_0_30'],2))}</td>
#             <td>{fmt_money(round(entry['oustanding_31_60'],2))}</td>
#             <td>{fmt_money(round(entry['oustanding_61_90'],2))}</td>
#             <td>{fmt_money(round(entry['oustanding_above_90'],2))}</td>
#             </tr>"""
#             # <td>{fmt_money(round(entry['oustanding_91_120'],2))}</td>
#             # <td>{fmt_money(round(entry['oustanding_above_121'],2))}</td>
			
		

#     data += f"<tr style='font-size:10px'><td width=10%></td><td width=10%></td><td width=10%><b>Total</b></td><td width=10%><b>{fmt_money(round(in_amount, 2))}</b></td><td width=10%><b>{fmt_money(round(paid_amount, 2))}</b></td><td width=10%><b>{fmt_money(round(credit_note, 2))}</b></td><td width=10%><b>{fmt_money(round(out_amount, 2))}</b></td><td width=5%></td><td width=5%><b>{fmt_money(round(age_0_30, 2))}</b></td><td width=5%><b>{fmt_money(round(age_31_60, 2))}</b></td><td width=5%><b>{fmt_money(round(age_61_90, 2))}</b></td><td width=5%><b>{fmt_money(round(age_above_90, 2))}</b></td></tr>"
#     data += "</table>"
#     return data
   
# import json
# from frappe.utils import today, date_diff, formatdate, fmt_money
# import frappe

# @frappe.whitelist()
# def ageing_report_test(doc):
#     # Convert doc string to dictionary if needed
#     if isinstance(doc, str):
#         doc = frappe._dict(json.loads(doc))

#     # Validate input
#     if not doc.get("company") or not doc.get("customer"):
#         return "<p style='color:red;'>Missing company or customer information.</p>"

#     in_amount = paid_amount = credit_note = out_amount = 0
#     age_0_30 = age_31_60 = age_61_90 = age_above_90 = 0
#     combined_data = []

#     data = "<table border='1px solid black' width='100%'>"
#     data += "<tr style='font-size:12px;background-color:#0F0F5C;'>"
#     data += "<td width=10%><p style=color:white;font-weight:bold>Posting Date</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Voucher No</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Customer LPO</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Invoiced Amount</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Paid Amount</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Credit Note</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Outstanding Amount</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>Age (Days)</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>0- 30</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>31-  60</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>61-  90</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>Above 90</p></td></tr>"

#     # Your logic here (shortened for brevity)
#     for c in doc.company:
#         if doc.customer:
#             si_list = frappe.db.sql(
#                 """SELECT * FROM `tabSales Invoice` WHERE company = %s and customer = %s and docstatus = 1 and is_return = 0 and invoice_type='Credit' and status !='Paid'  order by posting_date  ASC""",
#                 (c.company, doc.customer),
#                 as_dict=True
#             )
#             for i in si_list:
#                 result= frappe.db.sql("""
#                     SELECT sum(grand_total) as total
#                     FROM `tabSales Invoice` 
#                     WHERE company = %s AND return_against = %s AND docstatus = 1
#                 """, (c.company, i.name))
#                 return_amount = result[0][0] if result and result[0][0] else 0
				
#                 result_doc = frappe.db.sql("""
#                     SELECT name
#                     FROM `tabSales Invoice` 
#                     WHERE company = %s AND return_against = %s AND docstatus = 1
#                 """, (c.company, i.name), as_dict=True)
				
#                 pay_doc = []
#                 if result_doc:
#                     pay_doc = frappe.db.sql("""
#                         SELECT per.allocated_amount 
#                         FROM `tabPayment Entry Reference` AS per
#                         LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                         WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                     """, (c.company, result_doc[0]["name"]), as_dict=True)
#                 pay = frappe.db.sql("""
#                     SELECT per.allocated_amount 
#                     FROM `tabPayment Entry Reference` AS per
#                     LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                     WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                 """, (c.company, i.name), as_dict=True)
#                 value = sum(j["allocated_amount"] for j in pay) + sum(r["allocated_amount"] for r in pay_doc)

#                 jv = frappe.db.sql("""
#                     SELECT credit_in_account_currency 
#                     FROM `tabJournal Entry Account` AS per
#                     LEFT JOIN `tabJournal Entry` AS pe ON per.parent = pe.name
#                     WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                 """, (c.company, i.name), as_dict=True)
#                 for k in jv:
#                     value += k.credit_in_account_currency
				

#                 if value and return_amount:
#                     outstanding = i.grand_total - value + return_amount
#                 elif value:
#                     outstanding = i.grand_total - value
#                 elif return_amount:
#                     outstanding = i.grand_total + return_amount
#                 else:
#                     outstanding = i.grand_total
				
#                 out_amount += outstanding
#                 age = date_diff(today(), i.posting_date) if i.posting_date else 0

#                 if round(outstanding) != 0:
#                     if value:
#                         paid_amount += value
#                     if return_amount:
#                         credit_note += return_amount
#                     in_amount += i.grand_total
#                     if 0 <= age <= 30:
#                         age_0_30 += outstanding
#                     elif 31 <= age <= 60:
#                         age_31_60 += outstanding
#                     elif 61 <= age <= 90:
#                         age_61_90 += outstanding
#                     else:
#                         age_above_90 += outstanding
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 += outstanding
#                     # else:
#                     #     age_above_121 += outstanding
#                     combined_data.append({
#                         'posting_date': i.posting_date,
#                         'name': i.name,
#                         'po_no': i.po_no if i.po_no else '-',
#                         'grand_total': i.grand_total,
#                         'paid_amount': value if value else 0,
#                         'credit_note': return_amount if return_amount else 0,
#                         'outstanding': outstanding if outstanding else 0,
#                         'age': age,
#                         'oustanding_0_30':outstanding if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':outstanding if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':outstanding if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':outstanding if age > 90 else 0,
#                         # 'oustanding_91_120':outstanding if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':outstanding if age > 120 else 0,
#                     })

#             sales = frappe.db.sql(
#                 """SELECT * FROM `tabSales Invoice` WHERE company = %s and customer = %s and docstatus = 1 and is_return = 1 and invoice_type='Credit' and status !='Paid' AND (return_against IS NULL OR return_against = '')  order by posting_date  ASC""",
#                 (c.company, doc.customer),
#                 as_dict=True
#             )
#             for a in sales:
#                 pay = frappe.db.sql(""" SELECT per.allocated_amount FROM `tabPayment Entry Reference` AS per
#                 LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                 WHERE per.reference_name = '%s' AND pe.docstatus = 1 and pe.company = '%s' """ % (a.name, c.company), as_dict=True)
#                 value = sum(j.allocated_amount for j in pay)

#                 jv = frappe.db.sql(""" SELECT credit_in_account_currency FROM `tabJournal Entry Account` AS per
#                 LEFT JOIN `tabJournal Entry` AS pe ON per.parent = pe.name
#                 WHERE per.reference_name = '%s' AND pe.docstatus = 1 and pe.company = '%s'""" % (a.name, c.company), as_dict=True)
#                 value += sum(k.credit_in_account_currency for k in jv)

#                 outstanding = a.grand_total - value if value else a.grand_total
#                 out_amount += outstanding
#                 age = date_diff(today(), a.posting_date) if a.posting_date else 0

#                 if round(outstanding) != 0:
#                     if value:
#                         paid_amount += value
#                     if a.grand_total:
#                         credit_note += a.grand_total
#                     in_amount += a.grand_total
#                     if 0 <= age <= 30:
#                         age_0_30 += outstanding
#                     elif 31 <= age <= 60:
#                         age_31_60 += outstanding
#                     elif 61 <= age <= 90:
#                         age_61_90 += outstanding
#                     else:
#                         age_above_90 += outstanding
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 += outstanding
#                     # else:
#                     #     age_above_121 += outstanding
#                     combined_data.append({
#                         'posting_date': a.posting_date,
#                         'name': a.name,
#                         'po_no':a.po_no if i.po_no else '-',
#                         'grand_total': a.grand_total,
#                         'paid_amount': value if value else 0,
#                         'credit_note': a.grand_total if a.grand_total else 0,
#                         'outstanding': outstanding if outstanding else 0,
#                         'age': age,
#                         'oustanding_0_30':outstanding if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':outstanding if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':outstanding if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':outstanding if age > 90 else 0,
#                         # 'oustanding_91_120':outstanding if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':outstanding if age > 120 else 0,
#                     })

#             payment = frappe.db.sql("""
#                 SELECT * FROM `tabPayment Entry` 
#                 WHERE company = %s AND party = %s AND docstatus = 1 
#                 AND payment_type = 'Receive' 
#                 ORDER BY posting_date ASC
#             """, (c.company, doc.customer), as_dict=True)
#             for v in payment:
#                 unallocated_amount = v.unallocated_amount
#                 paid_amount += unallocated_amount
#                 out_amount -= unallocated_amount
#                 age = date_diff(today(), v.posting_date)
#                 if unallocated_amount != 0:
#                     if 0 <= age <= 30:
#                         age_0_30 -= unallocated_amount
#                     elif 31 <= age <= 60:
#                         age_31_60 -= unallocated_amount
#                     elif 61 <= age <= 90:
#                         age_61_90 -= unallocated_amount
#                     else:
#                         age_above_90 -= unallocated_amount
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 -= unallocated_amount
#                     # else:
#                     #     age_above_121 -= unallocated_amount
#                     combined_data.append({
#                         'posting_date': v.posting_date,
#                         'name': v.name,
#                         'po_no': v.reference_no if v.reference_no else '-',
#                         'grand_total': 0,
#                         'paid_amount': unallocated_amount if unallocated_amount else 0,
#                         'credit_note': 0,
#                         'outstanding': -unallocated_amount if unallocated_amount else 0,
#                         'age': age,
#                         'oustanding_0_30':-unallocated_amount if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':-unallocated_amount if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':-unallocated_amount if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':-unallocated_amount if age > 90 else 0,
#                         # 'oustanding_91_120':-unallocated_amount if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':-unallocated_amount if age > 120 else 0,
#                     })

#             journal = frappe.db.sql("""
#                 SELECT per.credit_in_account_currency, per.debit_in_account_currency, pe.name, pe.posting_date 
#                 FROM `tabJournal Entry Account` AS per
#                 LEFT JOIN `tabJournal Entry` AS pe ON per.parent = pe.name
#                 WHERE pe.company = %s AND per.account LIKE %s AND pe.docstatus = 1 
#                 AND party_type = 'Customer' AND party = %s AND per.reference_name IS NULL
#             """, (c.company, '%Debtors -%', doc.customer), as_dict=True)
#             for jour in journal:
#                 pay_journ = frappe.db.sql("""
#                     SELECT per.allocated_amount 
#                     FROM `tabPayment Entry Reference` AS per
#                     LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                     WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                 """, (c.company, jour.name), as_dict=True)
#                 value_journ = sum(jo["allocated_amount"] for jo in pay_journ)
#                 if value_journ:
#                     value_journ = value_journ
#                 else:
#                     value_journ = 0
#                 if jour.credit_in_account_currency:
#                     journ_amount_credit = jour.credit_in_account_currency
#                     paid_amount += journ_amount_credit - value_journ
#                     in_amount -= journ_amount_credit - value_journ
#                     out_amount -= journ_amount_credit - value_journ
#                     age = date_diff(today(), jour.posting_date)
#                     if 0 <= age <= 30:
#                         age_0_30 -= (jour.credit_in_account_currency -value_journ)
#                     elif 31 <= age <= 60:
#                         age_31_60 -= (jour.credit_in_account_currency -value_journ)
#                     elif 61 <= age <= 90:
#                         age_61_90 -= (jour.credit_in_account_currency -value_journ)
#                     else:
#                         age_above_90 -= (jour.credit_in_account_currency -value_journ)
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 -= (jour.credit_in_account_currency -value_journ)
#                     # else:
#                     #     age_above_121 -= (jour.credit_in_account_currency -value_journ)
#                     combined_data.append({
#                         'posting_date': jour.posting_date,
#                         'name': jour.name,
#                         'po_no':'-',
#                         'grand_total': -jour.credit_in_account_currency,
#                         'paid_amount': 0,
#                         'credit_note': '-',
#                         'outstanding': -(jour.credit_in_account_currency-value_journ) or 0,
#                         'age': age,
#                         'oustanding_0_30':-(jour.credit_in_account_currency-value_journ) if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':-(jour.credit_in_account_currency-value_journ) if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':-(jour.credit_in_account_currency-value_journ) if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':-(jour.credit_in_account_currency-value_journ) if age > 90 else 0,
#                         # 'oustanding_91_120':-(jour.credit_in_account_currency-value_journ) if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':-(jour.credit_in_account_currency-value_journ) if age > 120 else 0,
#                     })
	
#                 elif jour.debit_in_account_currency:
#                     journ_amount_debit = jour.debit_in_account_currency
#                     in_amount += journ_amount_debit - value_journ
#                     out_amount += journ_amount_debit - value_journ
#                     age = date_diff(today(), jour.posting_date)

#                     if 0 <= age <= 30:
#                         age_0_30 += (jour.debit_in_account_currency -value_journ)
#                     elif 31 <= age <= 60:
#                         age_31_60 += (jour.debit_in_account_currency -value_journ)
#                     elif 61 <= age <= 90:
#                         age_61_90 += (jour.debit_in_account_currency -value_journ)
#                     else:
#                         age_above_90 += (jour.debit_in_account_currency -value_journ)
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 += (jour.debit_in_account_currency -value_journ)
#                     # else:
#                     #     age_above_121 += (jour.debit_in_account_currency -value_journ)
	
#                     combined_data.append({
#                         'posting_date': jour.posting_date,
#                         'name': jour.name,
#                         'po_no':'-',
#                         'grand_total': jour.debit_in_account_currency,
#                         'paid_amount':value_journ or 0,
#                         'credit_note': 0,
#                         'outstanding': (jour.debit_in_account_currency -value_journ) or 0,
#                         'age': age,
#                         'oustanding_0_30':jour.debit_in_account_currency -value_journ if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':jour.debit_in_account_currency -value_journ if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':jour.debit_in_account_currency -value_journ if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':jour.debit_in_account_currency -value_journ if age > 90 else 0,
#                         # 'oustanding_91_120':jour.debit_in_account_currency -value_journ if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':jour.debit_in_account_currency -value_journ if age > 120 else 0,
#                     })

#     # Sort and display the rows
#     combined_data = sorted(combined_data, key=lambda x: x['posting_date'])
#     for entry in combined_data:
#         if entry['outstanding'] != 0:
#             data += f"""<tr style='font-size:10px'>
#             <td>{formatdate(entry['posting_date'],'dd-mm-yyyy')}</td>
#             <td>{entry['name']}</td>
#             <td>{entry['po_no']}</td>
#             <td>{fmt_money(round(entry['grand_total'], 2))}</td>
#             <td>{fmt_money(round(entry['paid_amount'], 2)) if entry['paid_amount']  else '-'}</td>
#             <td>{fmt_money(entry['credit_note'], 2) if entry['credit_note'] else '-'}</td>
#             <td>{fmt_money(round(entry['outstanding'], 2))}</td>
#             <td>{entry['age']}</td>
#             <td>{fmt_money(round(entry['oustanding_0_30'],2))}</td>
#             <td>{fmt_money(round(entry['oustanding_31_60'],2))}</td>
#             <td>{fmt_money(round(entry['oustanding_61_90'],2))}</td>
#             <td>{fmt_money(round(entry['oustanding_above_90'],2))}</td></tr>"""

#     # Final total row
#     data += f"<tr style='font-size:10px'><td></td><td></td><td><b>Total</b></td><td><b>{fmt_money(round(in_amount, 2))}</b></td><td><b>{fmt_money(round(paid_amount, 2))}</b></td><td><b>{fmt_money(round(credit_note, 2))}</b></td><td><b>{fmt_money(round(out_amount, 2))}</b></td><td></td><td><b>{fmt_money(round(age_0_30, 2))}</b></td><td><b>{fmt_money(round(age_31_60, 2))}</b></td><td><b>{fmt_money(round(age_61_90, 2))}</b></td><td><b>{fmt_money(round(age_above_90, 2))}</b></td></tr>"
#     data += "</table>"
#     return data

# import json
# from frappe.utils import today, date_diff, formatdate, fmt_money
# import frappe

# @frappe.whitelist()
# def ageing_report_test(doc):
#     # Convert doc string to dictionary if needed
#     if isinstance(doc, str):
#         doc = frappe._dict(json.loads(doc))

#     # Validate input
#     if not doc.get("company") or not doc.get("customer"):
#         return "<p style='color:red;'>Missing company or customer information.</p>"

#     in_amount = paid_amount = credit_note = out_amount = 0
#     age_0_30 = age_31_60 = age_61_90 = age_above_90 = 0
#     combined_data = []

#     data = "<table border='1px solid black' width='100%'>"
#     data += "<tr style='font-size:12px;background-color:#0F0F5C;'>"
#     data += "<td width=10%><p style=color:white;font-weight:bold>Posting Date</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Voucher No</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Customer LPO</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Invoiced Amount</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Paid Amount</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Credit Note</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Outstanding Amount</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>Age (Days)</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>0- 30</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>31-  60</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>61-  90</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>Above 90</p></td></tr>"

#     # Convert to list if needed (future proofing)
#     companies = doc.company if isinstance(doc.company, list) else [doc.company]

#     for c in companies:
#         doc["company"] = c
#         if doc.customer:
#             si_list = frappe.db.sql(
#                 """SELECT * FROM `tabSales Invoice` WHERE company = %s and customer = %s and docstatus = 1 and is_return = 0 and invoice_type='Credit' and status !='Paid'  order by posting_date  ASC""",
#                 (c.company, doc.customer),
#                 as_dict=True
#             )
#             for i in si_list:
#                 result= frappe.db.sql("""
#                     SELECT sum(grand_total) as total
#                     FROM `tabSales Invoice` 
#                     WHERE company = %s AND return_against = %s AND docstatus = 1
#                 """, (c.company, i.name))
#                 return_amount = result[0][0] if result and result[0][0] else 0
				
#                 result_doc = frappe.db.sql("""
#                     SELECT name
#                     FROM `tabSales Invoice` 
#                     WHERE company = %s AND return_against = %s AND docstatus = 1
#                 """, (c.company, i.name), as_dict=True)
				
#                 pay_doc = []
#                 if result_doc:
#                     pay_doc = frappe.db.sql("""
#                         SELECT per.allocated_amount 
#                         FROM `tabPayment Entry Reference` AS per
#                         LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                         WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                     """, (c.company, result_doc[0]["name"]), as_dict=True)
#                 pay = frappe.db.sql("""
#                     SELECT per.allocated_amount 
#                     FROM `tabPayment Entry Reference` AS per
#                     LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                     WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                 """, (c.company, i.name), as_dict=True)
#                 value = sum(j["allocated_amount"] for j in pay) + sum(r["allocated_amount"] for r in pay_doc)

#                 jv = frappe.db.sql("""
#                     SELECT credit_in_account_currency 
#                     FROM `tabJournal Entry Account` AS per
#                     LEFT JOIN `tabJournal Entry` AS pe ON per.parent = pe.name
#                     WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                 """, (c.company, i.name), as_dict=True)
#                 for k in jv:
#                     value += k.credit_in_account_currency
				

#                 if value and return_amount:
#                     outstanding = i.grand_total - value + return_amount
#                 elif value:
#                     outstanding = i.grand_total - value
#                 elif return_amount:
#                     outstanding = i.grand_total + return_amount
#                 else:
#                     outstanding = i.grand_total
				
#                 out_amount += outstanding
#                 age = date_diff(today(), i.posting_date) if i.posting_date else 0

#                 if round(outstanding) != 0:
#                     if value:
#                         paid_amount += value
#                     if return_amount:
#                         credit_note += return_amount
#                     in_amount += i.grand_total
#                     if 0 <= age <= 30:
#                         age_0_30 += outstanding
#                     elif 31 <= age <= 60:
#                         age_31_60 += outstanding
#                     elif 61 <= age <= 90:
#                         age_61_90 += outstanding
#                     else:
#                         age_above_90 += outstanding
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 += outstanding
#                     # else:
#                     #     age_above_121 += outstanding
#                     combined_data.append({
#                         'posting_date': i.posting_date,
#                         'name': i.name,
#                         'po_no': i.po_no if i.po_no else '-',
#                         'grand_total': i.grand_total,
#                         'paid_amount': value if value else 0,
#                         'credit_note': return_amount if return_amount else 0,
#                         'outstanding': outstanding if outstanding else 0,
#                         'age': age,
#                         'oustanding_0_30':outstanding if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':outstanding if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':outstanding if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':outstanding if age > 90 else 0,
#                         # 'oustanding_91_120':outstanding if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':outstanding if age > 120 else 0,
#                     })

#             sales = frappe.db.sql(
#                 """SELECT * FROM `tabSales Invoice` WHERE company = %s and customer = %s and docstatus = 1 and is_return = 1 and invoice_type='Credit' and status !='Paid' AND (return_against IS NULL OR return_against = '')  order by posting_date  ASC""",
#                 (c.company, doc.customer),
#                 as_dict=True
#             )
#             for a in sales:
#                 pay = frappe.db.sql(""" SELECT per.allocated_amount FROM `tabPayment Entry Reference` AS per
#                 LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                 WHERE per.reference_name = '%s' AND pe.docstatus = 1 and pe.company = '%s' """ % (a.name, c.company), as_dict=True)
#                 value = sum(j.allocated_amount for j in pay)

#                 jv = frappe.db.sql(""" SELECT credit_in_account_currency FROM `tabJournal Entry Account` AS per
#                 LEFT JOIN `tabJournal Entry` AS pe ON per.parent = pe.name
#                 WHERE per.reference_name = '%s' AND pe.docstatus = 1 and pe.company = '%s'""" % (a.name, c.company), as_dict=True)
#                 value += sum(k.credit_in_account_currency for k in jv)

#                 outstanding = a.grand_total - value if value else a.grand_total
#                 out_amount += outstanding
#                 age = date_diff(today(), a.posting_date) if a.posting_date else 0

#                 if round(outstanding) != 0:
#                     if value:
#                         paid_amount += value
#                     if a.grand_total:
#                         credit_note += a.grand_total
#                     in_amount += a.grand_total
#                     if 0 <= age <= 30:
#                         age_0_30 += outstanding
#                     elif 31 <= age <= 60:
#                         age_31_60 += outstanding
#                     elif 61 <= age <= 90:
#                         age_61_90 += outstanding
#                     else:
#                         age_above_90 += outstanding
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 += outstanding
#                     # else:
#                     #     age_above_121 += outstanding
#                     combined_data.append({
#                         'posting_date': a.posting_date,
#                         'name': a.name,
#                         'po_no':a.po_no if i.po_no else '-',
#                         'grand_total': a.grand_total,
#                         'paid_amount': value if value else 0,
#                         'credit_note': a.grand_total if a.grand_total else 0,
#                         'outstanding': outstanding if outstanding else 0,
#                         'age': age,
#                         'oustanding_0_30':outstanding if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':outstanding if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':outstanding if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':outstanding if age > 90 else 0,
#                         # 'oustanding_91_120':outstanding if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':outstanding if age > 120 else 0,
#                     })

#             payment = frappe.db.sql("""
#                 SELECT * FROM `tabPayment Entry` 
#                 WHERE company = %s AND party = %s AND docstatus = 1 
#                 AND payment_type = 'Receive' 
#                 ORDER BY posting_date ASC
#             """, (c.company, doc.customer), as_dict=True)
#             for v in payment:
#                 unallocated_amount = v.unallocated_amount
#                 paid_amount += unallocated_amount
#                 out_amount -= unallocated_amount
#                 age = date_diff(today(), v.posting_date)
#                 if unallocated_amount != 0:
#                     if 0 <= age <= 30:
#                         age_0_30 -= unallocated_amount
#                     elif 31 <= age <= 60:
#                         age_31_60 -= unallocated_amount
#                     elif 61 <= age <= 90:
#                         age_61_90 -= unallocated_amount
#                     else:
#                         age_above_90 -= unallocated_amount
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 -= unallocated_amount
#                     # else:
#                     #     age_above_121 -= unallocated_amount
#                     combined_data.append({
#                         'posting_date': v.posting_date,
#                         'name': v.name,
#                         'po_no': v.reference_no if v.reference_no else '-',
#                         'grand_total': 0,
#                         'paid_amount': unallocated_amount if unallocated_amount else 0,
#                         'credit_note': 0,
#                         'outstanding': -unallocated_amount if unallocated_amount else 0,
#                         'age': age,
#                         'oustanding_0_30':-unallocated_amount if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':-unallocated_amount if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':-unallocated_amount if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':-unallocated_amount if age > 90 else 0,
#                         # 'oustanding_91_120':-unallocated_amount if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':-unallocated_amount if age > 120 else 0,
#                     })

#             journal = frappe.db.sql("""
#                 SELECT per.credit_in_account_currency, per.debit_in_account_currency, pe.name, pe.posting_date 
#                 FROM `tabJournal Entry Account` AS per
#                 LEFT JOIN `tabJournal Entry` AS pe ON per.parent = pe.name
#                 WHERE pe.company = %s AND per.account LIKE %s AND pe.docstatus = 1 
#                 AND party_type = 'Customer' AND party = %s AND per.reference_name IS NULL
#             """, (c.company, '%Debtors -%', doc.customer), as_dict=True)
#             for jour in journal:
#                 pay_journ = frappe.db.sql("""
#                     SELECT per.allocated_amount 
#                     FROM `tabPayment Entry Reference` AS per
#                     LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                     WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#                 """, (c.company, jour.name), as_dict=True)
#                 value_journ = sum(jo["allocated_amount"] for jo in pay_journ)
#                 if value_journ:
#                     value_journ = value_journ
#                 else:
#                     value_journ = 0
#                 if jour.credit_in_account_currency:
#                     journ_amount_credit = jour.credit_in_account_currency
#                     paid_amount += journ_amount_credit - value_journ
#                     in_amount -= journ_amount_credit - value_journ
#                     out_amount -= journ_amount_credit - value_journ
#                     age = date_diff(today(), jour.posting_date)
#                     if 0 <= age <= 30:
#                         age_0_30 -= (jour.credit_in_account_currency -value_journ)
#                     elif 31 <= age <= 60:
#                         age_31_60 -= (jour.credit_in_account_currency -value_journ)
#                     elif 61 <= age <= 90:
#                         age_61_90 -= (jour.credit_in_account_currency -value_journ)
#                     else:
#                         age_above_90 -= (jour.credit_in_account_currency -value_journ)
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 -= (jour.credit_in_account_currency -value_journ)
#                     # else:
#                     #     age_above_121 -= (jour.credit_in_account_currency -value_journ)
#                     combined_data.append({
#                         'posting_date': jour.posting_date,
#                         'name': jour.name,
#                         'po_no':'-',
#                         'grand_total': -jour.credit_in_account_currency,
#                         'paid_amount': 0,
#                         'credit_note': '-',
#                         'outstanding': -(jour.credit_in_account_currency-value_journ) or 0,
#                         'age': age,
#                         'oustanding_0_30':-(jour.credit_in_account_currency-value_journ) if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':-(jour.credit_in_account_currency-value_journ) if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':-(jour.credit_in_account_currency-value_journ) if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':-(jour.credit_in_account_currency-value_journ) if age > 90 else 0,
#                         # 'oustanding_91_120':-(jour.credit_in_account_currency-value_journ) if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':-(jour.credit_in_account_currency-value_journ) if age > 120 else 0,
#                     })
	
#                 elif jour.debit_in_account_currency:
#                     journ_amount_debit = jour.debit_in_account_currency
#                     in_amount += journ_amount_debit - value_journ
#                     out_amount += journ_amount_debit - value_journ
#                     age = date_diff(today(), jour.posting_date)

#                     if 0 <= age <= 30:
#                         age_0_30 += (jour.debit_in_account_currency -value_journ)
#                     elif 31 <= age <= 60:
#                         age_31_60 += (jour.debit_in_account_currency -value_journ)
#                     elif 61 <= age <= 90:
#                         age_61_90 += (jour.debit_in_account_currency -value_journ)
#                     else:
#                         age_above_90 += (jour.debit_in_account_currency -value_journ)
#                     # elif 91 <= age <= 120:
#                     #     age_91_120 += (jour.debit_in_account_currency -value_journ)
#                     # else:
#                     #     age_above_121 += (jour.debit_in_account_currency -value_journ)
	
#                     combined_data.append({
#                         'posting_date': jour.posting_date,
#                         'name': jour.name,
#                         'po_no':'-',
#                         'grand_total': jour.debit_in_account_currency,
#                         'paid_amount':value_journ or 0,
#                         'credit_note': 0,
#                         'outstanding': (jour.debit_in_account_currency -value_journ) or 0,
#                         'age': age,
#                         'oustanding_0_30':jour.debit_in_account_currency -value_journ if 0 <= age <= 30 else 0,
#                         'oustanding_31_60':jour.debit_in_account_currency -value_journ if 31 <= age <= 60 else 0,
#                         'oustanding_61_90':jour.debit_in_account_currency -value_journ if 61 <= age <= 90 else 0,
#                         'oustanding_above_90':jour.debit_in_account_currency -value_journ if age > 90 else 0,
#                         # 'oustanding_91_120':jour.debit_in_account_currency -value_journ if 91 <= age <= 120 else 0,
#                         # 'oustanding_above_121':jour.debit_in_account_currency -value_journ if age > 120 else 0,
#                     })
#     combined_data = sorted(combined_data, key=lambda x: x['posting_date'])
#     for entry in combined_data:
#         if entry['outstanding'] != 0:
#             data += f"""<tr style='font-size:10px'>
#             <td>{formatdate(entry['posting_date'],'dd-mm-yyyy')}</td>
#             <td>{entry['name']}</td>
#             <td>{entry['po_no']}</td>
#             <td>{fmt_money(round(entry['grand_total'], 2))}</td>
#             <td>{fmt_money(round(entry['paid_amount'], 2)) if entry['paid_amount']  else '-'}</td>
#             <td>{fmt_money(entry['credit_note'], 2) if entry['credit_note'] else '-'}</td>
#             <td>{fmt_money(round(entry['outstanding'], 2))}</td>
#             <td>{entry['age']}</td>
#             <td>{fmt_money(round(entry['oustanding_0_30'],2))}</td>
#             <td>{fmt_money(round(entry['oustanding_31_60'],2))}</td>
#             <td>{fmt_money(round(entry['oustanding_61_90'],2))}</td>
#             <td>{fmt_money(round(entry['oustanding_above_90'],2))}</td></tr>"""

#     # Final total row
#     data += f"<tr style='font-size:10px'><td></td><td></td><td><b>Total</b></td><td><b>{fmt_money(round(in_amount, 2))}</b></td><td><b>{fmt_money(round(paid_amount, 2))}</b></td><td><b>{fmt_money(round(credit_note, 2))}</b></td><td><b>{fmt_money(round(out_amount, 2))}</b></td><td></td><td><b>{fmt_money(round(age_0_30, 2))}</b></td><td><b>{fmt_money(round(age_31_60, 2))}</b></td><td><b>{fmt_money(round(age_61_90, 2))}</b></td><td><b>{fmt_money(round(age_above_90, 2))}</b></td></tr>"
#     data += "</table>"

#     data += "</table>"
#     return data

import json
import html
import frappe
from frappe.utils import today, date_diff, formatdate, fmt_money, cstr

# @frappe.whitelist()
# def ageing_report_test(doc):
#     if isinstance(doc, str):
#         doc = frappe._dict(json.loads(doc))

#     if not doc.get("company") or not doc.get("customer"):
#         return "<p style='color:red;'>Missing company or customer information.</p>"

#     # Inline the accounts_aging() logic here
#     args = frappe._dict({
#         "company": doc.company,
#         "customer": doc.customer
#     })
#     data_rows = get_accounts_aging_data(args)  # function defined below

#     if not data_rows or len(data_rows) <= 1:
#         # Always build the table
#         data = "<table border='1' width='100%' style='border-collapse:collapse;'>"
#         data += "<thead><tr style='font-size:12px;background-color:#0F0F5C;'>"
#         headers = [
#             "Posting Date", "Voucher No", "Customer LPO", "Invoiced Amount",
#             "Paid Amount", "Credit Note", "Outstanding Amount", "Age (Days)",
#             "0-30", "31-60", "61-90", "Above 90"
#         ]
#         for head in headers:
#             data += f"<td style='color:white; font-weight:bold; text-align:center'>{head}</td>"
#         data += "</tr></thead><tbody>"

#         # If no rows available, show "No data" row
#         if not data_rows or len(data_rows) == 0:
#             data += f"<tr><td colspan='{len(headers)}' style='text-align:center; font-size:12px; color:red;'>No Data Available</td></tr>"
#         else:
#             for row in data_rows[:-1]:  # all except total
#                 data += f"<tr style='font-size:10px'>"
#                 for cell in row:
#                     data += f"<td style='text-align:right'>{html.escape(str(cell))}</td>"
#                 data += "</tr>"

#             # Total row
#             total_row = data_rows[-1]
#             data += "<tr style='font-size:10px; font-weight:bold; background-color:#eaeaea;'>"
#             for i, cell in enumerate(total_row):
#                 align = "left" if i < 3 else "right"
#                 data += f"<td style='text-align:{align}'>{html.escape(str(cell))}</td>"
#             data += "</tr>"

#         data += "</tbody></table>"
#         return cstr(data)


#     # build HTML table
#     data = "<table border='1' width='100%' style='border-collapse:collapse;'>"
#     data += "<thead><tr style='font-size:12px;background-color:#0F0F5C;'>"
#     headers = [
#         "Posting Date", "Voucher No", "Customer LPO", "Invoiced Amount",
#         "Paid Amount", "Credit Note", "Outstanding Amount", "Age (Days)",
#         "0-30", "31-60", "61-90", "Above 90"
#     ]
#     for head in headers:
#         data += f"<td style='color:white; font-weight:bold; text-align:center'>{head}</td>"
#     data += "</tr></thead><tbody>"

#     for row in data_rows[:-1]:  # all except total
#         data += f"<tr style='font-size:10px'>"
#         for cell in row:
#             data += f"<td style='text-align:right'>{html.escape(str(cell))}</td>"
#         data += "</tr>"

#     # Total row
#     total_row = data_rows[-1]
#     data += "<tr style='font-size:10px; font-weight:bold; background-color:#eaeaea;'>"
#     for i, cell in enumerate(total_row):
#         align = "left" if i < 3 else "right"
#         data += f"<td style='text-align:right'>{html.escape(str(cell))}</td>"
#     data += "</tr>"

#     data += "</tbody></table>"

#     return cstr(data)

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



# import json
# import html
# import frappe
# from frappe.utils import today, date_diff, formatdate, fmt_money, cstr

# @frappe.whitelist()
# def ageing_report_test(doc):
#     if isinstance(doc, str):
#         doc = frappe._dict(json.loads(doc))

#     # if not doc.get("company") or not doc.get("customer"):
#     #     return "<p style='color:red;'>Missing company or customer information.</p>"

#     in_amount = paid_amount = credit_note = out_amount = 0
#     age_0_30 = age_31_60 = age_61_90 = age_above_90 = 0
#     combined_data = []

#     data = "<table border='1px solid black' width='100%'>"
#     data += "<thead><tr style='font-size:12px;background-color:#0F0F5C;'>"
#     data += "<td width=10%><p style=color:white;font-weight:bold>Posting Date</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Voucher No</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Customer LPO</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Invoiced Amount</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Paid Amount</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Credit Note</p></td>"
#     data += "<td width=10%><p style='text-align:center;color:white;font-weight:bold'>Outstanding Amount</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>Age (Days)</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>0-30</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>31-60</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>61-90</p></td>"
#     data += "<td width=5%><p style='text-align:center;color:white;font-weight:bold'>Above 90</p></td></tr></thead><tbody>"

#     companies = doc.company if isinstance(doc.company, list) else [doc.company]

#     for company in companies:
#         doc.company = company

#         si_list = frappe.db.sql("""
#             SELECT * FROM `tabSales Invoice` 
#             WHERE company = %s AND customer = %s AND docstatus = 1 
#             AND is_return = 0 AND custom_invoice_type='Credit' AND status != 'Paid' 
#             ORDER BY posting_date ASC
#         """, (company, doc.customer), as_dict=True)

#         for i in si_list:
#             return_amount = frappe.db.sql("""
#                 SELECT sum(grand_total) FROM `tabSales Invoice` 
#                 WHERE company = %s AND return_against = %s AND docstatus = 1
#             """, (company, i.name))[0][0] or 0

#             result_doc = frappe.db.sql("""
#                 SELECT name FROM `tabSales Invoice` 
#                 WHERE company = %s AND return_against = %s AND docstatus = 1
#             """, (company, i.name), as_dict=True)

#             pay_doc = frappe.db.sql("""
#                 SELECT per.allocated_amount 
#                 FROM `tabPayment Entry Reference` AS per
#                 LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                 WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#             """, (company, result_doc[0]["name"]), as_dict=True) if result_doc else []

#             pay = frappe.db.sql("""
#                 SELECT per.allocated_amount 
#                 FROM `tabPayment Entry Reference` AS per
#                 LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
#                 WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#             """, (company, i.name), as_dict=True)

#             value = sum(j["allocated_amount"] for j in pay) + sum(r["allocated_amount"] for r in pay_doc)

#             jv = frappe.db.sql("""
#                 SELECT credit_in_account_currency 
#                 FROM `tabJournal Entry Account` AS per
#                 LEFT JOIN `tabJournal Entry` AS pe ON per.parent = pe.name
#                 WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
#             """, (company, i.name), as_dict=True)

#             value += sum(k.credit_in_account_currency for k in jv)

#             if value and return_amount:
#                 outstanding = i.grand_total - value + return_amount
#             elif value:
#                 outstanding = i.grand_total - value
#             elif return_amount:
#                 outstanding = i.grand_total + return_amount
#             else:
#                 outstanding = i.grand_total

#             out_amount += outstanding
#             age = date_diff(today(), i.posting_date) if i.posting_date else 0

#             if round(outstanding) != 0:
#                 if value: paid_amount += value
#                 if return_amount: credit_note += return_amount
#                 in_amount += i.grand_total

#                 if 0 <= age <= 30: age_0_30 += outstanding
#                 elif 31 <= age <= 60: age_31_60 += outstanding
#                 elif 61 <= age <= 90: age_61_90 += outstanding
#                 else: age_above_90 += outstanding

#                 data += f"""<tr style='font-size:10px'>
#                     <td>{formatdate(i.posting_date, 'dd-mm-yyyy')}</td>
#                     <td>{html.escape(i.name)}</td>
#                     <td>{html.escape(i.po_no) if i.po_no else '-'}</td>
#                     <td>{fmt_money(round(i.grand_total, 2))}</td>
#                     <td>{fmt_money(round(value, 2)) if value else '-'}</td>
#                     <td>{fmt_money(return_amount, 2) if return_amount else '-'}</td>
#                     <td>{fmt_money(round(outstanding, 2))}</td>
#                     <td>{age}</td>
#                     <td>{fmt_money(round(outstanding, 2)) if 0 <= age <= 30 else '0.00'}</td>
#                     <td>{fmt_money(round(outstanding, 2)) if 31 <= age <= 60 else '0.00'}</td>
#                     <td>{fmt_money(round(outstanding, 2)) if 61 <= age <= 90 else '0.00'}</td>
#                     <td>{fmt_money(round(outstanding, 2)) if age > 90 else '0.00'}</td>
#                 </tr>"""

#         # You can add the same logic for returns, payments, and journal entries below if needed.

#     # Total Row
#     data += f"""<tr style='font-size:10px;font-weight:bold'>
#         <td colspan='3'>Total</td>
#         <td>{fmt_money(round(in_amount, 2))}</td>
#         <td>{fmt_money(round(paid_amount, 2))}</td>
#         <td>{fmt_money(round(credit_note, 2))}</td>
#         <td>{fmt_money(round(out_amount, 2))}</td>
#         <td></td>
#         <td>{fmt_money(round(age_0_30, 2))}</td>
#         <td>{fmt_money(round(age_31_60, 2))}</td>
#         <td>{fmt_money(round(age_61_90, 2))}</td>
#         <td>{fmt_money(round(age_above_90, 2))}</td>
#     </tr></tbody></table>"""

#     return cstr(data)


# @frappe.whitelist()
# def return_account_summary_total(from_date,to_date,account):
#     data = '<table border="1" style="border-collapse: collapse; width: 100%;">'
#     data += '<tr style="background-color: #0F0F5C;"><td colspan="1"><b></b></td><td colspan="1"><b></b></td>'
#     data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Opening</td>'
#     data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Movement</td>'
#     data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Closing</td></tr>'
	
#     data += '<tr style="background-color: lightgray; color: white;">'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Account Code</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Account Name</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td></tr>'
#     main_account = frappe.db.get_value("Account", account, ["name", "account_number"], as_dict=True)
#     if not main_account:
#         frappe.throw(f"Account '{account}' not found")
#     def get_all_accounts(account_code):
#         accounts = frappe.db.get_all("Account", filters={"parent_account": account_code, "disabled": 0}, fields=["name", "account_number"])
#         all_accounts = accounts[:]
#         for acc in accounts:
#             child_accounts = get_all_accounts(acc.name)  # Recursively fetch child accounts
#             all_accounts.extend(child_accounts)
#         return all_accounts

#     accounts = [main_account] + get_all_accounts(account)
#     # accounts = frappe.db.get_all("Account", filters={"parent_account": account, "disabled": 0}, fields=["name","account_number"])
#     total_op_debit = total_op_credit = t_c_credit = t_p_credit = t_c_debit = t_p_debit = 0
#     for acc in accounts:
#         gle = frappe.db.sql("""
#         SELECT sum(debit) as debit_amount, sum(credit) as credit_amount
#         FROM `tabGL Entry` 
#         WHERE account = %s and posting_date < %s and is_opening = 'No'
#         and is_cancelled = 0
#         """, (acc.name,from_date), as_dict=True)
#         for g in gle:
#             g.debit_amount = g.debit_amount or 0
#             g.credit_amount = g.credit_amount or 0
#             t_p_debit += g.debit_amount
#             t_p_credit += g.credit_amount
			
#             sq = frappe.db.sql("""
#             SELECT sum(debit_in_account_currency) as debit, sum(credit_in_account_currency) as credit 
#             FROM `tabGL Entry` 
#             WHERE account = %s AND posting_date BETWEEN %s AND %s AND is_opening = 'No' AND is_cancelled = 0
#             """, (acc.name, from_date, to_date), as_dict=True)
			
#             for i in sq:
#                 i.credit = i.credit or 0
#                 i.debit = i.debit or 0
#                 op_credit = g.credit_amount + i.credit
#                 op_debit = g.debit_amount + i.debit
#                 total_op_debit += i.debit
#                 total_op_credit += i.credit
#                 t_c_credit += op_credit
#                 t_c_debit += op_debit
				
#                 if g.debit_amount or g.credit_amount or i.credit or i.debit:
#                     data += '<tr><td>%s</td><td>%s</td><td style="text-align:right">%s</td><td style="text-align:right">%s</td>' % (
#                         acc.account_number or '-', acc.name, fmt_money(g.debit_amount), fmt_money(g.credit_amount))
#                     data += '<td style="text-align:right">%s</td><td style="text-align:right">%s</td>' % (
#                         fmt_money(i.debit), fmt_money(i.credit))
#                     data += '<td style="text-align:right">%s</td><td style="text-align:right">%s</td></tr>' % (
#                         fmt_money(op_debit), fmt_money(op_credit))
	
#     data += '<tr style="text-align:right; font-weight:bold;"><td colspan = 2 style="text-align:center; font-weight:bold;">Total</td>'
#     data += '<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
#         fmt_money(t_p_debit), fmt_money(t_p_credit),
#         fmt_money(total_op_debit), fmt_money(total_op_credit),
#         fmt_money(t_c_debit), fmt_money(t_c_credit))
#     data += '</table>'
#     return data

# @frappe.whitelist()
# def return_account_summary_total(from_date, to_date, account=None, company=None):
#     data = '<table border="1" style="border-collapse: collapse; width: 100%;">'
#     data += '<tr style="background-color: #0F0F5C;"><td colspan="1"><b></b></td><td colspan="1"><b></b></td>'
#     data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Opening</td>'
#     data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Movement</td>'
#     data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Closing</td></tr>'

#     data += '<tr style="background-color: lightgray; color: white;">'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Account Code</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Account Name</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td></tr>'

#     if account:
#         main_account = frappe.db.get_value("Account", account, ["name", "account_number"], as_dict=True)
#         if not main_account:
#             frappe.throw(f"Account '{account}' not found")

#         def get_all_accounts(account_code):
#             accounts = frappe.db.get_all("Account", filters={"parent_account": account_code, "disabled": 0}, fields=["name", "account_number"])
#             all_accounts = accounts[:]
#             for acc in accounts:
#                 child_accounts = get_all_accounts(acc["name"])
#                 all_accounts.extend(child_accounts)
#             return all_accounts

#         accounts = [main_account] + get_all_accounts(account)
#     else:
#         accounts = frappe.db.get_all(
#             "Account",
#             filters={"is_group": 0, "disabled": 0, "company": company},
#             fields=["name", "account_number"]
#         )

#     total_op_debit = total_op_credit = t_c_credit = t_p_credit = t_c_debit = t_p_debit = 0

#     for acc in accounts:
#         # Opening Balance (before from_date)
#         gle = frappe.db.sql("""
#             SELECT SUM(debit) AS debit_amount, SUM(credit) AS credit_amount
#             FROM `tabGL Entry`
#             WHERE account = %s AND posting_date < %s AND is_opening = 'No' AND is_cancelled = 0 AND company = %s
#         """, (acc.name, from_date, company), as_dict=True)

#         for g in gle:
#             g.debit_amount = g.debit_amount or 0
#             g.credit_amount = g.credit_amount or 0
#             t_p_debit += g.debit_amount
#             t_p_credit += g.credit_amount

#             # Movement within date range
#             sq = frappe.db.sql("""
#                 SELECT SUM(debit_in_account_currency) AS debit, SUM(credit_in_account_currency) AS credit
#                 FROM `tabGL Entry`
#                 WHERE account = %s AND posting_date BETWEEN %s AND %s
#                 AND is_opening = 'No' AND is_cancelled = 0 AND company = %s
#             """, (acc.name, from_date, to_date, company), as_dict=True)

#             for i in sq:
#                 i.credit = i.credit or 0
#                 i.debit = i.debit or 0
#                 op_credit = g.credit_amount + i.credit
#                 op_debit = g.debit_amount + i.debit
#                 total_op_debit += i.debit
#                 total_op_credit += i.credit
#                 t_c_credit += op_credit
#                 t_c_debit += op_debit

#                 if g.debit_amount or g.credit_amount or i.credit or i.debit:
#                     data += f'<tr><td>{acc.account_number or "-"}</td><td>{acc.name}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(g.debit_amount)}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(g.credit_amount)}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(i.debit)}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(i.credit)}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(op_debit)}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(op_credit)}</td></tr>'

#     data += '<tr style="text-align:right; font-weight:bold;"><td colspan="2" style="text-align:center;">Total</td>'
#     data += f'<td>{fmt_money(t_p_debit)}</td><td>{fmt_money(t_p_credit)}</td>'
#     data += f'<td>{fmt_money(total_op_debit)}</td><td>{fmt_money(total_op_credit)}</td>'
#     data += f'<td>{fmt_money(t_c_debit)}</td><td>{fmt_money(t_c_credit)}</td></tr>'
#     data += '</table>'

#     return data

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


# @frappe.whitelist()
# def return_account_summary_total(from_date, to_date, account=None,company):
#     data = '<table border="1" style="border-collapse: collapse; width: 100%;">'
#     data += '<tr style="background-color: #0F0F5C;"><td colspan="1"><b></b></td><td colspan="1"><b></b></td>'
#     data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Opening</td>'
#     data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Movement</td>'
#     data += '<td colspan="2" style="text-align:center;color:white;font-weight:bold;">Closing</td></tr>'

#     data += '<tr style="background-color: lightgray; color: white;">'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Account Code</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Account Name</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Debit</td>'
#     data += '<td style="text-align:center; font-weight:bold; color:black;">Credit</td></tr>'
#     if account:
#         main_account = frappe.db.get_value("Account", account, ["name", "account_number"], as_dict=True)
#         if not main_account:
#             frappe.throw(f"Account '{account}' not found")

#         def get_all_accounts(account_code):
#             accounts = frappe.db.get_all("Account", filters={"parent_account": account_code, "disabled": 0}, fields=["name", "account_number"])
#             all_accounts = accounts[:]
#             for acc in accounts:
#                 child_accounts = get_all_accounts(acc["name"])
#                 all_accounts.extend(child_accounts)
#             return all_accounts

#         accounts = [main_account] + get_all_accounts(account)
#     else:
#         accounts = frappe.db.get_all(
#             "Account",
#             filters={"is_group": 0, "disabled": 0},
#             fields=["name", "account_number"]
#         )
#     total_op_debit = total_op_credit = t_c_credit = t_p_credit = t_c_debit = t_p_debit = 0

#     for acc in accounts:
#         gle = frappe.db.sql("""
#             SELECT sum(debit) as debit_amount, sum(credit) as credit_amount
#             FROM `tabGL Entry` 
#             WHERE account = %s and posting_date < %s and is_opening = 'No'
#             and is_cancelled = 0
#         """, (acc.name, from_date), as_dict=True)

#         for g in gle:
#             g.debit_amount = g.debit_amount or 0
#             g.credit_amount = g.credit_amount or 0
#             t_p_debit += g.debit_amount
#             t_p_credit += g.credit_amount

#             sq = frappe.db.sql("""
#                 SELECT sum(debit_in_account_currency) as debit, sum(credit_in_account_currency) as credit 
#                 FROM `tabGL Entry` 
#                 WHERE account = %s AND posting_date BETWEEN %s AND %s AND is_opening = 'No' AND is_cancelled = 0
#             """, (acc.name, from_date, to_date), as_dict=True)

#             for i in sq:
#                 i.credit = i.credit or 0
#                 i.debit = i.debit or 0
#                 op_credit = g.credit_amount + i.credit
#                 op_debit = g.debit_amount + i.debit
#                 total_op_debit += i.debit
#                 total_op_credit += i.credit
#                 t_c_credit += op_credit
#                 t_c_debit += op_debit

#                 if g.debit_amount or g.credit_amount or i.credit or i.debit:
#                     data += f'<tr><td>{acc.account_number or "-"}</td><td>{acc.name}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(g.debit_amount)}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(g.credit_amount)}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(i.debit)}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(i.credit)}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(op_debit)}</td>'
#                     data += f'<td style="text-align:right">{fmt_money(op_credit)}</td></tr>'

#     data += '<tr style="text-align:right; font-weight:bold;"><td colspan = 2 style="text-align:center;">Total</td>'
#     data += f'<td>{fmt_money(t_p_debit)}</td><td>{fmt_money(t_p_credit)}</td>'
#     data += f'<td>{fmt_money(total_op_debit)}</td><td>{fmt_money(total_op_credit)}</td>'
#     data += f'<td>{fmt_money(t_c_debit)}</td><td>{fmt_money(t_c_credit)}</td></tr>'
#     data += '</table>'

#     return data



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

# @frappe.whitelist()
# def get_sales_person(doc, name, from_date, to_date, company, sales_person_user):
#     data = "<table width=100% border=1px solid black><tr style='background-color:#0F0F5C;font-size:12px;text-align:center;'>"
#     data += "<td><b style='color:white;'>SL.NO</b></td><td colspan='2'><b style='color:white;'>Date</b></td><td><b style='color:white;'>Invoice Number</b></td>"
#     data += "<td><b style='color:white;'>Customer Name</b></td><td><b style='color:white;'>LPO NO</b></td><td><b style='color:white;'>Gross Amount</b></td>"
#     data += "<td><b style='color:white;'>Discount</b></td><td style=width:10%><b style='color:white;'>Ret. Amount</b></td><td style=width:10%><b style='color:white;'>Net</b></td>"
#     data += "<td><b style='color:white;'>Collected</b></td><td><b style='color:white;'>Balance</b></td></tr>"
#     if not doc.company and not sales_person_user:
#         sales_person = frappe.get_all("Sales Person", fields=["name"])
#         for s in sales_person:
#             data += get_sales_data_by_salesperson(s.name, from_date, to_date)
	
#     elif not doc.company and sales_person_user:
#         data += get_sales_data_by_salesperson(sales_person_user, from_date, to_date)

#     # CASE 3: Company provided, but no salesperson —> All salespersons in one company
#     elif doc.company and not sales_person_user:
#         sales_person = frappe.get_all("Sales Person", fields=["name"])
#         for s in sales_person:
#             data += get_sales_data_by_salesperson(s.name, from_date, to_date, doc.company)

#     # CASE 4: Both company and salesperson provided —> That salesperson's data in one company
#     else:
#         data += get_sales_data_by_salesperson(sales_person_user, from_date, to_date, doc.company)

#     data += "</table>"
#     return data





# def get_sales_data_by_salesperson(sales_person_user, from_date, to_date, company=None):
#     data = ""
#     j = 1
#     company_totals = {}
#     salesperson_totals = {
#         "total": 0,
#         "discount_amount": 0,
#         "convert_float": 0,
#         "net_total": 0,
#         "collected_total": 0,
#         "balance": 0
#     }

#     company_filter = {"custom_sales_personuser": sales_person_user, "posting_date": ("between", (from_date, to_date)), "docstatus": ("not in", [0, 2])}
#     if company:
#         company_filter["company"] = company

#     sales_invoice = frappe.get_all("Sales Invoice", filters=company_filter,
#                                    fields=["name", "customer", "total", "discount_amount", "posting_date", "outstanding_amount", "po_no", "company"],
#                                    order_by="posting_date")

#     if not sales_invoice:
#         data += f'<tr><td colspan="12" style="border: 1px solid black; background-color:lightgray;"><b style="color:black;font-size:12px">{sales_person_user}</b></td></tr>'
#         data += f'<tr style="font-size:12px;text-align:left;"><td colspan="6"><b>{company}</b></td>'
#         data += '<td style="text-align:right;"></td><td style="text-align:right;"></td><td style="text-align:right;"></td>'
#         data += '<td style="text-align:right;"></td><td style="text-align:right;"></td><td style="text-align:right;"></td></tr>'
#         data += f'<tr style="font-size:12px;text-align:left;"><td colspan="6"><b>Total for {sales_person_user}</b></td>'
#         data += '<td style="text-align:right;">0.00</td><td style="text-align:right;">0.00</td><td style="text-align:right;">0.00</td>'
#         data += '<td style="text-align:right;">0.00</td><td style="text-align:right;">0.00</td><td style="text-align:right;">0.00</td></tr>'
#         return data

		

#     data += f'<tr><td colspan="12" style="border: 1px solid black; background-color:lightgray;"><b style="color:black;font-size:12px">{sales_person_user}</b></td></tr>'

#     prev_company = None
#     for i in sales_invoice:
#         comp = i.company
#         if prev_company != comp:
#             data += f'<tr><td colspan="12" style="border: 1px solid black; background-color:lightgray;"><b style="color:black;font-size:12px">{comp}</b></td></tr>'
#             prev_company = comp

#         net = i.total - i.discount_amount
#         convert_float = int(i.total - net)
#         net_int = int(net)
#         collected = net - i.outstanding_amount
#         collected_int = int(collected)

#         data += f'<tr style="font-size:12px;">'
#         data += f'<td>{j}</td><td colspan="2" nowrap>{i.posting_date.strftime("%d-%m-%Y")}</td><td>{i.name}</td>'
#         data += f'<td>{i.customer}</td><td>{i.po_no}</td><td style="text-align:right;">{i.total}</td><td style="text-align:right;">{i.discount_amount}</td>'
#         data += f'<td style="text-align:right;">{convert_float}</td><td style="text-align:right;">{net_int}</td><td style="text-align:right;">{collected_int}</td><td style="text-align:right;">{i.outstanding_amount}</td></tr>'

#         if comp not in company_totals:
#             company_totals[comp] = {
#                 "total": 0, "discount_amount": 0, "convert_float": 0, "net_total": 0,
#                 "collected_total": 0, "balance": 0
#             }

#         company_totals[comp]["total"] += i.total
#         company_totals[comp]["discount_amount"] += i.discount_amount
#         company_totals[comp]["convert_float"] += convert_float
#         company_totals[comp]["net_total"] += net_int
#         company_totals[comp]["collected_total"] += collected_int
#         company_totals[comp]["balance"] += i.outstanding_amount

#         salesperson_totals["total"] += i.total
#         salesperson_totals["discount_amount"] += i.discount_amount
#         salesperson_totals["convert_float"] += convert_float
#         salesperson_totals["net_total"] += net_int
#         salesperson_totals["collected_total"] += collected_int
#         salesperson_totals["balance"] += i.outstanding_amount

#         j += 1

#     # Print total for each company
#     for comp, totals in company_totals.items():
#         data += f'<tr style="font-size:12px"><td colspan="6" style="border: 1px solid black;"><b>Total for {comp}</b></td>'
#         data += f'<td style="text-align:right;">{round(totals["total"], 2)}</td><td style="text-align:right;">{round(totals["discount_amount"], 2)}</td>'
#         data += f'<td style="text-align:right;">{round(totals["convert_float"], 2)}</td><td style="text-align:right;">{round(totals["net_total"], 2)}</td>'
#         data += f'<td style="text-align:right;">{round(totals["collected_total"], 2)}</td><td style="text-align:right;">{round(totals["balance"], 2)}</td></tr>'

#     # Print total for this salesperson
#     data += f'<tr style="font-size:12px"><td colspan="6" style="border: 1px solid black;"><b>Total for {sales_person_user}</b></td>'
#     data += f'<td style="text-align:right;">{round(salesperson_totals["total"], 2)}</td><td style="text-align:right;">{round(salesperson_totals["discount_amount"], 2)}</td>'
#     data += f'<td style="text-align:right;">{round(salesperson_totals["convert_float"], 2)}</td><td style="text-align:right;">{round(salesperson_totals["net_total"], 2)}</td>'
#     data += f'<td style="text-align:right;">{round(salesperson_totals["collected_total"], 2)}</td><td style="text-align:right;">{round(salesperson_totals["balance"], 2)}</td></tr>'

#     return data

#completed
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

#completed
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




# @frappe.whitelist()
# def margin_tool(item_details, discount=None, per=None,total=None,tax=None):
#     import json
#     item_details = json.loads(item_details)

#     data = ''
#     data += '''
#     <br>
#     <table style="border-collapse:collapse;">
#         <style>
#             table, tr, td, th {
#                 padding:5px;
#                 border: 1px solid black;
#                 font-size:11px;
#             }
#             td { text-align:left; }
#         </style>
#     '''

#     data += '''
#     <tr>
#         <th colspan="10" style="padding:1px;font-size:14px;background-color:#75506A;color:white;text-align:center;">
#             <b>ITEM DETAILS</b>
#         </th>
#     </tr>
#     <tr style="background-color:lightgrey">
#         <td width="40px"  style="text-align:center;"><b>S#</b></td>
#         <td width="250px" style="text-align:center;"><b>ITEM NAME</b></td>
#         <td width="300px" style="text-align:center;"><b>DESCRIPTION</b></td>

#         <td width="65px"  style="text-align:center;"><b>QTY</b></td>
#         <td width="65px"  style="text-align:center;"><b>UOM</b></td>
#         <td width="65px"  style="text-align:center;"><b>DISC %</b></td>
#         <td width="65px"  style="text-align:center;"><b>DISC.RATE</b></td>
#         <td width="65px"  style="text-align:center;"><b>DISC.AMT</b></td>
#         <td width="65px"  style="text-align:center;"><b>UNIT RATE</b></td>
#         <td width="65px"  style="text-align:center;"><b>AMOUNT</b></td>
#     </tr>
#     '''

#     dis = 0
#     amount = 0
#     discount = float(discount) if discount else 0.0
#     per = float(per) if per else 0.0
#     total = float(total) if total else 0.0
#     tax = float(tax) if tax else 0.0
#     for idx, i in enumerate(item_details, start=1):
#         dis += i["discount_amount"]
#         amount += i["amount"]

#         data += '''
#         <tr>
#             <td style="text-align:center;">{}</td>
#             <td>{}</td>
#             <td>{}</td>
#             <td style="text-align:right;">{}</td>
#             <td>{}</td>
#             <td style="text-align:right;">{}</td>
#             <td style="text-align:right;">{:.2f}</td>
#             <td style="text-align:right;">{:.2f}</td>
#             <td style="text-align:right;">{:.2f}</td>
#             <td style="text-align:right;">{:.2f}</td>
#         </tr>
#         '''.format(
#             idx,
#             i["item_name"],
#             i["description"],
#             i["qty"],
#             i["uom"],
#             i["discount_percentage"],
#             i["discount_rate"],
#             i["discount_amount"],
#             i["rate"],
#             i["amount"]
#         )

#     data += '''
#     <tr>
#         <td colspan="7" style="text-align:right;"><b>Total</b></td>
#         <td style="text-align:right;"><b>{:.2f}</b></td>
#         <td></td>
#         <td style="text-align:right;"><b>{:.2f}</b></td>
#     </tr>
#     <tr>
#         <td colspan="9" style="text-align:right;"><b>Additional Percentage</b></td>
#         <td style="text-align:right;"><b>{:.2f}</b></td>
#     </tr>
#     <tr>
#         <td colspan="9" style="text-align:right;"><b>Additional Discount</b></td>
#         <td style="text-align:right;"><b>{:.2f}</b></td>
#     </tr>
#     <tr>
#         <td colspan="9" style="text-align:right;"><b>Tax</b></td>
#         <td style="text-align:right;"><b>{:.2f}</b></td>
#     </tr>
#     <tr>
#         <td colspan="9" style="text-align:right;"><b>Net Total</b></td>
#         <td style="text-align:right;"><b>{:.2f}</b></td>
#     </tr>
	
#     </table>
#     '''.format(dis, amount, per, discount,tax,total)

#     return data

#completed
@frappe.whitelist()
def margin_tool(item_details, discount=None, per=None,total=None,tax=None):
	import json
	item_details = json.loads(item_details)

	data = ''
	data += """
		<br>
		<style>
			.margin-table {
				width: 100%;
				border-collapse: collapse;
				font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
				font-size: 12px;
				color: #333;
			}

			.margin-table th,
			.margin-table td {
				padding: 6px 8px;
				border: 1px solid #dcdcdc;
			}

			.margin-table thead th {
				background: linear-gradient(135deg, #75506A, #9A6C87);
				color: #fff;
				text-align: center;
				font-size: 13px;
				font-weight: 600;
			}

			.margin-table thead tr.title th {
				font-size: 15px;
				padding: 8px;
			}

			.margin-table tbody tr:nth-child(even) {
				background-color: #f9f9f9;
			}

			.margin-table tbody tr:hover {
				background-color: #f1edf0;
			}

			.text-right {
				text-align: right;
			}

			.text-center {
				text-align: center;
			}

			.summary-row td {
				font-weight: 600;
				background-color: #f4f4f4;
			}

			.net-total td {
				font-size: 13px;
				background-color: #75506A;
				color: #fff;
				font-weight: 700;
			}
			
		</style>

		<table class="margin-table">
			<thead>
				<tr class="title">
					<th colspan="10">ITEM DETAILS</th>
				</tr>
				<tr style="background: #e6e6e6; color: #333;">
					<th width="40" style="background: #e6e6e6; color: #333;">S#</th>
					<th width="250" style="background: #e6e6e6; color: #333;">Item Name</th>
					<th width="300" style="background: #e6e6e6; color: #333;">Description</th>
					<th width="70" style="background: #e6e6e6; color: #333;">Qty</th>
					<th width="70" style="background: #e6e6e6; color: #333;">UOM</th>
					<th width="70" style="background: #e6e6e6; color: #333;">Disc %</th>
					<th width="80" style="background: #e6e6e6; color: #333;">Disc Rate</th>
					<th width="90" style="background: #e6e6e6; color: #333;">Disc Amt</th>
					<th width="80" style="background: #e6e6e6; color: #333;">Unit Rate</th>
					<th width="90" style="background: #e6e6e6; color: #333;">Amount</th>
				</tr>
			</thead>
			<tbody>
		"""

	dis = 0
	amount = 0
	discount = float(discount) if discount else 0.0
	per = float(per) if per else 0.0
	total = float(total) if total else 0.0
	tax = float(tax) if tax else 0.0
	for idx, i in enumerate(item_details, start=1):
		dis += i["discount_amount"]
		amount += i["amount"]

		data += '''
		<tr>
			<td style="text-align:center;">{}</td>
			<td>{}</td>
			<td>{}</td>
			<td style="text-align:right;">{}</td>
			<td>{}</td>
			<td style="text-align:right;">{}</td>
			<td style="text-align:right;">{:.2f}</td>
			<td style="text-align:right;">{:.2f}</td>
			<td style="text-align:right;">{:.2f}</td>
			<td style="text-align:right;">{:.2f}</td>
		</tr>
		'''.format(
			idx,
			i["item_name"],
			i["description"],
			i["qty"],
			i["uom"],
			i["discount_percentage"],
			i["discount_rate"],
			i["discount_amount"],
			i["rate"],
			i["amount"]
		)

	data += """
		<tr class="summary-row">
			<td colspan="7" class="text-right">Total</td>
			<td class="text-right">{:.2f}</td>
			<td></td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="summary-row">
			<td colspan="9" class="text-right">Additional Percentage</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="summary-row">
			<td colspan="9" class="text-right">Additional Discount</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="summary-row">
			<td colspan="9" class="text-right">Tax</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="net-total">
			<td colspan="9" class="text-right">Net Total</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		</tbody>
		</table>
		""".format(dis, amount, per, discount, tax, total)
	return data


#completed
from frappe.utils import flt
from frappe.utils import flt
@frappe.whitelist()
def get_detail_so(item_code, company):
	date = frappe.db.get_value("Custom Settings", "Custom Settings", "date")
	so_details = []
	
	sa = frappe.db.sql("""
		SELECT `tabSales Order Item`.parent AS parent,
			SUM(`tabSales Order Item`.qty) AS qty,
			`tabSales Order Item`.delivered_qty AS delivered_qty
		FROM `tabSales Order`
		LEFT JOIN `tabSales Order Item` ON `tabSales Order`.name = `tabSales Order Item`.parent
		WHERE `tabSales Order Item`.item_code = '%s'
		AND `tabSales Order`.docstatus != 2
		AND `tabSales Order`.company = '%s'
		AND `tabSales Order`.transaction_date >= '%s'
		GROUP BY `tabSales Order Item`.parent
		ORDER BY `tabSales Order`.transaction_date
	""" % (item_code, company, date), as_dict=True)
	sa_names = {i.parent for i in sa}
	for i in sa:
		reser_qty = frappe.db.sql("""
			SELECT SUM(reserved_qty) AS total_reserved_qty
			FROM `tabStock Reservation Entry`
			WHERE voucher_no = '%s'
			AND docstatus = 1
			AND item_code = '%s'
			AND status IN ('Reserved', 'Partially Reserved')
		""" % (i.parent, item_code), as_dict=True)[0].total_reserved_qty or 0

		prq = frappe.db.sql("""
			SELECT (reserved_qty - delivered_qty) AS partially_delivered
			FROM `tabStock Reservation Entry`
			WHERE item_code = '%s' AND voucher_no = '%s' AND status = 'Partially Delivered'
		""" % (item_code, i.parent), as_dict=True)
		
		if prq:
			reser_qty = flt(prq[0]['partially_delivered']) or 0
		
		i.qty = i.qty or 0
		i.delivered_qty = i.delivered_qty or 0
		pending_qty = i.qty - i.delivered_qty
		sb = frappe.get_doc("Sales Order", i.parent)

		so_details.append(frappe._dict({
			"parent": i.parent,
			"qty": i.qty,
			"reserved_qty": reser_qty,
			"pending_qty": pending_qty,
			"rate": i.rate,
			"delivered_qty": i.delivered_qty,
			"transaction_date": sb.transaction_date,
			"customer": sb.customer,
			"po_no": sb.po_no,
			# "status": sb.custom_reservation_status
		}))
	
	additional_entries = frappe.db.sql("""
		SELECT 
			`tabStock Reservation Entry`.voucher_no AS voucher_no,
			`tabStock Reservation Entry`.reserved_qty,
			`tabSales Order`.transaction_date,
			`tabSales Order`.customer,
			`tabSales Order`.po_no
		FROM `tabStock Reservation Entry`
		LEFT JOIN `tabSales Order` ON `tabSales Order`.name = `tabStock Reservation Entry`.voucher_no
		LEFT JOIN `tabSales Order Item` ON `tabSales Order Item`.parent = `tabSales Order`.name
		WHERE `tabStock Reservation Entry`.item_code = %s
		AND  `tabStock Reservation Entry`.status IN ('Reserved', 'Partially Reserved')
		AND (`tabSales Order Item`.item_code != %s OR `tabSales Order Item`.item_code IS NULL)
		AND (`tabSales Order`.name IS NULL 
			OR (`tabSales Order`.docstatus != 2 
				AND `tabSales Order`.company = %s 
				AND `tabSales Order`.transaction_date >= %s))
		GROUP BY `tabStock Reservation Entry`.voucher_no
		ORDER BY `tabStock Reservation Entry`.creation
	""", (item_code, item_code, company, date), as_dict=True)

#  `tabSales Order`.custom_reservation_status   

	for entry in additional_entries:
		if entry.voucher_no not in sa_names:
			so_details.append(frappe._dict({
				"parent": entry.voucher_no,
				"qty": 0,  
				"reserved_qty": entry.reserved_qty or 0,
				"pending_qty": 0,  
				"rate": 0,  
				"delivered_qty": 0,
				"transaction_date": entry.transaction_date, 
				"customer": entry.customer, 
				"po_no": entry.po_no, 
				# "status": entry.custom_reservation_status
			}))
	
	return so_details

#completed
@frappe.whitelist()
def get_detail_po(item_code,company):
	date = frappe.db.get_value("Custom Settings","Custom Settings","date")
	po_details = []
	bal_qty = 0
	# pending_qty = 0
	sa = frappe.db.sql(""" select `tabPurchase Order Item`.parent as parent,`tabPurchase Order Item`.qty as qty from `tabPurchase Order`
	left join `tabPurchase Order Item` on `tabPurchase Order`.name = `tabPurchase Order Item`.parent
	where `tabPurchase Order Item`.item_code = '%s' and `tabPurchase Order`.docstatus = 1 and `tabPurchase Order`.company = '%s' and `tabPurchase Order`.transaction_date >= '%s'  order by transaction_date""" %(item_code,company,date),as_dict=True)
	for i in sa:
	# 	pending_qty = i.qty - i.delivered_qty
		pos = frappe.db.sql("""select sum(`tabPurchase Receipt Item`.received_qty) as received_qty from `tabPurchase Receipt`
		left join `tabPurchase Receipt Item` on `tabPurchase Receipt`.name = `tabPurchase Receipt Item`.parent
		where `tabPurchase Receipt Item`.item_code = '%s' and `tabPurchase Receipt Item`.purchase_order = '%s' and `tabPurchase Receipt`.company = '%s'  and `tabPurchase Receipt`.docstatus = 1 """ % (item_code,i.parent,company), as_dict=True)
		req=0
		for j in pos:
			req=j.received_qty
		po = frappe.db.get_value("Item Inspection",{"po_number":i.parent,"item_code":item_code},["sample"])
		if not po:
			po = 0
		if not req:
			req =0
		bal_qty = i.qty - req
		bal = 0
		if bal_qty >0:
			bal = bal_qty
		sb = frappe.get_doc("Purchase Order", i.parent)
		po_details.append(frappe._dict({"mr":req,"qc":po,"parent":i.parent,"qty":i.qty,"bal_qty":bal,"transaction_date":sb.transaction_date,"supplier":sb.supplier}))
	return po_details

#completed
@frappe.whitelist()
def get_item_price_dt(item_code):
	# item_code = "114-40002104GY"
	use = frappe.session.user
	role = frappe.get_roles(use)
	data = []
	row = []
	user = frappe.get_all("User Permission",{"user":use,"allow":"Price List"},["*"])
	item = frappe.get_all("Item",{"name":item_code},["*"])
	for i in item:
		if "Cost Viewer" in role:
			std = frappe.get_value("Item Price",{"item_code":i.item_code,"price_list":"STANDARD BUYING-USD"},["price_list_rate"])
			if std:
				row.append(frappe._dict({"price_list":"STANDARD BUYING-USD","price_list_rate":std}))
			if not std:
				std = 0
				row.append(frappe._dict({"price_list":"STANDARD BUYING-USD","price_list_rate":std}))
		for s in user:
			item = frappe.db.sql(""" select price_list_rate from `tabItem Price` where price_list = '%s' and item_code = '%s' """%(s.for_value,i.item_code),as_dict=True)
			if item:
				row.append(frappe._dict({"price_list":s.for_value,"price_list_rate":item[0]["price_list_rate"]}))
		data.append(row)
	return data	

@frappe.whitelist()
def get_woff_ded(sdate, edate, emp):
	"""Weekly-off (weekend) deduction for Annual Vacation boundary weeks.

	Working week is Sunday-Thursday. For every approved Annual Vacation
	leave, only the two boundary weekends are checked:

	  - the weekend closing the work-week containing the leave's first
	    working day (its start week)
	  - the weekend closing the work-week containing the leave's last
	    working day (its end week)

	Each boundary weekend is deducted in the payroll period that contains
	it - so a leave starting on Aug 30 deducts its start-weekend (Sep 4-5)
	in the September slip, and a leave ending Sep 30 deducts its
	end-weekend (Oct 2-3) in the October slip.

	A boundary weekend is unpaid when the employee has fewer than 3
	"present" days in the preceding work-week. A day counts as present
	when:
	  - it is a national holiday (holiday list entry with weekly_off = 0), or
	  - attendance is Present / Work From Home (Half Day counts 0.5), or
	  - the day is On Leave under a Leave Type with "Include Weekend"
	    (custom_include_weekend) checked, or
	  - no attendance exists and Payroll Settings treats unmarked days as
	    Present.

	Only weekend days falling inside [sdate, edate] are deducted, so a
	weekend belonging to the next payroll period (e.g. Oct 2-3 for a leave
	ending Sep 30) is picked up by that period's salary slip instead.
	"""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	sdate, edate = getdate(sdate), getdate(edate)
	window_start = add_days(sdate, -10)

	leaves = frappe.get_all(
		"Leave Application",
		filters={
			"employee": emp,
			"leave_type": "Annual Vacation",
			"docstatus": 1,
			"status": "Approved",
			"from_date": ["<=", edate],
			"to_date": [">=", window_start],
		},
		fields=["from_date", "to_date"],
	)
	if not leaves:
		return 0

	# --- weekly-off days + national holidays from the employee's holiday list
	try:
		holiday_list = get_holiday_list_for_employee(emp, raise_exception=False)
	except Exception:
		holiday_list = None

	off_dates, holidays = set(), set()
	if holiday_list:
		for h in frappe.get_all(
			"Holiday",
			filters={
				"parent": holiday_list,
				"holiday_date": ["between", [window_start, edate]],
			},
			fields=["holiday_date", "weekly_off"],
		):
			(off_dates if cint(h.weekly_off) else holidays).add(getdate(h.holiday_date))

	if not off_dates:
		# no weekly-offs configured; fall back to Friday + Saturday
		d = window_start
		while d <= edate:
			if d.weekday() in (4, 5):
				off_dates.add(d)
			d = add_days(d, 1)

	# group weekly-off dates into consecutive blocks (e.g. Fri+Sat)
	blocks = []
	for d in sorted(off_dates):
		if blocks and blocks[-1][-1] == add_days(d, -1):
			blocks[-1].append(d)
		else:
			blocks.append([d])

	# boundary weekends = the off-blocks closing the work-weeks containing
	# the leave's first and last working days (skips weekly-off days when
	# the leave boundary itself falls on a weekend).
	target_blocks = []
	seen = set()
	for leave in leaves:
		start_work = getdate(leave.from_date)
		while start_work in off_dates:
			start_work = add_days(start_work, 1)
		end_work = getdate(leave.to_date)
		while end_work in off_dates:
			end_work = add_days(end_work, -1)

		for bound in (start_work, end_work):
			block = next((b for b in blocks if b[-1] >= bound), None)
			if block and block[0] not in seen:
				seen.add(block[0])
				target_blocks.append(block)

	if not target_blocks:
		return 0

	# --- present-day evaluation data
	doj, relieving_date = frappe.db.get_value(
		"Employee", emp, ["date_of_joining", "relieving_date"]
	)
	doj = getdate(doj) if doj else None
	relieving_date = getdate(relieving_date) if relieving_date else None

	attendance = {
		getdate(a.attendance_date): a
		for a in frappe.get_all(
			"Attendance",
			filters={
				"employee": emp,
				"docstatus": 1,
				"attendance_date": ["between", [window_start, edate]],
			},
			fields=["attendance_date", "status", "leave_type"],
		)
	}

	include_weekend_types = set(
		frappe.get_all(
			"Leave Type", filters={"custom_include_weekend": 1}, pluck="name"
		)
	)
	unmarked_present = (
		frappe.get_cached_value(
			"Payroll Settings", None, "consider_unmarked_attendance_as"
		)
		== "Present"
	)

	def present_days(week_days):
		count = 0.0
		for d in week_days:
			if (doj and d < doj) or (relieving_date and d > relieving_date):
				continue
			if d in holidays:
				count += 1
				continue
			row = attendance.get(d)
			if not row:
				if unmarked_present:
					count += 1
				continue
			if row.status in ("Present", "Work From Home"):
				count += 1
			elif row.status == "Half Day":
				count += 0.5
			elif row.status == "On Leave" and row.leave_type in include_weekend_types:
				count += 1
		return count

	deduction_count = 0
	for block in target_blocks:
		# work-week = run of non-weekly-off days right before the block
		week_days = []
		d = add_days(block[0], -1)
		while d not in off_dates and len(week_days) < 6:
			week_days.append(d)
			d = add_days(d, -1)

		if present_days(week_days) < 3:
			deduction_count += sum(1 for d in block if sdate <= d <= edate)

	return deduction_count

#completed		
@frappe.whitelist()
def update_logistic_request(doc,method):
	if doc.custom_logistics_request:
		if frappe.db.exists('Logistics Request',{'name':doc.custom_logistics_request}):
			logistics=frappe.get_doc('Logistics Request',{'name':doc.custom_logistics_request})
			if logistics.workflow_state=='Out for Delivery':
				logistics.workflow_state='Arrived'
			logistics.save(ignore_permissions=True)
			# frappe.db.commit()  


@frappe.whitelist()
def logistic_req_close_mail():
	from frappe.utils import add_days, today, formatdate
	date = add_days(today(), 7)
	lr = frappe.db.get_all(
		'Logistics Request',
		filters={
			'workflow_state': ['!=', 'Closed'],
			'eta': ['<=', date],
			'eta': ['!=', ''],
		},
		fields=['name', 'eta']
	)
	if lr:
		table = '''
			<table border="1" width="100%" style="border-collapse: collapse; margin-bottom: 10px;">
				<tr style="background-color: #0f1568 ;color: white;text-align:center;font-size: 12px;">
					<td><b>Sr</b></td>
					<td><b>ID</b></td>
					<td><b>ETA</b></td>
				</tr>
		'''
		s_no = 1
		for l in lr:
			if l.eta:
				table += f'''
					<tr style="font-size: 12px;">
						<td style="text-align:left;">{s_no}</td>
						<td style="text-align:left;">{l.name}</td>
						<td style="text-align:left;">{formatdate(l.eta)}</td>
					</tr>
				'''
				s_no += 1
		table += '</table>'
		recipient_users = frappe.db.get_list(
			"Has Role",
			filters={"role": 'Logistics User', "parenttype": "User"},
			fields=["parent as user_name"]
		)
		message=f"""<p><b>Dear Sir/Madam,</b><br> 
				The listed Logistics Requests have ETA within one week. Kindly review these requests.<br><br>
				{table}
				<br><b>Note:</b> This is an automated email notification. Please do not reply to this email.</p>
				"""
		print(message)
		recipient = []
		for user in recipient_users:
			is_active = frappe.db.get_value('User', user.user_name, 'enabled')
			email = frappe.db.get_value('User', user.user_name, 'email')
			if is_active and email:
				recipient.append(email)
		print(recipient)
		if recipient:
			frappe.sendmail(
				recipients='abdulla.pi@groupteampro.com',
				subject="Logistics Requests not closed",
				message=f"""<p><b>Dear Sir/Madam,</b><br><br>  
				The listed Logistics Requests have ETA within one week. Kindly review these requests.<br><br>
				{table}
				<br><b>Note:</b> This is an automated email notification. Please do not reply to this email.</p>
				"""
			)

import base64

@frappe.whitelist()
def get_base64_images(file_url):
	from frappe.utils import get_files_path
	import os
	file_rel_path = file_url.replace("/private/files/", "")
	file_path = os.path.join(get_files_path("pdf_images", is_private=True), os.path.basename(file_rel_path))

	if not os.path.exists(file_path):
		frappe.throw(f"File not found: {file_path}")

	with open(file_path, "rb") as f:
		encoded = base64.b64encode(f.read()).decode()

	return f"data:image/png;base64,{encoded}"


import frappe
import os
import subprocess
from frappe.utils import get_files_path
from pdf2image import convert_from_path

@frappe.whitelist()
def convert_file_to_images(file_url):
	if not file_url:
		frappe.throw("No file URL provided")

	file_ext = file_url.lower().split('.')[-1]

	output_dir = get_files_path("pdf_images", is_private=True)
	os.makedirs(output_dir, exist_ok=True)

	original_filename = os.path.basename(file_url).replace(' ', '_')
	is_private = file_url.startswith("/private/")
	download_path = get_files_path(os.path.basename(file_url), is_private=is_private)
	if not os.path.exists(download_path):
		download_path = get_files_path(original_filename, is_private=is_private)
	if not os.path.exists(download_path):
		frappe.throw(f"File not found: {file_url}")

	if file_ext != "pdf":
		try:
			subprocess.run([
				"libreoffice", "--headless", "--convert-to", "pdf",
				"--outdir", output_dir, download_path
			], check=True)

			pdf_filename = os.path.basename(download_path).rsplit('.', 1)[0] + ".pdf"
			pdf_path = os.path.join(output_dir, pdf_filename)
		except subprocess.CalledProcessError as e:
			frappe.throw(f"Failed to convert {file_ext} to PDF: {str(e)}")
	else:
		pdf_path = download_path

	try:
		images = convert_from_path(pdf_path, dpi=130, poppler_path="/usr/bin")
	except Exception as e:
		frappe.throw(f"PDF conversion error: {str(e)}")

	image_paths = []
	for i, img in enumerate(images):
		img_filename = f"{original_filename}_page_{i + 1}.png"
		img_path = os.path.join(output_dir, img_filename)
		img.save(img_path, "PNG")
		image_paths.append(f"/private/files/pdf_images/{img_filename}")

	return image_paths


import frappe
from frappe.model.document import Document

def create_project_on_so_submit(doc, method):
	existing = frappe.db.exists("Project", {"sales_order": doc.name})
	if existing:
		return

	project_name = f"{doc.name}_{doc.customer}"
	if doc.po_no:
		series = f"{doc.customer}-{doc.po_no}-{doc.name}"
	else:
		series = f"{doc.customer}-{doc.name}"

	project = frappe.get_doc({
		"doctype": "Project",
		"naming_series": series,  
		"project_name": project_name,
		"sales_order": doc.name,
		"customer": doc.customer
	})

	project.insert(ignore_permissions=True)
	frappe.msgprint(f"Project '{project.project_name}' created.")

@frappe.whitelist()
def create_lr_in_po(doc,method):
	if doc.custom_purchase_type=="Import":
		lr=frappe.new_doc("Logistics Request")
		lr.order_no=doc.name
		lr.logistic_type="Import"
		lr.po_so="Purchase Order"
		lr.currency=doc.currency
		lr.conv_rate=doc.conversion_rate
		lr.cargo_type=doc.custom_cargo_type
		lr.product_description=doc.items
		lr.inventory_destination=doc.custom_inventory_destination
		lr.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.msgprint(f"Logistics Request '{lr.name}' created.")


#completed
import frappe
from frappe.model.document import Document

@frappe.whitelist()
def create_logistics_request_for_purchase_orders(po_names,cargo_type,inventory_destination):
	import json

	if isinstance(po_names, str):
		po_names = json.loads(po_names)

	if not po_names:
		frappe.throw("No Purchase Orders selected.")

	logistics_request = frappe.new_doc("Logistics Request")
	logistics_request.logistic_type = "Import"
	logistics_request.po_so = "Purchase Order"
	total_amount = 0  
	for po_name in po_names:
		po = frappe.get_doc("Purchase Order", po_name)
		logistics_request.currency = po.currency
		logistics_request.conv_rate = po.conversion_rate
		logistics_request.cargo_type = cargo_type
		logistics_request.inventory_destination = inventory_destination
		for item in po.items:
			# total_requested_qty = frappe.db.sql("""
			#     SELECT SUM(lri.qty)
			#     FROM `tabLogistics Request Item` lri
			#     JOIN `tabLogistics Request` lr ON lri.parent = lr.name
			#     WHERE lri.voucher_no = %s AND lri.item_code = %s AND lr.workflow_state != 'Draft'
			# """, (po.name, item.item_code))[0][0] or 0
			total_requested_qty = frappe.db.sql("""
				SELECT COALESCE(SUM(lri.qty), 0)
				FROM `tabLogistics Request Item` lri
				INNER JOIN `tabLogistics Request` lr
					ON lr.name = lri.parent
				WHERE lri.voucher_no = %s
				AND lri.po_item = %s
				AND lr.workflow_state != 'Draft'
			""", (po.name, item.name))[0][0]
			pending_qty = item.qty - total_requested_qty

			if pending_qty > 0:
				rate = item.rate
				amount = pending_qty * rate
				base_rate = item.base_rate or rate * po.conversion_rate
				base_amount = item.base_amount or amount * po.conversion_rate

				logistics_request.append("product_description", {
					"item_code": item.item_code,
					"item_name": item.item_name,
					"po_item":item.name,
					"description": item.description,
					"qty": pending_qty,
					"rate": rate,
					"uom": item.uom,
					"amount": amount,
					"currency":po.currency,
					"conversion_factor": item.conversion_factor or 1,
					"base_rate": base_rate,
					"base_amount": base_amount,
					"voucher_no": po.name,
					"voucher_type": "Purchase Order",
					"supplier":po.supplier,
					"requester_name":po.custom_sales_person,
					"box_name":item.custom_box_name,
					"pallet_name":item.custom_pallet_name,
					"no_of_boxes":item.custom_no_of_boxes,
					"no_of_pallets":item.custom_no_of_pallets,
					"total_box_weight_kg":item.custom_total_box_weight_kg,
					"total_pallet_weight_kg":item.custom_total_pallet_weight_kg,
					"box_length_mm":item.custom_box_length_mm,
					"pallet_length_mm":item.custom_pallet_length_mm,
					"box_breadth_mm":item.custom_box_breadth_mm,
					"pallet_breadth_mm":item.custom_pallet_breadth_mm,
					"box_height_mm":item.custom_box_height_mm,
					"pallet_height_mm":item.custom_pallet_height_mm,
					"cbm":item.custom_cbm,
					"packing_weight_kg":item.custom_packing_weight_kg,
					"gross_weight_kg":item.custom_gross_weight_kg
				})

				total_amount += amount  # Accumulate amount
		box_data, pallet_data = get_box_summary_po(po_name)
		for row in box_data:
			logistics_request.append("box_summary_table", {
				"box": row.get("box"),
				"total_no_of_box": row.get("total_no_of_box"),
				"weight_per_unit": row.get("weight_per_unit"),
				"total_weight": row.get("total_weight"),
				"total_length": row.get("total_length"),
				"total_breadth": row.get("total_breadth"),
				"total_height": row.get("total_height")
			})

		for pal in pallet_data:
			logistics_request.append("pallet_summary", {
				"pallet": pal.get("box"),
				"total_no_of_pallet": pal.get("total_no_of_box"),
				"weight_per_unit": pal.get("weight_per_unit"),
				"total_weight": pal.get("total_weight"),
				"total_length": pal.get("total_length"),
				"total_breadth": pal.get("total_breadth"),
				"total_height": pal.get("total_height")
			})

	if not logistics_request.get("product_description"):
		frappe.throw("All selected Purchase Orders are already fully included in previous Logistics Requests.")

	logistics_request.grand_total = total_amount  # Set computed grand total
	if total_amount>0:
		logistics_request.custom_duty =total_amount*0.45
	logistics_request.save(ignore_permissions=True)
	frappe.db.commit()

	return frappe.msgprint(f"Logistics Request <a href='/app/logistics-request/{logistics_request.name}'><b>{logistics_request.name}</b></a> created successfully.")

#completed
@frappe.whitelist()
def get_box_summary_po(po_name):
	if not frappe.db.exists("Purchase Order", po_name):
		return [], []

	data = frappe.db.sql("""
	SELECT custom_box_name as box_name, custom_no_of_boxes as total_no,
		   SUM(IFNULL(custom_weight_per_unit_kg, 0)) as weight_per_unit,
		   SUM(IFNULL(custom_total_box_weight_kg, 0)) as total_weight,
		   SUM(IFNULL(custom_box_length_mm, 0)) as blength,
		   SUM(IFNULL(custom_box_height_mm, 0)) as bheight,
		   SUM(IFNULL(custom_box_breadth_mm, 0)) as bbreadth
	FROM `tabPurchase Order Item`
	WHERE parent = %s
	GROUP BY custom_box_name
""", (po_name,), as_dict=True)


	box_summary = [
		{
			"box": row.box_name,
			"total_no_of_box": row.total_no,
			"weight_per_unit": row.weight_per_unit,
			"total_weight": row.total_weight,
			"total_length": row.blength,
			"total_breadth": row.bbreadth,
			"total_height": row.bheight
		}
		for row in data if row.box_name and row.total_no
	]
	data2 = frappe.db.sql("""
		SELECT custom_pallet_name as pallet_name, custom_no_of_pallets as total_no,
			   SUM(custom_p_weight_per_unit_kg) as weight_per_unit,
			   SUM(custom_total_pallet_weight_kg) as total_weight,
			   SUM(custom_pallet_length_mm) as plength,
			   SUM(custom_pallet_breadth_mm) as pbreadth,
			   SUM(custom_pallet_height_mm) as pheight
		FROM `tabPurchase Order Item`
		WHERE parent = %s
		GROUP BY custom_pallet_name
	""", (po_name,), as_dict=True)

	pallet_summary = [
		{
			"box": row.pallet_name,
			"total_no_of_box": row.total_no,
			"weight_per_unit": row.weight_per_unit,
			"total_weight": row.total_weight,
			"total_length": row.plength,
			"total_breadth": row.pbreadth,
			"total_height": row.pheight
		}
		for row in data2 if row.pallet_name and row.total_no
	]
	return box_summary, pallet_summary


#completed
import frappe
from frappe.model.document import Document

@frappe.whitelist()
def create_logistics_request_for_sales_invoice(so_names,cargo_type):
	import json

	if isinstance(so_names, str):
		so_names = json.loads(so_names)

	if not so_names:
		frappe.throw("No Sales Invoices selected.")

	logistics_request = frappe.new_doc("Logistics Request")
	logistics_request.logistic_type = "Export"
	logistics_request.po_so = "Sales Invoice"
	

	total_amount = 0  # To accumulate grand total

	for po_name in so_names:
		po = frappe.get_doc("Sales Invoice", po_name)
		logistics_request.currency = po.currency
		logistics_request.conv_rate = po.conversion_rate
		logistics_request.cargo_type = cargo_type
		logistics_request.custom_customer_final_destination=po.customer
		logistics_request.inventory_destination = "Direct to Customer"
		for item in po.items:
			# total_requested_qty = frappe.db.sql("""
			#     SELECT SUM(qty)
			#     FROM `tabLogistics Request Item`
			#     WHERE voucher_no = %s AND item_code = %s
			# """, (po.name, item.item_code))[0][0] or 0
			total_requested_qty = frappe.db.sql("""
				SELECT SUM(lri.qty)
				FROM `tabLogistics Request Item` lri
				JOIN `tabLogistics Request` lr ON lri.parent = lr.name
				WHERE lri.voucher_no = %s AND lri.item_code = %s AND lr.workflow_state != 'Draft'
			""", (po.name, item.item_code))[0][0] or 0
			pending_qty = item.qty - total_requested_qty

			if pending_qty > 0:
				rate = item.rate
				amount = pending_qty * rate
				base_rate = item.base_rate or rate * po.conversion_rate
				base_amount = item.base_amount or amount * po.conversion_rate

				logistics_request.append("product_description", {
					"item_code": item.item_code,
					"item_name": item.item_name,
					"description": item.description,
					"qty": pending_qty,
					"rate": rate,
					"uom": item.uom,
					"amount": amount,
					"conversion_factor": item.conversion_factor or 1,
					"base_rate": base_rate,
					"base_amount": base_amount,
					"voucher_no": po.name,
					"voucher_type": "Sales Invoice",
					"customer":po.customer,
					"requester_name":po.custom_sales_person,
					"box_name":item.custom_box,
					"pallet_name":item.custom_pallet,
					"no_of_boxes":item.custom_no_of_boxes,
					"no_of_pallets":item.custom_no_of_pallets,
					"total_box_weight_kg":item.custom_total_weight_of_boxes,
					"total_pallet_weight_kg":item.custom_total_weight_of_pallets,
					"box_length_mm":item.custom_box_length,
					"pallet_length_mm":item.custom_pallet_length,
					"box_breadth_mm":item.custom_box_breadth,
					"pallet_breadth_mm":item.custom_pallet_breadth,
					"box_height_mm":item.custom_box_height,
					"pallet_height_mm":item.custom_pallet_height,
					"cbm":item.custom_cbm,
					"packing_weight_kg":item.custom_packing_weight,
					"gross_weight_kg":item.custom_gross_weight
				})

				total_amount += amount  # Accumulate amount
		box_data, pallet_data = get_box_summary_si(po_name)
		for row in box_data:
			logistics_request.append("box_summary_table", {
				"box": row.get("box"),
				"total_no_of_box": row.get("total_no_of_box"),
				"weight_per_unit": row.get("weight_per_unit"),
				"total_weight": row.get("total_weight"),
				"total_length": row.get("total_length"),
				"total_breadth": row.get("total_breadth"),
				"total_height": row.get("total_height")
			})

		for pal in pallet_data:
			logistics_request.append("pallet_summary", {
				"pallet": pal.get("box"),
				"total_no_of_pallet": pal.get("total_no_of_box"),
				"weight_per_unit": pal.get("weight_per_unit"),
				"total_weight": pal.get("total_weight"),
				"total_length": pal.get("total_length"),
				"total_breadth": pal.get("total_breadth"),
				"total_height": pal.get("total_height")
			})

	if not logistics_request.get("product_description"):
		frappe.throw("All selected Sales Invoices are already fully included in previous Logistics Requests.")

	logistics_request.grand_total = total_amount  # Set computed grand total
	if total_amount>0:
		logistics_request.custom_duty =total_amount*0.45
	logistics_request.save(ignore_permissions=True)
	frappe.db.commit()

	return frappe.msgprint(f"Logistics Request <a href='/app/logistics-request/{logistics_request.name}'><b>{logistics_request.name}</b></a> created successfully.")

#completed
@frappe.whitelist()
def get_box_summary_si(po_name):
	if not frappe.db.exists("Sales Invoice", po_name):
		return [], []

	data = frappe.db.sql("""
	SELECT custom_box as box_name, custom_no_of_boxes as total_no,
		   SUM(IFNULL(custom_weight_per_unit_b, 0)) as weight_per_unit,
		   SUM(IFNULL(custom_total_weight_of_boxes, 0)) as total_weight,
		   SUM(IFNULL(custom_box_length, 0)) as blength,
		   SUM(IFNULL(custom_box_height, 0)) as bheight,
		   SUM(IFNULL(custom_box_breadth, 0)) as bbreadth
	FROM `tabSales Invoice Item`
	WHERE parent = %s
	GROUP BY custom_box
""", (po_name,), as_dict=True)


	box_summary = [
		{
			"box": row.box_name,
			"total_no_of_box": row.total_no,
			"weight_per_unit": row.weight_per_unit,
			"total_weight": row.total_weight,
			"total_length": row.blength,
			"total_breadth": row.bbreadth,
			"total_height": row.bheight
		}
		for row in data if row.box_name and row.total_no
	]
	data2 = frappe.db.sql("""
		SELECT custom_pallet as pallet_name, custom_no_of_pallets as total_no,
			   SUM(custom_weight_per_unit_p) as weight_per_unit,
			   SUM(custom_total_weight_of_pallets) as total_weight,
			   SUM(custom_pallet_length) as plength,
			   SUM(custom_pallet_breadth) as pbreadth,
			   SUM(custom_pallet_height) as pheight
		FROM `tabSales Invoice Item`
		WHERE parent = %s
		GROUP BY custom_pallet
	""", (po_name,), as_dict=True)

	pallet_summary = [
		{
			"box": row.pallet_name,
			"total_no_of_box": row.total_no,
			"weight_per_unit": row.weight_per_unit,
			"total_weight": row.total_weight,
			"total_length": row.plength,
			"total_breadth": row.pbreadth,
			"total_height": row.pheight
		}
		for row in data2 if row.pallet_name and row.total_no
	]
	return box_summary, pallet_summary


#completed
@frappe.whitelist()
def create_logistics_request_for_sales_orders(so_names,cargo_type):
	import json

	if isinstance(so_names, str):
		so_names = json.loads(so_names)

	if not so_names:
		frappe.throw("No Sales Orders selected.")

	logistics_request = frappe.new_doc("Logistics Request")
	logistics_request.logistic_type = "Export"
	logistics_request.po_so = "Sales Order"
	total_amount = 0  # To accumulate grand total

	for po_name in so_names:
		po = frappe.get_doc("Sales Order", po_name)
		logistics_request.currency = po.currency
		logistics_request.conv_rate = po.conversion_rate
		logistics_request.cargo_type = cargo_type
		logistics_request.inventory_destination = "Direct to Customer"
		logistics_request.custom_customer_final_destination=po.customer
		for item in po.items:
			total_requested_qty = frappe.db.sql("""
				SELECT SUM(lri.qty)
				FROM `tabLogistics Request Item` lri
				JOIN `tabLogistics Request` lr ON lri.parent = lr.name
				WHERE lri.voucher_no = %s AND lri.item_code = %s AND lr.workflow_state != 'Draft'
			""", (po.name, item.item_code))[0][0] or 0
			pending_qty = item.qty - total_requested_qty

			if pending_qty > 0:
				rate = item.rate
				amount = pending_qty * rate
				base_rate = item.base_rate or rate * po.conversion_rate
				base_amount = item.base_amount or amount * po.conversion_rate

				logistics_request.append("product_description", {
					"item_code": item.item_code,
					"item_name": item.item_name,
					"description": item.description,
					"qty": pending_qty,
					"rate": rate,
					"uom": item.uom,
					"amount": amount,
					"conversion_factor": item.conversion_factor or 1,
					"base_rate": base_rate,
					"base_amount": base_amount,
					"voucher_no": po.name,
					"voucher_type": "Sales Order",
					"customer":po.customer,
					"requester_name":po.custom_sales_person,
					"box_name":item.custom_box_name,
					"pallet_name":item.custom_pallet_name,
					"no_of_boxes":item.custom_no_of_boxes,
					"no_of_pallets":item.custom_no_of_pallets,
					"total_box_weight_kg":item.custom_total_box_weight_kg,
					"total_pallet_weight_kg":item.custom_p_weight_per_unit_kg,
					"box_length_mm":item.custom_box_length_mm,
					"pallet_length_mm":item.custom_pallet_length_mm,
					"box_breadth_mm":item.custom_box_breadth_mm,
					"pallet_breadth_mm":item.custom_pallet_breadth_mm,
					"box_height_mm":item.custom_box_height_mm,
					"pallet_height_mm":item.custom_pallet_height_mm,
					"cbm":item.custom_cbm,
					"packing_weight_kg":item.custom_packing_weight_kg,
					"gross_weight_kg":item.custom_gross_weight_kg
				})

				total_amount += amount  # Accumulate amount
		box_data, pallet_data = get_box_summary_so(po_name)
		for row in box_data:
			logistics_request.append("box_summary_table", {
				"box": row.get("box"),
				"total_no_of_box": row.get("total_no_of_box"),
				"weight_per_unit": row.get("weight_per_unit"),
				"total_weight": row.get("total_weight"),
				"total_length": row.get("total_length"),
				"total_breadth": row.get("total_breadth"),
				"total_height": row.get("total_height")
			})

		for pal in pallet_data:
			logistics_request.append("pallet_summary", {
				"pallet": pal.get("box"),
				"total_no_of_pallet": pal.get("total_no_of_box"),
				"weight_per_unit": pal.get("weight_per_unit"),
				"total_weight": pal.get("total_weight"),
				"total_length": pal.get("total_length"),
				"total_breadth": pal.get("total_breadth"),
				"total_height": pal.get("total_height")
			})

	if not logistics_request.get("product_description"):
		frappe.throw("All selected Sales Orders are already fully included in previous Logistics Requests.")

	logistics_request.grand_total = total_amount  # Set computed grand total
	if total_amount>0:
		logistics_request.custom_duty =total_amount*0.45
	logistics_request.save(ignore_permissions=True)
	frappe.db.commit()

	return frappe.msgprint(f"Logistics Request <a href='/app/logistics-request/{logistics_request.name}'><b>{logistics_request.name}</b></a> created successfully.")


#completed
@frappe.whitelist()
def get_box_summary_so(po_name):
	if not frappe.db.exists("Sales Order", po_name):
		return [], []

	data = frappe.db.sql("""
	SELECT custom_box_name as box_name, custom_no_of_boxes as total_no,
		   SUM(IFNULL(custom_weight_per_unit_kg, 0)) as weight_per_unit,
		   SUM(IFNULL(custom_total_box_weight_kg, 0)) as total_weight,
		   SUM(IFNULL(custom_box_length_mm, 0)) as blength,
		   SUM(IFNULL(custom_box_height_mm, 0)) as bheight,
		   SUM(IFNULL(custom_box_breadth_mm, 0)) as bbreadth
	FROM `tabSales Order Item`
	WHERE parent = %s
	GROUP BY custom_box_name
""", (po_name,), as_dict=True)


	box_summary = [
		{
			"box": row.box_name,
			"total_no_of_box": row.total_no,
			"weight_per_unit": row.weight_per_unit,
			"total_weight": row.total_weight,
			"total_length": row.blength,
			"total_breadth": row.bbreadth,
			"total_height": row.bheight
		}
		for row in data if row.box_name and row.total_no
	]
	data2 = frappe.db.sql("""
		SELECT custom_pallet_name as pallet_name, custom_no_of_pallets as total_no,
			   SUM(custom_p_weight_per_unit_kg) as weight_per_unit,
			   SUM(custom_total_pallet_weight_kg) as total_weight,
			   SUM(custom_pallet_length_mm) as plength,
			   SUM(custom_pallet_breadth_mm) as pbreadth,
			   SUM(custom_pallet_height_mm) as pheight
		FROM `tabSales Order Item`
		WHERE parent = %s
		GROUP BY custom_pallet_name
	""", (po_name,), as_dict=True)

	pallet_summary = [
		{
			"box": row.pallet_name,
			"total_no_of_box": row.total_no,
			"weight_per_unit": row.weight_per_unit,
			"total_weight": row.total_weight,
			"total_length": row.plength,
			"total_breadth": row.pbreadth,
			"total_height": row.pheight
		}
		for row in data2 if row.pallet_name and row.total_no
	]
	return box_summary, pallet_summary


#completed
@frappe.whitelist()
def create_logistics_request_for_delivery(lr_names):
	import json

	if isinstance(lr_names, str):
		lr_names = json.loads(lr_names)

	if not lr_names:
		frappe.throw("No Delivery Note selected.")

	logistics_request = frappe.new_doc("Logistics Request")
	logistics_request.logistic_type = "Local Delivery"
	logistics_request.po_so = "Delivery Note"
	
	total_amount = 0 

	for po_name in lr_names:
		po = frappe.get_doc("Delivery Note", po_name)
		logistics_request.currency = po.currency
		logistics_request.conv_rate = po.conversion_rate
		logistics_request.cargo_type = "Road"
		logistics_request.inventory_destination = "Direct to Customer"
		logistics_request.customer=po.customer
		for item in po.items:
			# total_requested_qty = frappe.db.sql("""
			#     SELECT SUM(qty)
			#     FROM `tabLogistics Request Item`
			#     WHERE voucher_no = %s AND item_code = %s
			# """, (po.name, item.item_code))[0][0] or 0
			total_requested_qty = frappe.db.sql("""
				SELECT SUM(lri.qty)
				FROM `tabLogistics Request Item` lri
				JOIN `tabLogistics Request` lr ON lri.parent = lr.name
				WHERE lri.voucher_no = %s AND lri.item_code = %s AND lr.workflow_state != 'Draft'
			""", (po.name, item.item_code))[0][0] or 0
			pending_qty = item.qty - total_requested_qty

			if pending_qty > 0:
				rate = item.rate
				amount = pending_qty * rate
				base_rate = item.base_rate or rate * po.conversion_rate
				base_amount = item.base_amount or amount * po.conversion_rate

				logistics_request.append("product_description", {
					"item_code": item.item_code,
					"item_name": item.item_name,
					"description": item.description,
					"qty": pending_qty,
					"rate": rate,
					"uom": item.uom,
					"amount": amount,
					"conversion_factor": item.conversion_factor or 1,
					"base_rate": base_rate,
					"base_amount": base_amount,
					"voucher_no": po.name,
					"voucher_type": "Delivery Note",
					"customer":po.customer,
					"requester_name":frappe.session.user,
					"box_name":item.custom_box_name,
					"pallet_name":item.custom_pallet_name,
					"no_of_boxes":item.custom_no_of_boxes,
					"no_of_pallets":item.custom_no_of_pallets,
					"total_box_weight_kg":item.custom_total_box_weight_kg,
					"total_pallet_weight_kg":item.custom_p_weight_per_unit_kg,
					"box_length_mm":item.custom_box_length_mm,
					"pallet_length_mm":item.custom_pallet_length_mm,
					"box_breadth_mm":item.custom_box_breadth_mm,
					"pallet_breadth_mm":item.custom_pallet_breadth_mm,
					"box_height_mm":item.custom_box_height_mm,
					"pallet_height_mm":item.custom_pallet_height_mm,
					"cbm":item.custom_cbm,
					"packing_weight_kg":item.custom_packing_weight_kg,
					"gross_weight_kg":item.custom_gross_weight_kg
					
				})

				total_amount += amount  # Accumulate amount
		box_data, pallet_data = get_box_summary_dn(po_name)
		for row in box_data:
			logistics_request.append("box_summary_table", {
				"box": row.get("box"),
				"total_no_of_box": row.get("total_no_of_box"),
				"weight_per_unit": row.get("weight_per_unit"),
				"total_weight": row.get("total_weight"),
				"total_length": row.get("total_length"),
				"total_breadth": row.get("total_breadth"),
				"total_height": row.get("total_height")
			})

		for pal in pallet_data:
			logistics_request.append("pallet_summary", {
				"pallet": pal.get("box"),
				"total_no_of_pallet": pal.get("total_no_of_box"),
				"weight_per_unit": pal.get("weight_per_unit"),
				"total_weight": pal.get("total_weight"),
				"total_length": pal.get("total_length"),
				"total_breadth": pal.get("total_breadth"),
				"total_height": pal.get("total_height")
			})

	if not logistics_request.get("product_description"):
		frappe.throw("All selected Delivery Note are already fully included in previous Logistics Requests.")

	logistics_request.grand_total = total_amount  # Set computed grand total
	if total_amount>0:
		logistics_request.custom_duty =total_amount*0.45
	logistics_request.save(ignore_permissions=True)
	frappe.db.commit()

	return frappe.msgprint(f"Logistics Request <a href='/app/logistics-request/{logistics_request.name}'><b>{logistics_request.name}</b></a> created successfully.")


#completed
@frappe.whitelist()
def get_box_summary_dn(po_name):
	if not frappe.db.exists("Delivery Note", po_name):
		return [], []

	data = frappe.db.sql("""
	SELECT custom_box_name as box_name, custom_no_of_boxes as total_no,
		   SUM(IFNULL(custom_weight_per_unit_kg, 0)) as weight_per_unit,
		   SUM(IFNULL(custom_total_box_weight_kg, 0)) as total_weight,
		   SUM(IFNULL(custom_box_length_mm, 0)) as blength,
		   SUM(IFNULL(custom_box_height_mm, 0)) as bheight,
		   SUM(IFNULL(custom_box_breadth_mm, 0)) as bbreadth
	FROM `tabDelivery Note Item`
	WHERE parent = %s
	GROUP BY custom_box_name
""", (po_name,), as_dict=True)


	box_summary = [
		{
			"box": row.box_name,
			"total_no_of_box": row.total_no,
			"weight_per_unit": row.weight_per_unit,
			"total_weight": row.total_weight,
			"total_length": row.blength,
			"total_breadth": row.bbreadth,
			"total_height": row.bheight
		}
		for row in data if row.box_name and row.total_no
	]
	data2 = frappe.db.sql("""
		SELECT custom_pallet_name as pallet_name, custom_no_of_pallets as total_no,
			   SUM(custom_p_weight_per_unit_kg) as weight_per_unit,
			   SUM(custom_total_pallet_weight_kg) as total_weight,
			   SUM(custom_pallet_length_mm) as plength,
			   SUM(custom_pallet_breadth_mm) as pbreadth,
			   SUM(custom_pallet_height_mm) as pheight
		FROM `tabDelivery Note Item`
		WHERE parent = %s
		GROUP BY custom_pallet_name
	""", (po_name,), as_dict=True)

	pallet_summary = [
		{
			"box": row.pallet_name,
			"total_no_of_box": row.total_no,
			"weight_per_unit": row.weight_per_unit,
			"total_weight": row.total_weight,
			"total_length": row.plength,
			"total_breadth": row.pbreadth,
			"total_height": row.pheight
		}
		for row in data2 if row.pallet_name and row.total_no
	]
	return box_summary, pallet_summary


#completed
@frappe.whitelist()
def update_quote_value(estimation=None, margin=None):
	if estimation is None or margin is None:
		return 0
	value = 100 - float(margin)
	if value == 0:
		frappe.throw("Margin cannot be 100%: quoted value cannot be derived from the cost estimation.")
	quote_value = 100 * float(estimation) / float(value)
	return quote_value

#completed
@frappe.whitelist()
def update_quote_value_by_cost(estimation=None, margin=None):
	if estimation is None or margin is None:
		return 0
	value = float(margin)/float(100)
	quote_value = float(estimation) + (float (estimation) * float(value))
	return quote_value
  
@frappe.whitelist()
def update_lead_name(doc,method):
	frappe.db.set_value('Lead',doc.name,'party_name',doc.name)
	doc.reload()

@frappe.whitelist()
def update_lead_status(doc,name):
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project",doc.custom_project_reference)
		ref.append('table_gygr',{
			'document_type':doc.doctype,
			'document_type_name':doc.name,
			'status':doc.status
		})
		ref.save(ignore_permissions=True)
		frappe.db.commit()
	


@frappe.whitelist()
def update_sfp_status(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.project_reference:
		ref = frappe.get_doc("Reference Project", doc.project_reference)

		# Check if a matching row exists
		exists = False
		for row in ref.table_gygr:
			if row.document_type_name == doc.party_name:
				ref.remove(row)
				exists = True

		
		ref.append("table_gygr", {
			"document_type": doc.doctype,
			"document_type_name": doc.name,
			"status": doc.status
		})

		ref.save(ignore_permissions=True)
		frappe.db.commit()

@frappe.whitelist()
def update_opp_status(doc, name):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.custom_project_reference:
		ref = frappe.get_doc("Reference Project", doc.custom_project_reference)

		# Check if a matching row exists
		exists = False
		for row in ref.table_gygr:
			if row.document_type_name == doc.custom_sales_follow_up:
				ref.remove(row)
				exists = True
				break  # Stop after finding and removing the first match
			if row.document_type_name == doc.party_name:
				ref.remove(row)
				exists = True
				break 

		ref.append("table_gygr", {
			"document_type": doc.doctype,
			"document_type_name": doc.name,
			"status": doc.status
		})

		ref.save(ignore_permissions=True)
		frappe.db.commit()

@frappe.whitelist()
def enqueue_lr_update_dn(doc, method):
	frappe.enqueue(
		"jgb.jgb.custom.update_logistics_status_from_dn",
		doc_name=doc.name, 
		queue="long",
		timeout=600
	)

@frappe.whitelist()
def update_logistics_status_from_dn(doc_name):
	doc = frappe.get_doc("Delivery Note", doc_name) 
	if not doc.items:
		return

	status_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
	current_status = status_map.get(doc.docstatus, "Unknown")

	for item in doc.items:
		linked_docs = []

		if item.against_sales_order:
			linked_docs.append(("Sales Order", item.against_sales_order))

		if item.against_sales_invoice:
			linked_docs.append(("Sales Invoice", item.against_sales_invoice))

		if not linked_docs:
			continue
				
		lr_docs = frappe.get_all("Logistics Request", fields=["name"])
		for lr in lr_docs:
			lr_doc = frappe.get_doc("Logistics Request", lr.name)

			matched = False
			for voucher_type, voucher_no in linked_docs:
				for row in lr_doc.product_description:
					if row.voucher_type == voucher_type and row.voucher_no == voucher_no:
						matched = True
						break
				if matched:
					break

			if not matched:
				continue

			if doc.docstatus == 2:  # Cancelled
				to_remove = []
				for row in lr_doc.lr_status_details:
					if row.voucher_type == "Delivery Note" and row.voucher_name == doc.name:
						to_remove.append(row)

				for row in to_remove:
					lr_doc.lr_status_details.remove(row)


			else:
				updated = False
				for lr_status in lr_doc.lr_status_details:
					if lr_status.voucher_type == "Delivery Note" and lr_status.voucher_name == doc.name:
						lr_status.status = current_status
						updated = True
						break

				if not updated:
					lr_doc.append("lr_status_details", {
						"voucher_type": "Delivery Note",
						"voucher_name": doc.name,
						"status": current_status
					})

			lr_doc.save(ignore_permissions=True)



#On first save of PR, PR  ID is set in LR
@frappe.whitelist()
def update_pr_in_lr_draft(doc,method):
	if doc.custom_logistics_request:
		if frappe.db.exists('Logistics Request',{'name':doc.custom_logistics_request}):
			docs=frappe.get_doc("Logistics Request",doc.custom_logistics_request)
			docs.append("lr_status_details",{
				"voucher_type":"Purchase Receipt",
				"voucher_name":doc.name,
				"status":"Draft"
			})
			docs.has_purchase_receipt=1
			docs.save(ignore_permissions=True)

#completed
@frappe.whitelist()
def update_pr_in_lr_submit(doc,method):
	if doc.custom_logistics_request:
		if frappe.db.exists('Logistics Request',{'name':doc.custom_logistics_request}):
			docs=frappe.get_doc("Logistics Request",doc.custom_logistics_request)
			if docs.lr_status_details:
				for i in docs.lr_status_details:
					if i.voucher_name==doc.name:
						frappe.db.set_value("LR Status Details", i.name, "status", "Submitted", update_modified=False)

#On first save of PR, PR  ID is set in LR
@frappe.whitelist()
def update_pr_in_lr_cancel(doc,method):
	if doc.custom_logistics_request:
		if frappe.db.exists('Logistics Request',{'name':doc.custom_logistics_request}):
			docs=frappe.get_doc("Logistics Request",doc.custom_logistics_request)
			if docs.lr_status_details:
				for i in docs.lr_status_details:
					if i.voucher_name==doc.name:
						docs.remove(i)
			docs.save(ignore_permissions=True)


@frappe.whitelist()
def create_scheduled_job_type():
	pos = frappe.db.exists('Scheduled Job Type', 'send_lr_eta_team_mail')
	if not pos:
		sjt = frappe.new_doc("Scheduled Job Type")
		sjt.update({
			"method" : 'jgb.jgb.doctype.logistics_request.logistics_request.send_lr_eta_team_mail',
			"frequency" : 'Cron',
			"cron_format":"00 9 * * *"
		})
		sjt.save(ignore_permissions=True)


@frappe.whitelist()
def update_advance_po(doc,method):
	sales_orders = list({item.sales_order for item in doc.items if item.sales_order})

	if not sales_orders:
		doc.custom_so_advance_paid = 0
		return

	total_advance = 0

	for so in sales_orders:
		advance_paid = frappe.db.sql("""
			SELECT SUM(pe.paid_amount)
			FROM `tabPayment Entry Reference` per
			JOIN `tabPayment Entry` pe ON per.parent = pe.name
			WHERE per.reference_doctype = 'Sales Order'
			AND per.reference_name = %s
			AND pe.docstatus = 1
		""", (so,), as_list=1)[0][0] or 0

		total_advance += advance_paid

	doc.custom_so_advance_paid = total_advance


@frappe.whitelist()
def batch_status_update_exisiting():
	filename='/files/contact_import_ready15ef1d.csv'
	from frappe.utils.file_manager import get_file
	filepath = get_file(filename)
	pps = read_csv_content(filepath[1])
	ind=0
	for pp in pps:
		invoice = frappe.new_doc("Contact")
		if pp[0]!= "first_name":
			if pp[0]:
				invoice.first_name = pp[0]
			if pp[1]: 
				invoice.last_name = pp[1]
			
			if pp[4]:
				invoice.append("phone_nos", {
					"phone": pp[4],
					"is_primary_mobile_no": 1,
				})
			if pp[2]:
				invoice.append("email_ids", {
					"email_id": pp[2],
				})
			invoice.append("links", {
				"link_doctype": "Customer",
				"link_name":pp[5],
			})
			invoice.save()
			# frappe.db.set_value("",{"name":pp[0]},"batch_status",pp[1])
			ind+=1
			# print(pp[0])
			# print(pp[1])
		print(ind)

import frappe
from frappe.contacts.doctype.address.address import get_address_display

@frappe.whitelist()
def update_supp_address():
	# Get all Address documents
	address_list = frappe.get_all("Address", fields=["*"])
	
	for addr in address_list:
		# Check if the address_title matches a Supplier name
		supplier_name = frappe.db.get_value("Supplier", {"name": addr.address_title}, "name")
		if supplier_name:
			# Get full address display text
			address_display = get_address_display(addr.name)
			frappe.db.set_value("Supplier", supplier_name, "supplier_primary_address", addr.name)
			# Update the Supplier document with the primary address
			raw_display = get_address_display(addr.name)

			# Clean it: remove <br>, extra spaces
			cleaned_display = clean_address_html(raw_display)

			# Set primary_address (Plain text, no line breaks)
			frappe.db.set_value("Supplier", supplier_name, "primary_address", cleaned_display)
	
import re
def clean_address_html(address_html):
# Split by <br> (case-insensitive)
	lines = re.split(r'<br\s*/?>', address_html, flags=re.IGNORECASE)
	
	cleaned = []
	prev = None
	for line in lines:
		line = line.strip()
		if line and line != prev:
			cleaned.append(line)
			prev = line
	
	return "<br>".join(cleaned)


#completed
import frappe
from frappe.utils import nowtime
@frappe.whitelist()
def update_excess_qty_pr(doc, method):
	if not doc.items:
		return
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type = "Material Receipt"
	stock_entry.company = doc.company
	stock_entry.posting_date = doc.posting_date
	stock_entry.posting_time = doc.posting_time or nowtime()
	stock_entry.custom_purchase_receipt=doc.name
	target_warehouse = doc.set_warehouse or frappe.db.get_value("Warehouse", {
		"warehouse_name": "Transit Warehouse",
		"company": doc.company
	}, "name")

	if not target_warehouse:
		frappe.throw(f"Target warehouse not found for company {doc.company}")

	for item in doc.items:
			if item.custom_excess_quantity > 0:
				# Only allow excess qty when received qty actually exceeds PO qty
				po_qty = 0
				if item.purchase_order and item.purchase_order_item:
					po_qty = frappe.db.get_value(
						"Purchase Order Item",
						item.purchase_order_item,
						"qty",
					) or 0
				if po_qty and item.received_qty <= po_qty:
					frappe.throw(
						_(
							"Row {0}: Excess Quantity cannot be set for item {1}. "
							"Received qty ({2}) does not exceed PO qty ({3}). "
							"Please clear the Excess Quantity field."
						).format(item.idx, item.item_code, item.received_qty, po_qty)
					)
				stock_entry.append("items", {
					"item_code": item.item_code,
					"qty": item.custom_excess_quantity,
					"t_warehouse": target_warehouse,
					"uom": item.uom,
					"stock_uom": item.stock_uom,
					"conversion_factor": item.conversion_factor,
					"basic_rate": item.rate,
					"expense_account": item.expense_account or "",
					"cost_center": item.cost_center or "",
				})

	if stock_entry.items:
		stock_entry.insert()
		stock_entry.submit()
		frappe.msgprint(f"Stock Entry {stock_entry.name} created for excess quantity.")


#completed
import re
import frappe

@frappe.whitelist()
def get_srbnb_account_for_division(division=None, company=None):
	if not division:
		return
	snrb_account = frappe.db.get_value(
		"Division Account Details", {"parent": division,"company": company},"snrb_account")
	if snrb_account:
		return snrb_account

#completed
@frappe.whitelist()
def cost_center_from_division(division=None, company=None):
	if not division:
		return  
	cost_center = frappe.db.get_value(
		"Division Account Details", {"parent": division,"company": company}, "cost_center")
	if cost_center:
		return cost_center


#completed
def extract_keyword_from_division(division):
	# Custom logic to extract from full name like "HVAC Division - (HVA)"
	match = re.search(r'([A-Za-z\s]+)\s+Division', division)
	if match:
		return match.group(1).strip()
	# fallback
	return division.split('-')[0].strip()

#completed
def set_expense_account_from_division_for_item(doc, method=None):
	"""
	Set accounts in Item Defaults based on division and item type
	- Stock items (is_stock_item = 1): Use SRBNB from Division Account Details
	- Non-stock items (is_stock_item = 0): Use COS from Division Account Details
	- Also sets income_account from Division Account Details
	"""
	if not doc.item_group:
		return
	
	# Get division from item group
	division = frappe.db.get_value("Item Group", doc.item_group, "custom_group_name")
	if not division:
		return
	
	# Get company (use first company if multiple)
	company = doc.get("custom_company") or "Joint Global Business Co LLC"
	
	# Get division account details
	div_details = frappe.db.get_value("Division Account Details", 
		{"parent": division, "company": company}, 
		["snrb_account", "expense_account", "cos_account", "income_account"], as_dict=True)
	
	if not div_details:
		return
	
	# Find or create Item Default for the company
	item_default = frappe.db.get_value("Item Default", 
		{"parent": doc.name, "company": company}, "name")
	
	updates = {}
	
	# Set expense_account based on item type
	if doc.is_stock_item:
		# Stock items use SRBNB
		if div_details.snrb_account:
			updates["expense_account"] = div_details.snrb_account
	else:
		# Non-stock items use COS (fallback to COG if COS not set)
		cos_acc = div_details.cos_account or div_details.expense_account
		if cos_acc:
			updates["expense_account"] = cos_acc
	
	# Set income_account
	if div_details.income_account:
		updates["income_account"] = div_details.income_account
	
	if item_default:
		# Update existing Item Default
		if updates:
			frappe.db.set_value("Item Default", item_default, updates)
	else:
		# Create new Item Default
		item_default_doc = frappe.new_doc("Item Default")
		item_default_doc.parent = doc.name
		item_default_doc.parenttype = "Item"
		item_default_doc.parentfield = "item_defaults"
		item_default_doc.company = company
		
		# Set accounts
		for key, value in updates.items():
			setattr(item_default_doc, key, value)
		
		# Set other defaults if available
		buying_cc = doc.get("buying_cost_center")
		if buying_cc:
			item_default_doc.buying_cost_center = buying_cc
		selling_cc = doc.get("selling_cost_center")
		if selling_cc:
			item_default_doc.selling_cost_center = selling_cc
		
		item_default_doc.insert()


#completed
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


#completed
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

#completed
@frappe.whitelist()
def get_expense_account_for_division(division=None, company=None):
	if not division:
		return
	expense_account = frappe.db.get_value("Division Account Details",{"parent": division,"company": company},"expense_account")
	if not expense_account:
		return
	if expense_account:
		return expense_account

def extract_keyword_from_division(division):
	match = re.search(r'([A-Za-z\s]+)\s+Division', division)
	if match:
		return match.group(1).strip()
	return division.split('-')[0].strip()


@frappe.whitelist()
def preserve_item_tax_template_before_validate(doc, method=None):
	"""
	Runs as before_validate hook (after claudion4saudi's update_pi_item_tax_templates).
	Saves the user's per-item tax template selection so it can be restored after
	ERPNext's validate_item_tax_template overwrites it.
	
	IMPORTANT: This hook runs AFTER claudion4saudi's hook in the before_validate chain.
	At this point, claudion4saudi has already set all items to the document-level ZATCA template.
	We need to detect if the user had manually set different templates per item.
	
	Since we can't know the user's original selection after claudion4saudi overwrites it,
	we use a different approach: we check if items have DIFFERENT tax templates set
	(which means the user manually changed them) and preserve those.
	"""
	# Store the current state (post-claudion4saudi, pre-ERPNext-validate)
	# If items have different templates, the user has manually overridden them
	if not hasattr(doc, '_user_tax_template_selection'):
		doc._user_tax_template_selection = {}
		for item in doc.items:
			if item.item_code and item.item_tax_template:
				doc._user_tax_template_selection[item.name or item.idx] = item.item_tax_template


#completed
@frappe.whitelist()
def preserve_item_tax_template(doc, method=None):
	"""Restore user-selected item_tax_template after ERPNext validate overwrites it"""
	if hasattr(doc, '_user_tax_template_selection'):
		import json
		from erpnext.stock.get_item_details import get_item_tax_map
		
		changed = False
		for item in doc.items:
			key = item.name or item.idx
			saved_template = doc._user_tax_template_selection.get(key)
			if saved_template and item.item_tax_template != saved_template:
				template_company = frappe.db.get_value("Item Tax Template", saved_template, "company")
				if template_company == doc.company:
					item.item_tax_template = saved_template
					item.item_tax_rate = get_item_tax_map(
						company=doc.company,
						item_tax_template=saved_template,
						as_json=True,
					)
					changed = True
		
		if changed:
			# Manually recalculate tax amounts without calling calculate_taxes_and_totals
			# (which would re-trigger validate_item_tax_template and overwrite again)
			for tax in doc.taxes:
				item_wise_detail = {}
				total_tax_amount = 0.0
				
				for item in doc.items:
					item_tax_map = json.loads(item.item_tax_rate) if item.item_tax_rate else {}
					tax_rate = item_tax_map.get(tax.account_head, tax.rate)
					
					if tax.charge_type == "On Net Total":
						tax_amount = flt(item.net_amount * tax_rate / 100.0, tax.precision("tax_amount"))
					else:
						tax_amount = flt(tax.tax_amount, tax.precision("tax_amount"))
					
					item_wise_detail[item.item_code] = [tax_rate, tax_amount]
					total_tax_amount += tax_amount
				
				tax.item_wise_tax_detail = json.dumps(item_wise_detail)
				tax.tax_amount = total_tax_amount
				tax.tax_amount_after_discount_amount = total_tax_amount
				tax.base_tax_amount = total_tax_amount
				tax.base_tax_amount_after_discount_amount = total_tax_amount
				tax.total = flt(doc.net_total + total_tax_amount, tax.precision("total"))
				tax.base_total = tax.total
			
			# Update doc totals
			doc.total_taxes_and_charges = sum(t.tax_amount for t in doc.taxes)
			doc.base_total_taxes_and_charges = doc.total_taxes_and_charges
			doc.grand_total = flt(doc.net_total + doc.total_taxes_and_charges, doc.precision("grand_total"))
			doc.base_grand_total = doc.grand_total


@frappe.whitelist()
def set_expense_account_from_division(doc, method):
	company = doc.company
	division = doc.custom_division
	if not division:
		return
	
	# Get COG, SRBNB and COS from Division Account Details
	div_details = frappe.db.get_value("Division Account Details", 
		{"parent": division, "company": company}, 
		["expense_account", "snrb_account", "cos_account"], as_dict=True)
	
	if not div_details:
		return
	
	# Check if update_stock is disabled on the PI
	update_stock_disabled = doc.update_stock == 0 if hasattr(doc, 'update_stock') else False
	
	for item in doc.items:
		if not item.item_code:
			continue
		
		# Check if item is a stock item
		is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
		
		# Check if item has a linked Purchase Receipt
		pr_field = None
		if hasattr(item, 'purchase_receipt_item') and item.purchase_receipt_item:
			pr_field = item.purchase_receipt_item
		elif hasattr(item, 'purchase_receipt') and item.purchase_receipt:
			pr_field = item.purchase_receipt
		
		has_pr = frappe.db.exists("Purchase Receipt Item", {"name": pr_field}) if pr_field else False
		
		# Stock items with update_stock=0 should always use SRBNB (clearing GRNI from PR)
		if is_stock_item and update_stock_disabled:
			if div_details.snrb_account:
				item.expense_account = div_details.snrb_account
		elif is_stock_item:
			# Stock items with update_stock=1 use COG
			if div_details.expense_account:
				item.expense_account = div_details.expense_account
		else:
			# Non-stock items: default to COS, but respect manual override
			# Replace COG-type accounts (auto-filled from Item Default) with COS,
			# but keep any other account the user set (e.g. Saber Charges, COS)
			cos_acc = div_details.cos_account or div_details.expense_account
			if not cos_acc:
				continue
			if not item.expense_account:
				item.expense_account = cos_acc
			elif item.expense_account != cos_acc:
				# Check if current account is a COG-type account (auto-filled default)
				current_type = frappe.db.get_value("Account", item.expense_account, "account_type")
				if current_type == "Cost of Goods Sold":
					item.expense_account = cos_acc

def set_snrb_account_from_division(doc, method):
	company = doc.company
	division = doc.custom_division
	if not division:
		return
	snrb_account = frappe.db.get_value("Division Account Details",{"parent": division,"company": company},"snrb_account")
	if not snrb_account:
		return
	for item in doc.items:
		if not item.item_code:
			continue
		item.expense_account = snrb_account

import frappe
@frappe.whitelist()
def set_income_account_from_division(doc, method):
	company = doc.company
	division = doc.custom_division
	if not division:
		return
	income_account = frappe.db.get_value("Division Account Details",{"parent": division,"company": company},"income_account")
	if not income_account:
		return
	for item in doc.items:
		if not item.item_code:
			continue
		item.income_account = income_account

import frappe
import re

@frappe.whitelist()
def set_zatca_exemption_from_category(doc, method):
	"""Auto-set exemption reason code and export flag based on ZATCA tax category."""
	category = doc.get("custom_zatca_tax_category")
	if not category:
		return
	if category == "Services outside scope of tax / Not subject to VAT":
		doc.custom_exemption_reason_code = "VATEX-SA-OOS"
		doc.custom_zatca_export_invoice = 1
	elif category == "Zero Rated":
		if not doc.get("custom_exemption_reason_code") or doc.get("custom_exemption_reason_code") == "Standard 15%":
			doc.custom_exemption_reason_code = "VATEX-SA-29"
	elif category == "Standard":
		if not doc.get("custom_exemption_reason_code"):
			doc.custom_exemption_reason_code = "Standard 15%"

#completed
@frappe.whitelist()
def get_inventory_account_for_division(division=None,company=None ):
	if not division:
		return
	inventory_account = frappe.db.get_value(
		"Division Account Details", {"parent": division,"company": company},"inventory_account")
	if inventory_account:
		return inventory_account

def extract_keyword_from_division(division):
	match = re.search(r'([A-Za-z\s]+)\s+Division', division)
	if match:
		return match.group(1).strip()
	return division.split('-')[0].strip()


def set_inventory_account_from_division(doc, method):
	company = doc.company
	division = doc.custom_division

	if not division:
		return
	inventory_account = frappe.db.get_value(
		"Division Account Details", {"parent": division,"company": company},"inventory_account")
	if inventory_account:
		doc.custom_inventory_account = inventory_account

#completed
import frappe
import os
import openpyxl
import tempfile
from frappe.utils.csvutils import read_csv_content
from frappe.utils.file_manager import get_file

@frappe.whitelist()
def upload_item_sheet(docname, file_url):
	try:
		file_doc, file_content_or_path = get_file(file_url)
		if os.path.exists(file_content_or_path):
			filepath = file_content_or_path
		else:
			suffix = ".xlsx" if file_url.endswith(".xlsx") else ".csv"
			tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
			if isinstance(file_content_or_path, bytes):
				tmp.write(file_content_or_path)
			else:
				tmp.write(file_content_or_path.encode())
			tmp.close()
			filepath = tmp.name

		ext = os.path.splitext(filepath)[1].lower()

		doc = frappe.get_doc("Quotation", docname)

		if ext == ".xlsx":
			wb = openpyxl.load_workbook(filepath, data_only=True)
			ws = wb.active
			for row in ws.iter_rows(min_row=2, values_only=True):
				if not any(row): 
					continue
				item_code, qty, rate = row
				doc.append("items", {
					"item_code": item_code,
					"qty": qty,
					"rate": rate,
					"custom_cost":rate,
					"custom_total_costcompany_currency":rate*qty*doc.custom_brand_conversion_rate
				})

		elif ext == ".csv":
			with open(filepath, "r", encoding="utf-8-sig") as f:
				rows = read_csv_content(f.read())
			for row in rows[1:]:
				if not any(row):
					continue
				item_code, qty, rate = row
				doc.append("items", {
					"item_code": item_code,
					"qty": qty,
					"rate": rate,
					"custom_cost":rate,
					"custom_total_costcompany_currency":rate*qty*doc.custom_brand_conversion_rate
				})
				# item_code, item_name, qty, uom, discount_per, discount_rate, discount_amount, rate, amount = row
				# doc.append("items", {
				#     "item_code": item_code,
				#     "item_name": item_name,
				#     "qty": qty,
				#     "uom": uom,
				#     "discount_percentage": discount_per,
				#     "discount_amount": discount_amount,
				#     "rate": rate,
				#     "amount": amount
				# })

		else:
			frappe.throw(f"Unsupported file format: {ext}")

		doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {"status": "success", "message": "Items imported successfully."}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Item Sheet Import Failed")
		return {"status": "error", "message": str(e)}


import frappe
import os
import openpyxl
import tempfile
from frappe.utils.csvutils import read_csv_content
from frappe.utils.file_manager import get_file

@frappe.whitelist()
def upload_item_sheet_po(docname, file_url):
	try:
		file_doc, file_content_or_path = get_file(file_url)
		if os.path.exists(file_content_or_path):
			filepath = file_content_or_path
		else:
			suffix = ".xlsx" if file_url.endswith(".xlsx") else ".csv"
			tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
			if isinstance(file_content_or_path, bytes):
				tmp.write(file_content_or_path)
			else:
				tmp.write(file_content_or_path.encode())
			tmp.close()
			filepath = tmp.name

		ext = os.path.splitext(filepath)[1].lower()

		doc = frappe.get_doc("Purchase Order", docname)

		if ext == ".xlsx":
			wb = openpyxl.load_workbook(filepath, data_only=True)
			ws = wb.active
			for row in ws.iter_rows(min_row=2, values_only=True):
				if not any(row): 
					continue
				item_code, qty, rate = row
				doc.append("items", {
					"item_code": item_code,
					"qty": qty,
					"rate": rate
				})

		elif ext == ".csv":
			with open(filepath, "r", encoding="utf-8-sig") as f:
				rows = read_csv_content(f.read())
			for row in rows[1:]:
				if not any(row):
					continue
				item_code, qty, rate = row
				doc.append("items", {
					"item_code": item_code,
					"qty": qty,
					"rate": rate
				})
				# item_code, item_name, qty, uom, discount_per, discount_rate, discount_amount, rate, amount = row
				# doc.append("items", {
				#     "item_code": item_code,
				#     "item_name": item_name,
				#     "qty": qty,
				#     "uom": uom,
				#     "discount_percentage": discount_per,
				#     "discount_amount": discount_amount,
				#     "rate": rate,
				#     "amount": amount
				# })

		else:
			frappe.throw(f"Unsupported file format: {ext}")

		doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {"status": "success", "message": "Items imported successfully."}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Item Sheet Import Failed")
		return {"status": "error", "message": str(e)}



# residency_scanner.py

import frappe
from frappe import _

@frappe.whitelist()
def create_residency_permit(resident_id, resident_name, ocr_text=None):
	doc = frappe.get_doc({
		"doctype": "Residency Permit Details",
		"qid": resident_id,
		"name1": resident_name,
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"status": "success", "docname": doc.name}

@frappe.whitelist()
def get_item_ledger(item_code, from_date, to_date, warehouse=None):
	filters = {
		"item_code": item_code,
		"posting_date": ["between", [from_date, to_date]],"is_cancelled":0
	}
	if warehouse:
		filters["warehouse"] = warehouse

	ledgers = frappe.get_all(
		"Stock Ledger Entry",
		filters=filters,
		fields=[
			"posting_date",
			"voucher_type",
			"voucher_no",
			"warehouse",
			"actual_qty",
			"qty_after_transaction"
		],
		order_by="posting_date asc"
	)
	if ledgers:
		return format_ledger_response(ledgers)

	fallback_filters = {
		"item_code": item_code,
		"posting_date": ["<=", to_date],"is_cancelled":0
	}
	if warehouse:
		fallback_filters["warehouse"] = warehouse

	fallback_ledgers = frappe.get_all(
		"Stock Ledger Entry",
		filters=fallback_filters,
		fields=[
			"posting_date",
			"voucher_type",
			"voucher_no",
			"warehouse",
			"actual_qty",
			"qty_after_transaction"
		],
		order_by="posting_date asc"
	)

	return format_ledger_response(fallback_ledgers)


def format_ledger_response(ledgers):
	"""Format serial numbers and return"""
	result = []
	for idx, l in enumerate(ledgers, 1):
		result.append({
			"s_no": idx,
			"posting_date": l.posting_date,
			"voucher_type": l.voucher_type,
			"voucher_no": l.voucher_no,
			"warehouse": l.warehouse,
			"actual_qty": l.actual_qty,
			"balance_qty": l.qty_after_transaction
		})
	return result

@frappe.whitelist()
def restrict_expense_claim(doc, method):
	import datetime
	from frappe.utils import today, add_days, getdate

	current_time = datetime.datetime.now()
	current_date = today()
	if isinstance(current_date, str):
		current_date = datetime.datetime.strptime(current_date, "%Y-%m-%d").date()

	current_month = current_time.month
	current_year = current_time.year
	if current_month == 1:
		previous_month = 12
		previous_month_year = current_year - 1
	else:
		previous_month = current_month - 1
		previous_month_year = current_year

	if doc.custom_ec_to_date:
		if isinstance(doc.custom_ec_to_date, str):
			claim_date = datetime.datetime.strptime(doc.custom_ec_to_date, "%Y-%m-%d").date()
		else:
			claim_date = doc.custom_ec_to_date

		if claim_date.year == previous_month_year and claim_date.month == previous_month:

			allowed_upto = add_days(claim_date, 3)

			if current_date > allowed_upto:
				frappe.throw("Expense Claims for the previous month are not allowed after the first 3 days of the current month.")

			if current_date.day > 3:
				frappe.throw("Expense Claims for the previous month are not allowed after the 3rd day of the month.")

		else:
			pass




@frappe.whitelist()
def process_uploaded_file(file_url, quotation_name):
	import frappe, os
	from io import BytesIO
	from frappe.utils.file_manager import get_file
	from openpyxl import load_workbook

	file_doc = frappe.get_doc("File", {"file_url": file_url})
	content = None
	file_path = None

	try:
		file_path = frappe.utils.get_site_path(file_doc.file_url.strip("/"))
		if not os.path.exists(file_path):
			raise FileNotFoundError
	except Exception:
		content = file_doc.get_content()

	try:
		if content:
			wb = load_workbook(filename=BytesIO(content), data_only=True)
		else:
			wb = load_workbook(filename=file_path, data_only=True)
		sheet = wb.active
	except Exception as e:
		frappe.throw(f"Unable to read Excel file: {str(e)}")

	rows = list(sheet.iter_rows(values_only=True))
	if not rows:
		frappe.throw("Excel file is empty.")

   

	
	quotation = frappe.get_doc("Quotation", quotation_name)
	if quotation.custom_brand == "Pennbarry":
		data_rows = rows[2:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[9] or 0
			rate = row_vals[10] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:min(8, len(row_vals))] if v]

			if brand:
				item_name_parts.append(str(brand).strip())


			item_name = "-".join(item_name_parts)
			item_description_data=[str(v).strip() for v in row_vals[:min(8, len(row_vals))] if v]
			item_description="-".join(item_description_data)
			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
		frappe.db.commit()
	elif quotation.custom_brand == "Hattersley":
		quotation.price_list = ""

		data_rows = rows[0:]
		for pp in data_rows:
			if not pp[6] or pp[0] == "Qty":
				continue

			# Description should be index 1 to 4 only
			description = "-".join(str(x) for x in pp[1:4] if x)

			# Rate logic
			rate = pp[4] if pp[4] else pp[5]

			quotation.append("items", {
				"item_code": pp[6],
				"item_name": pp[7],
				"qty": pp[0],
				"rate": rate,
				"description": description,
			})
		for row in list(quotation.items):
			if not row.item_code:
				quotation.remove(row)

		quotation.save(ignore_permissions=True)
		frappe.db.commit()

	elif quotation.custom_brand == "Antec Controls":
		data_rows = rows[2:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[4] or 0
			rate = row_vals[5] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:3] if v]
			item_description_data=[str(v).strip() for v in row_vals[:4] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description= "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
		frappe.db.commit()
	elif quotation.custom_brand == "EH Price-VAV/CAV":
		data_rows = rows[1:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[1] or 0
			rate = row_vals[11] or 0


			item_name_parts = [str(v).strip() for v in row_vals[2:11] if v]
			item_description_data = [str(v).strip() for v in row_vals[2:11] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())
			# item_description_data.append("""Variable Air Volume - Pressure Independent Type
			#         Casing : - 20mm Ga Galvanized Steel Sheet (Double skin)
			#         Insulation : - 1" Insulation (48kg/m³, WGF)
			#         Controls : - Neptronic – Bacnet  MS/TP - (EVCB14NIT0S Actuator + TDU00-100 -Thermostat)
			#         Electric Heater : - Neptronic - Modulating Type.
			#         Attenuator : - ATTSP(Where Mentioned)
			#         Accessories : HB - Hanger Bracket, GT - Gauge taps, DSW - Disconnect switch, Transformer """)
			item_name = "-".join(item_name_parts)
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		# quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
	elif quotation.custom_brand == "EH Price-SA":
		data_rows = rows[1:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[8] or 0
			rate = row_vals[9] or 0


			item_name_parts = [str(v).strip() for v in row_vals[1:8] if v]
			item_description_data = [str(v).strip() for v in row_vals[1:8] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
	elif quotation.custom_brand == "EH Price-Dampers":
		data_rows = rows[1:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[7] or 0
			rate = row_vals[8] or 0


			item_name_parts = [str(v).strip() for v in row_vals[1:7] if v]
			item_description_data = [str(v).strip() for v in row_vals[1:7] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			# item_description_data.append("""Motorised Smoke & Fire Damper
			#     Model : FSD-3V-S-231 ( UL Classified) - Class I - (3 Hrs.)
			#     Frame : 16 gauge galvanized steel construction
			#     Blade : 16 gauge triple V grove galvanized steel construction
			#     Fusible Link : UL Listed , Electro-thermal fusible link with 165°F temperature tripping point.
			#     Actuator : Honeywell ,  Spring return Complies with UL873 standard.""")
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.custom_company=quotation.company
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)

	elif quotation.custom_brand == "Vortice":
		data_rows = rows[1:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[5] or 0
			rate = row_vals[6] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:5] if v]
			item_description_data=[str(v).strip() for v in row_vals[:5] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description= "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
		frappe.db.commit()

	return "Items created successfully"





@frappe.whitelist()
def process_uploaded_file_po_create(file_url, division_code, product_short, division, product, po_name, brand = None):
	"""
	Process Excel file, create Item documents if not exist, 
	and return item data for appending to PO.
	"""
	import frappe
	from io import BytesIO
	from openpyxl import load_workbook
	from frappe.utils import today

	file_doc = frappe.get_doc("File", {"file_url": file_url})
	content = file_doc.get_content()

	wb = load_workbook(filename=BytesIO(content), data_only=True)
	sheet = wb.active
	rows = list(sheet.iter_rows(values_only=True))
	if len(rows) <= 2:
		frappe.throw("Excel is empty or missing data rows")

	data_rows = rows[2:]  # skip header
	items = []

	prefix = f"{division_code}-{product_short}"

	for idx, row in enumerate(data_rows, start=3):
		if not any(row): continue

		row_vals = list(row)
		qty = float(row_vals[9] or 1)
		rate = float(row_vals[10] or 0)
		item_name_parts = [str(v).strip() for v in row_vals[:min(8, len(row_vals))] if v]

		if brand:
			item_name_parts.append(str(brand).strip())


		if not item_name_parts:
			frappe.throw(f"Row #{idx}: Item name is empty")

		item_name = "-".join(item_name_parts)

		# Check if Item exists
		existing_item = frappe.db.get_value(
			"Item",
			{"item_name": item_name, "item_code": ["like", f"{prefix}%"]},
			"name"
		)

		if existing_item:
			item_code = existing_item
		else:
			# Generate new item_code
			last_item = frappe.db.sql("""
				SELECT item_code FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)
			num = 0
			if last_item:
				try:
					num = int(last_item[0]["item_code"].split("-")[-1])
				except: num = 0
			item_code = f"{prefix}-{num + 1:06d}"

			# Create Item document
			item_doc = frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_name,
				"description": item_name,
				"item_group": division,
				"custom_product":product,
				"custom_auto_created_item": 1,
				"custom_purchase_order_reference":po_name
			})
			item_doc.insert(ignore_permissions=True)
			frappe.db.commit()

		# Add to list for PO
		items.append({
			"item_code": item_code,
			"item_name": item_name,
			"qty": qty,
			"rate": rate
		})

	return items

#completed
from frappe.utils import today
@frappe.whitelist()
def process_uploaded_file_so(file_url, salesorder_name):
	import frappe, os
	from io import BytesIO
	from frappe.utils.file_manager import get_file
	from openpyxl import load_workbook

	file_doc = frappe.get_doc("File", {"file_url": file_url})
	content = None
	file_path = None

	try:
		file_path = frappe.utils.get_site_path(file_doc.file_url.strip("/"))
		if not os.path.exists(file_path):
			raise FileNotFoundError
	except Exception:
		content = file_doc.get_content()

	try:
		if content:
			wb = load_workbook(filename=BytesIO(content), data_only=True)
		else:
			wb = load_workbook(filename=file_path, data_only=True)
		sheet = wb.active
	except Exception as e:
		frappe.throw(f"Unable to read Excel file: {str(e)}")

	rows = list(sheet.iter_rows(values_only=True))
	if not rows:
		frappe.throw("Excel file is empty.")

	data_rows = rows[2:]

	salesorder = frappe.get_doc("Sales Order", salesorder_name)
	division_code = salesorder.custom_division_short_code
	product_short = salesorder.custom_product_short_code
	cost_center = salesorder.cost_center
	brand = salesorder.custom_brand
	quo = salesorder.custom_brand_exchange_rate
	conver = salesorder.conversion_rate

	if salesorder.custom_brand == "Pennbarry":
		salesorder.items = [row for row in salesorder.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[9] or 0
			rate = row_vals[10] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:min(8, len(row_vals))] if v]

			if brand:
				item_name_parts.append(str(brand).strip())


			item_name = "-".join(item_name_parts)

			item_description_data = [str(v).strip() for v in row_vals[:min(8, len(row_vals))] if v]
			item_description = "-".join(item_description_data)
			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["item_name"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()
	
	elif salesorder.custom_brand == "Antec Controls":
		salesorder.items = [row for row in salesorder.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[4] or 0
			rate = row_vals[5] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:3] if v]
			item_description_data=[str(v).strip() for v in row_vals[:4] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description= "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()
	elif salesorder.custom_brand == "EH Price-VAV":
		salesorder.items = [row for row in salesorder.items if row.item_code]
		data_rows = rows[1:]
		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[1] or 0
			rate = row_vals[11] or 0


			item_name_parts = [str(v).strip() for v in row_vals[2:11] if v]
			item_description_data = [str(v).strip() for v in row_vals[2:11] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())
			# item_description_data.append("""Variable Air Volume - Pressure Independent Type
			#         Casing : - 20mm Ga Galvanized Steel Sheet (Double skin)
			#         Insulation : - 1" Insulation (48kg/m³, WGF)
			#         Controls : - Neptronic – Bacnet  MS/TP - (EVCB14NIT0S Actuator + TDU00-100 -Thermostat)
			#         Electric Heater : - Neptronic - Modulating Type.
			#         Attenuator : - ATTSP(Where Mentioned)
			#         Accessories : HB - Hanger Bracket, GT - Gauge taps, DSW - Disconnect switch, Transformer """)
			item_name = "-".join(item_name_parts)
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()
	elif salesorder.custom_brand == "EH Price-SA":
		salesorder.items = [row for row in salesorder.items if row.item_code]
		data_rows = rows[1:]
		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[8] or 0
			rate = row_vals[9] or 0


			item_name_parts = [str(v).strip() for v in row_vals[1:8] if v]
			item_description_data = [str(v).strip() for v in row_vals[1:8] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()
	elif salesorder.custom_brand == "EH Price-Dampers":
		salesorder.items = [row for row in salesorder.items if row.item_code]
		data_rows = rows[1:]
		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[7] or 0
			rate = row_vals[8] or 0


			item_name_parts = [str(v).strip() for v in row_vals[1:7] if v]
			item_description_data = [str(v).strip() for v in row_vals[1:7] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			# item_description_data.append("""Motorised Smoke & Fire Damper
			#     Model : FSD-3V-S-231 ( UL Classified) - Class I - (3 Hrs.)
			#     Frame : 16 gauge galvanized steel construction
			#     Blade : 16 gauge triple V grove galvanized steel construction
			#     Fusible Link : UL Listed , Electro-thermal fusible link with 165°F temperature tripping point.
			#     Actuator : Honeywell ,  Spring return Complies with UL873 standard.""")
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()

	elif salesorder.custom_brand == "Vortice":
		salesorder.items = [row for row in salesorder.items if row.item_code]
		data_rows = rows[1:]
		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[5] or 0
			rate = row_vals[6] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:5] if v]
			item_description_data=[str(v).strip() for v in row_vals[:5] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description= "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": salesorder.custom_division,
				"custom_sales_order_reference": salesorder_name,
				"custom_auto_created_item": 1,
				"custom_product": salesorder.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_cost": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_custom_total_costcompany_currency": rate * qty * quo

			})

		salesorder.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"income_account": "4001 - Revenue - HVAC - JGB",
			},
			"Valves and Pipeline (VLP)": {
				"income_account": "4002 - Revenue - Valves & Pipelines - JGB",
			},
			"Filtration Division (FRD)": {
				"income_account": "4004 - Revenue - Filtration - JGB",
			},
			"Waterworks Division (WTR)": {
				"income_account": "4003 - Revenue - Waterworks - JGB",
			}
		}

		div = salesorder.custom_division

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		salesorder.set("items", [])
		for it in created_items:
			salesorder.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"delivery_date":salesorder.delivery_date,
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["custom_price_cost"]/salesorder.conversion_rate,
				"cost_center": cost_center,
				"delivery_date": today(),
				"custom_income_account": income_account,
				"custom_cost":it["rate"],
				"base_rate": it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_custom_total_costcompany_currency": it["custom_custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_custom_total_costcompany_currency"]

			})

		salesorder.save(ignore_permissions=True)
		frappe.db.commit()
	return "Items created successfully"


#completed
import frappe
import random

@frappe.whitelist()
def get_unique_random_number(doctype):
	while True:
		number = random.randint(10000000, 99999999)  # 8-digit random number
		exists = frappe.db.exists(doctype, {"custom_po_name": number})
		if not exists:
			return number



import frappe

@frappe.whitelist()
def validate_items_before_hod_review(doc, method):
	if doc.workflow_state == "HOD Pending":
		if not doc.items:
			frappe.throw("Cannot move to HOD review — No items added in the Quotation.")
		
		for item in doc.items:
			if not item.item_code:
				frappe.throw("Cannot move to HOD review — No Items added in the Quotation.")
	

#completed
@frappe.whitelist()
def get_selling_cost_center(item_code, company):
	return frappe.db.get_value(
		"Item Default",
		{"parent": item_code, "company": company},
		"selling_cost_center"
	)



#completed
import frappe
@frappe.whitelist()
def set_po_series(doc, method):
	prefix = "POJGBKSA"
	latest = frappe.db.sql("""
		SELECT name FROM `tabPurchase Order`
		WHERE name LIKE %s and amended_from is null
		ORDER BY name DESC
		LIMIT 1
	""", (prefix + "%",), as_dict=True)

	if latest:
		last_number = int(latest[0].name.replace(prefix, ""))
		new_number = last_number + 1
	else:
		new_number = 2001

	doc.custom_po_naming_series = f"{prefix}{new_number}"

	# doc.naming_series = prefix


import frappe

@frappe.whitelist()
def get_next_po_series():
	prefix = "POJGBKSA"
	latest = frappe.db.sql("""
		SELECT name FROM `tabPurchase Order`
		WHERE name LIKE %s
		ORDER BY name DESC
		LIMIT 1
	""", (prefix + "%",), as_dict=True)

	if latest:
		try:
			last_number = int(latest[0].name.replace(prefix, ""))
		except:
			last_number = 2000
		new_number = last_number + 1
	else:
		new_number = 2001

	return f"{prefix}{new_number}"



import frappe
@frappe.whitelist()
def set_so_series(doc, method):
	prefix = "SOJGBKSA"
	latest = frappe.db.sql("""
		SELECT name FROM `tabSales Order`
		WHERE name LIKE %s and amended_from is null
		ORDER BY name DESC
		LIMIT 1
	""", (prefix + "%",), as_dict=True)

	if latest:
		last_number = int(latest[0].name.replace(prefix, ""))
		new_number = last_number + 1
	else:
		new_number = 2001

	doc.custom_so_naming_series = f"{prefix}{new_number}"
	# doc.naming_series = prefix



import frappe

@frappe.whitelist()
def send_notification_to_sales(doc, method):
	po_list = list(set([item.purchase_order for item in doc.items if item.purchase_order]))

	if not po_list:
		return

	for po in po_list:
		so = frappe.db.get_value(
			"Purchase Order Item",
			{"parent": po},
			"sales_order"
		)
		if not so:
			continue

		sales_persons = frappe.db.get_all(
			"Sales Order",
			{'name': so},
			['custom_sales_person']
		)

		if not sales_persons:
			continue

		for sp in sales_persons:
			email = sp.custom_sales_person

			if not email:
				continue

			frappe.sendmail(
				recipients=[email],
				subject=f"Purchase Receipt Created for Sales Order {so}",
				message=f"""
					Dear Sales Person,<br><br>
					Purchase Receipt <b>{doc.name}</b> has been created for Sales Order <b>{so}</b>.<br><br>
					Regards,<br>
					ERP
				"""
			)


#completed		
import frappe
from frappe.utils.file_manager import save_file
from openpyxl import Workbook

@frappe.whitelist()
def get_item_template():

	wb = Workbook()
	ws = wb.active
	ws.title = "Item Template"

	# Add only headings
	ws.append(["Item Code", "Qty", "Rate"])

	# Save temporarily
	file_path = "/tmp/item_template.xlsx"
	wb.save(file_path)

	# Read file
	with open(file_path, "rb") as f:
		file = save_file(
			"Item_Template.xlsx",
			f.read(),
			None,   # dt → no doctype
			None,   # dn → no docname
			folder="Home/Attachments",
			is_private=0
		)

	return file.file_url

# @frappe.whitelist()
# def get_item_without_code_template(brand):
# 	brand_doc = frappe.get_doc("Brand", brand)
# 	file_url = brand_doc.custom_download_template

# 	if not file_url:
# 		frappe.throw("No template attached in this Brand")

# 	file_doc = frappe.get_doc("File", {"file_url": file_url})

# 	file_content = file_doc.get_content()

# 	frappe.local.response.filename = file_doc.file_name
# 	frappe.local.response.filecontent = file_content
# 	frappe.local.response.type = "download"


#completed
import frappe
import openpyxl
from openpyxl import Workbook
from io import BytesIO

@frappe.whitelist()
def get_item_without_code_template(brand=None, product=None):
	brand_doc = frappe.get_doc("Brand", brand)
	if brand_doc.custom_download_template:
		file_doc = frappe.get_doc(
			"File",
			{"file_url": brand_doc.custom_download_template}
		)
		file_content = file_doc.get_content()
		frappe.local.response.filename = file_doc.file_name
		frappe.local.response.filecontent = file_content
		frappe.local.response.type = "download"
		return
	headers = []
	if product:
		product_doc = frappe.get_doc("Product", product)
		for row in product_doc.product_naming:
			if row.title:
				headers.append(row.title)
	headers.extend(["Qty", "Rate"])
	wb = Workbook()
	ws = wb.active
	ws.title = "Template"
	for col_num, header in enumerate(headers, 1):
		ws.cell(row=1, column=col_num).value = header
	output = BytesIO()
	wb.save(output)
	frappe.local.response.filename = "Default_Template.xlsx"
	frappe.local.response.filecontent = output.getvalue()
	frappe.local.response.type = "download"


# your_app/custom/employee.py
import frappe

import frappe

def before_save_employee(doc, method):
	"""
	Auto-generate Employee Number based on the last employee_number in DB
	"""
	if doc.is_new() :
		# Get the highest employee_number from all Employee records
		last_emp = frappe.db.sql("""
			SELECT MAX(CAST(employee_number AS UNSIGNED)) 
			FROM `tabEmployee`
			WHERE employee_number REGEXP '^[0-9]+$'
		""")[0][0]

		if last_emp:
			new_number = int(last_emp) + 1

		doc.employee_number = str(new_number)
		doc.name = str(new_number)



# def merge_full_name_existing_users():
#     users = frappe.get_all("User", filters={"enabled": 1}, fields=["name", "first_name", "middle_name", "last_name"])
#     # users="gafoor@jgbksa.com"
	
#     for user in users:
#         first = user.get("first_name") or ""
#         middle = user.get("middle_name") or ""
#         last = user.get("last_name") or ""

#         full_name = " ".join([first, middle, last]).strip()
#         if frappe.db.get_value("User", user.name, "full_name") != full_name:
#             frappe.db.set_value("User", user.name, "full_name", full_name)
	
#     frappe.db.commit()
#     print("Full names updated for all users.")

@frappe.whitelist()
def validate_sow_amount(doc, method):
	if doc.custom_sow_as_item == 1:
		total_sow_amount = sum(item.sow_amount for item in doc.custom_sow if item.sow_amount)
		if doc.base_total != total_sow_amount:
			frappe.throw(f"Total SOW Amount ({total_sow_amount}) does not match the Quotation Item Amount ({doc.base_total}). Please correct the amounts in the items.")


#completed
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

import frappe

def update_pi_items(doc, method):
	doc.taxes = []
	for ro in doc.purchase_receipts:  
		if not ro.receipt_document:
			continue
		pi = frappe.get_doc("Purchase Invoice", ro.receipt_document)
		ro.supplier = pi.supplier
		ro.grand_total = pi.grand_total
		ro.posting_date = pi.posting_date

	
	for row in doc.custom_purchase_invoice:  
		if not row.receipt_document:
			continue
		pi = frappe.get_doc("Purchase Invoice", row.receipt_document)
		row.supplier = pi.supplier
		row.grand_total = pi.grand_total
		row.posting_date = pi.posting_date

		pi_items = get_pi_items(row.receipt_document)
		

		if not pi_items:
			continue

		for d in pi_items:
			doc.append("taxes", {
				"description": d.get("description"),
				"amount": d.get("amount"),
				"expense_account": d.get("expense_account")
			})
			


import frappe
@frappe.whitelist()
def update_full_name_hook(doc, method):
	first = doc.first_name or ""
	middle = doc.middle_name or ""
	last = doc.last_name or ""
	doc.full_name = " ".join(filter(None, [first, middle, last]))
	
	

#Set the all values in advance invoice table from the below so
@frappe.whitelist()
def update_child_values(so):
	sales=frappe.get_doc("Sales Order",so)
	return sales.items


# #Set the all values in advance invoice from the below so
# @frappe.whitelist()
# def update_normal_values(so):
#     sales=frappe.get_doc("Sales Order",so)
#     return sales.total_bidding_price , sales.project_discount_per , sales.project_discount_amt,sales.discount_tolerance_amount,sales.net_bidding_price,sales.discount_upto

#Update the money in words for advance invoice
#completed
@frappe.whitelist()
def update_advance_money(advance):
	words=frappe.utils.money_in_words(advance)
	return words


#completed
@frappe.whitelist()
def get_series(company,doctype):
	series = frappe.db.get_value("Company",{"name":company},["abbr"])
	return f"{series}-{"RET"}-.YYYY."

#Set the all values in advance invoice from the below so
@frappe.whitelist()
def update_item_values(so):
	sales=frappe.get_doc("Sales Order",so)
	return sales.total_qty , sales.base_total , sales.total

#Create new journal entry while submission of advance invoice
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
	
	
#Cancel the journal entry to match with cancel advance invoice
@frappe.whitelist()
def cancel_journal_entry_retention(doc,method):
	jv = frappe.db.get_value("Journal Entry",{"cheque_no":doc.name},["name"])
	if jv:
		jv_cancel=frappe.get_doc("Journal Entry",jv)
		if jv_cancel.docstatus == 1:
			jv_cancel.cancel()

@frappe.whitelist()
def create_new_address(doc, method):
	# Find existing billing address linked to this customer (by Dynamic Link,
	# not by address_title, so renaming the customer doesn't create duplicates)
	existing_address_name = frappe.db.get_value(
		"Dynamic Link",
		{
			"parenttype": "Address",
			"link_doctype": "Customer",
			"link_name": doc.name,
			"parentfield": "links",
		},
		"parent",
	)

	if not existing_address_name:
		add = frappe.new_doc("Address")
		add.address_type = "Billing"
		add.address_title = doc.customer_name

		add.address_line1 = doc.custom_street_name
		add.custom_address_line_1street_arabic = doc.custom_street_name_in_arabic

		add.address_line2 = doc.custom_district
		add.custom_street_in_arabic = doc.custom_district_in_arabic
		add.custom_area = doc.custom_district
		add.address_in_arabic = doc.custom_district_in_arabic

		add.custom_building_number = doc.custom_building_number
		add.city = doc.custom_city
		add.custom_city_in_arabic   = doc.custom_city_in_arabic
		add.state = doc.custom_state
		add.custom_state_in_arabic = doc.custom_state_in_arabic
		add.custom_additional_number = doc.custom_additional_number
		add.pincode = doc.custom_zippostal_code
		add.email_id = doc.custom_email
		add.phone = doc.custom_contact_no
		add.fax = doc.custom_fax_number_
		add.phone = doc.custom_phone
		add.country = doc.custom_country
		add.custom_country_in_arabic = doc.custom_country_in_arabic
		# Add link to customer
		add.append("links", {
			"link_doctype": "Customer",
			"link_name": doc.name
		})
	else:
		add = frappe.get_doc("Address", existing_address_name)
		if not add.address_type == "Billing":
			add.address_type = "Billing"
		if not add.address_title == doc.customer_name:
			add.address_title = doc.customer_name
		if not add.address_line1 == doc.custom_street_name:
			add.address_line1 = doc.custom_street_name
		if not add.custom_address_line_1street_arabic == doc.custom_street_name_in_arabic:
			add.custom_address_line_1street_arabic = doc.custom_street_name_in_arabic
		if not add.address_line2 == doc.custom_district:
			add.address_line2 = doc.custom_district
		if not add.custom_street_in_arabic == doc.custom_district_in_arabic:
			add.custom_street_in_arabic = doc.custom_district_in_arabic
		if not add.custom_area == doc.custom_district:
			add.custom_area = doc.custom_district
		if not add.address_in_arabic == doc.custom_district_in_arabic:
			add.address_in_arabic = doc.custom_district_in_arabic
		if not add.custom_building_number == doc.custom_building_number:
			add.custom_building_number = doc.custom_building_number
		if not add.city == doc.custom_city:
			add.city = doc.custom_city
		if not add.custom_city_in_arabic == doc.custom_city_in_arabic:
			add.custom_city_in_arabic   = doc.custom_city_in_arabic
		if add.state != doc.custom_state:
			add.state = doc.custom_state
		if add.custom_state_in_arabic != doc.custom_state_in_arabic:
			add.custom_state_in_arabic = doc.custom_state_in_arabic
		if not add.pincode == doc.custom_zippostal_code:
			add.pincode = doc.custom_zippostal_code
		if add.email_id != doc.custom_email:
			add.email_id = doc.custom_email
		if add.phone != doc.custom_contact_no:
			add.phone = doc.custom_contact_no
		if add.fax != doc.custom_fax_number_:
			add.fax = doc.custom_fax_number_
		if add.custom_additional_number != doc.custom_additional_number:
			add.custom_additional_number = doc.custom_additional_number
		if add.phone != doc.custom_phone:
			add.phone = doc.custom_phone
		if add.country != doc.custom_country:
			add.country = doc.custom_country
		if add.custom_country_in_arabic != doc.custom_country_in_arabic:
			add.custom_country_in_arabic = doc.custom_country_in_arabic

		# Ensure the customer link exists on this address
		already_linked = any(
			l.link_doctype == "Customer" and l.link_name == doc.name
			for l in add.links
		)
		if not already_linked:
			add.append("links", {
				"link_doctype": "Customer",
				"link_name": doc.name
			})
	add.save(ignore_permissions=True)
	if not doc.customer_primary_address:
		# doc.customer_primary_address=add.name
		frappe.db.set_value("Customer",doc.name,"customer_primary_address",add.name)
	frappe.db.commit()

@frappe.whitelist()
def create_new_customer_address(doc, method):
	# Find existing billing address linked to this customer (by Dynamic Link,
	# not by address_title, so renaming the customer doesn't create duplicates)
	existing_address_name = frappe.db.get_value(
		"Dynamic Link",
		{
			"parenttype": "Address",
			"link_doctype": "Customer",
			"link_name": doc.name,
			"parentfield": "links",
		},
		"parent",
	)

	if not existing_address_name:
		add = frappe.new_doc("Address")
		add.address_type = "Billing"
		add.address_title = doc.customer_name

		add.address_line1 = doc.custom_street_name
		add.custom_address_line_1street_arabic = doc.custom_street_name_in_arabic

		add.address_line2 = doc.custom_district
		add.custom_street_in_arabic = doc.custom_district_in_arabic
		add.custom_area = doc.custom_district
		add.address_in_arabic = doc.custom_district_in_arabic

		add.custom_building_number = doc.custom_building_number
		add.city = doc.custom_city
		add.custom_city_in_arabic   = doc.custom_city_in_arabic
		add.state = doc.custom_state
		add.custom_state_in_arabic = doc.custom_state_in_arabic
		add.custom_additional_number = doc.custom_additional_number
		add.pincode = doc.custom_zippostal_code
		add.email_id = doc.custom_email
		add.phone = doc.custom_contact_no
		add.fax = doc.custom_fax_number_
		add.phone = doc.custom_phone
		add.country = doc.custom_country
		add.custom_country_in_arabic = doc.custom_country_in_arabic
		# Add link to customer
		add.append("links", {
			"link_doctype": "Customer",
			"link_name": doc.name
		})
	else:
		add = frappe.get_doc("Address", existing_address_name)
		if not add.address_type == "Billing":
			add.address_type = "Billing"
		if not add.address_title == doc.customer_name:
			add.address_title = doc.customer_name
		if not add.address_line1 == doc.custom_street_name:
			add.address_line1 = doc.custom_street_name
		if not add.custom_address_line_1street_arabic == doc.custom_street_name_in_arabic:
			add.custom_address_line_1street_arabic = doc.custom_street_name_in_arabic
		if not add.address_line2 == doc.custom_district:
			add.address_line2 = doc.custom_district
		if not add.custom_street_in_arabic == doc.custom_district_in_arabic:
			add.custom_street_in_arabic = doc.custom_district_in_arabic
		if not add.custom_area == doc.custom_district:
			add.custom_area = doc.custom_district
		if not add.address_in_arabic == doc.custom_district_in_arabic:
			add.address_in_arabic = doc.custom_district_in_arabic
		if not add.custom_building_number == doc.custom_building_number:
			add.custom_building_number = doc.custom_building_number
		if not add.city == doc.custom_city:
			add.city = doc.custom_city
		if not add.custom_city_in_arabic == doc.custom_city_in_arabic:
			add.custom_city_in_arabic   = doc.custom_city_in_arabic
		if add.state != doc.custom_state:
			add.state = doc.custom_state
		if add.custom_state_in_arabic != doc.custom_state_in_arabic:
			add.custom_state_in_arabic = doc.custom_state_in_arabic
		if not add.pincode == doc.custom_zippostal_code:
			add.pincode = doc.custom_zippostal_code
		if add.email_id != doc.custom_email:
			add.email_id = doc.custom_email
		if add.phone != doc.custom_contact_no:
			add.phone = doc.custom_contact_no
		if add.fax != doc.custom_fax_number_:
			add.fax = doc.custom_fax_number_
		if add.custom_additional_number != doc.custom_additional_number:
			add.custom_additional_number = doc.custom_additional_number
		if add.phone != doc.custom_phone:
			add.phone = doc.custom_phone
		if add.country != doc.custom_country:
			add.country = doc.custom_country
		if add.custom_country_in_arabic != doc.custom_country_in_arabic:
			add.custom_country_in_arabic = doc.custom_country_in_arabic

		# Ensure the customer link exists on this address
		already_linked = any(
			l.link_doctype == "Customer" and l.link_name == doc.name
			for l in add.links
		)
		if not already_linked:
			add.append("links", {
				"link_doctype": "Customer",
				"link_name": doc.name
			})
	add.save(ignore_permissions=True)
	if not doc.customer_primary_address:
		doc.customer_primary_address=add.name
	doc.save()
	frappe.db.commit()


	
import datetime
@frappe.whitelist()
def allocate_annual_vacation():
	
	today = frappe.utils.getdate()
	employees = frappe.get_all("Employee", filters ={'status':"Active"},fields=["name", "date_of_joining"])
	for emp in employees:
		doj = emp.date_of_joining
		if not doj:
			continue
		
		doj = frappe.utils.getdate(doj)

		one_year_date = doj + datetime.timedelta(days=365)
		if today < one_year_date:
			continue
		anniv_this_year = doj.replace(year=today.year)
		if anniv_this_year == today:
			start_date = anniv_this_year
			end_date = anniv_this_year.replace(year=anniv_this_year.year + 1) - datetime.timedelta(days=1)
			existing = frappe.db.exists(
				"Leave Allocation",
				{
					"employee": emp.name,
					"leave_type": "Annual Vacation",
					"from_date": start_date,
					"to_date": end_date,
					"docstatus": ["!=", "2"]
				}
			)

			if existing:
				continue  
			allocation = frappe.new_doc("Leave Allocation")
			allocation.employee = emp.name
			allocation.leave_type = "Annual Vacation"
			allocation.from_date = start_date
			allocation.to_date = end_date
			allocation.new_leaves_allocated = 30
			allocation.save(ignore_permissions=True)
			allocation.submit()

	return "Annual vacation leave allocation checked & created where needed."

   

#completed
import frappe
from frappe.utils import getdate

@frappe.whitelist()
def check_ticket_taken(employee, from_date):
	year = getdate(from_date).year

	exists = frappe.db.exists(
		"Leave Application",
		{
			"employee": employee,
			"custom_ticket_required": 1,
			"docstatus": ["!=", 2],
			"from_date": ["between", [f"{year}-01-01", f"{year}-12-31"]]
		}
	)

	if exists:
		return "ALREADY_TAKEN"
	else:
		return "NOT_TAKEN"


#completed
@frappe.whitelist()
def create_additional_salary(doc,method):
	
	diff=date_diff(doc.end_date,doc.start_date)+1
	year = getdate(doc.start_date).year
	year_start = f"{year}-01-01"
	year_end = f"{year}-12-31"
	
	for i in doc.employees:
		ind_deduction=0
		sl_deduction=0
		basic=frappe.db.get_value("Employee",i.employee,'custom_basic')
		hra=frappe.db.get_value("Employee",i.employee,'custom_hra')
		if frappe.db.exists("Attendance",{"employee": i.employee,"attendance_date": ["between", [year_start, year_end]],"docstatus": 1,"status": "On Leave","leave_type": "Industrial Sick Leave"}):
			att_list = []
			att = frappe.db.get_all(
				"Attendance",
				filters={
					"employee": i.employee,
					"attendance_date": ["between", [year_start, year_end]],
					"docstatus": 1,
					"status": "On Leave",
					"leave_type": "Industrial Sick Leave"
				},
				fields=["attendance_date"],
				order_by="attendance_date asc"    
			)

			att_list = [d.attendance_date for d in att]

			start = getdate(doc.start_date)
			end = getdate(doc.end_date)

			tot_val = 0

			curr = start
			while curr <= end:
				# print(curr)
				if curr in att_list:
					pos = att_list.index(curr) + 1   
					# print(pos)
					if pos > 30:
						tot_val += 1
				curr += timedelta(days=1)
			tot_val=tot_val*0.25
			if basic > 0:
				basic=basic/diff
				basic=basic*tot_val
			if hra > 0:
				hra=hra/diff
				hra=hra*tot_val
			ind_deduction=basic+hra

		if frappe.db.exists("Attendance",{"employee": i.employee,"attendance_date": ["between", [year_start, year_end]],"docstatus": 1,"status": "On Leave","leave_type": "Sick Leave"}):
			att_list = []
			att = frappe.db.get_all(
				"Attendance",
				filters={
					"employee": i.employee,
					"attendance_date": ["between", [year_start, year_end]],
					"docstatus": 1,
					"status": "On Leave",
					"leave_type": "Industrial Sick Leave"
				},
				fields=["attendance_date"],
				order_by="attendance_date asc"    
			)

			att_list = [d.attendance_date for d in att]

			start = getdate(doc.start_date)
			end = getdate(doc.end_date)

			before_90 = 0
			after_90=0

			curr = start
			while curr <= end:
				# print(curr)
				if curr in att_list:
					pos = att_list.index(curr) + 1  
					if pos < 30:
						before_90 += 0
					elif pos > 30 and pos <= 90:
						before_90 += 1
					else:
						after_90 += 1
				curr += timedelta(days=1)
			ded_1=before_90*0.25
			ded_2=after_90*0.5
			if basic > 0:
				basic=basic/diff
				basic_one_by_three=basic*ded_1
				basic_half=basic*ded_2
				basic=basic_half+basic_one_by_three
			if hra > 0:
				hra=hra/diff
				hra_one_by_three=hra*ded_1
				hra_half=hra*ded_2
				hra=hra_half+hra_one_by_three
			sl_deduction=basic+hra

		tot_deduction=sl_deduction+ind_deduction
		if tot_deduction > 0:
			if not frappe.db.exists("Additional Salary",{"payroll_date":["between", [doc.start_date, doc.end_date]],"docstatus":1,"employee":i.employee,"salary_component":"Leave Deduction"}):
				ld=frappe.new_doc("Additional Salary")
				ld.payroll_date=doc.start_date
				ld.employee=i.employee
				ld.salary_component="Leave Deduction"
				ld.amount=tot_deduction
				ld.overwrite_salary_structure_amount=1
				ld.custom_payroll_entry=doc.name
				ld.save(ignore_permissions=True)
				ld.submit()


#completed
@frappe.whitelist()
def delete_additional_salary(doc,method):
	if frappe.db.exists("Additional Salary",{"custom_payroll_entry":doc.name}):
		docs=frappe.db.get_all("Additional Salary",{"custom_payroll_entry":doc.name},['name'])
		for d in docs:
			ld=frappe.get_doc("Additional Salary",d.name)
			if ld.docstatus==1:
				ld.cancel()
			ld.delete()

# def update_pr_currency(doc, method):
#     if doc.custom_logistics_request:
#         if frappe.db.exists("Logistics Request", doc.custom_logistics_request):
#             currency = frappe.db.get_value(
#                 "Logistics Request",
#                 doc.custom_logistics_request,
#                 "currency"
#             )
#             frappe.db.set_value("Purchase Receipt", doc.name, "currency", currency)



@frappe.whitelist()
def check_customer_field_so(doc, method):
	customer = doc.customer
	cust = frappe.get_doc("Customer", customer)

	sections = {
		"Billing": {
			"custom_attention": "Attention",
			"custom_email": "Email",
			"custom_contact_no": "Contact No",
			"custom_territory": "Territory",
			"custom_building_number": "Building Number",
			"custom_street_name": "Street",
			"custom_district": "District",
			"custom_city": "City",
			"custom_state": "State",
			"custom_zippostal_code": "ZIP/Postal Code",
			"custom_phone": "Phone",
			"custom_attention_in_arabic": "Attention in Arabic",
			"custom_email_in_arabic": "Email in Arabic",
			"custom_contact_no_in_arabic": "Contact No in Arabic",
			"custom_territory_in_arabic": "Territory in Arabic",
			"custom_building_number_in_arabic": "Building Number in Arabic",
			"custom_street_in_arabic": "Street in Arabic",
			"custom_district_in_arabic": "District in Arabic",
			"custom_city_in_arabic": "City in Arabic",
			"custom_state_in_arabic": "State in Arabic",
			"custom_postal_code_in_arabic": "ZIP/Postal Code in Arabic",
			"custom_phone_number_in_arabic": "Phone Number in Arabic",
		},
		"Shipping": {
			"custom_attention_": "Attention",
			"custom_email_": "Email",
			"custom_contact_no_": "Contact No",
			"custom_region_": "Territory",
			"custom_building_number_": "Building Number",
			"custom_street": "Street",
			"custom_district_": "District",
			"custom_city_": "City",
			"custom_state_": "State",
			"custom_postal_code": "ZIP/Postal Code",
			"custom_phone_number": "Phone",
			"custom_attention_in_arabic_": "Attention in Arabic",
			"custom_email_in_arabic_": "Email in Arabic",
			"custom_contact_no_in_arabic_": "Contact No in Arabic",
			"custom_territory_in_arabic_": "Territory in Arabic",
			"custom_building_number_in_arabic_": "Building Number in Arabic",
			"custom_street_in_arabic": "Street in Arabic",
			"custom_district_in_arabic_": "District in Arabic",
			"custom_city_in_arabic_": "City in Arabic",
			"custom_state_in_arabic_": "State in Arabic",
			"custom_postal_code_in_arabic": "ZIP/Postal Code in Arabic",
			"custom_phone_number_in_arabic": "Phone Number in Arabic",
		}
	}

	missing_fields = []

	for section_name, fields in sections.items():
		for field, label in fields.items():
			if not cust.get(field):
				missing_fields.append(f"{label} ({section_name})")

	if missing_fields:
		frappe.throw(
			"Please fill the following fields in Customer before saving the Sales Order:\n- " 
			+ "\n- ".join(missing_fields)
		)

# Email to ajmal@jgbksa.com on submission of DN
@frappe.whitelist()
def send_mail_for_dn(doc, method):
	link = frappe.utils.get_url_to_form("Delivery Note", doc.name)
	subject = f"Delivery Note Submitted – {doc.name}"
	message = f"""
	<p>Dear Sir/Madam,</p>
	<p>This is to inform you that the following Delivery Note has been successfully submitted:</p>
	<p>
		<strong>Delivery Note No:</strong>
		<a href="{link}" target="_blank">{doc.name}</a>
	</p>

	<p>Please review the details at your convenience.</p>

	<p>Regards,<br>
	ERP System</p>
	"""
	frappe.sendmail(
		recipients=["ajmal@jgbksa.com"],
		subject=subject,
		message=message
	)

# @frappe.whitelist()
# def update_lr_req():
#     frappe.db.set_value("Logistics Request","LR-2025-00002","etd",None)
#     frappe.db.set_value("Logistics Request","LR-2025-00002","eta",None)
#     frappe.db.set_value("Logistics Request","LR-2025-00002","master_bl_number__awb","")
#     frappe.db.set_value("Logistics Request","LR-2025-00002","custom_schedule",0)
#     frappe.db.set_value("Logistics Request","LR-2025-00002","workflow_state","Scheduled")

#completed
@frappe.whitelist()
def money_in_words_advance_invoice(amt):
	
	if amt:
		amt_word = money_in_words(flt(amt))
		return amt_word


	 
# @frappe.whitelist()
# def update_advance_amount(doc,method):
#     if doc.advance_amount1:
#         frappe.db.set_value("Advance Invoice",doc.name,"advance_amount1",doc.advance_amount1)

@frappe.whitelist()
def create_new_journal_entry(doc,method):
	document = frappe.get_doc("Advance Invoice", doc.name)
	sales=frappe.get_doc("Sales Order",doc.sales_order)
	jv = frappe.new_doc("Journal Entry")
	jv.voucher_type = "Journal Entry"
	jv.company = document.company
	jv.posting_date = doc.transaction_date
	jv.user_remark = f"Customer Name : {sales.customer} Order No : {doc.sales_order} Order Date : {sales.transaction_date} Project : {sales.project}"
	jv.cheque_no = doc.name
	jv.custom_advance_invoice=doc.name
	jv.cheque_date = document.transaction_date
	advance_account = frappe.db.get_value("Company", {"name": document.company}, "custom_default_advance_account")
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



@frappe.whitelist()
def cancel_journal_entry(doc,method):
	jv = frappe.db.get_value("Journal Entry",{"cheque_no":doc.name},["name"])
	if jv:
		jv_cancel=frappe.get_doc("Journal Entry",jv)
		if jv_cancel.docstatus == 1:
			jv_cancel.cancel()
			





# @frappe.whitelist()
# def make_payment_entry_from_advance_sales_invoice(advance_invoice):
# 	ai = frappe.get_doc("Advance Sales Invoice", advance_invoice)

# 	if not ai.sales_order:
# 		frappe.throw(_("Sales Order is not linked to this Advance Sales Invoice"))

# 	if not flt(ai.grand_total):
# 		frappe.throw(_("Grand Total is required to create Payment Entry"))

# 	existing_pe = frappe.db.sql(
# 		"""
# 		SELECT DISTINCT pe.name
# 		FROM `tabPayment Entry` pe
# 		INNER JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
# 		WHERE pe.docstatus = 1
# 			AND pe.party = %s
# 			AND pe.company = %s
# 			AND per.reference_doctype = 'Sales Order'
# 			AND per.reference_name = %s
# 			AND ROUND(pe.paid_amount, 2) = ROUND(%s, 2)
# 		""",
# 		(ai.party, ai.company, ai.sales_order, flt(ai.grand_total)),
# 		as_dict=1,
# 	)
# 	if existing_pe:
# 		return {
# 			"payment_entry": existing_pe[0].name,
# 			"is_existing": True,
# 		}

# 	return {
# 		"payment_entry": None,
# 		"is_existing": False,
# 	}


#completed
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

	
# @frappe.whitelist()
# def make_payment_entry_from_advance_invoice(advance_invoice):
# 	ai = frappe.get_doc("Proforma Invoice", advance_invoice)

# 	existing_pe = frappe.db.get_value(
# 		"Payment Entry",
# 		{"docstatus": 1, "custom_advance_invoice": ai.name},
# 		"name",
# 	)
# 	if existing_pe:
# 		return {"payment_entry": existing_pe, "is_existing": True}

# 	return {"payment_entry": None, "is_existing": False}

	

#completed
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
	
	  
#completed
@frappe.whitelist()
def update_leave_salary(doc,method):
	if doc.custom_leave_salary:
		if frappe.db.exists('Leave Salary',{'name':doc.custom_leave_salary,'docstatus':['!=',2]}):
			frappe.db.set_value('Leave Salary',doc.custom_leave_salary,'status','Unpaid')
			frappe.db.set_value('Leave Salary',doc.custom_leave_salary,'payment_entry_created',1)


@frappe.whitelist()
def update_party(doc,method):
	if doc.custom_leave_salary:
		if frappe.db.exists('Leave Salary',{'name':doc.custom_leave_salary,'docstatus':['!=',2]}):
			employee=frappe.db.get_value('Leave Salary',doc.custom_leave_salary,'employee')
			doc.party=employee


@frappe.whitelist()
def get_annual_leave_details(employee):
	leaves = frappe.get_all("Leave Application",filters={ "employee": employee,"leave_type": "Annual Vacation","docstatus":["!=",2] , "workflow_state":["!=", "Rejected"]},fields=["from_date","to_date", "total_leave_days","description"], order_by="from_date desc")

	html = """
	<div>
		<table class="table table-bordered table-striped" style="width:100%;">
			<thead>
				<tr>
					<th>S.No</th>
					<th>From Date</th>
					<th>To Date</th>
					<th>No. of Days</th>
					<th>Reason</th>
				</tr>
			</thead>
			<tbody>
	"""

	if leaves:
		for i, l in enumerate(leaves, start=1):
			html += f"""
				<tr>
					<td>{i}</td>
					<td>{formatdate(l.from_date, "dd-MM-yyyy")}</td>
					<td>{formatdate(l.to_date, "dd-MM-yyyy")}</td>
					<td>{l.total_leave_days}</td>
					<td>{l.description or '-'}
				</td>
			</tr>
			"""
	else:
		html += """
			<tr>
				<td colspan="5" style="text-align:center;">
					No Annual Leave Records Found
				</td>
			</tr>
		"""

	html += """
			</tbody>
		</table>
	</div>
	"""

	return html


#completed
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
def on_update_sales_person(doc, method):
	sales_person = frappe.db.get_value("Sales Person", {"employee": doc.name}, "name")
	if sales_person:
		sp = frappe.get_doc("Sales Person", sales_person)
		sp.custom_user_id = doc.user_id
		sp.custom_designation = doc.designation
		sp.custom_cell_number = doc.cell_number
		sp.custom_company = doc.company
		
		sp.save(ignore_permissions=True)
		if sp.name != doc.employee_name:
			frappe.rename_doc("Sales Person", sp.name,doc.employee_name)
		
@frappe.whitelist()
def update_item_default():
	item_defaults = frappe.get_all(
		"Item Default",
		filters={
			"income_account": ["like", "%General Income%"]
		},
		fields=["name", "income_account", "parent"],
		limit=2000
	)

	for row in item_defaults:
		if row.income_account:
			frappe.db.set_value(
				"Item Default",
				row.name,
				"income_account",
				None
			)

	frappe.db.commit()

@frappe.whitelist()
def get_sales_order():
	# count = 0
	# sales = frappe.get_all("Sales Order",
	#     filters={"docstatus":("!=",2)},
	#     fields=["name","custom_quote_value","base_total"])
	# for s in sales:
	#     if s.custom_quote_value != s.base_total:
	#         count += 1
	# print (count)
	total = frappe.db.get_value("Sales Order","SOJGBKSA2565","base_total")
	frappe.db.set_value("Sales Order","SOJGBKSA2565","custom_quote_value",total)
	# frappe.db.set_value("Custom Field","Sales Order-custom_quote_value","label","SO Value (SAR)")
	
@frappe.whitelist()
def update_emp_advance_workflow():
	frappe.db.set_value("Employee Advance","HR-EAD-2026-00011","docstatus","2")



#completed
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

@frappe.whitelist()
def update_cost_center(doc, method):
	if not doc.custom_cost_center and doc.voucher_type!="Depreciation Entry" and not doc.custom_leave_application and not doc.custom_ticket_reference and not doc.is_system_generated:
		frappe.throw("Kindly Select the Cost Center")
	if (doc.custom_leave_application or doc.custom_ticket_reference or doc.custom_full_and_final_settlement) and not doc.is_new() and not doc.custom_cost_center:
		frappe.throw("Kindly Select the Cost Center")
	if doc.custom_cost_center:
		for row in doc.accounts:
			row.cost_center = doc.custom_cost_center

@frappe.whitelist()
def update_cost_center_jv(doc,cost_center):
	doc=frappe.get_doc("Journal Entry",doc)
	if not doc.custom_cost_center and doc.voucher_type!="Depreciation Entry" and not doc.custom_leave_application and not doc.custom_ticket_reference and not doc.is_system_generated:
		frappe.throw("Kindly Select the Cost Center")
	if (doc.custom_leave_application or doc.custom_ticket_reference) and not doc.is_new() and not doc.custom_cost_center:
		frappe.throw("Kindly Select the Cost Center")
	if doc.custom_cost_center:
		for row in doc.accounts:
			row.cost_center = cost_center

@frappe.whitelist()
def update_payment_status_submission(doc, method):
	status = "Paid" if doc.is_paid else "Unpaid"
	frappe.db.set_value("Expense Claim",doc.name,"custom_payment_status",status)

@frappe.whitelist()
def update_payment_status_cancel(doc, method):
	frappe.db.set_value("Expense Claim",doc.name,"custom_payment_status","Cancelled")



import frappe
from frappe.utils import flt



import frappe
from frappe.utils import flt

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

import frappe

def send_dn_submission_mail(doc, method):
	sales_order = None
	for item in doc.items:
		if item.against_sales_order:
			sales_order = item.against_sales_order
			break
	if not sales_order:
		return
	so_owner = frappe.db.get_value("Sales Order", sales_order, "owner")
	if not so_owner:
		return
	email_id = frappe.db.get_value("User", so_owner, "email")
	if not email_id:
		return
	posting_date = formatdate(doc.posting_date, "dd-MM-yyyy")
	subject = f"Delivery Note Submitted for Sales Order {sales_order}"
	message = f"""
	Dear User,<br><br>
	Delivery Note <b>{doc.name}</b> has been submitted against
	Sales Order <b>{sales_order}</b>.<br><br>
	<b>Customer:</b> {doc.customer}<br>
	<b>Posting Date:</b> {posting_date}<br><br>
	Kindly check and proceed further if required.<br><br>
	Regards,<br>
	ERP System
	"""

	frappe.sendmail(
		recipients=[email_id],
		subject=subject,
		message=message,
		reference_doctype="Delivery Note",
		reference_name=doc.name
	)

import frappe
from frappe.model.naming import make_autoname

@frappe.whitelist()
def set_customer_series(doc, method):
	doc.naming_series = "C-.#####"

@frappe.whitelist()
def set_supplier_series(doc,method):
	doc.naming_series = "S-.#####"

@frappe.whitelist()
def validate_so_mandatory(doc,method):
	if doc.has_value_changed("workflow_state") and doc.workflow_state=="S.E Pending":
		if not doc.po_no:
			frappe.throw("Customer Purchase Order is mandatory before proceeding to the next approval level.")
		if not doc.custom_sales_personuser:
			frappe.throw("Sales Person User must be specified before proceeding to the next approval level.")
		if not doc.payment_terms_template:
			frappe.throw("Payment Terms Template is required before proceeding to the next approval level.")
		if not doc.custom_delivery_terms:
			frappe.throw("Kindly enter the Delivery Terms before move to next level")
		if not doc.custom_support_engineer:
			frappe.throw("Support Engineer must be specified before proceeding to the next approval level.")


#completed
@frappe.whitelist()
def validate_po_mandatory(doc,method):
	if doc.has_value_changed("workflow_state") and doc.workflow_state=="S.E Pending":
		if not doc.custom_purchase_type:
			frappe.throw("Purchase Type is mandatory before proceeding to the next approval level.")
		if not doc.payment_terms_template:
			frappe.throw("Payment Terms Template is required before proceeding to the next approval level.")
		if not doc.custom_delivery_terms:
			frappe.throw("Kindly enter the Delivery Terms before move to next level")
		if not doc.custom_support_engineer:
			frappe.throw("Support Engineer must be specified before proceeding to the next approval level.")
	if doc.has_value_changed("workflow_state") and doc.workflow_state=="Regional Accountant Pending":
		if not doc.custom_purchase_type:
			frappe.throw("Purchase Type is mandatory before proceeding to the next approval level.")
		if not doc.payment_terms_template:
			frappe.throw("Payment Terms Template is required before proceeding to the next approval level.")
		if not doc.custom_delivery_terms:
			frappe.throw("Kindly enter the Delivery Terms before move to next level")
		if not doc.custom_support_engineer:
			frappe.throw("Support Engineer must be specified before proceeding to the next approval level.")

@frappe.whitelist()
def validate_qtn_mandatory(doc,method):
	if not doc.custom_sales_personuser:
		frappe.throw("Sales Person User must be specified before submit")
	if not doc.custom_support_engineer:
		frappe.throw("Support Engineer must be specified before submit")
	if not doc.payment_terms_template:
		frappe.throw("Payment Terms Template is required before submit")
	if not doc.custom_delivery_terms:
		frappe.throw("Kindly enter the Delivery Terms before submit")
	
@frappe.whitelist()
def update_project_naming_series():
	sales_orders = frappe.get_all(
		"Sales Order",
		filters={"docstatus": 1},
		fields=["name", "customer", "po_no"]
	)

	for so in sales_orders:
		project = frappe.db.get_value(
			"Project",
			{"sales_order": so.name},
			"name"
		)

		if not project:
			continue
		if so.po_no:
			new_name = f"{so.customer}-{so.po_no}-{so.name}"
		else:
			new_name = f"{so.customer}-{so.name}"
		project_name = f"{so.name}_{so.customer}"

		if project == new_name:
			continue

		# Rename project (this updates naming series)
		frappe.rename_doc(
			"Project",
			project,
			new_name,
		)

		# Update other fields after rename
		frappe.db.set_value(
			"Project",
			new_name,
			"project_name",
			project_name
		)

	frappe.db.commit()




import frappe
from frappe.utils import getdate, nowdate, formatdate

@frappe.whitelist()
def send_iqama_expiry_mail():

	today = getdate(nowdate())

	alert_30 = {}
	alert_15 = {}
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=[
			"name",
			"employee_name",
			"company",
			"department",
			"designation",
			"custom_iqama_expiry_date"
		],
		order_by="name"
	)

	for emp in employees:

		if not emp.custom_iqama_expiry_date:
			continue

		expiry_date = getdate(emp.custom_iqama_expiry_date)
		days_diff = (expiry_date - today).days

		row = {
			"ID": emp.name,
			"employee": emp.employee_name,
			"company": emp.company,
			"department": emp.department,
			"designation": emp.designation,
			"expiry": formatdate(expiry_date),
			"status": "Expired" if days_diff < 0 else f"Due in {days_diff} days"
		}

		if days_diff <= 30:
			alert_30.setdefault(emp.company, []).append(row)

		elif days_diff == 15:
			alert_15.setdefault(emp.company, []).append(row)


	for company, rows in alert_30.items():
		send_mail(company, rows,
			subject="IQAMA Expiry Reminder – 30 Days Left"
		)

	for company, rows in alert_15.items():
		send_mail(company, rows,
			subject="IQAMA Expiry Reminder – 15 Days Left"
		)

def send_mail(company, rows, subject):

	recipients = get_hr_emails_by_company(company)

	if not recipients:
		return

	html = """
	<p>Dear Sir/Madam,</p>
	<p>Please find below IQAMA Expiry Details of Employee</p>
	<table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;">
		<tr>
			<th>Employee ID</th>
			<th>Employee Name</th>
			<th>Company</th>
			<th>Department</th>
			<th>Designation</th>
			<th>Expiry Date</th>
			<th>Status</th>
		</tr>
	""".format(company)

	for r in rows:
		html += f"""
		<tr>
			<td>{r['ID']}</td>
			<td>{r['employee']}</td>
			<td>{r['company']}</td>
			<td>{r['department']}</td>
			<td>{r['designation']}</td>
			<td>{r['expiry']}</td>
			<td>{r['status']}</td>
		</tr>
		"""

	html += "</table>"

	frappe.sendmail(
		recipients=recipients,
		subject=subject,
		message=html
	)


def get_hr_emails_by_company(company):

	data = frappe.db.sql("""
		SELECT DISTINCT u.email
		FROM `tabUser` u
		JOIN `tabHas Role` hr ON hr.parent = u.name
		JOIN `tabEmployee` e ON e.user_id = u.name
		WHERE hr.role IN ('HR User', 'HR Manager')
		  AND u.enabled = 1
		  AND e.company = %s
	""", company, as_dict=True)

	return [d.email for d in data if d.email]


@frappe.whitelist()
def allocate_leaves_annual():
	employees = frappe.db.sql(
		"""
		SELECT name, date_of_joining
		FROM `tabEmployee`
		WHERE date_of_joining >= '2026-01-01'
		""",
		as_dict=True
	)
	print(employees)
	for e in employees:
		leave_qty = 0

		from_date = e.date_of_joining
		if from_date > getdate(from_date):
			continue
		to_date = add_days(add_years(from_date, 1), -1)

		join_month_last_day = get_last_day(from_date)
		days_in_month = join_month_last_day.day

		worked_days = date_diff(join_month_last_day, from_date) + 1

		leave_qty += (2.5 / days_in_month) * worked_days

		# if from_date <= getdate('2026-01-31'):
		#     leave_qty += 2.5
		print(e.name)
		print(leave_qty)
		leave_qty = round(leave_qty, 2)

		if leave_qty <= 0:
			continue

		leave_alloc = frappe.new_doc("Leave Allocation")
		leave_alloc.employee = e.name
		leave_alloc.leave_type = "Annual Vacation"
		leave_alloc.from_date = from_date
		leave_alloc.to_date = to_date
		leave_alloc.new_leaves_allocated = leave_qty
		leave_alloc.total_leaves_allocated = leave_qty
		leave_alloc.save(ignore_permissions=True)

# @frappe.whitelist()
# def create_expense_salary(doc, method):
# 	salary_component = "Monthly Expenses"

# 	expense_claims = frappe.db.sql(
# 		"""
# 		SELECT name, grand_total
# 		FROM `tabExpense Claim`
# 		WHERE
# 			docstatus = 1
# 			AND employee = %s
# 			AND custom_ec_from_date BETWEEN %s AND %s
# 			AND IFNULL(custom_payment_status, '') != 'Paid'
# 		""",
# 		(doc.employee, doc.start_date, doc.end_date),
# 		as_dict=True
# 	)
# 	if not expense_claims:
# 		return

# 	expense_total = sum(d.grand_total for d in expense_claims)
# 	if expense_total <= 0:
# 		return
# 	existing = frappe.db.exists(
# 		"Additional Salary",
# 		{
# 			"docstatus": 1,
# 			"employee": doc.employee,
# 			"salary_component": salary_component,
# 			"amount": expense_total,
# 			"payroll_date": ('between', (doc.start_date, doc.end_date)),
# 		}
# 	)

# 	if existing:
# 		return
# 	additional_salary = frappe.get_doc({
# 		"doctype": "Additional Salary",
# 		"employee": doc.employee,
# 		"salary_component": salary_component,
# 		"amount": expense_total,
# 		"payroll_date": doc.start_date,
# 		"company": doc.company,
# 		"overwrite_salary_structure_amount": 1,
# 	})

# 	for ec in expense_claims:
	   

# 		additional_salary.append("custom_expense_split_up", {
# 			"expense_id": ec.name,
# 			"expense_amount": ec.grand_total
# 		})

# 	if additional_salary.custom_expense_split_up:
# 		additional_salary.insert(ignore_permissions=True)
# 		additional_salary.submit()
# 	else:
# 		frappe.log_error("No valid expense claims to append in Additional Salary", 'Expense Claim Debug')


# 	for ec in expense_claims:
# 		frappe.db.set_value(
# 			"Expense Claim",
# 			ec.name,
# 			{
# 				"status": "Paid",
# 				"custom_payment_status": "Paid"
# 			},
# 			update_modified=False
# 		)


#completed
@frappe.whitelist()
def create_expense_salary(doc, method):
	salary_component = "Monthly Expenses"

	expense_claims = frappe.db.sql(
		"""
		SELECT name, grand_total
		FROM `tabExpense Claim`
		WHERE
			docstatus = 1
			AND employee = %s
			AND custom_ec_from_date BETWEEN %s AND %s
			AND IFNULL(custom_payment_status, '') != 'Paid'
		""",
		(doc.employee, doc.start_date, doc.end_date),
		as_dict=True
	)
	if not expense_claims:
		return

	for ec in expense_claims:
		if ec.grand_total <= 0:
			continue

		# check via child table whether this exact expense claim
		# is already linked to a submitted Additional Salary
		existing = frappe.db.sql(
			"""
			SELECT parent
			FROM `tabExpense Split Up`
			WHERE expense_id = %s
			AND parenttype = 'Additional Salary'
			AND parent IN (
				SELECT name FROM `tabAdditional Salary`
				WHERE docstatus = 1
			)
			""",
			(ec.name,)
		)
		if existing:
			continue

		additional_salary = frappe.get_doc({
			"doctype": "Additional Salary",
			"employee": doc.employee,
			"salary_component": salary_component,
			"amount": ec.grand_total,
			"payroll_date": doc.start_date,
			"company": doc.company,
			"overwrite_salary_structure_amount": 0,
		})

		additional_salary.append("custom_expense_split_up", {
			"expense_id": ec.name,
			"expense_amount": ec.grand_total
		})

		if additional_salary.custom_expense_split_up:
			additional_salary.insert(ignore_permissions=True)
			additional_salary.submit()

			frappe.db.set_value(
				"Expense Claim",
				ec.name,
				{
					"status": "Paid",
					"custom_payment_status": "Paid"
				},
				update_modified=False
			)
		else:
			frappe.log_error(f"No valid expense claim to append for {ec.name}", 'Expense Claim Debug')

@frappe.whitelist()
def update_sales_person_details():
	users=frappe.db.get_all("Sales Person",{"enabled":1},["name","employee","custom_user_id"])
	ind=0
	for i in users:
		if i.employee and i.custom_user_id:
			emp=frappe.db.get_value("Employee",i.employee,"user_id")
			if emp and not emp==i.custom_user_id:
				ind+=1
				frappe.db.set_value("Sales Person",i.name,"custom_user_id",emp)
	print(ind)

def update_pr_currency_validate(doc,method):
	if doc.custom_logistics_request and doc.items:
		if doc.items[0].purchase_order:
			po = frappe.get_doc("Purchase Order", doc.items[0].purchase_order)
			doc.currency = po.currency
			doc.conversion_rate = po.conversion_rate

@frappe.whitelist()
def update_lr_pr():
	doc=frappe.get_doc("Logistics Request","LR-2026-00090")
	doc.lr_status_details=[]
	doc.save()


@frappe.whitelist()
def allocate_sl():

	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active",'name':('not in',('21065','21005','HR-EMP-00001'))},
		fields=["name", "date_of_joining"]
	)

	current_date = getdate(today())
	current_year = current_date.year

	for emp in employees:

		if not emp.date_of_joining:
			continue

		doj = getdate(emp.date_of_joining)
		first_anniversary = add_years(doj, 1)

		if current_date < first_anniversary:

			from_date = doj
			to_date = add_days(first_anniversary, -1)

		else:
			current_year_anniversary = doj.replace(year=current_year)

			try:
				current_year_anniversary = doj.replace(year=current_year)
			except ValueError:
				current_year_anniversary = doj.replace(year=current_year, day=28)

			if current_date < current_year_anniversary:
				from_date = add_years(current_year_anniversary, -1)
				to_date = add_days(current_year_anniversary, -1)
			else:
				from_date = current_year_anniversary
				next_anniversary = add_years(current_year_anniversary, 1)
				to_date = add_days(next_anniversary, -1)

		exists = frappe.db.exists(
			"Leave Allocation",
			{
				"employee": emp.name,
				"leave_type": "Sick Leave",
				"from_date": from_date,
				"to_date": to_date
			}
		)

		if exists:
			continue

		leave = frappe.get_doc({
			"doctype": "Leave Allocation",
			"employee": emp.name,
			"leave_type": "Sick Leave",
			"from_date": from_date,
			"to_date": to_date,
			"new_leaves_allocated": 30
		})

		leave.insert(ignore_permissions=True)
		leave.submit()

	frappe.db.commit()

	return "Sick Leave Allocation Completed"

#completed
@frappe.whitelist()
def update_item_code_creation(doc,method):
	if frappe.flags.in_import:
		item_group_short_code = frappe.db.get_value("Item Group", {"name": doc.item_group}, "custom_short_code")
		product_short_code = frappe.db.get_value("Product", {"name": doc.custom_product}, "short_code")

		if not item_group_short_code or not product_short_code:
			frappe.throw("Missing short code for Item Group or Product.")

		prefix = f"{item_group_short_code}-{product_short_code}-"

		existing_items = frappe.db.get_all("Item", filters={
			"item_code": ["like", f"{prefix}%"]
		}, fields=["item_code"])

		max_num = 0
		pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$") 
		for item in existing_items:
			item_code = item["item_code"]
			match = pattern.match(item_code)
			if match:
				num_part = int(match.group(1))
				if num_part > max_num:
					max_num = num_part

		next_num = max_num + 1
		next_code = f"{prefix}{str(next_num).zfill(6)}" 

		doc.custom_item=next_code
		doc.item_code=next_code
		if doc.custom_product_naming_parameters:
			item_name = "-".join(
				row.value for row in doc.custom_product_naming_parameters
				if row.value
			)
			doc.item_name = item_name


@frappe.whitelist()
def update_item_name_for_15th_row_delivery_note():
	delivery_notes = frappe.db.get_value(
		"Delivery Note Item",
		{"parent": "JGB-VLP-DN-2026-00094","item_code":"VLP-HNS-000560"},
		["name"]
	)

  
		
	if delivery_notes:
		item_name = frappe.db.get_value("Item", "VLP-HNS-000560", "description")
		frappe.db.set_value("Delivery Note Item", delivery_notes, "description", item_name)




def allocate_pilgrimage_leave():
	today = getdate(nowdate())
	employees = frappe.db.get_all("Employee", {'status':'Active'}, [ 'name','date_of_joining'])
	for e in employees:
		fifth_anniversary = add_years(e.date_of_joining, 5)
		to_date= add_years(fifth_anniversary, 50)
		if today >= fifth_anniversary:
			if not frappe.db.exists("Leave Allocation",{'leave_type':'Pilgrimage Leave','employee':e.name,'docstatus':1}):
				la=frappe.new_doc('Leave Allocation')
				la.employee=e.name
				la.leave_type='Pilgrimage Leave'
				la.from_date=fifth_anniversary
				la.new_leaves_allocated=10
				la.to_date=to_date
				la.insert(ignore_permissions=True)
				la.submit()


#completed
@frappe.whitelist()
def update_ipc_values(dn):
	delivery_note = frappe.get_doc("Delivery Note", dn)
	return delivery_note.items

#completed
@frappe.whitelist()
def update_ipc_values_so(so):
	sales_order = frappe.get_doc("Sales Order", so)
	return sales_order.items


#completed
@frappe.whitelist()
def update_ipc_values_ipc(ipc):
	sales_order = frappe.get_doc("Interim Payment Certificate", ipc)
	return sales_order.items , sales_order.retention_percentage , sales_order.advance_percentage , sales_order.previously_certified_value

#completed
@frappe.whitelist()
def update_previously_certified_value(so):
	result = frappe.db.sql(
		"""
		SELECT SUM(balance_amount)
		FROM `tabInterim Payment Certificate`
		WHERE sales_order = %s
		AND docstatus = 1
		""",
		so,
	)

	net_certified_to_date = result[0][0] or 0
	return net_certified_to_date


@frappe.whitelist()
def update_addendum(doc,method):
	if doc.custom_contract_price and not doc.custom_addendum_1:
		if doc.base_total > doc.custom_contract_price:
			addendum_amount = doc.base_total - doc.custom_contract_price
			frappe.db.set_value("Sales Order",doc.name,"custom_addendum_1",addendum_amount)
	elif doc.custom_contract_price and not doc.custom_addendum_2:
		if doc.base_total > doc.custom_contract_price:
			addendum_amount = doc.base_total - (doc.custom_contract_price + doc.custom_addendum_1)
			frappe.db.set_value("Sales Order",doc.name,"custom_addendum_2",addendum_amount)
		else:
			frappe.db.set_value("Sales Order",doc.name,"custom_addendum_2",0)
	elif doc.custom_contract_price and not doc.custom_addendum_3:
		if doc.base_total > doc.custom_contract_price:
			addendum_amount = doc.base_total - (doc.custom_contract_price + doc.custom_addendum_1 + doc.custom_addendum_2)
			frappe.db.set_value("Sales Order",doc.name,"custom_addendum_3",addendum_amount)
		else:
			frappe.db.set_value("Sales Order",doc.name,"custom_addendum_3",0)
	elif doc.custom_contract_price and not doc.custom_addendum_4:
		if doc.base_total > doc.custom_contract_price:
			addendum_amount = doc.base_total - (doc.custom_contract_price + doc.custom_addendum_1 + doc.custom_addendum_2 + doc.custom_addendum_3)
			frappe.db.set_value("Sales Order",doc.name,"custom_addendum_4",addendum_amount)
		else:
			frappe.db.set_value("Sales Order",doc.name,"custom_addendum_4",0)
			

@frappe.whitelist()
def update_contract_price(doc,method):
	frappe.db.set_value("Sales Order",doc.name,"custom_contract_price",doc.base_total)


#completed
@frappe.whitelist()
def update_advance_percentage(so):
	advance = frappe.db.sql(
		"""
		SELECT SUM(asi.custom_advance_percentage)
		FROM `tabAdvance Sales Invoice` asi
		INNER JOIN `tabPayment Entry Reference` pre
			ON pre.parent = asi.name
		WHERE
			asi.docstatus = 1
			AND pre.reference_name = %s
		""",
		(so,),
	)[0][0] or 0
	return advance


@frappe.whitelist()
def update_ipc_qty_sold(doc,method):
	qty_ipc = 0
	if doc.custom_interim_payment_certificate:
		dn = frappe.get_doc("Interim Payment Certificate", doc.custom_interim_payment_certificate)
		for d in dn.items:
			for i in doc.items:
				if d.item_code == i.item_code and d.name == i.custom_ipc_details:
					qty_ipc += i.qty
					qty = qty_ipc + d.inv_qty 
				frappe.db.set_value("IPC Item", d.name, "inv_qty", qty)

@frappe.whitelist()
def reduce_ipc_qty_sold(doc,method):
	qty_ipc = 0
	if doc.custom_interim_payment_certificate:
		dn = frappe.get_doc("Interim Payment Certificate", doc.custom_interim_payment_certificate)
		for d in dn.items:
			for i in doc.items:
				if d.item_code == i.item_code and d.name == i.custom_ipc_details:
					qty_ipc += i.qty
					qty = qty_ipc - d.inv_qty
				frappe.db.set_value("IPC Item", d.name, "inv_qty", qty)


#completed
@frappe.whitelist()
def get_leave_year(employee, leave_date=None):

	doj = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not doj:
		frappe.throw("Date of Joining not found")

	doj = getdate(doj)

	ref_date = getdate(leave_date) if leave_date else getdate()

	from_date = doj.replace(year=ref_date.year)
	if ref_date < from_date:
		from_date = add_years(from_date, -1)

	to_date = add_days(add_years(from_date, 1), -1)

	return {
		"from_date": from_date,
		"to_date": to_date
	}


#completed
@frappe.whitelist()
def check_annual_vacation_doj_year(employee, leave_from_date, current_doc=None):
	doj = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not doj:
		return {"eligible": True}

	doj = getdate(doj)
	leave_from_date = getdate(leave_from_date)

	years_completed = (
		leave_from_date.year - doj.year
		- ((leave_from_date.month, leave_from_date.day) < (doj.month, doj.day))
	)

	period_start = add_years(doj, years_completed)
	period_end = add_days(add_years(doj, years_completed + 1), -1)

	existing = frappe.db.get_value(
		"Leave Application",
		{
			"employee": employee,
			"custom_approval_status":"Eligible",
			"leave_type": "Annual Vacation",
			"docstatus": ["!=", 2],
			"from_date": [">=", period_start],
			"to_date": ["<=", period_end],
			"name": ["!=", current_doc],
		},
		"name",
	)

	if existing:
		return {
			"eligible": False,
			"leave_application": existing,
			"period_start": period_start,
			"period_end": period_end,
		}

	return {
		"eligible": True,
		"period_start": period_start,
		"period_end": period_end,
	}

#completed
@frappe.whitelist()
def get_vacation_pay_table(employee,from_date):

	if not employee:
		return ""

	filters = {
		"employee": employee,
		"docstatus": 1
	}
	if from_date:
		filters["to_date"] = ["<", from_date]

	leave_apps = frappe.get_all(
		"Leave Application",
		filters=filters,
		fields=[
			"name", "from_date", "to_date", "total_leave_days",
			"custom_ticket_fare", "custom_employee_return_fare",
			"custom_leave_salary_amount",
			"custom_spouse_fare", "custom_child_fare",
			"custom_spouse_return_fare", "custom_child_return_fare"
		],
		order_by="from_date asc"
	)

	expense_totals = {}
	if leave_apps:
		expense_entries = frappe.get_all(
			"Direct Expense Entry",
			filters={
				"docstatus": 1,
				"reference_no": ["in", [leave.name for leave in leave_apps]]
			},
			fields=["reference_no", "total_amount"]
		)
		for entry in expense_entries:
			expense_totals[entry.reference_no] = (
				expense_totals.get(entry.reference_no, 0) + (entry.total_amount or 0)
			)

	year_counts = {}
	for leave in leave_apps:
		leave_year = getdate(leave.from_date).year
		year_counts[leave_year] = year_counts.get(leave_year, 0) + 1

	rows = ""
	count = 0
	prev_year = None
	for leave in leave_apps:
		leave_year = getdate(leave.from_date).year
		year_cell = ""
		if leave_year != prev_year:
			year_cell = f'<td rowspan="{year_counts[leave_year]}" style="text-align:center;vertical-align:middle;font-weight:bold;">{leave_year}</td>'
			prev_year = leave_year

		ticket = (leave.custom_ticket_fare or 0) + (leave.custom_employee_return_fare or 0)
		exit_entry = expense_totals.get(leave.name, 0)
		vacation = leave.custom_leave_salary_amount or 0
		family_ticket = (
			(leave.custom_spouse_fare or 0) + (leave.custom_child_fare or 0)
			+ (leave.custom_spouse_return_fare or 0) + (leave.custom_child_return_fare or 0)
		)
		count += 1
		rows += f"""
		<tr>
			{year_cell}
			<td style="text-align:center;">{formatdate(leave.from_date, "dd/MM/yy")} - {formatdate(leave.to_date, "dd/MM/yy")}</td>
			<td style="text-align:center;">{leave.total_leave_days or 0}</td>
			<td style="text-align:right;">{ticket:.2f}</td>
			<td style="text-align:right;">{exit_entry:.2f}</td>
			<td style="text-align:right;">{vacation:.2f}</td>
			<td style="text-align:right;">{family_ticket:.2f}</td>
		</tr>
		"""

	html = f"""
	<table class="table table-bordered">
		<thead>
			<tr>
				<th style="text-align:center;">Year</th>
				<th style="text-align:center;">Period</th>
				<th style="text-align:center;">No.of days</th>
				<th style="text-align:center;">Ticket</th>
				<th style="text-align:center;">Exit/entry</th>
				<th style="text-align:center;">Vacation</th>
				<th style="text-align:center;">Family Ticket</th>
			</tr>
		</thead>
		<tbody>
			{rows}
		</tbody>
	</table>
	"""
	if count==0:
		html=f"""<p style="text-align:center;"><b>No Previous payment records against {employee}</b></p>"""
	return html

#completed
def get_promotion_row(employee, from_date, to_date):
	emp = frappe.get_doc("Employee", employee)

	from_date = getdate(from_date)
	to_date = getdate(to_date)

	rows = [
		r for r in emp.custom_internal_work_historys
		if r.promotion_date
		and from_date <= getdate(r.promotion_date) <= to_date
	]
	if not rows:
		return None

	rows.sort(key=lambda r: getdate(r.promotion_date))
	return rows[0]



def get_latest_promotion_row(employee):
	emp = frappe.get_doc("Employee", employee)

	rows = [r for r in emp.custom_internal_work_historys if r.promotion_date]
	if not rows:
		return None

	rows.sort(key=lambda r: getdate(r.promotion_date), reverse=True)
	return rows[0]


def split_by_month(from_date, to_date):
	periods = []
	current = getdate(from_date)
	to_date = getdate(to_date)

	while current <= to_date:
		end = min(get_last_day(current), to_date)
		periods.append((current, end))
		current = add_days(end, 1)

	return periods


def prorated_amount(amount, days, month_days):
	return (amount / 30) * days if amount else 0


#completed
def render_html(data,hra_only):
	
	hra_only=int(hra_only)
	html = """
	<h4>Vacation Pay Calculation</h4>
	<table class="table table-bordered">
		<thead style="background:#343a40;color:white;">
			<tr>
				<th>Component</th>
				<th>From</th>
				<th>To</th>
				<th>Days</th>
				<th>Increment Type</th>
				<th style="text-align:right;">Amount</th>
			</tr>
		</thead>
		<tbody>
	"""

	total = 0

	for row in data:
		first = True
		for b in row["breakdown"]:
			if row['component'] in ['Basic','HRA']:
				
				if hra_only==0 or (hra_only==1 and row['component'] in ('Basic','HRA')) :
					html += f"""
					<tr>
						{f"<td rowspan='{len(row['breakdown'])}'><b>{row['component']}</b></td>" if first else ""}
						<td>{b['from']}</td>
						<td>{b['to']}</td>
						<td align="center">{b['days']}</td>
						<td style="
							font-weight:{'700' if b['type']=='No Increment' else '600'};
							color:{
								'#dc3545' if b['type']=='Previous Salary'
								else '#28a745' if b['type']=='Revised Salary'
								else '#000'
							};
						">
							{b['type']}
						</td>

						<td align="right">{b['amount']}</td>
					</tr>
					"""
					first = False
					total += b["amount"]

	html += f"""
		<tr style="background:#212529;color:white;font-weight:700;">
			<td colspan="5" align="right">Overall Total</td>
			<td align="right">{round(total, 2)}</td>
		</tr>
		</tbody>
	</table>
	"""

	return html

#completed
def render_promotion_summary(rows):
	if not rows:
		return """
		<h4>Promotion Details</h4>
		<p style="font-weight:600;color:#6c757d;">
			No promotion in the vacation period
		</p>
		"""

	html = """
	<h4>Promotion Details</h4>
	<table class="table table-bordered">
		<thead style="background:#E9E4D4 ;color:black;">
			<tr>
				<th>Component</th>
				<th>Promotion Date</th>
				<th style="color:#dc3545;">Old Value</th>
				<th style="color:#28a745;">Revised Value</th>
			</tr>
		</thead>
		<tbody>
	"""

	for r in rows:
		html += f"""
		<tr>
			<td><b>{r['component']}</b></td>
			<td>{r['date']}</td>
			<td style="color:#dc3545;font-weight:600;" align="right">{r['old']}</td>
			<td style="color:#28a745;font-weight:600;" align="right">{r['new']}</td>
		</tr>
		"""

	html += "</tbody></table><br>"
	return html


def get_salary_structure_assignment(employee, from_date):
	return frappe.db.get_value(
		"Salary Structure Assignment",
		{
			"employee": employee,
			"docstatus": 1,
			"from_date": ("<=", from_date)
		},
		["name", "salary_structure"],
		order_by="from_date desc"
	)


def get_applicable_promotion(employee, date):
	emp = frappe.get_doc("Employee", employee)

	promotions = [
		row for row in emp.custom_internal_work_historys
		if row.promotion_date and getdate(row.promotion_date) <= date
	]

	if not promotions:
		return None

	return sorted(promotions, key=lambda x: getdate(x.promotion_date))[-1]

#completed
def split_period(from_date, to_date):
	periods = []
	current = from_date

	while current <= to_date:
		month_end = get_last_day(current)
		period_end = min(month_end, to_date)
		periods.append((current, period_end))
		current = add_days(period_end, 1)

	return periods

#completed
def get_month_days(date):
	return date_diff(get_last_day(date), get_first_day(date)) + 1

#completed
def prorate(amount, days, month_days):
	if not amount or not days:
		return 0
	return (amount / 30) * days

PROMOTION_FIELD_MAP = {
	"Basic": "basic",
	"HRA": "hra",
	"Telephone": "telephone",
	"Transport": "transport",
	"Travel Allowance": "travel_allowance",
}

EMPLOYEE_FIELD_MAP = {
	"Basic": "custom_basic",
	"HRA": "custom_hra",
	"Telephone": "custom_telephone",
	"Transport": "custom_transport",
	"Travel Allowance": "custom_travel_allowance",
}

COMPONENT_OLD_DAYS_FIELD = {
	"Basic": "custom_old_salary_days",
	"HRA": "custom_old_hra_days",
}

#completed
@frappe.whitelist()
def calculate_vacation_pay(name,hra_only):
	doc = frappe.get_doc("Leave Application", name)
	employee_map = EMPLOYEE_FIELD_MAP
	promotion_map = PROMOTION_FIELD_MAP
	if doc.leave_type != "Annual Vacation" or doc.custom_payment_type != "Pay Now":
		return

	employee = frappe.get_doc("Employee", doc.employee)

	periods = split_period(getdate(doc.from_date), getdate(doc.to_date))

	from_date = getdate(doc.from_date)
	latest_promotion = get_latest_promotion_row(doc.employee)
	period_promotion = get_promotion_row(
		doc.employee,
		doc.from_date,
		doc.to_date
	)

	results = []
	promotion_summary = []
	if hra_only==1:
		employee_map = {
			"Basic": "custom_basic",
			"HRA": "custom_hra",
		}
		promotion_map = {
			"HRA": "hra",
		}
	for component, emp_field in employee_map.items():
		emp_amt = float(employee.get(emp_field) or 0)
		breakdown = []
		summary_added = False

		old_days = float(doc.get(COMPONENT_OLD_DAYS_FIELD.get(component)) or 0)
		if hra_only == 1 and component == "Basic" and not old_days:
			continue
		if old_days > 0:
			future_promotion = latest_promotion
			promo_date = (
				add_days(from_date, old_days)
				if future_promotion or (hra_only == 1 and component == "Basic") else None
			)
		else:
			future_promotion = period_promotion
			promo_date = (
				getdate(period_promotion.promotion_date)
				if period_promotion else None
			)
		promo_frac = old_days % 1

		for start, end in periods:
			month_days = get_month_days(start)
			days = date_diff(end, start) + 1

			old_amt = emp_amt
			new_amt = emp_amt

			if future_promotion and component in promotion_map:
				field = promotion_map[component]

				old_amt = float(
					getattr(future_promotion, field, emp_amt) or emp_amt
				)
				new_amt = float(
					getattr(future_promotion, "new_" + field, old_amt) or old_amt
				)

			if hra_only == 1 and component == "Basic":
				new_amt = 0

			is_revised = promo_date and old_amt != new_amt

			if is_revised and not summary_added and not (hra_only == 1 and component == "Basic"):
				promotion_summary.append({
					"component": component,
					"date": promo_date,
					"old": round(old_amt, 2),
					"new": round(new_amt, 2),
				})
				summary_added = True

			if promo_date and (start < promo_date <= end or (start == promo_date and promo_frac)) and is_revised:
				before_days = date_diff(add_days(promo_date, -1), start) + 1 + promo_frac
				amt1 = prorate(old_amt, before_days, month_days)

				if amt1 > 0:
					breakdown.append({
						"from": start,
						"to": promo_date if promo_frac else add_days(promo_date, -1),
						"days": before_days,
						"type": "Previous Salary",
						"amount": round(amt1, 2),
					})

				after_days = date_diff(end, promo_date) + 1 - promo_frac
				amt2 = prorate(new_amt, after_days, month_days)

				if amt2 > 0:
					breakdown.append({
						"from": promo_date,
						"to": end,
						"days": after_days,
						"type": "Revised Salary",
						"amount": round(amt2, 2),
					})

			elif promo_date and end < promo_date:
				amt = prorate(old_amt, days, month_days)
				if amt > 0:
					breakdown.append({
						"from": start,
						"to": end,
						"days": days,
						"type": "Previous Salary" if is_revised else "No Increment",
						"amount": round(amt, 2),
					})


			elif promo_date and start >= promo_date:
				amt = prorate(new_amt if is_revised else emp_amt, days, month_days)
				if amt > 0:
					breakdown.append({
						"from": start,
						"to": end,
						"days": days,
						"type": "Revised Salary" if is_revised else "No Increment",
						"amount": round(amt, 2),
					})


			else:
				# No promotion impact
				amt = prorate(emp_amt, days, month_days)
				if amt > 0:
					breakdown.append({
						"from": start,
						"to": end,
						"days": days,
						"type": "No Increment",
						"amount": round(amt, 2),
					})

		if breakdown:
			results.append({
				"component": component,
				"breakdown": breakdown,
			})

	html = ""
	html += render_promotion_summary(promotion_summary)
	html += render_html(results,hra_only)
	return html


#completed
@frappe.whitelist()
def on_extend_leave(employee, previous_to_date, current_to_date, name):

	previous_to_date = getdate(previous_to_date)
	current_to_date = getdate(current_to_date)

	att_date = add_days(previous_to_date, 1)
	leave_days=date_diff(current_to_date,previous_to_date)
	while att_date <= current_to_date:
		create_or_update_attendance(employee, att_date, name)
		att_date = add_days(att_date, 1)
	ledger=frappe.get_doc('Leave Ledger Entry',{'transaction_type':'Leave Application','transaction_name':name})
	ledger.leaves-=leave_days
	ledger.save(ignore_permissions=True)


#completed
def create_or_update_attendance(employee, att_date,name):
		
	if frappe.db.exists("Attendance",{'employee':employee,"attendance_date":att_date,"docstatus":['!=',2]}):
		doc = frappe.get_doc("Attendance", {'employee':employee,"attendance_date":att_date,"docstatus":['!=',2]})
		doc.leave_type = "Annual Vacation"
		doc.leave_application = name
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.new_doc("Attendance")
		doc.employee = employee
		doc.attendance_date = att_date
		doc.leave_type = "Annual Vacation"
		doc.leave_application = name
		doc.status = "On Leave"
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
		doc.submit()

# @frappe.whitelist()
# def update_so_delivery():
#     frappe.db.sql("""
#         UPDATE `tabSales Order Item`
#         SET delivered_qty = %s
#         WHERE parent = %s
#         AND item_code = %s
#     """, (1000, "SOJGBKSA2389-1", "VLP-HNS-000047"))
#     frappe.db.sql("""
#         UPDATE `tabSales Order Item`
#         SET delivered_qty = %s
#         WHERE parent = %s
#         AND item_code = %s
#     """, (350, "SOJGBKSA2389-1", "VLP-HNS-000049"))
#     frappe.db.sql("""
#         UPDATE `tabSales Order Item`
#         SET delivered_qty = %s
#         WHERE parent = %s
#         AND item_code = %s
#     """, (300, "SOJGBKSA2389-1", "VLP-HNS-000048"))
#     frappe.db.sql("""
#         UPDATE `tabSales Order Item`
#         SET delivered_qty = %s
#         WHERE parent = %s
#         AND item_code = %s
#     """, (350, "SOJGBKSA2389-1", "VLP-HNS-000050"))
#     frappe.db.sql("""
#         UPDATE `tabSales Order Item`
#         SET delivered_qty = %s
#         WHERE parent = %s
#         AND item_code = %s
#     """, (350, "SOJGBKSA2389-1", "VLP-HNS-000272"))
#     frappe.db.sql("""
#         UPDATE `tabSales Order Item`
#         SET delivered_qty = %s
#         WHERE parent = %s
#         AND item_code = %s
#     """, (300, "SOJGBKSA2389-1", "VLP-HNS-000273"))
#     frappe.db.sql("""
#         UPDATE `tabSales Order Item`
#         SET delivered_qty = %s
#         WHERE parent = %s
#         AND item_code = %s
#     """, (50, "SOJGBKSA2389-1", "VLP-HNS-000274"))
#     frappe.db.sql("""
#         UPDATE `tabSales Order Item`
#         SET delivered_qty = %s
#         WHERE parent = %s
#         AND item_code = %s
#     """, (50, "SOJGBKSA2389-1", "VLP-HNS-000275"))
#     frappe.db.sql("""
#         UPDATE `tabSales Order Item`
#         SET delivered_qty = %s
#         WHERE parent = %s
#         AND item_code = %s
#     """, (150, "SOJGBKSA2389-1", "VLP-HNS-000251"))


#completed
@frappe.whitelist()
def check_for_zatca_category(doc,method):
	if doc.custom_zatca_tax_category=='' and doc.workflow_state=='Approved':
		frappe.throw('<b>ZATCA Tax Category</b> is mandatory')


#completed
@frappe.whitelist()
def update_zatca_category(doc,method):
	if doc.custom_zatca_tax_category=='' and doc.total_taxes_and_charges==0 and not doc.custom_logistics_request:
		frappe.msgprint('<b>ZATCA Tax Category</b> updated as Zero Rated')
		doc.custom_zatca_tax_category='Zero Rated'
		doc.custom_exemption_reason_code='VATEX-SA-32'

@frappe.whitelist()
def update_existing_item_defaults():
	items = frappe.get_all("Item", {"is_stock_item": 1}, ["name"])
	ind=0
	for item in items:
		doc = frappe.get_doc("Item", item.name)
		updated = False
		if doc.item_defaults:
			for row in doc.item_defaults:
				if row.income_account:
					print(doc.name)
					ind+=1
					row.income_account = ""
					updated = True
		if updated:
			doc.save(ignore_permissions=True)
	print(ind)

import frappe
from frappe.utils.file_manager import get_file
from frappe.utils.csvutils import read_csv_content
from openpyxl import Workbook
from io import BytesIO

@frappe.whitelist()
def export_item_transaction_report():

	filename = '/files/Non Stock Item List.csv'   
	filepath = get_file(filename)

	rows = read_csv_content(filepath[1])

	item_codes = []
	for row in rows:
		if row[0] != "ID":
			if row[0]:
				item_codes.append(row[0])

	result = []

	tables = {
		"Sales Order": "Sales Order Item",
		"Delivery Note": "Delivery Note Item",
		"Sales Invoice": "Sales Invoice Item",
		"Purchase Order": "Purchase Order Item",
		"Purchase Receipt": "Purchase Receipt Item",
		"Purchase Invoice": "Purchase Invoice Item"
	}

	for doctype, child in tables.items():

		data = frappe.get_all(
			child,
			filters={"item_code": ["in", item_codes]},
			fields=["item_code", "parent"]
		)

		for d in data:
			result.append([
				d.item_code,
				doctype,
				d.parent
			])

	wb = Workbook()
	ws = wb.active
	ws.title = "Item Transactions"

	ws.append(["Item Code", "Transaction Type", "Transaction ID"])

	for r in result:
		ws.append(r)

	file_stream = BytesIO()
	wb.save(file_stream)

	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": "Item_Transaction_Report.xlsx",
		"is_private": 0,
		"content": file_stream.getvalue()
	})

	file_doc.save(ignore_permissions=True)

	return file_doc.file_url


@frappe.whitelist()
def update_dn_so_qty(doc, method):
	if not doc.items:
		return
	for item in doc.items:
		if item.against_sales_order and item.so_detail:
			current_delivered = frappe.db.get_value("Sales Order Item",item.so_detail,"delivered_qty") or 0
			zoho_delivered = frappe.db.get_value("Sales Order Item",item.so_detail,"custom_zoho_delivered_qty") or 0
			new_qty = current_delivered + zoho_delivered
			frappe.db.set_value("Sales Order Item",item.so_detail,"delivered_qty",new_qty)

# On submission of Advance Sales Invoice validation against PE
@frappe.whitelist()
def validate_advance_sales_invoice(doc, method):
	# Validation removed: Advance Sales Invoice can now be submitted before the Payment Entry is created.
	# Payment Entry creation is provided via the "Create Payment Entry" button on the form.
	pass


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

import frappe
from frappe.utils import getdate, add_years, add_days, date_diff, nowdate

@frappe.whitelist()
def update_leave_allocation():
	emp_list = ['21117', '21134', '21124', '21127', '21105', '21106', '21099', '21107', '21144', '21143', '21142', 
				'21141', '21140', '21139', '21138', '21135', '21137', '21136', '21130', '21129', '21128', '21110', '21122']
	present_list=[]
	leave_type = 'Annual Vacation'
	today = getdate(nowdate())

	for e in emp_list:
		# 1. Check if allocation already exists
		if frappe.db.exists('Leave Allocation', {'employee': e, 'leave_type': leave_type, 'docstatus': 1}):
			present_list.append(e)
			continue
		
		doj = getdate(frappe.db.get_value('Employee', e, 'date_of_joining'))
		if not doj:
			continue

		first_year_end = add_days(add_years(doj, 1), -1)

		if first_year_end < today:
			create_allocation(e, leave_type, doj, first_year_end, 30)
			
			next_start = add_days(first_year_end, 1)
			next_end = add_days(add_years(next_start, 1), -1)
			create_allocation(e, leave_type, next_start, next_end, 30)
			
		else:
			days_passed = date_diff(today, doj)
			months_passed = days_passed / 30.0
			leaves_earned = int(months_passed) * 2.5
			if leaves_earned > 0:
				create_allocation(e, leave_type, doj, first_year_end, leaves_earned)
	print(present_list)
def create_allocation(employee, leave_type, from_date, to_date, leaves):
	print(employee)
	print(leaves)
	allocation = frappe.get_doc({
		"doctype": "Leave Allocation",
		"employee": employee,
		"leave_type": leave_type,
		"from_date": from_date,
		"to_date": to_date,
		"new_leaves_allocated": leaves,
		"docstatus": 1 # This submits the document immediately
	})
	allocation.insert()
	frappe.db.commit()




import frappe
import openpyxl

@frappe.whitelist()
def generate_so_delivery_report():

	file_url ="/files/JGB SO New.xlsx"

	file_doc = frappe.get_doc("File", {"file_url": file_url})
	file_path = file_doc.get_full_path()

	wb = openpyxl.load_workbook(file_path)
	sheet = wb.active

	result = []

	# Skip header row (row 1)
	for row in sheet.iter_rows(min_row=2, values_only=True):
		so_number = row[0]

		if not so_number:
			continue

		so_name = frappe.db.get_value(
			"Sales Order",
			{"custom_zoho_so_number": so_number},
			"name"
		)

		if not so_name:
			continue

		so = frappe.get_doc("Sales Order", so_name)

		for item in so.items:
			item_code = item.item_code

			dn_data = frappe.db.sql("""
				SELECT SUM(dni.qty) as delivered_qty
				FROM `tabDelivery Note Item` dni
				JOIN `tabDelivery Note` dn ON dn.name = dni.parent
				WHERE dn.docstatus = 1
				AND dni.against_sales_order = %s
				AND dni.item_code = %s
			""", (so.name, item_code), as_dict=1)

			delivered_qty = dn_data[0].delivered_qty if dn_data and dn_data[0].delivered_qty else 0

			result.append([
				so_number,
				so.name,
				item_code,
				item.delivered_qty,
				item.custom_zoho_delivered_qty,
				delivered_qty
			])

	# Create new Excel
	new_wb = openpyxl.Workbook()
	new_sheet = new_wb.active

	# Header
	new_sheet.append([
		"Zoho SO Number",
		"SO ID",
		"Item Code",
		"Delivered Qty",
		"Zoho Delivered Qty",
		"DN Qty"
	])

	# Data
	for row in result:
		new_sheet.append(row)

	file_name = "SO_Delivery_Report.xlsx"
	file_path = "/tmp/" + file_name
	new_wb.save(file_path)

	with open(file_path, "rb") as f:
		new_file = frappe.get_doc({
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": "Sales Order",
			"attached_to_name": so.name,
			"is_private": 0,
			"folder": "Home",
			"content": f.read()
		})
		new_file.save()

	return new_file.file_url

#completed
@frappe.whitelist()
def update_submitted_doc(docname, parent_data, child_data):
	doc = frappe.get_doc("Leave Application", docname)
	
	parent_dict = frappe.parse_json(parent_data)
	doc.update(parent_dict)
	
	doc.set("custom_family_details", [])
	for row in frappe.parse_json(child_data):
		doc.append("custom_family_details", row)
	
	doc.save("Update")
	return True

#completed
@frappe.whitelist()
def update_return_ticket(docname, parent_data, child_data):
	doc = frappe.get_doc("Leave Application", docname)
	
	parent_dict = frappe.parse_json(parent_data)
	doc.update(parent_dict)
	
	doc.set("custom_family_details_return", [])
	for row in frappe.parse_json(child_data):
		doc.append("custom_family_details_return", row)
	
	doc.save("Update")
	return True

#completed
@frappe.whitelist()
def get_lr_from_dn(dn):
	if not dn:
		return []

	data = frappe.db.sql("""
		SELECT DISTINCT parent AS lr_id
		FROM `tabLogistics Request Item`
		WHERE voucher_type = 'Delivery Note'
		AND voucher_no = %s
	""", dn, as_dict=1)

	return data


import frappe
@frappe.whitelist()
def update_lcv_currency():
	invoices = frappe.get_all("Landed Cost Voucher",{"docstatus": ["!=", 2]},["name"])
	ind=0
	for inv in invoices:
		ind+=1
		doc = frappe.get_doc("Landed Cost Voucher", inv.name)
		for row in doc.custom_purchase_invoice:
			if row.receipt_document_type and row.receipt_document:
				currency = frappe.db.get_value(row.receipt_document_type,row.receipt_document,"currency")
				if currency and row.currency != currency:
					frappe.db.set_value(row.doctype,row.name,"currency",currency)
	print(ind)
	print("Completed")


#completed
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
from frappe import _
# Notify Sales Engineer and Sales Person when Sales Order is updated after submission
@frappe.whitelist()
def notify_sales_order_update(doc, method):
	if doc.docstatus != 1:
		return

	old_doc = doc.get_doc_before_save()
	if not old_doc:
		return
	if old_doc.docstatus == 0 and doc.docstatus == 1:
		return

	if flt(old_doc.total) != flt(doc.total):

		last_idx = frappe.db.sql("""
			SELECT IFNULL(MAX(idx), 0)
			FROM `tabSales Order History`
			WHERE parent=%s
		""", doc.name)[0][0]

		row = frappe.new_doc("Sales Order History")
		row.parent = doc.name
		row.parenttype = "Sales Order"
		row.parentfield = "custom_sales_order_history"
		row.idx = last_idx + 1

		row.user = frappe.session.user
		row.date = now_datetime()
		row.value_from = old_doc.total
		row.value_to = doc.total
		row.remarks = f"Sales Order {doc.name} value updated from {old_doc.total} to {doc.total}"
		row.insert(ignore_permissions=True)
	users_to_notify = []

	if doc.owner and doc.owner!="Administrator":
		users_to_notify.append(doc.owner)

	if getattr(doc, "custom_sales_person", None):
		users_to_notify.append(doc.custom_sales_person)
	sales_engineers = frappe.db.sql_list("""
		SELECT DISTINCT
			`tabUser`.name
		FROM `tabHas Role`
		INNER JOIN `tabUser` ON `tabUser`.name = `tabHas Role`.parent
		WHERE `tabHas Role`.role = 'Sales Engineer'
		AND `tabUser`.enabled = 1
		AND `tabUser`.name != 'Administrator'
	""")

	for se in sales_engineers:
		users_to_notify.append(se)
	if not users_to_notify:
		return

	message = f"Sales Order {doc.name} has been updated. Please review the changes."

	frappe.get_doc({
		"doctype": "Comment",
		"comment_type": "Comment",
		"reference_doctype": "Sales Order",
		"reference_name": doc.name,
		"content": message,
		"comment_by": frappe.session.user,
		"communication_type": "Notification"
	}).insert(ignore_permissions=True)

	for user in users_to_notify:
		frappe.sendmail(
			recipients=[user],
			subject=f"Update on Sales Order {doc.name}",
			message=message
		)

import frappe
from frappe.utils import now_datetime
from frappe.utils.data import flt

def create_so_history(doc, remarks, value_from=0, value_to=0):
	last_idx = frappe.db.sql("""
		SELECT IFNULL(MAX(idx), 0)
		FROM `tabSales Order History`
		WHERE parent=%s
	""", doc.name)[0][0]

	row = frappe.new_doc("Sales Order History")
	row.parent = doc.name
	row.parenttype = "Sales Order"
	row.parentfield = "custom_sales_order_history"
	row.idx = last_idx + 1
	row.user = frappe.session.user
	row.date = now_datetime()
	row.value_from = value_from
	row.value_to = value_to
	row.remarks = remarks
	row.insert(ignore_permissions=True)

def so_amend_history(doc, method):

	if not doc.amended_from:
		return

	old_total = frappe.db.get_value(
		"Sales Order",
		doc.amended_from,
		"total"
	) or 0

	create_so_history(
		doc,
		remarks=f"Sales Order Amended from {doc.amended_from}",
		value_from=old_total,
		value_to=doc.total
	)


import frappe
from frappe.utils import flt

def expense_claim_before_insert(doc, method=None):
	if not doc.is_new():
		return

	if doc.advances:
		for d in doc.get("advances"):
			if flt(d.unclaimed_amount) > 0:
				d.unclaimed_amount = flt(d.unclaimed_amount, 2)




import frappe

@frappe.whitelist()
def change_outstanding():
	invoice_name = "JGB-VLP-SI-2026-00192"
	outstanding_amount = 188173.87  

	si = frappe.get_doc("Sales Invoice", invoice_name)

	frappe.db.set_value(
		"Sales Invoice",
		invoice_name,
		"outstanding_amount",
		outstanding_amount
	)

	frappe.db.commit()

	return f"Outstanding Amount updated to {outstanding_amount}"


#completed
@frappe.whitelist()
def create_pay_now_deduction(doc, method):
	leave_filters = {
		'to_date': ('between', [doc.start_date, doc.end_date]),
		'leave_type': 'Annual Vacation',
		'employee': doc.employee,
		'docstatus': 1,
		'custom_payment_type': 'Pay Now'
	}
	if frappe.db.exists('Leave Application', leave_filters):
		ded_amount = frappe.db.get_value('Leave Application', leave_filters, 'custom_leave_salary_amount')
		salary_filters = {
			"employee": doc.employee, 
			"salary_component": "Leave Deduction",
			"payroll_date": doc.start_date,
			"docstatus": 1
		}
		if not frappe.db.exists('Additional Salary', salary_filters):
			add_salary = frappe.new_doc('Additional Salary')
			add_salary.employee = doc.employee
			add_salary.salary_component = 'Leave Deduction'
			add_salary.payroll_date = doc.start_date
			add_salary.amount = ded_amount  
			add_salary.overwrite_salary_structure_amount = 1        
			add_salary.insert() 
			add_salary.submit()


#completed
@frappe.whitelist()
def calculate_vacation_pay_by_month(leave_application, hra_only=0):
	hra_only = cint(hra_only)
	if isinstance(leave_application, str):
		leave_application = frappe.get_doc("Leave Application", leave_application)
	if (
		not hasattr(leave_application, "leave_type")
		or leave_application.leave_type != "Annual Vacation"
		or getattr(leave_application, "custom_payment_type", None) != "Pay Now"
	):
		return []

	employee_map = {"Basic": "custom_basic", "HRA": "custom_hra"}
	promotion_map = {"HRA": "hra"} if hra_only else PROMOTION_FIELD_MAP

	employee = frappe.get_doc("Employee", leave_application.employee)
	periods = split_period(getdate(leave_application.from_date), getdate(leave_application.to_date))

	from_date = getdate(leave_application.from_date)
	latest_promotion = get_latest_promotion_row(leave_application.employee)
	period_promotion = get_promotion_row(
		leave_application.employee,
		leave_application.from_date,
		leave_application.to_date
	)

	monthly_totals = {}

	for component, emp_field in employee_map.items():
		emp_amt = float(employee.get(emp_field) or 0)

		old_days = float(leave_application.get(COMPONENT_OLD_DAYS_FIELD.get(component)) or 0)
		if hra_only == 1 and component == "Basic" and not old_days:
			continue
		if old_days > 0:
			future_promotion = latest_promotion
			promo_date = (
				add_days(from_date, old_days)
				if future_promotion or (hra_only == 1 and component == "Basic") else None
			)
		else:
			future_promotion = period_promotion
			promo_date = (
				getdate(period_promotion.promotion_date)
				if period_promotion else None
			)
		promo_frac = old_days % 1

		for start, end in periods:
			month_days = get_month_days(start)
			days = date_diff(end, start) + 1

			old_amt = emp_amt
			new_amt = emp_amt

			if future_promotion and component in promotion_map:
				field = promotion_map[component]
				old_amt = float(getattr(future_promotion, field, emp_amt) or emp_amt)
				new_amt = float(getattr(future_promotion, "new_" + field, old_amt) or old_amt)

			if hra_only == 1 and component == "Basic":
				new_amt = 0

			is_revised = promo_date and old_amt != new_amt

			if is_revised and (start < promo_date <= end or (start == promo_date and promo_frac)):
				before_days = date_diff(add_days(promo_date, -1), start) + 1 + promo_frac
				after_days = date_diff(end, promo_date) + 1 - promo_frac

				amount = round(
					prorate(old_amt, before_days, month_days)
					+ prorate(new_amt, after_days, month_days),
					2,
				)
			elif is_revised and end < promo_date:
				amount = round(prorate(old_amt, days, month_days), 2)
			elif is_revised and start >= promo_date:
				amount = round(prorate(new_amt, days, month_days), 2)
			else:
				amount = round(prorate(emp_amt, days, month_days), 2)

			if amount:
				monthly_totals[start] = monthly_totals.get(start, 0) + amount

	return [
		{"from_date": start, "amount": round(amt, 2)}
		for start, amt in sorted(monthly_totals.items())
	]

#completed
@frappe.whitelist()
def create_vacation_pay_deductions(doc, method):
	# Leave Deduction is no longer created - this only reconciles (cancels)
	# leftover Leave Deduction rows for the leave's months.
	from jgb.jgb.teampro.leave_application import _sync_leave_deduction_months

	if doc.leave_type != "Annual Vacation":
		return
	_sync_leave_deduction_months(doc)


@frappe.whitelist()
def process_existing_pay_now_vacation_leaves(create=0):
	"""Legacy utility - Leave Deduction rows are no longer created. With
	create=1 it reconciles (cancels) leftover Leave Deduction rows for the
	months covering Pay Now leaves."""
	from frappe.utils import get_first_day, get_last_day
	from jgb.jgb.teampro.leave_application import reconcile_leave_deduction

	create = cint(create)
	leave_apps = frappe.get_all(
		"Leave Application",
		filters={
			"docstatus": 1,
			"status": "Approved",
			"leave_type": "Annual Vacation",
			"custom_payment_type": "Pay Now",
		},
		fields=["name", "employee", "company", "custom_pay_hra_only"],
	)

	records = []

	for la in leave_apps:
		months = set()
		for row in calculate_vacation_pay_by_month(la.name, cint(la.get("custom_pay_hra_only") or 0)):
			months.add(get_first_day(getdate(row["from_date"])))

			records.append({
				"employee": la.employee,
				"leave_application": la.name,
				"company": la.company,
				"salary_component": "Leave Deduction",
				"payroll_date": row["from_date"],
				"amount": row["amount"],
			})

		if create:
			for m in months:
				reconcile_leave_deduction(la.employee, la.company, m, get_last_day(m))

	return {
		"mode": "reconciled" if create else "preview",
		"count": len(records),
		"records": records,
	}


def send_agm_dm_notification(doc, method):

	if doc.workflow_state != "AGM/DM Pending":
		return

	if not doc.custom_division:
		return

	division = frappe.get_doc("Division", doc.custom_division)

	email_list = []

	for row in division.division_managers:
		if row.division_manager:
			email_list.append(row.division_manager)

	if email_list:
		frappe.sendmail(
			recipients=email_list,
			subject=f"{doc.name} - Pending for AGM/DM",
			message=f"""
			<p>Dear Sir/Madam,</p>

				<p>
				This is to inform you that the Sales Order 
				<strong>
					<a href="{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }" target="_blank">
						{ doc.name }
					</a>
				</strong> 
				is currently pending your approval.
				</p>

				<p>
				Please review the details and take the necessary action.
				</p>

			"""
		)


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


import frappe
from datetime import date, timedelta
import calendar
from frappe.utils import getdate, add_years, add_months

@frappe.whitelist()
def create_update_leave_allocation_new():
	today = getdate(date.today())
	# today = getdate("2026-08-17") 
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		# 'employee': ["not in", ["21064", "21048", "21059", "21050"]]
		fields=["name", "date_of_joining"]
	)
	for emp in employees:
		doj = getdate(emp.date_of_joining)
		if not doj or today < doj:
			continue
		current_year_doj = doj.replace(year=today.year)
		if today < current_year_doj:
			base_doj = doj.replace(year=today.year - 1)
		else:
			base_doj = current_year_doj
		# next_allocation_date = add_months(base_doj, 1)
		# if today < next_allocation_date:
		# 	continue
		if today < base_doj:
			continue
		if today.day < doj.day:
			continue
		year_start = doj.replace(year=today.year)
		if year_start > today:
			year_start = year_start.replace(year=today.year - 1)
		year_end = add_years(year_start, 1) - timedelta(days=1)
		la_name = frappe.db.exists(
			"Leave Allocation",
			{
				"employee": emp.name,
				"leave_type": "Annual Vacation",
				"from_date": year_start,
				"to_date": year_end,
				"docstatus": 1
			}
		)
		# la_name ="HR-LAL-2026-00264"
		if la_name:
			la = frappe.get_doc("Leave Allocation", la_name)
		else:
			la = frappe.new_doc("Leave Allocation")
			la.employee = emp.name
			la.leave_type = "Annual Vacation"
			la.from_date = year_start
			la.to_date = year_end
			la.carry_forward = 1
			la.new_leaves_allocated = 0
		allocated_months = int(la.new_leaves_allocated / 2.5)
		current_month_index = (
			(today.year - year_start.year) * 12
			+ today.month - year_start.month
		)
		if current_month_index < allocated_months:
			continue
		# is_first_year = year_start == doj
		# # first_allocation_date = add_months(doj, 1)
		# # is_first_allocation_month = (
		# # 	today.year == first_allocation_date.year
		# # 	and today.month == first_allocation_date.month
		# # )
		# is_first_allocation_month = (
		# 	today.year == doj.year
		# 	and today.month == doj.month
		# )
		# if is_first_year and is_first_allocation_month and la.new_leaves_allocated == 0:
		# 	month_days = calendar.monthrange(doj.year, doj.month)[1]
		# 	worked_days = month_days - doj.day + 1
		# 	allocation = round((2.5 / month_days) * worked_days, 2)
		# else:
		allocation = 2.5
		la.new_leaves_allocated += allocation
		la.save(ignore_permissions=True)
		if la.docstatus == 0:
			la.submit()


import json
import frappe
import time
from frappe.utils import now_datetime


def capture_so_changes(doc, method):
	frappe.enqueue("jgb.jgb.custom.create_so_history_from_version",queue="short",docname=doc.name)

def create_so_history_from_version(docname):
	time.sleep(2)
	doc = frappe.get_doc("Sales Order", docname)
	if doc.docstatus != 1:
		return
	# old_doc = doc.get_doc_before_save()
	# if not old_doc:
	#     return
	# if old_doc.docstatus == 0 and doc.docstatus == 1:
	#     return
	version_name = frappe.db.sql("""
		SELECT name
		FROM `tabVersion`
		WHERE ref_doctype='Sales Order'
		AND docname=%s
		ORDER BY creation DESC
		LIMIT 1
	""", docname)
	if not version_name:
		return
	version = frappe.get_doc("Version", version_name[0][0])
	try:
		data = json.loads(version.data)
	except Exception:
		return
	changes = []
	value_from = 0
	value_to = 0
	payment_terms_changed = False

	for field in data.get("changed", []):
		if len(field) < 3:
			continue

		fieldname = field[0]
		old_value = field[1]
		new_value = field[2]

		if fieldname == "payment_terms_template":
			payment_terms_changed = True
			value_from = old_value or ""
			value_to = new_value or ""

			changes.append(
				f"Payment Terms updated from '{old_value}' to '{new_value}'"
			)

		elif fieldname == "total":
			value_from = old_value
			value_to = new_value

			changes.append(
				f"Sales Order value updated from {old_value} to {new_value}"
			)
	row_changed = data.get("row_changed", [])
	for row in row_changed:
		if not isinstance(row, list):
			continue
		if len(row) < 4:
			continue
		table_name = row[0]
		if table_name != "items":
			continue
		item_row_name = row[2]
		changed_fields = row[3]
		item_code = frappe.db.get_value("Sales Order Item",item_row_name,"item_code") or ""
		for field in changed_fields:
			if len(field) < 3:
				continue
			fieldname = field[0]
			old_value = field[1]
			new_value = field[2]
			if fieldname in ("qty", "stock_qty"):
				changes.append(f"Quantity updated for {item_code} from {old_value} to {new_value}")
			elif fieldname == "rate":
				changes.append(f"Rate updated for {item_code} from {old_value} to {new_value}")
			elif fieldname == "amount":
				changes.append(f"Amount updated for {item_code} from {old_value} to {new_value}")
	if not changes:
		return
	remarks = "\n".join(changes)
	exists = frappe.db.exists("Sales Order History",{"parent": docname,"remarks": remarks})
	if exists:
		return
	last_idx = frappe.db.sql("""
		SELECT IFNULL(MAX(idx),0)
		FROM `tabSales Order History`
		WHERE parent=%s
	""", docname)[0][0]
	history = frappe.get_doc({
		"doctype": "Sales Order History",
		"parent": docname,
		"parenttype": "Sales Order",
		"parentfield": "custom_sales_order_history",
		"idx": last_idx + 1,
		"user": version.owner,
		"date": now_datetime(),
		"value_from": value_from,
		"value_to": value_to,
		"remarks": remarks
	})
	history.insert(ignore_permissions=True)
	users_to_notify = []
	if doc.owner and doc.owner != "Administrator":
		users_to_notify.append(doc.owner)
		
	if getattr(doc, "custom_sales_person", None):
		users_to_notify.append(doc.custom_sales_person)
	if getattr(doc, "custom_support_engineer", None):
		users_to_notify.append(doc.custom_support_engineer)
	# sales_engineers = frappe.db.sql_list("""
	#     SELECT DISTINCT
	#         u.name
	#     FROM `tabHas Role` hr
	#     INNER JOIN `tabUser` u
	#         ON u.name = hr.parent
	#     WHERE hr.role = 'Sales Engineer'
	#     AND u.enabled = 1
	#     AND u.name != 'Administrator'
	# """)
	# users_to_notify.extend(sales_engineers)
	users_to_notify = list(set(users_to_notify))
	if users_to_notify:
		message = f"""Sales Order <b>{doc.name}</b> has been updated.<br><br>
		Changes:<br>
		{remarks.replace(chr(10), '<br>')}
		"""
		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "Sales Order",
			"reference_name": doc.name,
			"content": message,
			"comment_by": version.owner,
			"communication_type": "Notification"
		}).insert(ignore_permissions=True)
		frappe.sendmail(
			recipients=users_to_notify,
			cc="faizah@jgbksa.com",
			subject=f"Sales Order Updated - {doc.name}",
			message=message
		)

import json
import html
import frappe
from frappe.utils import today, date_diff, cstr


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


# import frappe
# from openpyxl import Workbook
# from io import BytesIO

# @frappe.whitelist()
# def export_po_receipt_mismatch():

#     data = frappe.db.sql("""
#         SELECT
#             po.name AS purchase_order,
#             poi.item_code,
#             poi.qty AS po_qty,
#             poi.received_qty,
#             pri.parent AS purchase_receipt,
#             pri.qty AS pr_qty,
#             pr.posting_date
#         FROM `tabPurchase Order Item` poi
#         JOIN `tabPurchase Order` po
#             ON po.name = poi.parent
#         JOIN `tabPurchase Receipt Item` pri
#             ON pri.purchase_order = po.name
#             AND pri.item_code = poi.item_code
#         JOIN `tabPurchase Receipt` pr
#             ON pr.name = pri.parent
#         WHERE po.docstatus = 1
#             AND pr.docstatus = 1
#     """, as_dict=True)

#     wb = Workbook()
#     ws = wb.active
#     ws.title = "PO Receipt Check"

#     headers = [
#         "Purchase Order",
#         "Item Code",
#         "PO Qty",
#         "Received Qty",
#         "Purchase Receipt",
#         "PR Qty",
#         "Posting Date"
#     ]

#     for col_num, header in enumerate(headers, 1):
#         ws.cell(row=1, column=col_num).value = header

#     for row_num, row in enumerate(data, 2):
#         ws.cell(row=row_num, column=1).value = row.purchase_order
#         ws.cell(row=row_num, column=2).value = row.item_code
#         ws.cell(row=row_num, column=3).value = row.po_qty
#         ws.cell(row=row_num, column=4).value = row.received_qty
#         ws.cell(row=row_num, column=5).value = row.purchase_receipt
#         ws.cell(row=row_num, column=6).value = row.pr_qty
#         ws.cell(row=row_num, column=7).value = str(row.posting_date)

#     output = BytesIO()
#     wb.save(output)

#     file_doc = frappe.get_doc({
#         "doctype": "File",
#         "file_name": "PO_Receipt_Check.xlsx",
#         "is_private": 0,
#         "content": output.getvalue()
#     })

#     file_doc.save(ignore_permissions=True)
#     frappe.db.commit()

#     return file_doc.file_url




@frappe.whitelist()
def ageing_report_summary_sales_person(doc):
	import json, html
	from frappe.utils import cstr

	try:
		if isinstance(doc, str):
			doc = frappe._dict(json.loads(doc))

		if not doc.get("company"):
			frappe.throw("Kindly choose company")

		args = frappe._dict({
			"company": doc.get("company"),
			"sales_person": doc.get("sales_person") or None,
			"region": doc.get("region") or None,
			"to_date": doc.get("to_date") or None
		})

		data_rows = accounts_aging_sales_person(args) or []

		def fmt_currency(val):
			try:
				num = float(val)
				return f"{num:,.2f}"
			except (ValueError, TypeError):
				return str(val)

		html_output = """
		<style>
			.ar-table { width: 100%; border-collapse: collapse; font-family: 'Calibri', Arial, sans-serif; font-size: 10px; table-layout: fixed; }
			.ar-table thead th { background: #1F3864; color: #FFFFFF; font-weight: bold; text-align: center; padding: 8px 2px; border: 1px solid #1F3864; font-size: 11px; word-wrap: break-word; overflow-wrap: break-word; }
			.ar-table tbody td { padding: 4px 2px; border: 1px solid #D0D0D0; word-wrap: break-word; overflow-wrap: break-word; }
			.ar-table tbody tr.alt-row { background: #F7F9FC; }
			.ar-table tbody tr.salesperson-row td { background: #4472C4; color: #FFFFFF; font-weight: bold; font-size: 13px; text-align: center; padding: 10px; }
			.ar-table tbody tr.subtotal-row td { background: #D9E1F2; font-weight: bold; color: #1F3864; font-size: 11px; }
			.ar-table tbody tr.grand-total-row td { background: #1F3864; color: #FFFFFF; font-weight: bold; font-size: 12px; }
			.ar-table tbody td.text-left { text-align: left; }
			.ar-table tbody td.currency { text-align: right; font-variant-numeric: tabular-nums; }
		</style>
		<table class="ar-table">
		"""

		headers = [
			"Posting Date", "Voucher No", "Customer Code", "Customer Name", "Customer LPO",
			"Invoiced", "Paid", "Credit Note",
			"Outstanding", "Age", "0-30", "31-60", "61-90", "Above 90"
		]

		widths = ["7%", "10%", "8%", "12%", "10%", "7%", "7%", "7%", "7%", "4%", "5%", "5%", "5%", "5%"]

		html_output += "<thead><tr>"
		for i, head in enumerate(headers):
			html_output += f"<th style='width:{widths[i]}'>{head}</th>"
		html_output += "</tr></thead><tbody>"

		alt_row = False
		for row in data_rows:

			if not row:
				continue

			row_str = str(row[0]) if len(row) > 0 else ""

			# Sales Person Heading
			if row_str.startswith("SALESPERSON:"):
				html_output += f"""
				<tr class="salesperson-row">
					<td colspan="14">{html.escape(row_str.replace("SALESPERSON:", "").strip())}</td>
				</tr>
				"""
				alt_row = False
				continue

			# Grand Total
			if row_str == "GRAND TOTAL":
				html_output += "<tr class='grand-total-row'>"
				html_output += f"<td colspan='5' style='text-align:left'>{html.escape(row_str)}</td>"
				for cell in row[5:]:
					html_output += f"<td class='currency'>{html.escape(fmt_currency(cell))}</td>"
				html_output += "</tr>"
				alt_row = False
				continue

			# Subtotal
			if row_str.startswith("Subtotal:"):
				html_output += "<tr class='subtotal-row'>"
				html_output += f"<td colspan='5' style='text-align:left'>{html.escape(row_str)}</td>"
				for cell in row[5:]:
					html_output += f"<td class='currency'>{html.escape(fmt_currency(cell))}</td>"
				html_output += "</tr>"
				alt_row = False
				continue

			# Regular data row
			row_class = " class='alt-row'" if alt_row else ""
			html_output += f"<tr{row_class}>"
			for i, cell in enumerate(row):
				align = "text-left" if i < 5 else "currency"
				html_output += f"<td class='{align}'>{html.escape(str(cell))}</td>"
			html_output += "</tr>"
			alt_row = not alt_row

		html_output += "</tbody></table>"

		return cstr(html_output)

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Ageing Report Error")
		frappe.throw(f"Report Error: {str(e)}")


@frappe.whitelist()
def receivable_summary_salesperson(doc):
	import json, html
	from frappe.utils import cstr, fmt_money

	def fmt_currency(val):
		try:
			num = float(val)
			if num == 0:
				return "0.00"
			return f"{num:,.2f}"
		except (ValueError, TypeError):
			return str(val)

	try:
		if isinstance(doc, str):
			doc = frappe._dict(json.loads(doc))

		if not doc.get("company"):
			frappe.throw("Kindly choose company")

		args = frappe._dict({
			"company": doc.get("company"),
			"sales_person": doc.get("sales_person") or None,
			"region": doc.get("region") or None,
			"to_date": doc.get("to_date") or None
		})

		data_rows = accounts_receivable_summary(args) or []

		html_output = """
		<style>
			.ar-table {
				width: 100%;
				border-collapse: collapse;
				font-family: 'Calibri', Arial, sans-serif;
				font-size: 11px;
			}
			.ar-table thead th {
				background: #1F3864;
				color: #FFFFFF;
				font-weight: bold;
				text-align: center;
				padding: 10px 6px;
				border: 1px solid #1F3864;
				font-size: 12px;
			}
			.ar-table tbody td {
				padding: 6px 8px;
				border: 1px solid #D0D0D0;
			}
			.ar-table tbody tr.alt-row {
				background: #F7F9FC;
			}
			.ar-table tbody tr.salesperson-row td {
				background: #4472C4;
				color: #FFFFFF;
				font-weight: bold;
				font-size: 14px;
				text-align: center;
				padding: 10px;
			}
			.ar-table tbody tr.subtotal-row td {
				background: #D9E1F2;
				font-weight: bold;
				color: #1F3864;
				font-size: 12px;
			}
			.ar-table tbody tr.grand-total-row td {
				background: #1F3864;
				color: #FFFFFF;
				font-weight: bold;
				font-size: 13px;
			}
			.ar-table tbody td.text-left { text-align: left; }
			.ar-table tbody td.text-right { text-align: right; }
			.ar-table tbody td.text-center { text-align: center; }
			.ar-table tbody td.currency {
				text-align: right;
				font-variant-numeric: tabular-nums;
			}
		</style>
		<table class="ar-table">
		"""

		headers = [
			"Customer Code", "Customer Name",
			"Invoiced", "Paid", "Credit Note", "Outstanding"
		]

		widths = ["15%", "30%", "15%", "15%", "15%", "15%"]

		html_output += "<thead><tr>"
		for i, head in enumerate(headers):
			html_output += f"<th style='width:{widths[i]}'>{head}</th>"
		html_output += "</tr></thead><tbody>"

		alt_row = False
		for row in data_rows:

			if not row:
				continue

			row_str = str(row[0]) if len(row) > 0 else ""

			# Sales Person Heading
			if row_str.startswith("SALESPERSON:"):
				html_output += f"""
				<tr class="salesperson-row">
					<td colspan="6">{html.escape(row_str.replace("SALESPERSON:", "").strip())}</td>
				</tr>
				"""
				alt_row = False
				continue

			# Grand Total
			if row_str == "GRAND TOTAL":
				html_output += "<tr class='grand-total-row'>"
				html_output += f"<td colspan='2' style='text-align:left'>{html.escape(row_str)}</td>"
				for cell in row[2:]:
					html_output += f"<td class='currency'>{html.escape(fmt_currency(cell))}</td>"
				html_output += "</tr>"
				alt_row = False
				continue

			# Subtotal
			if row_str.startswith("Subtotal:"):
				html_output += "<tr class='subtotal-row'>"
				html_output += f"<td colspan='2' style='text-align:left'>{html.escape(row_str)}</td>"
				for cell in row[2:]:
					html_output += f"<td class='currency'>{html.escape(fmt_currency(cell))}</td>"
				html_output += "</tr>"
				alt_row = False
				continue

			# Regular data row
			row_class = " class='alt-row'" if alt_row else ""
			html_output += f"<tr{row_class}>"
			html_output += f"<td class='text-left'>{html.escape(str(row[0]))}</td>"
			html_output += f"<td class='text-left'>{html.escape(str(row[1]))}</td>"
			for cell in row[2:]:
				html_output += f"<td class='currency'>{html.escape(fmt_currency(cell))}</td>"
			html_output += "</tr>"
			alt_row = not alt_row

		html_output += "</tbody></table>"

		return cstr(html_output)

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Receivable Summary Sales Person Error")
		frappe.throw(f"Report Error: {str(e)}")




@frappe.whitelist()
def send_agm_dm_notification_po(doc, method):

	if doc.workflow_state != "AGM/DM Pending":
		return

	if not doc.custom_division:
		return

	division = frappe.get_doc("Division", doc.custom_division)

	email_list = []


	for row in division.division_managers:
		if row.division_manager:
			email_list.append(row.division_manager)

	if email_list:
		frappe.sendmail(
			recipients=email_list,
			subject=f"Purchase Order {doc.name} Awaiting Approval",
			message=f"""
			<p>Dear Sir/Madam,</p>

				<p>
				This is to inform you that the Purchase Order 
				<strong>
					<a href="{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }" target="_blank">
						{ doc.name }
					</a>
				</strong> 
				is currently pending your approval.
				</p>

				<p>
				Please review the details and take the necessary action.
				</p>

			"""
		)



@frappe.whitelist()
def send_payment_terms_notification(doc, method):
	old_doc = doc.get_doc_before_save()

	if not old_doc:
		return

	if old_doc.payment_terms_template == doc.payment_terms_template:
		return

	cfo_emails = frappe.db.sql_list("""
		SELECT u.email
		FROM `tabHas Role` hr
		INNER JOIN `tabUser` u
			ON u.name = hr.parent
		WHERE hr.role = 'CFO'
		AND u.enabled = 1
	""")

	if not cfo_emails:
		return
	
	user_name = frappe.db.get_value(
		"User",
		frappe.session.user,
		"full_name"
	) or frappe.session.user

	frappe.sendmail(
		recipients=cfo_emails,
		subject=f"Payment Terms Updated for Sales Order {doc.name}",
		message=f"""
		<p>Dear Sir/Madam,</p>

		<p>The Payment Terms for Sales Order <b>{doc.name}</b> have been updated after submission by <b>{user_name}</b>.</p>

		<p>The Payment Terms have been changed from <b>{old_doc.payment_terms_template or 'None'}</b> to <b>{doc.payment_terms_template or 'None'}</b>.</p>

		<p>Please review the updated Payment Terms at your convenience.</p>

		<p>Regards,<br>ERP System</p>
		"""
	)



#completed
import frappe
from frappe.utils import getdate

@frappe.whitelist()
def load_repair_summary(doc, method=None):

	doc.set("custom_repair_summary", [])

	if not doc.asset:
		return

	repairs = frappe.get_all(
		"Asset Repair",
		filters={
			"asset": doc.asset,
			"docstatus": 1,
			"name": ["!=", doc.name]
		},
		fields=[
			"name",
			"failure_date",
			"repair_status",
			"asset"
			
		],
		order_by="failure_date desc"
	)

	for repair in repairs:
		repair_doc = frappe.get_doc("Asset Repair", repair.name)

		estimated_cost = 0
		actual_cost = 0
		remarks = []

		for row in repair_doc.custom_asset_estimation_details:
			estimated_cost += row.estimated_amount or 0
			actual_cost += row.actual_amount or 0

			if row.error_description:
				remarks.append(row.error_description)

		doc.append("custom_repair_summary", {
			"asset": repair.asset,
			"repair_date": getdate(repair.failure_date) if repair.failure_date else None,
			"repair_status": repair.repair_status,
			"estimated_cost": estimated_cost,
			"actual_cost": actual_cost,
			"remarks": ", ".join(remarks)
		})




@frappe.whitelist()
def send_workflow_email(doc, method=None):
	if not doc.has_value_changed("workflow_state"):
		return

	if doc.workflow_state == "Pending for HR Manager":
		send_email_to_role(
			role="HR Manager",
			subject=f"Asset Repair {doc.name} - Pending for HR Manager",
			message=f"""
			<p>Dear Sir/Madam,</p>
			<p>
				Asset Repair
				<a href="{frappe.utils.get_url()}/app/asset-repair/{doc.name}">
				<b>{doc.name}</b>
				</a>
				is pending for your approval for Asset <b>{doc.asset}</b>. Please review and take the necessary action.
			</p>
			<p>Regards,<br>ERPNext</p>
			"""
		)

	elif doc.workflow_state == "Pending for Chief Acc. Verification":
		send_email_to_role(
			role="Regional Accountant",
			subject=f"Asset Repair {doc.name} - Pending for Chief Acc. Verification",
			message=f"""
			<p>Dear Sir/Madam,</p>
			<p>
				Asset Repair
				<a href="{frappe.utils.get_url()}/app/asset-repair/{doc.name}">
				<b>{doc.name}</b>
				</a>
				is pending for your approval for Asset <b>{doc.asset}</b>. Please review and take the necessary action.
			</p>
			<p>Regards,<br>ERPNext</p>
			"""
		)

	elif doc.workflow_state == "Approved":
		if doc.custom_custodian:
			email = frappe.db.get_value("Employee", doc.custom_custodian, "user_id")

			if email:
				frappe.sendmail(
					recipients=[email],
					subject=f"Asset Repair {doc.name} Approved",
					message=f"""
					<p>Dear {doc.custom_custodian_name},</p>

					<p>
					Asset Repair
					<a href="{frappe.utils.get_url()}/app/asset-repair/{doc.name}">
					<b>{doc.name}</b>
					</a>
					has been approved for Asset <b>{doc.asset}</b>.
					</p>

					<p>Regards,<br>ERPNext</p>
					"""
				)


def send_email_to_role(role, subject, message):
	users = frappe.get_all(
		"Has Role",
		filters={"role": role},
		pluck="parent"
	)

	emails = []
	for user in users:
		email = frappe.db.get_value("User", user, "email")
		if email:
			emails.append(email)

	if emails:
		frappe.sendmail(
			recipients=emails,
			subject=subject,
			message=message
		)



# @frappe.whitelist()
# def update_received_qty_po():

#     po_name = "JGB-VPD-PO-2025-00005-1"   

#     if not frappe.db.exists("Purchase Order", po_name):
#         frappe.throw("Purchase Order not found")

#     po = frappe.get_doc("Purchase Order", po_name)

#     for item in po.items:

#         received_qty = frappe.db.sql("""
#             SELECT COALESCE(SUM(pri.qty), 0)
#             FROM `tabPurchase Receipt Item` pri
#             INNER JOIN `tabPurchase Receipt` pr
#                 ON pr.name = pri.parent
#             WHERE pr.docstatus = 1
#                 AND pri.purchase_order = %s
#                 AND pri.item_code = %s
#         """, (po_name, item.item_code))[0][0]

#         frappe.db.set_value(
#             "Purchase Order Item",
#             item.name,
#             "received_qty",
#             received_qty,
#             update_modified=False
#         )

#         print(f"{po_name} | {item.item_code} | {item.received_qty} -> {received_qty}")

#     po.reload()
#     po.set_status(update=True)

#     frappe.db.commit()

#     print(f"Purchase Order {po_name} updated successfully.")


# # @frappe.whitelist()
# # def update_received_qty():
# # 	import frappe

# # 	po_list = [
# # 		"POJGBKSA2362",
# # 	]

# # 	for po_name in po_list:
# # 		po = frappe.get_doc("Purchase Order", po_name)

# # 		for item in po.items:
# # 			frappe.db.set_value(
# # 				"Purchase Order Item",
# # 				item.name,
# # 				"received_qty",
# # 				0,
# # 				update_modified=False
# # 			)

# # 		po.reload()
# # 		po.set_status(update=True)

# # 	frappe.db.commit()

# # 	print("Received Qty updated to 0 successfully.")



# @frappe.whitelist()
# def update_received_qty_for_item_repeat():
# 	purchase_order = "JGB-VPD-PO-2025-00005-1"
# 	purchase_order_item = "dmrqn06r4b"   
# 	received_qty = 0

# 	po = frappe.get_doc("Purchase Order", purchase_order)

# 	for item in po.items:
# 		if item.name == purchase_order_item:
# 			item.received_qty = received_qty

# 	po.save(ignore_permissions=True)
# 	frappe.db.commit()

# 	print("Received Qty updated successfully.")




# import frappe

# @frappe.whitelist()
# def update_received_qty_excluding_po():

#     exclude_pos = [
#     "POJGBKSA2362",
#     "POJGBKSA2359",
#     "POJGBKSA2340",
#     "POJGBKSA2328",
#     "POJGBKSA2262",
#     "POJGBKSA2230-1",
#     "POJGBKSA2228",
#     "POJGBKSA2214",
#     "POJGBKSA2200",
#     "POJGBKSA2180-1",
#     "POJGBKSA2177",
#     "POJGBKSA2148",
#     "POJGBKSA2138",
#     "POJGBKSA2126",  
#     "POJGBKSA2123",
#     "POJGBKSA2119",
#     "POJGBKSA2118",
#     "POJGBKSA2117",
#     "POJGBKSA2112",
#     "POJGBKSA2102",
#     "POJGBKSA2096-1",
#     "POJGBKSA2093",
#     "POJGBKSA2057",
#     "POJGBKSA2048",
# 	"JGB-VPD-PO-2025-00005-1"
# ]

#     purchase_orders = frappe.get_all(
#         "Purchase Order",
#         filters={
#             "docstatus": 1,
#             "name": ["not in", exclude_pos]
#         },
#         pluck="name"
#     )

#     for po_name in purchase_orders:

#         po = frappe.get_doc("Purchase Order", po_name)

#         for item in po.items:

#             received_qty = frappe.db.sql("""
#                 SELECT COALESCE(SUM(pri.qty), 0)
#                 FROM `tabPurchase Receipt Item` pri
#                 INNER JOIN `tabPurchase Receipt` pr
#                     ON pr.name = pri.parent
#                 WHERE
#                     pr.docstatus = 1
#                     AND pri.purchase_order = %s
#                     AND pri.item_code = %s
#             """, (po_name, item.item_code))[0][0]

#             frappe.db.set_value(
#                 "Purchase Order Item",
#                 item.name,
#                 "received_qty",
#                 received_qty,
#                 update_modified=False
#             )

#             print(
#                 f"{po_name} | {item.item_code} | "
#                 f"Old: {item.received_qty} -> New: {received_qty}"
#             )

#         po.reload()
#         po.set_status(update=True)

#     frappe.db.commit()

#     print("Received Qty updated successfully.")



import frappe
import json
import html
from frappe import _
from frappe.utils import cstr

from jgb.jgb.doctype.accounts_report_dashboard.advance_received_from_customer import customer_advances_aging


@frappe.whitelist()
def ageing_report_summary_advance_received(doc):
	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))

	if not doc.get("company"):
		frappe.throw(_("Kindly choose Company"))

	filters = frappe._dict({
		"company": doc.company,
		"customer": doc.get("customer"),
		"to_date": doc.get("to_date")
	})

	data_rows = customer_advances_aging(filters)

	def fmt_currency(val):
		try:
			num = float(val)
			return f"{num:,.2f}"
		except (ValueError, TypeError):
			return str(val)

	headers = [
		"Posting Date",
		"Voucher No",
		"Sales Engineer",
		"Reference / Remarks",
		"Advance Received",
		"Allocated Amount",
		"Credit Note",
		"Unallocated Amount",
		"Age (Days)",
		"0-30",
		"31-60",
		"61-90",
		"Above 90"
	]

	widths = [
		"9%", "12%", "12%", "15%",
		"8%", "8%", "8%", "8%",
		"5%", "5%", "5%", "5%", "8%"
	]

	html_output = """
	<style>
		.ar-table { width: 100%; border-collapse: collapse; font-family: 'Calibri', Arial, sans-serif; font-size: 10px; table-layout: fixed; }
		.ar-table thead th { background: #1F3864; color: #FFFFFF; font-weight: bold; text-align: center; padding: 8px 4px; border: 1px solid #1F3864; font-size: 11px; }
		.ar-table tbody td { padding: 4px 4px; border: 1px solid #D0D0D0; }
		.ar-table tbody tr.alt-row { background: #F7F9FC; }
		.ar-table tbody tr.subtotal-row td { background: #D9E1F2; font-weight: bold; color: #1F3864; font-size: 11px; }
		.ar-table tbody tr.grand-total-row td { background: #1F3864; color: #FFFFFF; font-weight: bold; font-size: 12px; }
		.ar-table tbody td.text-left { text-align: left; }
		.ar-table tbody td.currency { text-align: right; font-variant-numeric: tabular-nums; }
	</style>
	<table class="ar-table">
	"""

	# Header
	html_output += "<thead><tr>"
	for i, header in enumerate(headers):
		html_output += f"<th style='width:{widths[i]}'>{html.escape(header)}</th>"
	html_output += "</tr></thead><tbody>"

	# Body
	alt_row = False
	for row in data_rows:

		first_col = cstr(row[0])

		# Grand Total
		if first_col == "GRAND TOTAL":
			html_output += "<tr class='grand-total-row'>"
			html_output += f"<td colspan='4' style='text-align:left'>{html.escape(first_col)}</td>"
			for cell in row[4:]:
				html_output += f"<td class='currency'>{html.escape(fmt_currency(cell))}</td>"
			html_output += "</tr>"
			alt_row = False

		# Subtotal
		elif first_col.startswith("Subtotal:"):
			html_output += "<tr class='subtotal-row'>"
			html_output += f"<td colspan='4' style='text-align:left'>{html.escape(first_col)}</td>"
			for cell in row[4:]:
				html_output += f"<td class='currency'>{html.escape(fmt_currency(cell))}</td>"
			html_output += "</tr>"
			alt_row = False

		else:
			row_class = " class='alt-row'" if alt_row else ""
			html_output += f"<tr{row_class}>"
			for idx, cell in enumerate(row):
				align = "text-left" if idx <= 3 else "currency"
				html_output += f"<td class='{align}'>{html.escape(cstr(cell))}</td>"
			html_output += "</tr>"
			alt_row = not alt_row

	html_output += """
		</tbody>
	</table>
	"""

	return cstr(html_output)


import frappe

@frappe.whitelist()
def fix_row_index(lr_name='LR-2026-00416', po_name='POJGBKSA2127', item_code='VLP-VLV-000187'):
	# 1. Remove the old row (only the one at idx 1)
	lr = frappe.get_doc("Logistics Request", lr_name)
	target_row_name = None
	
	for row in lr.product_description:
		if row.item_code == item_code and row.idx == 1:
			target_row_name = row.name
			break
	
	if target_row_name:
		frappe.delete_doc("Logistics Request Item", target_row_name)
	else:
		return {"status": "error", "message": "Row not found at index 1"}

	# 2. Get data from Purchase Order to re-add
	po = frappe.get_doc("Purchase Order", po_name)
	item = next((i for i in po.items if i.item_code == item_code), None)
	if not item:
		return {"status": "error", "message": "Item not found in PO"}

	# 3. Re-add at index 16
	conv_rate = float(lr.conversion_rate or 1)
	pending_qty = float(item.qty or 0)
	rate = float(item.rate or 0)
	amount = pending_qty * rate

	new_child = frappe.get_doc({
		"doctype": "Logistics Request Item", 
		"parent": lr_name,
		"parentfield": "product_description",
		"parenttype": "Logistics Request",
		"idx": 16, # Force index 16
		
		# All original fields mapped
		"item_code": item.item_code,
		"item_name": item.item_name,
		"description": item.description,
		"qty": pending_qty,
		"po_item": item.name,
		"rate": rate,
		"currency": lr.currency,
		"uom": item.uom,
		"amount": amount,
		"conversion_factor": item.conversion_factor or 1,
		"base_rate": rate * conv_rate,
		"base_amount": amount * conv_rate,
		"voucher_no": po.name,
		"voucher_type": "Purchase Order",
		"supplier": po.supplier,
		"requester_name": po.custom_sales_person,
		
		# Custom Packing Fields
		"box_name": item.get("custom_box_name"),
		"pallet_name": item.get("custom_pallet_name"),
		"no_of_boxes": item.get("custom_no_of_boxes"),
		"no_of_pallets": item.get("custom_no_of_pallets"),
		"total_box_weight_kg": item.get("custom_total_box_weight_kg"),
		"total_pallet_weight_kg": item.get("custom_total_pallet_weight_kg"),
		"box_length_mm": item.get("custom_box_length_mm"),
		"pallet_length_mm": item.get("custom_pallet_length_mm"),
		"box_breadth_mm": item.get("custom_box_breadth_mm"),
		"pallet_breadth_mm": item.get("custom_pallet_breadth_mm"),
		"box_height_mm": item.get("custom_box_height_mm"),
		"pallet_height_mm": item.get("custom_pallet_height_mm"),
		"cbm": item.get("custom_cbm"),
		"packing_weight_kg": item.get("custom_packing_weight_kg"),
		"gross_weight_kg": item.get("custom_gross_weight_kg")
	})
	
	new_child.insert(ignore_permissions=True)
	frappe.db.commit()
	
	return {"status": "success", "message": "Row moved to index 16 successfully."}


import frappe

import frappe

@frappe.whitelist()
def move_row_16_to_14():
	lr = frappe.get_doc("Logistics Request", "LR-2026-00416")

	row14 = None
	row16 = None

	for row in lr.product_description:
		if row.idx == 14:
			row14 = row
		elif row.idx == 16:
			row16 = row

	if not row14 or not row16:
		return {
			"status": "error",
			"message": "Row 14 or Row 16 not found."
		}

	# Copy all field values from row16 to row14
	exclude_fields = [
		"name", "parent", "parentfield", "parenttype",
		"doctype", "idx", "owner", "creation",
		"modified", "modified_by", "docstatus"
	]

	for key, value in row16.as_dict().items():
		if key not in exclude_fields:
			row14.set(key, value)

	# Delete row16 from child table
	lr.remove(row16)

	# Re-index child table
	for i, d in enumerate(lr.product_description, start=1):
		d.idx = i

	# Update submitted document
	lr.flags.ignore_validate_update_after_submit = True
	lr.save(ignore_permissions=True)

	frappe.db.commit()

	return {
		"status": "success",
		"message": "Row 16 data moved to Row 14 and Row 16 deleted successfully."
	}

def notify_salary_structure_assignment(doc, method):
	frappe.msgprint(
		_(
			"Employee <b>{0}</b> has been created successfully.<br><br>"
			"Please create the <b>Salary Structure Assignment</b> for this employee."
		).format(doc.employee_name),
		title=_("Salary Structure Assignment"),
		indicator="orange"
	)


import frappe

@frappe.whitelist()
def update_po_received_qty():
	po = frappe.get_doc("Purchase Order", "JGB-VPD-PO-2025-00004")

	for item in po.items:
		frappe.db.set_value(
			"Purchase Order Item",
			"4j1po4fddo",
			"received_qty",
			0,
			update_modified=False
		)

	frappe.db.commit()
	frappe.msgprint("Received Qty updated successfully.")



#completed
from frappe.utils import flt

@frappe.whitelist()
def get_so_qty_dashboard(sales_order):
	if not sales_order or not frappe.db.exists("Sales Order", sales_order):
		return {}

	so = frappe.get_doc("Sales Order", sales_order)
	item_map = {
		d.item_code: {
			"so_qty": 0.0,
			"delivered_qty": 0.0,
			"po_qty": 0.0,
			"received_qty": 0.0,
			"stock_qty": 0.0,
			"reserved_qty": 0.0,
		}
		for d in so.items
	}

	for d in so.items:
		item_map[d.item_code]["so_qty"] += flt(d.qty)
		item_map[d.item_code]["delivered_qty"] += flt(d.delivered_qty)

	for d in frappe.db.sql(
		"""
		SELECT poi.item_code, SUM(poi.qty) as qty
		FROM `tabPurchase Order Item` poi
		JOIN `tabPurchase Order` po ON po.name = poi.parent
		WHERE po.docstatus = 1 AND poi.sales_order = %s
		GROUP BY poi.item_code
	""",
		(sales_order,),
		as_dict=1,
	):
		if d.item_code in item_map:
			item_map[d.item_code]["po_qty"] += flt(d.qty)

	for d in frappe.db.sql(
		"""
		SELECT pri.item_code, SUM(pri.qty) as qty
		FROM `tabPurchase Receipt Item` pri
		JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
		JOIN `tabPurchase Order Item` poi ON poi.name = pri.purchase_order_item
		WHERE pr.docstatus = 1 AND poi.sales_order = %s
		GROUP BY pri.item_code
	""",
		(sales_order,),
		as_dict=1,
	):
		if d.item_code in item_map:
			item_map[d.item_code]["received_qty"] += flt(d.qty)

	if item_map:
		item_codes = tuple(item_map.keys())
		for d in frappe.db.sql(
			"""
			SELECT item_code, SUM(actual_qty) as actual_qty, SUM(reserved_qty) as reserved_qty
			FROM `tabBin`
			WHERE item_code IN %s
			GROUP BY item_code
		""",
			(item_codes,),
			as_dict=1,
		):
			if d.item_code in item_map:
				item_map[d.item_code]["stock_qty"] += flt(d.actual_qty)
				item_map[d.item_code]["reserved_qty"] += flt(d.reserved_qty)

	totals = {
		"total_po_qty": sum(v["po_qty"] for v in item_map.values()),
		"total_received_qty": sum(v["received_qty"] for v in item_map.values()),
		"total_so_qty": sum(v["so_qty"] for v in item_map.values()),
		"total_delivered_qty": sum(v["delivered_qty"] for v in item_map.values()),
		"total_stock_qty": sum(v["stock_qty"] for v in item_map.values()),
		"total_reserved_qty": sum(v["reserved_qty"] for v in item_map.values()),
	}
	totals["balance_receive"] = totals["total_po_qty"] - totals["total_received_qty"]
	totals["balance_delivery"] = totals["total_so_qty"] - totals["total_delivered_qty"]
	totals["total_free_stock"] = totals["total_stock_qty"] - totals["total_reserved_qty"]

	items = []
	for item_code, data in item_map.items():
		items.append(
			{
				"item_code": item_code,
				"so_qty": data["so_qty"],
				"delivered_qty": data["delivered_qty"],
				"po_qty": data["po_qty"],
				"received_qty": data["received_qty"],
				"stock_qty": data["stock_qty"],
				"reserved_qty": data["reserved_qty"],
				"balance_receive": flt(data["po_qty"]) - flt(data["received_qty"]),
				"balance_delivery": flt(data["so_qty"]) - flt(data["delivered_qty"]),
				"free_stock": flt(data["stock_qty"]) - flt(data["reserved_qty"]),
			}
		)

	return {"items": items, "totals": totals}

#completed
@frappe.whitelist()
def get_po_so_qty_dashboard(purchase_order):
	if not purchase_order or not frappe.db.exists("Purchase Order", purchase_order):
		return {}

	po_items = frappe.get_all(
		"Purchase Order Item",
		filters={"parent": purchase_order},
		fields=["name", "item_code", "sales_order_item"],
		order_by="idx",
	)

	so_item_names = [d.sales_order_item for d in po_items if d.sales_order_item]
	so_item_data = {}
	if so_item_names:
		for d in frappe.db.sql(
			"""
			SELECT name, qty, delivered_qty
			FROM `tabSales Order Item`
			WHERE name IN %s
		""",
			(tuple(so_item_names),),
			as_dict=1,
		):
			so_item_data[d.name] = {
				"so_qty": flt(d.qty),
				"delivered_qty": flt(d.delivered_qty),
			}

	items = []
	for d in po_items:
		so = so_item_data.get(d.sales_order_item, {"so_qty": 0, "delivered_qty": 0})
		so_qty = so["so_qty"]
		delivered_qty = so["delivered_qty"]
		items.append(
			{
				"item_code": d.item_code,
				"so_qty": so_qty,
				"delivered_qty": delivered_qty,
				"balance_so_qty": so_qty - delivered_qty,
			}
		)

	return {"items": items}




@frappe.whitelist()
def delete_stock_reservation_entry():
	frappe.delete_doc("Stock Reservation Entry", "MAT-SRE-2026-00018", force=True)
	frappe.db.commit()


@frappe.whitelist()
def _get_profitability_data(sales_invoice):
	doc = frappe.get_doc("Sales Invoice", sales_invoice)
	company_currency = frappe.get_cached_value("Company", doc.company, "default_currency")
	rows = []
	totals = frappe._dict(
		so_qty=0.0,
		inv_qty=0.0,
		dn_qty=0.0,
		cost=0.0,
		rate=0.0,
		profit=0.0,
		profit_pct=0.0,
	)
	for item in doc.items:
		ordered_qty = 0.0
		if item.sales_order and item.so_detail:
			ordered_qty = frappe.db.get_value("Sales Order Item", item.so_detail, "qty") or 0.0

		delivered_qty = 0.0
		if item.dn_detail:
			dn = frappe.db.get_value("Delivery Note Item", item.dn_detail, "qty")
			delivered_qty = flt(dn)
		elif item.sales_order:
			filters = {"against_sales_order": item.sales_order, "docstatus": 1}
			if item.so_detail:
				filters["so_detail"] = item.so_detail
			dn_items = frappe.get_all(
				"Delivery Note Item",
				filters=filters,
				fields=["qty"],
				order_by="creation",
			)
			delivered_qty = sum(flt(d.qty) for d in dn_items)

		bin_filters = {"item_code": item.item_code}
		if item.warehouse:
			bin_filters["warehouse"] = item.warehouse
		bins = frappe.get_all(
			"Bin",
			filters=bin_filters,
			fields=["valuation_rate"],
		)
		cost = 0.0
		if bins:
			cost = flt(sum(flt(b.valuation_rate) for b in bins) / len(bins))
		if not cost:
			cost = flt(frappe.db.get_value("Item", item.item_code, "valuation_rate"))
		if not cost:
			cost = flt(frappe.db.get_value("Item", item.item_code, "last_purchase_rate"))
		if not cost:
			pi_rate = frappe.db.sql(
				"""
				SELECT pii.base_rate
				FROM `tabPurchase Invoice Item` pii
				INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
				WHERE pii.item_code = %s AND pi.docstatus = 1
				ORDER BY pi.posting_date DESC, pii.creation DESC
				LIMIT 1
				""",
				item.item_code,
			)
			if pi_rate:
				cost = flt(pi_rate[0][0])

		so_qty = flt(ordered_qty)
		inv_qty = flt(item.qty)
		dn_qty = flt(delivered_qty)
		rate = flt(item.rate)
		base_rate = flt(item.base_rate)
		total = (base_rate - cost) * inv_qty if cost > 0 else 0.0
		profit_pct = 0.0
		if cost > 0:
			profit_pct = ((base_rate - cost) / cost) * 100

		rows.append(
			{
				"item": f"{item.item_code}: {item.item_name or ''}",
				"so_qty": so_qty,
				"inv_qty": inv_qty,
				"dn_qty": dn_qty,
				"cost": cost,
				"rate": rate,
				"total": total,
				"profit_pct": profit_pct,
			}
		)

		totals.so_qty += so_qty
		totals.inv_qty += inv_qty
		totals.dn_qty += dn_qty
		totals.cost += cost * inv_qty
		totals.rate += rate * inv_qty
		totals.profit += total

	if totals.cost > 0:
		totals.profit_pct = (totals.profit / totals.cost) * 100

	return frappe._dict(
		doc=doc,
		company_currency=company_currency,
		doc_currency=doc.currency,
		rows=rows,
		totals=totals,
	)


@frappe.whitelist()
def get_profitability_html(sales_invoice):
	data = _get_profitability_data(sales_invoice)
	company_currency = data.company_currency
	doc_currency = data.doc_currency
	rows = data.rows
	totals = data.totals

	html = """
	<table class="table table-bordered" style="width:100%">
		<thead>
			<tr style="background-color:#f3f4f6;">
				<th style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
			</tr>
		</thead>
		<tbody>
	""".format(
		_("Item"),
		_("SO Qty"),
		_("Inv.Qty"),
		_("DN Qty"),
		_("Cost"),
		_("Rate"),
		_("Total"),
		_("Profit %"),
	)
	for row in rows:
		profit_color = "#dc3545" if row["profit_pct"] < 0 else "#28a745" if row["profit_pct"] > 0 else "inherit"
		html += """
		<tr>
			<td>{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right" style="color:{}">{}</td>
		</tr>
		""".format(
			frappe.utils.escape_html(row["item"]),
			frappe.format(row["so_qty"], {"fieldtype": "Float"}),
			frappe.format(row["inv_qty"], {"fieldtype": "Float"}),
			frappe.format(row["dn_qty"], {"fieldtype": "Float"}),
			fmt_money(row["cost"], currency=company_currency),
			fmt_money(row["rate"], currency=doc_currency),
			fmt_money(row["total"], currency=company_currency),
			profit_color,
			frappe.format(row["profit_pct"], {"fieldtype": "Float"}) + " %",
		)

	overall_color = "#dc3545" if totals.profit_pct < 0 else "#28a745" if totals.profit_pct > 0 else "inherit"
	html += """
		<tr style="background-color:#f3f4f6; font-weight: bold;">
			<td>{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right" style="color:{}">{}</td>
		</tr>
	""".format(
		_("<b>Total</b>"),
		frappe.format(totals.so_qty, {"fieldtype": "Float"}),
		frappe.format(totals.inv_qty, {"fieldtype": "Float"}),
		frappe.format(totals.dn_qty, {"fieldtype": "Float"}),
		fmt_money(totals.cost, currency=company_currency),
		fmt_money(totals.rate, currency=doc_currency),
		fmt_money(totals.profit, currency=company_currency),
		overall_color,
		frappe.format(totals.profit_pct, {"fieldtype": "Float"}) + " %",
	)
	html += "</tbody></table>"
	return html


@frappe.whitelist()
def download_profitability_excel(sales_invoice):
	from frappe.utils.xlsxutils import build_xlsx_response

	data = _get_profitability_data(sales_invoice)
	xlsx_rows = [
		[
			"Item",
			"SO Qty",
			"Inv.Qty",
			"DN Qty",
			"Cost",
			"Rate",
			"Total",
			"Profit %",
		]
	]
	for row in data.rows:
		xlsx_rows.append(
			[
				row["item"],
				row["so_qty"],
				row["inv_qty"],
				row["dn_qty"],
				row["cost"],
				row["rate"],
				row["total"],
				row["profit_pct"],
			]
		)
	xlsx_rows.append(
		[
			"Total",
			data.totals.so_qty,
			data.totals.inv_qty,
			data.totals.dn_qty,
			data.totals.cost,
			data.totals.rate,
			data.totals.profit,
			data.totals.profit_pct,
		]
	)
	build_xlsx_response(xlsx_rows, f"Profitability_{sales_invoice}")



#completed
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


def get_employee_advance_je_amount(account, doc):
	account_currency = frappe.db.get_value("Account", account, "account_currency")
	if account_currency != doc.currency:
		amount = flt(doc.paid_amount) * flt(doc.exchange_rate)
		exchange_rate = 1
	else:
		amount = doc.paid_amount
		exchange_rate = doc.exchange_rate
	return amount, exchange_rate, account_currency




#completed
@frappe.whitelist()
def download_so_qty_dashboard(sales_order):
	result = get_so_qty_dashboard(sales_order)
	if not result or not result.get("items"):
		frappe.throw("No data found for the selected Sales Order")

	from io import BytesIO
	from openpyxl import Workbook
	from openpyxl.styles import Font

	headers = [
		"Item",
		"Total Outgoing PO Qty",
		"Received Qty",
		"Balance to Receive",
		"SO Qty",
		"Delivered Qty",
		"Balance to Deliver",
		"Physical Stock",
		"Free Stock",
	]

	wb = Workbook()
	ws = wb.active
	ws.title = "SO Qty Dashboard"
	if "Sheet" in wb.sheetnames:
		wb.remove(wb["Sheet"])

	ws.append(headers)
	for cell in ws[1]:
		cell.font = Font(bold=True)

	for d in result["items"]:
		ws.append([
			d["item_code"],
			d["po_qty"],
			d["received_qty"],
			d["balance_receive"],
			d["so_qty"],
			d["delivered_qty"],
			d["balance_delivery"],
			d["stock_qty"],
			d["free_stock"],
		])

	xlsx_file = BytesIO()
	wb.save(xlsx_file)

	frappe.response["filename"] = f"{sales_order}_qty_dashboard.xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"


#completed
@frappe.whitelist()
def download_po_so_qty_dashboard(purchase_order):
	result = get_po_so_qty_dashboard(purchase_order)
	if not result or not result.get("items"):
		frappe.throw("No data found for the selected Purchase Order")

	from io import BytesIO
	from openpyxl import Workbook
	from openpyxl.styles import Font

	headers = [
		"Item",
		"Sales Order Qty",
		"Delivered Qty",
		"Balance SO Qty",
	]

	wb = Workbook()
	ws = wb.active
	ws.title = "PO SO Qty Dashboard"
	if "Sheet" in wb.sheetnames:
		wb.remove(wb["Sheet"])

	ws.append(headers)
	for cell in ws[1]:
		cell.font = Font(bold=True)

	for d in result["items"]:
		ws.append([
			d["item_code"],
			d["so_qty"],
			d["delivered_qty"],
			d["balance_so_qty"],
		])

	xlsx_file = BytesIO()
	wb.save(xlsx_file)

	frappe.response["filename"] = f"{purchase_order}_po_so_qty_dashboard.xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"



@frappe.whitelist()
def auto_submit_depreciation_entry(doc, method=None):
	if doc.voucher_type != "Depreciation Entry":
		return
	if not doc.meta.get_workflow():
		return
	if doc.get("workflow_state") != "Draft":
		return

	from frappe.model.workflow import apply_workflow

	original_user = frappe.session.user

	try:
		frappe.set_user("Administrator")

		je = frappe.get_doc("Journal Entry", doc.name)

		apply_workflow(je.as_dict(), "Send to CFO")


		je.reload()
		apply_workflow(je.as_dict(), "Approve")

	finally:
		frappe.set_user(original_user)


def auto_set_is_stock_item(doc, method=None):
	"""Auto-set is_stock_item based on Item Group's custom_is_stock_group flag.

	Runs on before_insert and validate. Ensures items in non-stock groups
	(e.g. Non Stock Items, Fixed Assets) don't have Maintain Stock enabled,
	and items in stock groups do.
	"""
	if not doc.item_group:
		return

	if doc.is_fixed_asset or doc.custom_item_type == "Bundle":
		doc.is_stock_item = 0
		return

	is_stock_group = frappe.db.get_value("Item Group", doc.item_group, "custom_is_stock_group")
	if is_stock_group is not None:
		doc.is_stock_item = 1 if cint(is_stock_group) else 0


@frappe.whitelist()
def disable_user_employee_status_change(doc, method):
	if not doc.user_id:
		return

	user = frappe.db.get_value("User", doc.user_id, "enabled")

	if doc.status in ["Left", "Inactive"]:
		if user == 1:
			frappe.db.set_value("User", doc.user_id, "enabled", 0)
			frappe.msgprint(f"User {doc.user_id} disabled automatically since Employee status is {doc.status}.")




import frappe

#completed
def has_connected_document(po_name):
	"""
	Check whether the Purchase Order is connected
	to a Purchase Receipt or Purchase Invoice.
	"""

	purchase_receipt = frappe.db.exists(
		"Purchase Receipt Item",
		{
			"purchase_order": po_name,
			"docstatus": ["!=", 2]
		}
	)

	if purchase_receipt:
		return True

	purchase_invoice = frappe.db.exists(
		"Purchase Invoice Item",
		{
			"purchase_order": po_name,
			"docstatus": ["!=", 2]
		}
	)

	if purchase_invoice:
		return True

	return False


@frappe.whitelist()
def check_purchase_order_connection(po_name):
	return has_connected_document(po_name)


def validate_purchase_order_cancellation(doc, method=None):
	"""
	Prevent Sales Managers from cancelling a Purchase Order
	when it is already connected to another document.
	"""

	# System Manager can cancel
	if "System Manager" in frappe.get_roles(frappe.session.user):
		return

	# Check only Sales Manager
	if "Sales Manager" not in frappe.get_roles(frappe.session.user):
		return

	# Check connected documents
	if has_connected_document(doc.name):
		frappe.throw(
			"This Purchase Order is already connected to another document. "
			"Sales Manager cannot cancel it directly. "
			"Please mention @Accounts and request cancellation with remarks."
		)