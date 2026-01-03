# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
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


class LeaveSalary(Document):
    def validate(self):
        existing_forms = frappe.db.sql(
            """
            SELECT
                name,from_date, to_date
            FROM `tabLeave Salary`
            WHERE employee = %(employee)s
            AND to_date >= %(from_date)s AND from_date <= %(to_date)s
            AND name != %(name)s
            """,
            {
                "employee": self.employee,
                "from_date": self.from_date,
                "to_date": self.to_date,
                "name": self.name,
            },
            as_dict=True,
        )

        for d in existing_forms:
            form_link = get_link_to_form("Leave Salary", d["name"])
            msg = _(
                "Employee {0} has already created a Leave Salary between {1} and {2}: {3}"
            ).format(
                self.employee,
                formatdate(d["from_date"]),
                formatdate(d["to_date"]),
                form_link
            )
            frappe.throw(msg)

        if self.from_date and self.to_date and getdate(self.to_date) < getdate(self.from_date):
            frappe.throw(_("To date cannot be before From date"))


@frappe.whitelist()
def create_payment_entry_ignore_mandatory(company,party,custom_leave_salary,net_pay):
    doc = frappe.new_doc("Payment Entry")
    net_pay=float(net_pay)
    doc.company = company
    doc.posting_date = today()
    doc.paid_amount = net_pay or 0
    doc.received_amount = net_pay or 0
    doc.payment_type= 'Pay'
    doc.party_type= 'Employee'
    doc.source_exchange_rate=1
    doc.target_exchange_rate=1
    doc.custom_currency='SAR'
    doc.party= party
    doc.naming_series='ACC-PAY-.YYYY.-'
    doc.custom_leave_salary=custom_leave_salary

    doc.flags.ignore_mandatory = True
    doc.flags.ignore_permissions = True

    doc.insert()
    return doc.name