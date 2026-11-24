import frappe
from frappe.utils import flt
from frappe import _
from frappe.utils import nowdate, getdate, add_years, formatdate
from frappe.utils.data import date_diff, now_datetime, nowdate, today, add_days
from datetime import date, timedelta
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



@frappe.whitelist()
def delete_additional_salary(doc,method):
	if frappe.db.exists("Additional Salary",{"custom_payroll_entry":doc.name}):
		docs=frappe.db.get_all("Additional Salary",{"custom_payroll_entry":doc.name},['name'])
		for d in docs:
			ld=frappe.get_doc("Additional Salary",d.name)
			if ld.docstatus==1:
				ld.cancel()
			ld.delete()




@frappe.whitelist()
def update_party(doc,method):
	if doc.custom_leave_salary:
		if frappe.db.exists('Leave Salary',{'name':doc.custom_leave_salary,'docstatus':['!=',2]}):
			employee=frappe.db.get_value('Leave Salary',doc.custom_leave_salary,'employee')
			doc.party=employee
