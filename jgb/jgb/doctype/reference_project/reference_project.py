# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReferenceProject(Document):
	# pass
	def validate(self):
		tot=0
		if self.table_gygr:
			for i in self.table_gygr:
				if i.projection:
					tot+=i.projection
		self.total_project_projection=tot
