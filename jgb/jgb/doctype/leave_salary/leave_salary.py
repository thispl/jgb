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


