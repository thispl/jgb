# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ResignationForm(Document):
	def on_submit(self):
		if self.workflow_state=='Approved':
			frappe.db.set_value('Employee',self.employee,'status','Left')
			frappe.db.set_value('Employee',self.employee,'relieving_date',self.approved_relieving_date)
