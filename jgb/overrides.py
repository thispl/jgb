import datetime
from frappe.utils import nowdate
import frappe
from datetime import timedelta
import frappe
from frappe.desk.doctype.event.event import Event
from frappe.utils import add_days, cint, cstr, flt, getdate, rounded, date_diff, money_in_words, formatdate, get_first_day,today
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from frappe.utils import nowdate, getdate, add_years, formatdate
from frappe.utils import (
    add_days,
    ceil,
    cint,
    cstr,
    date_diff,
    floor,
    flt,
    formatdate,
    get_first_day,
    get_last_day,
    get_link_to_form,
    getdate,
    money_in_words,
    rounded,
)
class CustomSalarySlip(SalarySlip):
    def get_date_details(self):
        doj=frappe.db.get_value('Employee',{'name':self.employee},['date_of_joining'])
        basic=frappe.db.get_value('Employee',{'name':self.employee},['custom_basic'])
        hra=frappe.db.get_value('Employee',{'name':self.employee},['custom_hra'])
        anniversary = getdate(add_years(doj, 1))
        fifth_anniversary = getdate(add_years(doj, 5))
        gratuity = 0
        if self.end_date and fifth_anniversary < getdate(self.end_date):
            if basic+hra==0:
                gratuity=0
            else:
                gratuity = ((flt(basic)) + flt(hra)) / 12
        elif self.end_date and anniversary < getdate(self.end_date):
            if basic+hra==0:
                gratuity=0
            else:
                gratuity = ((0.5 * flt(basic)) + flt(hra)) / 12
        else:
            gratuity=0
        self.custom_gratuity = gratuity