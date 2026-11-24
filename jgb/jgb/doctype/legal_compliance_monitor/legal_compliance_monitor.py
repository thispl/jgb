# Copyright (c) 2026, JGB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, getdate, nowdate


class LegalComplianceMonitor(Document):
	def validate(self):
		self.calculate_dates_and_status()

	def calculate_dates_and_status(self):
		if self.renewability == "Permanent / Lifetime":
			self.status = "Permanent"
			self.days_left = None
			self.frequency_days = None
			return

		if self.renewability == "Non-Renewable":
			self.status = "Not Renewable"
			self.days_left = None
			self.frequency_days = None
			return

		if self.renewability == "Renewable" and self.expiry_date:
			diff = date_diff(self.expiry_date, nowdate())
			self.days_left = diff

			if self.last_renewal_date:
				self.frequency_days = date_diff(self.expiry_date, self.last_renewal_date)

			if diff < 0:
				self.status = "Expired"
			elif diff <= 30:
				self.status = "Expiring Soon"
			else:
				self.status = "Valid"
