# Copyright (c) 2026, JGB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, cint, flt, getdate


class AssetPrepaymentSchedule(Document):
	def validate(self):
		if self.docstatus == 0:
			self.validate_asset()
			if not self.get("prepayment_schedule"):
				self.make_prepayment_schedule()

	def validate_asset(self):
		asset = frappe.db.get_value("Asset", self.asset, ["docstatus", "name"], as_dict=True)
		if not asset:
			frappe.throw(_("Asset {0} not found.").format(self.asset))
		if asset.docstatus == 2:
			frappe.throw(_("Asset {0} is cancelled.").format(self.asset))

	def make_prepayment_schedule(self):
		self.prepayment_schedule = []
		net_amount = flt(self.prepaid_amount) - flt(self.opening_amortized_prepayment)
		num = cint(self.total_number_of_prepayments)
		if net_amount <= 0 or num <= 0 or not self.prepayment_start_date:
			return

		per_row = flt(net_amount / num, 2)
		accumulated = flt(self.opening_amortized_prepayment)
		for i in range(num):
			# last row absorbs the rounding remainder
			amount = flt(net_amount - per_row * (num - 1), 2) if i == num - 1 else per_row
			accumulated = flt(accumulated + amount, 2)
			self.append(
				"prepayment_schedule",
				{
					"schedule_date": add_months(self.prepayment_start_date, i * cint(self.frequency_of_prepayment)),
					"prepayment_amount": amount,
					"accumulated_prepayment_amount": accumulated,
				},
			)

	def on_submit(self):
		self.db_set("status", "Active")

	def before_cancel(self):
		self.cancel_prepayment_entries()

	def cancel_prepayment_entries(self):
		for d in self.get("prepayment_schedule"):
			if d.journal_entry:
				je = frappe.get_doc("Journal Entry", d.journal_entry)
				if je.docstatus == 1:
					je.cancel()
				elif je.docstatus == 0:
					je.delete()

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		if self.asset and frappe.db.exists("Asset", self.asset):
			from jgb.jgb.asset_prepayment import update_asset_prepaid_amounts

			update_asset_prepaid_amounts(self.asset)


@frappe.whitelist()
def make_prepayment_entry(asset_prepayment_schedule_name, date=None):
	frappe.has_permission("Journal Entry", throw=True)

	doc = frappe.get_doc("Asset Prepayment Schedule", asset_prepayment_schedule_name)
	date = getdate(date)
	for row in doc.get("prepayment_schedule"):
		if getdate(row.schedule_date) == date:
			if row.journal_entry and frappe.db.get_value(
				"Journal Entry", row.journal_entry, "docstatus"
			) != 2:
				frappe.throw(_("Journal Entry {0} already exists for this row.").format(row.journal_entry))
			row.db_set("journal_entry", None)
			from jgb.jgb.asset_prepayment import _make_prepayment_journal_entry

			_make_prepayment_journal_entry(doc, row)
			break

	return doc


def get_asset_prepayment_schedule_name(asset_name, status=None):
	filters = {"asset": asset_name, "docstatus": ["<", 2]}
	if status:
		filters["status"] = status
	return frappe.db.get_value("Asset Prepayment Schedule", filters, "name")
