# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class FullandFinalSettlement(Document):
    pass

@frappe.whitelist()
def get_working_days(employee,last,doj):
    doj_date = getdate(doj)
    last_date = getdate(last)
    total_days = (last_date - doj_date).days + 1  
    period_in_months = total_days / 30.44  
    period_in_years = total_days / 365.25 
    period = round(period_in_years, 2)  
    # if period <= 5:
    total = frappe.db.sql("""
        SELECT COUNT(*) as count 
        FROM `tabAttendance` 
        WHERE attendance_date BETWEEN %s AND %s 
          AND status = 'Present'  
          AND employee = %s
          AND docstatus != 2
    """, (doj, last, employee), as_dict=True)[0]

    return {
        "working_days": total["count"],
        "employment_period_years": period
    }

@frappe.whitelist()
def get_pre_abs(employee,start,end):
    start_date = getdate(start)
    last_date = getdate(end)
    
    present = frappe.db.sql("""
        SELECT COUNT(*) as count 
        FROM `tabAttendance` 
        WHERE attendance_date BETWEEN %s AND %s 
          AND status = 'Present'  
          AND employee = %s
          AND docstatus != 2
    """, (start, end, employee), as_dict=True)[0]
    absent = frappe.db.sql("""
        SELECT COUNT(*) as count 
        FROM `tabAttendance` 
        WHERE attendance_date BETWEEN %s AND %s 
          AND status = 'Absent'  
          AND employee = %s
          AND docstatus != 2
    """, (start, end, employee), as_dict=True)[0]
    absent = frappe.db.sql("""
        SELECT COUNT(*) as count 
        FROM `tabAttendance` 
        WHERE attendance_date BETWEEN %s AND %s 
          AND status = 'Absent'  
          AND employee = %s
          AND docstatus != 2
    """, (start, end, employee), as_dict=True)[0]
    ot_hrs = frappe.db.sql("""
        SELECT SUM(custom_ot_hours) as count 
        FROM `tabAttendance` 
        WHERE attendance_date BETWEEN %s AND %s 
          AND status = 'Absent'  
          AND employee = %s
          AND docstatus != 2
    """, (start, end, employee), as_dict=True)[0]
    return {
        "pre": present["count"],
        "abs": absent["count"],
        "ot": ot_hrs["count"],
    }


from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
@frappe.whitelist()
def get_annual_vacation_balance(employee, last_day_of_work):
    balance = get_leave_balance_on(employee,"Annual Vacation",last_day_of_work)

    return balance
