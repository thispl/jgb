# Copyright (c) 2026, JGB and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification import (
	JGB_COMPANY,
)


class TestDivisionInventoryReclassification(FrappeTestCase):
	def test_rejects_wrong_company(self):
		"""Only Joint Global Business Co LLC is allowed; other companies must be rejected."""
		if not frappe.db.exists("Company", JGB_COMPANY):
			self.skipTest(f"{JGB_COMPANY} not present in this site")

		other_company = frappe.db.get_value("Company", {"name": ["!=", JGB_COMPANY]}, "name")
		if not other_company:
			self.skipTest("No second company available to test rejection")

		doc = frappe.new_doc("Division Inventory Reclassification")
		doc.company = other_company
		doc.posting_date = "2026-01-01"
		doc.append("division_reclass_items", {
			"division": "HVAC Division - (HVA)",
			"inventory_account": "1201 - Inventory - HVAC - JGB",
			"amount": 100,
		})
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_requires_at_least_one_row(self):
		if not frappe.db.exists("Company", JGB_COMPANY):
			self.skipTest(f"{JGB_COMPANY} not present in this site")

		doc = frappe.new_doc("Division Inventory Reclassification")
		doc.company = JGB_COMPANY
		doc.posting_date = "2026-01-01"
		with self.assertRaises(frappe.ValidationError):
			doc.insert()
