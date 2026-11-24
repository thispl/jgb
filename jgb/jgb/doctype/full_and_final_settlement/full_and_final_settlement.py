# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt
from dateutil.relativedelta import relativedelta
from frappe.utils import get_first_day, get_last_day, format_datetime, get_url_to_form
from frappe import _
from frappe.utils import getdate, add_years


class FullandFinalSettlement(Document):
    def before_insert(self):
        doj=frappe.db.get_value('Employee',{'name':self.employee},['date_of_joining'])
        basic=frappe.db.get_value('Employee',{'name':self.employee},['custom_basic'])
        hra=frappe.db.get_value('Employee',{'name':self.employee},['custom_hra'])
        anniversary = getdate(add_years(doj, 1))
        fifth_anniversary = getdate(add_years(doj, 5))
        gratuity = 0
        if self.last_day_of_work and fifth_anniversary < getdate(self.last_day_of_work):
            if basic+hra==0:
                gratuity=0
            else:
                gratuity = ((float(basic)) + float(hra)) / 12
        elif self.last_day_of_work and anniversary < getdate(self.last_day_of_work):
            if basic+hra==0:
                gratuity=0
            else:
                gratuity = ((0.5 * float(basic)) + float(hra)) / 12
        else:
            gratuity=0
        self.eligible_gratuity = gratuity
        self.gratuity_amount = gratuity
        
    def validate(self):
        employee=self.employee
        total = frappe.db.sql("""
            SELECT COUNT(*) as count 
            FROM `tabAttendance` 
            WHERE attendance_date BETWEEN %s AND %s 
            AND status = 'Present'  
            AND employee = %s
            AND docstatus != 2
        """, (self.date_of_joining, self.last_day_of_work, employee), as_dict=True)[0]
        self.noof_days_worked=total
        abs = frappe.db.sql("""
            SELECT COUNT(*) as count 
            FROM `tabAttendance` 
            WHERE attendance_date BETWEEN %s AND %s 
            AND status = 'Absent'  
            AND employee = %s
            AND docstatus != 2
        """, (self.date_of_joining, self.last_day_of_work, employee), as_dict=True)[0]
        self.absent_days=abs
        ot = frappe.db.sql("""
            SELECT SUM(custom_ot_hours) as count 
            FROM `tabAttendance` 
            WHERE attendance_date BETWEEN %s AND %s   
            AND employee = %s
            AND docstatus != 2
        """, (self.date_of_joining, self.last_day_of_work, employee), as_dict=True)[0]
        self.total_ot=ot
        if self.date_of_joining and self.last_day_of_work:
            doj = getdate(self.date_of_joining)
            last_day = getdate(self.last_day_of_work)

            diff = relativedelta(last_day, doj)
            # diff = relativedelta(self.last_day_of_work, self.date_of_joining)
            years = diff.years
            months = diff.months
            days = diff.days

            self.employment_duration = f"{years} Years, {months} Months, {days} Days"

            # EOSB Calculation (Saudi Labor Law Article 84 & 85)
            base_wage = flt(self.basic_salary) + flt(self.hra)
            if base_wage > 0 and years > 0:
                # Article 84: per-year rate — half month wage if service < 5 years,
                # full month wage if service >= 5 years, then multiply by total years
                if years < 5:
                    base_benefit = (0.5 * base_wage) * years
                else:
                    base_benefit = (1.0 * base_wage) * years

                # Article 85: reduction factor based on relieving type
                if self.type in ("Termination", "Retirement"):
                    factor = 1.0
                elif self.type == "Resignation":
                    if years < 2:
                        factor = 0.0
                    elif years < 5:
                        factor = 1.0 / 3.0
                    elif years < 10:
                        factor = 2.0 / 3.0
                    else:
                        factor = 1.0
                else:
                    factor = 0.0

                self.eos_benefit = base_benefit * factor
            else:
                self.eos_benefit = 0
        first_day=get_first_day(self.last_day_of_work)
        last_day=get_last_day(self.last_day_of_work)
        if frappe.db.exists("Additional Salary",{'docstatus':1, "employee":self.employee,"payroll_date":('between',(first_day,last_day)),"salary_component":'Loan / Advance'}):
            self.loan_other_deduction=frappe.db.get_value("Additional Salary",{'docstatus':1, "employee":self.employee,"payroll_date":('between',(first_day,last_day)),"salary_component":'Loan / Advance'})
        earnings=flt(self.leave_balance_amount)+flt(self.gratuity_amount)+flt(self.additions)
        deductions=flt(self.loan_other_deduction)+flt(self.leave_pay_gratuity_total)
        self.net_pay=earnings-deductions
@frappe.whitelist()
def get_working_days(employee,last,doj):
    doj_date = getdate(doj)
    last_date = getdate(last)
    total_days = (last_date - doj_date).days + 1  
    period_in_months = total_days / 30.44  
    period_in_years = total_days / 365.25 
    period = round(period_in_years, 2)  
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


@frappe.whitelist()
def create_journal(name):
    la = frappe.get_doc('Full and Final Settlement', name)
    if la.workflow_state == 'Approved':
        existing_jv = frappe.db.get_value('Journal Entry', {'docstatus': ['!=', 2], 'custom_full_and_final_settlement': la.name}, 'name')
        if existing_jv:
            return existing_jv
        jv = frappe.new_doc('Journal Entry')
        jv.voucher_type = 'Bank Entry'
        jv.company = la.company
        jv.is_system_generated=1
        jv.posting_date = frappe.utils.today()
        jv.custom_division = frappe.db.get_value('Employee', la.employee, 'custom_division') or 'Common'
        jv.user_remark = f"Full and Final Settlememt payment - {la.name}"
        jv.custom_full_and_final_settlement = la.name
        jv.cheque_date=jv.posting_date
        payable = frappe.db.get_value('Account', {'company': la.company, 'account_number': '2239'}, 'name')
        provision = frappe.db.get_value('Account', {'company': la.company, 'account_number': '2235'}, 'name')
        bank = frappe.db.get_value('Account', {'company': la.company, 'account_number': '1051'}, 'name')
        amount = la.net_pay
        jv.append('accounts', {
            'account': payable,
            'party_type': 'Employee',
            'party': la.employee,
            'debit_in_account_currency': amount
        })
        jv.append('accounts', {
            'account': provision,
            'debit_in_account_currency': amount
        })
        jv.append('accounts', {
            'account': payable,
            'party_type': 'Employee',
            'party': la.employee,
            'credit_in_account_currency': amount
        })
        jv.append('accounts', {
            'account': bank,
            'credit_in_account_currency': amount
        })

        jv.insert() 
        return jv.name
