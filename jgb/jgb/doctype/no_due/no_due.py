# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Nodue(Document):

    def validate(self):
        self.validate_resignation_exists()

    def validate_resignation_exists(self):
        resignation = frappe.db.exists("Resignation Form",{"employee": self.employee})
        if not resignation:
            frappe.throw(
                "You cannot apply No Due without applying Resignation first."
            )

    def on_submit(self):
        self.update_resignation_status()

    def update_resignation_status(self):
        resignation_name = frappe.db.get_value(
            "Resignation Form", {"employee": self.employee, "workflow_state": "Draft"}, "name")
        if not resignation_name:
            return
        res_doc = frappe.get_doc("Resignation Form", resignation_name)

        # if res_doc.relieving_date != self.last_working_date:
        #     frappe.throw(
        #         f"""
        #         Relieving Date mismatch <br><br>
        #         <b>Resignation:</b> {res_doc.relieving_date}<br>
        #         <b>No Due:</b> {self.last_working_date}
        #         """
        #     )

        res_doc.workflow_state = "Pending for HOD"
        res_doc.save(ignore_permissions=True)
