# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ResignationForm(Document):
    def on_submit(self):
        if self.workflow_state=='Approved':
            frappe.db.set_value('Employee',self.employee,'status','Left')
            frappe.db.set_value('Employee',self.employee,'relieving_date',self.approved_relieving_date)
            frappe.db.set_value("Employee",self.employee,"resignation_letter_date",self.posting_date)

    def on_cancel(self):
        if self.workflow_state=='Cancelled':
            frappe.db.set_value('Employee',self.employee,'status','Active')
            frappe.db.set_value('Employee',self.employee,'relieving_date',None)
            frappe.db.set_value("Employee",self.employee,"resignation_letter_date",None)
            self.cancel_no_due()

    def validate(self):
        if self.workflow_state == "Pending for HOD":
            self.validate_no_due_approved()

    def validate_no_due_approved(self):
        no_due = frappe.db.get_value( "No due", {"employee": self.employee, "workflow_state": "Approved" }, "name" )
        if not no_due:
            frappe.throw(
                "No Due is not Approved. Please get No Due approved before submitting resignation."
            )

    def cancel_no_due(self):
        no_due_list = frappe.get_all("No due",filters={ "employee": self.employee,"docstatus": 1},pluck="name")
        for no_due in no_due_list:
            nd_doc = frappe.get_doc("No due", no_due)
            nd_doc.workflow_state = "Cancelled"
            nd_doc.cancel()
