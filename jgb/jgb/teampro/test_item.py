import re

import frappe
from frappe.tests.utils import FrappeTestCase


class TestItemNaming(FrappeTestCase):
	"""update_item_code_creation must enforce GROUP-PRODUCT-NNNNNN on insert."""

	def test_pattern_enforced(self):
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": "TEST-TYPED-CODE",
			"item_group": "Valves and Pipeline (VLP)",
			"custom_product": "Hangers and Supports (HNS)",
			"custom_item_type": "Stock",
		}).insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Item", item.name, force=1)
		self.assertRegex(item.name, r"^VLP-HNS-\d{6}$")
		self.assertEqual(item.item_code, item.name)
		self.assertEqual(item.custom_item, item.name)

	def test_blocked_without_product(self):
		with self.assertRaises(frappe.exceptions.ValidationError):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": "TEST-TYPED-CODE",
				"custom_item_type": "Stock",
			}).insert(ignore_permissions=True)


def run_check():
	"""bench --site <site> execute jgb.jgb.teampro.test_item.run_check"""
	item = frappe.get_doc({
		"doctype": "Item",
		"item_code": "TEST-TYPED-CODE",
		"item_group": "Valves and Pipeline (VLP)",
		"custom_product": "Hangers and Supports (HNS)",
		"custom_item_type": "Stock",
	}).insert(ignore_permissions=True)
	assert re.match(r"^VLP-HNS-\d{6}$", item.name), item.name
	assert item.item_code == item.custom_item == item.name
	frappe.delete_doc("Item", item.name, force=1)

	try:
		frappe.get_doc({
			"doctype": "Item",
			"item_code": "TEST-TYPED-CODE-2",
			"custom_item_type": "Stock",
		}).insert(ignore_permissions=True)
	except frappe.exceptions.ValidationError:
		pass
	else:
		raise AssertionError("insert without item_group/custom_product should throw")

	asset = frappe.get_doc({
		"doctype": "Item",
		"item_code": "TEST-ASSET-001",
		"item_group": "Fixed Assets Register (FAR)",
		"is_fixed_asset": 1,
		"asset_category": "Other Assets",
		"custom_item_type": "Asset",
	}).insert(ignore_permissions=True)
	assert asset.name == "TEST-ASSET-001"
	frappe.delete_doc("Item", asset.name, force=1)

	return "ok"
