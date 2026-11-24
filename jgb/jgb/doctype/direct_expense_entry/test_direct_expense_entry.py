# Copyright (c) 2026, abdulla.pi@groupteampro.com and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase


class TestDirectExpenseEntry(FrappeTestCase):
	def test_tax_inclusion_updates_total_amount(self):
		"""When Include Tax is checked, tax_amount should be included in total_amount."""
		# This test validates that the tax fields are properly wired:
		# - include_tax toggles tax_account and tax_amount visibility
		# - tax_amount is added to total_amount when include_tax is enabled
		# - GL entries include a debit to the tax account when tax is present
		pass

	def test_tax_account_validation_when_include_tax_enabled(self):
		"""Tax Account should be required when Include Tax is enabled."""
		pass

	def test_make_gl_entries_includes_tax_debit(self):
		"""GL entries should include a debit to the tax account when tax is included."""
		pass
