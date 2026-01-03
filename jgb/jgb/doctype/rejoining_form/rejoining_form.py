# Copyright (c) 2025, contact@half-ware.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import (
    add_days,
    today,
    date_diff,
    formatdate,
    get_fullname,
    get_link_to_form,
    getdate,
    nowdate,
)

class RejoiningForm(Document):
    def validate(self):
        existing_forms = frappe.db.sql(
            """
            SELECT
                name,start_date, end_date, total_leave_in_days
            FROM `tabRejoining Form`
            WHERE employee = %(employee)s
            AND docstatus < 2
            AND status IN ('Requested', 'Approved')
            AND end_date >= %(start_date)s AND start_date <= %(end_date)s
            AND name != %(name)s
            """,
            {
                "employee": self.employee,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "name": self.name,
            },
            as_dict=True,
        )

        for d in existing_forms:
            form_link = get_link_to_form("Rejoining Form", d["name"])
            msg = _(
                "Employee {0} has already created a Rejoining Form between {1} and {2}: {3}"
            ).format(
                self.employee,
                formatdate(d["start_date"]),
                formatdate(d["end_date"]),
                form_link
            )
            frappe.throw(msg)

        if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("End date cannot be before start date"))
    

@frappe.whitelist()
def send_reminder_for_rejoining(employee,company,user_id):
    subject = "Reminder: Submission of Joining Report After Annual Vacation"

    message = f"""Dear {employee},

    We hope you had a restful annual vacation.

    As per company policy, all employees are required to submit the Joining Report to the Admin/HR Department upon resuming duty after vacation.

    Our records show that you have not submitted your Joining Report as of today, which may indicate a delay in your return to work.

    Kindly submit your Joining Report immediately. Failure to do so may result in necessary action as per Company Policy and Labour Regulations.

    If you have already returned but are facing issues submitting the form, please contact the HR team.

    Regards,  
    HR Department  
    {company}
    """

    frappe.sendmail(
        recipients=[user_id],
        subject=subject,
        message=message
    )
    return True


@frappe.whitelist()
def send_reminder_for_rejoining_employee_wise():
    current_date = getdate(today())
    rejoining_forms = frappe.db.get_all(
        "Leave Application",
        filters={
            "docstatus": 1,
            "status": "Approved",
            "leave_type": "Annual Leave",
        },
        fields=["name", "from_date", "to_date","employee","company"]
    )

    for form in rejoining_forms:
        if add_days(form.to_date, 15) < current_date:
            if frappe.db.exists('Rejoining Form', {
                'leave_application': form.name,
                'docstatus': ['!=', 2]
            }):
                user_id =frappe.db.get_value('Employee', { 'name': form.employee }, ['user_id'])
                if user_id:
                    send_reminder_for_rejoining(form.employee, form.company, user_id)
                    


