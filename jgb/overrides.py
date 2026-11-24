import datetime
from frappe.utils import nowdate
import frappe
from datetime import timedelta
import frappe
from frappe.desk.doctype.event.event import Event
from frappe.utils import add_days, cint, cstr, flt, getdate, rounded, date_diff, money_in_words, formatdate, get_first_day,today
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from hrms.payroll.doctype.additional_salary.additional_salary import AdditionalSalary
from frappe.utils import nowdate, getdate, add_years, formatdate
from frappe.utils import (
	add_days,
	ceil,
	cint,
	cstr,
	date_diff,
	floor,
	flt,
	formatdate,
	get_first_day,
	get_last_day,
	get_link_to_form,
	getdate,
	money_in_words,
	rounded,
)
class CustomSalarySlip(SalarySlip):
	def validate(self):
		super().validate()
		# Create Leave Deduction AS BEFORE apply_annual_vacation so that
		# calculate_net_pay() pulls it into the deductions table.
		# (The validate doc_event hook runs AFTER this method returns,
		#  so the AS would be created too late to be included.)
		from jgb.jgb.teampro.salary_slip import create_pay_now_deduction
		create_pay_now_deduction(self, "validate")
		self.apply_annual_vacation()
 
	def on_cancel(self):
		super().on_cancel()
		self.cancel_linked_additional_salaries()
 
	def on_trash(self):
		# Capture additional salary names from rows BEFORE super().on_trash() clears them
		additional_salary_names = set()
		for row in list(self.earnings) + list(self.deductions):
			if row.additional_salary and row.salary_component in ["Vacation Pay", "Leave Deduction"]:
				additional_salary_names.add(row.additional_salary)
 
		super().on_trash()
 
		# Also search by employee + payroll_date + component (in case rows are already gone)
		additional_salary_names.update(self._find_additional_salaries())
 
		for name in additional_salary_names:
			self._cancel_additional_salary(name)
 
	def cancel_linked_additional_salaries(self):
		"""Cancel Additional Salary records for Vacation Pay and Leave Deduction
		that were created for this salary slip."""
		components_to_cancel = ["Vacation Pay", "Leave Deduction"]
 
		additional_salary_names = set()
		for row in list(self.earnings) + list(self.deductions):
			if row.additional_salary and row.salary_component in components_to_cancel:
				additional_salary_names.add(row.additional_salary)
 
		# Also search by employee + payroll_date + component
		additional_salary_names.update(self._find_additional_salaries())
 
		for name in additional_salary_names:
			self._cancel_additional_salary(name)
 
	def _find_additional_salaries(self):
		"""Find Additional Salaries by employee + payroll_date + salary_component.
		This catches Additional Salaries that are not linked in the salary slip rows
		(e.g., rows already deleted)."""
		names = set()
		ads = frappe.get_all(
			"Additional Salary",
			filters={
				"employee": self.employee,
				"salary_component": ["in", ["Vacation Pay", "Leave Deduction"]],
				"payroll_date": ["between", [self.start_date, self.end_date]],
				"docstatus": 1,
			},
			pluck="name",
		)
		names.update(ads)
		return names
 
	def _cancel_additional_salary(self, name):
		"""Cancel a single Additional Salary.
 
		Always clears custom_payroll_entry before cancelling to avoid
		'Cannot link cancelled document' error.
		"""
		if not frappe.db.exists("Additional Salary", {"name": name, "docstatus": 1}):
			return
 
		try:
			# Always clear custom_payroll_entry before cancelling
			pe_name = frappe.db.get_value("Additional Salary", name, "custom_payroll_entry")
			if pe_name:
				frappe.db.set_value(
					"Additional Salary", name, "custom_payroll_entry", None, update_modified=False
				)
 
			# Reload the doc after clearing the link, then cancel
			ad = frappe.get_doc("Additional Salary", name)
			ad.cancel()
		except Exception:
			frappe.log_error(
				f"Failed to cancel Additional Salary {name} for Salary Slip {self.name}"
			)
 
	def apply_annual_vacation(self):
		"""Deduct Annual Vacation days (Pay With Payroll / Pay Now) from
		payment_days and create an Additional Salary (Earning) for Vacation Pay.
		"""
		try:
			holidays = self.get_holidays_for_employee(self.start_date, self.end_date)
		except Exception:
			holidays = []
 
		vacation_days = self.get_annual_vacation_days_for_slip(holidays)
 
		if not vacation_days or not flt(vacation_days):
			return
 
		if not cint(self.total_working_days):
			return
 
		# Create Additional Salary for Vacation Pay (before recalculating,
		# so it gets pulled in during calculate_net_pay)
		self.create_vacation_pay_additional_salary()
 
		# Deduct vacation days from payment_days
		if flt(self.payment_days) > flt(vacation_days):
			self.payment_days = flt(self.payment_days) - flt(vacation_days)
		else:
			self.payment_days = 0
 
		# Recalculate all component amounts with the updated payment_days.
		# This also pulls in the Vacation Pay Additional Salary automatically.
		self.calculate_net_pay()
 
	def get_annual_vacation_days_for_slip(self, holidays=None):
		"""Returns the number of Annual Vacation days (Pay With Payroll / Pay Now)
		within the salary slip period.

		Annual Vacation's Leave Type has include_holiday = 1, so holidays
		(weekly-offs) that fall inside a leave are counted as leave days. Since
		payment_days / total_working_days are on a calendar-day basis
		(include_holidays_in_total_working_days = 1) - and the Vacation Pay /
		Leave Deduction amounts are prorated on calendar days too - the whole
		calendar overlap must be deducted here. Holiday dates are only skipped
		when the Leave Type says holidays are not leave days.
		"""
		leaves = frappe.get_all(
			"Leave Application",
			filters={
				"employee": self.employee,
				"leave_type": "Annual Vacation",
				"docstatus": 1,
				"status": "Approved",
				"custom_payment_type": ["in", ["Pay With Payroll", "Pay Now"]],
				"from_date": ["<=", self.end_date],
				"to_date": [">=", self.start_date],
			},
			fields=["name", "from_date", "to_date", "half_day", "half_day_date"],
		)
 
		if not leaves:
			return 0
 
		slip_start = getdate(self.start_date)
		slip_end = getdate(self.end_date)
		include_holiday = cint(
			frappe.db.get_value("Leave Type", "Annual Vacation", "include_holiday")
		)
		holiday_set = (
			set(getdate(h) for h in holidays) if holidays and not include_holiday else set()
		)
 
		vacation_dates = set()
		half_day_dates = set()
 
		for leave in leaves:
			leave_from = getdate(leave.from_date)
			leave_to = getdate(leave.to_date)
 
			overlap_start = max(leave_from, slip_start)
			overlap_end = min(leave_to, slip_end)
 
			if overlap_start > overlap_end:
				continue
 
			current = overlap_start
			while current <= overlap_end:
				if current in holiday_set:
					current = add_days(current, 1)
					continue
				vacation_dates.add(current)
				if cint(leave.half_day) and (
					getdate(leave.half_day_date) == current or leave_from == leave_to
				):
					half_day_dates.add(current)
				current = add_days(current, 1)
 
		vacation_days = 0
		for d in vacation_dates:
			if d in half_day_dates:
				vacation_days += 0.5
			else:
				vacation_days += 1
 
		return flt(vacation_days)
 
	def create_vacation_pay_additional_salary(self):
		"""Create an Additional Salary (Earning) for Vacation Pay using the
		existing calculate_leave_salary function from the leave application.

		Only the portion overlapping the salary slip period is used, so a
		leave spanning two months (e.g. Jul-Aug) only contributes its August
		portion to the August salary slip.
		"""
		from jgb.jgb.teampro.leave_application import calculate_vacation_pay_by_month

		slip_start = getdate(self.start_date)
		slip_end = getdate(self.end_date)
 
		leaves = frappe.get_all(
			"Leave Application",
			filters={
				"employee": self.employee,
				"leave_type": "Annual Vacation",
				"docstatus": 1,
				"status": "Approved",
				"custom_payment_type": "Pay With Payroll",
				"from_date": ["<=", self.end_date],
				"to_date": [">=", self.start_date],
			},
			fields=["name", "from_date", "to_date", "custom_pay_hra_only"],
		)
 
		if not leaves:
			return
 
		vacation_pay_amount = 0
		for leave in leaves:
			for row in calculate_vacation_pay_by_month(leave.name, cint(leave.custom_pay_hra_only or 0)):
				row_date = getdate(row["from_date"])
				# Only include months overlapping the salary slip period
				if slip_start <= row_date <= slip_end:
					vacation_pay_amount += flt(row["amount"])
 
		vacation_pay_amount = flt(round(vacation_pay_amount, 2))
 
		if vacation_pay_amount <= 0:
			return
 
		existing = frappe.get_all(
			"Additional Salary",
			filters={
				"employee": self.employee,
				"salary_component": "Vacation Pay",
				"payroll_date": self.start_date,
				"docstatus": 1,
			},
		)
 
		if existing:
			return
 
		additional_salary = frappe.get_doc({
			"doctype": "Additional Salary",
			"employee": self.employee,
			"salary_component": "Vacation Pay",
			"amount": vacation_pay_amount,
			"payroll_date": self.start_date,
			"type": "Earning",
			"overwrite_salary_structure_amount": 1,
			"company": self.company,
		})
 
		additional_salary.insert(ignore_permissions=True)
		additional_salary.submit()
	# def validate(self):
	#     super().validate()
	#     self.apply_annual_vacation()
 
	# def apply_annual_vacation(self):
	#     """Deduct Annual Vacation days (Pay With Payroll / Pay Now) from
	#     payment_days and create an Additional Salary (Earning) for Vacation Pay.
	#     """
	#     try:
	#         holidays = self.get_holidays_for_employee(self.start_date, self.end_date)
	#     except Exception:
	#         holidays = []
 
	#     vacation_days = self.get_annual_vacation_days_for_slip(holidays)
 
	#     if not vacation_days or not flt(vacation_days):
	#         return
 
	#     if not cint(self.total_working_days):
	#         return
 
	#     # Create Additional Salary for Vacation Pay (before recalculating,
	#     # so it gets pulled in during calculate_net_pay)
	#     self.create_vacation_pay_additional_salary()
 
	#     # Deduct vacation days from payment_days
	#     if flt(self.payment_days) > flt(vacation_days):
	#         self.payment_days = flt(self.payment_days) - flt(vacation_days)
	#     else:
	#         self.payment_days = 0
 
	#     # Recalculate all component amounts with the updated payment_days.
	#     # This also pulls in the Vacation Pay Additional Salary automatically.
	#     self.calculate_net_pay()
 
	# def get_annual_vacation_days_for_slip(self, holidays=None):
	#     """Returns the number of Annual Vacation days (Pay With Payroll / Pay Now)
	#     within the salary slip period, excluding holidays.
	#     """
	#     leaves = frappe.get_all(
	#         "Leave Application",
	#         filters={
	#             "employee": self.employee,
	#             "leave_type": "Annual Vacation",
	#             "docstatus": 1,
	#             "status": "Approved",
	#             "custom_payment_type": ["in", ["Pay With Payroll", "Pay Now"]],
	#             "from_date": ["<=", self.end_date],
	#             "to_date": [">=", self.start_date],
	#         },
	#         fields=["name", "from_date", "to_date", "half_day", "half_day_date"],
	#     )
 
	#     if not leaves:
	#         return 0
 
	#     slip_start = getdate(self.start_date)
	#     slip_end = getdate(self.end_date)
	#     holiday_set = set(getdate(h) for h in holidays) if holidays else set()
 
	#     vacation_dates = set()
	#     half_day_dates = set()
 
	#     for leave in leaves:
	#         leave_from = getdate(leave.from_date)
	#         leave_to = getdate(leave.to_date)
 
	#         overlap_start = max(leave_from, slip_start)
	#         overlap_end = min(leave_to, slip_end)
 
	#         if overlap_start > overlap_end:
	#             continue
 
	#         current = overlap_start
	#         while current <= overlap_end:
	#             if current in holiday_set:
	#                 current = add_days(current, 1)
	#                 continue
	#             vacation_dates.add(current)
	#             if cint(leave.half_day) and (
	#                 getdate(leave.half_day_date) == current or leave_from == leave_to
	#             ):
	#                 half_day_dates.add(current)
	#             current = add_days(current, 1)
 
	#     vacation_days = 0
	#     for d in vacation_dates:
	#         if d in half_day_dates:
	#             vacation_days += 0.5
	#         else:
	#             vacation_days += 1
 
	#     return flt(vacation_days)
 
	# def create_vacation_pay_additional_salary(self):
	#     """Create an Additional Salary (Earning) for Vacation Pay using the
	#     existing calculate_leave_salary function from the leave application.
	#     """
	#     from jgb.utils import calculate_leave_salary
 
	#     leaves = frappe.get_all(
	#         "Leave Application",
	#         filters={
	#             "employee": self.employee,
	#             "leave_type": "Annual Vacation",
	#             "docstatus": 1,
	#             "status": "Approved",
	#             "custom_payment_type": ["in", ["Pay With Payroll", "Pay Now"]],
	#             "from_date": ["<=", self.end_date],
	#             "to_date": [">=", self.start_date],
	#         },
	#         fields=["name", "from_date", "to_date", "custom_pay_hra_only"],
	#     )
 
	#     if not leaves:
	#         return
 
	#     vacation_pay_amount = 0
	#     for leave in leaves:
	#         result = calculate_leave_salary(leave.name, leave.custom_pay_hra_only or 0)
	#         vacation_pay_amount += flt(result.get("total", 0))
 
	#     vacation_pay_amount = flt(round(vacation_pay_amount, 2))
 
	#     if vacation_pay_amount <= 0:
	#         return
 
	#     existing = frappe.get_all(
	#         "Additional Salary",
	#         filters={
	#             "employee": self.employee,
	#             "salary_component": "Vacation Pay",
	#             "payroll_date": self.start_date,
	#             "docstatus": 1,
	#         },
	#     )
 
	#     if existing:
	#         return
 
	#     additional_salary = frappe.get_doc({
	#         "doctype": "Additional Salary",
	#         "employee": self.employee,
	#         "salary_component": "Vacation Pay",
	#         "amount": vacation_pay_amount,
	#         "payroll_date": self.start_date,
	#         "type": "Earning",
	#         "overwrite_salary_structure_amount": 1,
	#         "company": self.company,
	#     })
 
	#     additional_salary.insert(ignore_permissions=True)
	#     additional_salary.submit()
	# def get_working_days_details(self, lwp=None, for_preview=0):
	# 	super().get_working_days_details(lwp=lwp, for_preview=for_preview)

	# 	# Weekly-off (weekend) deduction: an employee must have >= 3 present
	# 	# days in the Sun-Thu week closing on a weekend to be paid for it.
	# 	# Applied only to Annual Vacation boundary weeks; see jgb.jgb.custom.get_woff_ded.
	# 	if for_preview or frappe.get_cached_value(
	# 		"Payroll Settings", None, "payroll_based_on"
	# 	) != "Attendance":
	# 		return

	# 	from jgb.jgb.custom import get_woff_ded

	# 	woff_deduction = flt(get_woff_ded(self.start_date, self.end_date, self.employee))
	# 	if woff_deduction:
	# 		self.leave_without_pay = flt(self.leave_without_pay) + woff_deduction
	# 		self.payment_days = max(0, flt(self.payment_days) - woff_deduction)

	def get_date_details(self):
		doj=frappe.db.get_value('Employee',{'name':self.employee},['date_of_joining'])
		basic=frappe.db.get_value('Employee',{'name':self.employee},['custom_basic'])
		hra=frappe.db.get_value('Employee',{'name':self.employee},['custom_hra'])
		anniversary = getdate(add_years(doj, 1))
		fifth_anniversary = getdate(add_years(doj, 5))
		gratuity = 0
		if self.end_date and fifth_anniversary < getdate(self.end_date):
			if basic+hra==0:
				gratuity=0
			else:
				gratuity = ((flt(basic)) + flt(hra)) / 12
		elif self.end_date and anniversary < getdate(self.end_date):
			if basic+hra==0:
				gratuity=0
			else:
				gratuity = ((0.5 * flt(basic)) + flt(hra)) / 12
		else:
			gratuity=0
		self.custom_gratuity = gratuity


# ---------------------------------------------------------------------------
# Divisional SRNB (Stock Received But Not Billed) overrides
#
# ERPNext hardcodes the Company-level "stock_received_but_not_billed" account
# for the SRNB GL entry on Purchase Receipt and for the reversal on Purchase
# Invoice.  These overrides replace that account with the divisional SRNB
# account (2501-2505) from "Division Account Details" based on the document's
# custom_division field.
# ---------------------------------------------------------------------------

from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice


def _get_divisional_srnb_account(division, company):
	"""Return the divisional SRNB account from Division Account Details, or None."""
	if not division or not company:
		return None
	return frappe.db.get_value(
		"Division Account Details",
		{"parent": division, "company": company},
		"snrb_account",
	)


# Division mapping for Stock Entry items
_SE_IG_TO_DIV = {
	"HVAC Division - (HVA)": "HVAC Division - (HVA)",
	"Filtration Division (FRD)": "Filtration Division (FRD)",
	"Valves and Pipeline (VLP)": "Valves and Pipeline (VLP)",
	"Waterworks Division (WTR)": "Waterworks Division (WTR)",
	"Misting (MST)": "Misting (MST)",
	"Fire Alarm & Security (FAR)": "Fire Alarm & Security (FAR)",
}

_SE_DIV_TO_CC = {
	"HVAC Division - (HVA)": "HVAC Division - JGB",
	"Valves and Pipeline (VLP)": "Valves & Pipeline Division - JGB",
	"Waterworks Division (WTR)": "Waterworks Division - JGB",
	"Filtration Division (FRD)": "Filtration Division - JGB",
	"Misting (MST)": "Misting - JGB",
	"Common": "Main - JGB",
}


def set_stock_entry_divisional_accounts(doc, method=None):
	"""Auto-set expense_account and cost_center on Stock Entry items based on item group.

	- All purposes: post value difference to the company Stock Adjustment Account
	- Cost center follows the item's division
	"""
	if doc.company != "Joint Global Business Co LLC":
		return

	stock_adjustment_account = frappe.db.get_value(
		"Company", doc.company, "stock_adjustment_account"
	)

	# Determine division from item groups of all items
	igs = set()
	for item in doc.items:
		ig = frappe.db.get_value("Item", item.item_code, "item_group") or "Common"
		igs.add(ig)

	if len(igs) == 1:
		div = _SE_IG_TO_DIV.get(list(igs)[0], "Common")
	else:
		divs = set(_SE_IG_TO_DIV.get(ig, "Common") for ig in igs)
		div = divs.pop() if len(divs) == 1 else "Common"

	target_cc = _SE_DIV_TO_CC.get(div, "Main - JGB")

	# target_acct = stock_adjustment_account or "5954 - Stock Adjustment - JGB"
	target_acct = stock_adjustment_account

	for item in doc.items:
		if target_acct:
			item.expense_account = target_acct
		item.cost_center = target_cc



class CustomPurchaseReceipt(PurchaseReceipt):
	"""Override PR so the SRNB GL entry uses the divisional SRNB account."""

	def make_item_gl_entries(self, gl_entries, warehouse_account=None):
		# Temporarily patch get_company_default so that "stock_received_but_not_billed"
		# returns the divisional SRNB account instead of the Company-level default.
		divisional_srnb = _get_divisional_srnb_account(self.custom_division, self.company)
		if not divisional_srnb:
			# No division set — fall back to standard ERPNext behaviour
			return super().make_item_gl_entries(gl_entries, warehouse_account=warehouse_account)

		original_get_company_default = self.get_company_default

		def patched_get_company_default(fieldname, **kwargs):
			if fieldname == "stock_received_but_not_billed":
				return divisional_srnb
			return original_get_company_default(fieldname, **kwargs)

		self.get_company_default = patched_get_company_default
		try:
			return super().make_item_gl_entries(gl_entries, warehouse_account=warehouse_account)
		finally:
			self.get_company_default = original_get_company_default


class CustomPurchaseInvoice(PurchaseInvoice):
	"""Override PI so the SRNB reversal uses the divisional SRNB account."""

	def set_expense_account(self, for_validate=False):
		# Temporarily patch get_company_default so that "stock_received_but_not_billed"
		# returns the divisional SRNB account instead of the Company-level default.
		divisional_srnb = _get_divisional_srnb_account(self.custom_division, self.company)

		if not divisional_srnb:
			return super().set_expense_account(for_validate=for_validate)

		original_get_company_default = self.get_company_default

		def patched_get_company_default(fieldname, **kwargs):
			if fieldname == "stock_received_but_not_billed":
				return divisional_srnb
			return original_get_company_default(fieldname, **kwargs)

		self.get_company_default = patched_get_company_default
		try:
			return super().set_expense_account(for_validate=for_validate)
		finally:
			self.get_company_default = original_get_company_default

	def get_gl_entries(self, warehouse_account=None):
		# Also patch get_gl_entries which reads stock_received_but_not_billed at line 836
		divisional_srnb = _get_divisional_srnb_account(self.custom_division, self.company)

		if not divisional_srnb:
			return super().get_gl_entries(warehouse_account=warehouse_account)

		original_get_company_default = self.get_company_default

		def patched_get_company_default(fieldname, **kwargs):
			if fieldname == "stock_received_but_not_billed":
				return divisional_srnb
			return original_get_company_default(fieldname, **kwargs)

		self.get_company_default = patched_get_company_default
		try:
			return super().get_gl_entries(warehouse_account=warehouse_account)
		finally:
			self.get_company_default = original_get_company_default




class CustomAdditionalSalary(AdditionalSalary):
	def on_submit(self):
		super().on_submit()
		self.add_to_draft_salary_slips()

	def on_cancel(self):
		super().on_cancel()
		self.revert_linked_expense_claims_and_salary_slip()

	def add_to_draft_salary_slips(self):
		"""Recalculate the draft Salary Slips whose period covers this Additional
		Salary so the newly submitted component is pulled in.

		Salary Slip components are only computed on save/validate, so an
		Additional Salary submitted after the slip was created (e.g. created via
		a Payroll Entry run) is otherwise never reflected in it. Submitted slips
		are intentionally left untouched - they have to be cancelled/amended
		manually because they may carry accrual Journal Entries.
		"""
		for slip_name in self._get_draft_salary_slips():
			try:
				slip = frappe.get_doc("Salary Slip", slip_name)
				slip.calculate_net_pay()
				slip.flags.ignore_validate = True
				slip.save(ignore_permissions=True)
			except Exception:
				frappe.log_error(
					f"Failed to recalculate draft Salary Slip {slip_name} for Additional Salary {self.name}"
				)

	def _get_draft_salary_slips(self):
		"""Draft Salary Slips for this employee whose period covers the
		Additional Salary (recurring or one-time)."""
		filters = {"employee": self.employee, "docstatus": 0}

		if self.is_recurring:
			# same rule as hrms get_additional_salaries: slip end date must fall
			# inside the additional salary's from_date..to_date
			filters["end_date"] = ["between", [self.from_date, self.to_date]]
		elif self.payroll_date:
			# one-time: payroll date must fall inside the slip period
			filters["start_date"] = ["<=", self.payroll_date]
			filters["end_date"] = [">=", self.payroll_date]
		else:
			return []

		return frappe.get_all("Salary Slip", filters=filters, pluck="name")

	def revert_linked_expense_claims_and_salary_slip(self):
		for row in self.get("custom_expense_split_up", []):
			claim_id = row.get("expense_id") or row.get("expense_claim_id")
			if not claim_id:
				continue

			expense_claim = frappe.get_doc("Expense Claim", claim_id)
			expense_claim.set_status(update=True)

		self.remove_from_draft_salary_slip()

	def remove_from_draft_salary_slip(self):
		if not self.employee or not self.payroll_date:
			return

		for slip_name in frappe.get_all(
			"Salary Slip",
			filters={
				"employee": self.employee,
				"start_date": ["<=", self.payroll_date],
				"end_date": [">=", self.payroll_date],
				"docstatus": 0,
			},
			pluck="name",
		):
			slip = frappe.get_doc("Salary Slip", slip_name)

			for component_type in ("earnings", "deductions"):
				for row in list(slip.get(component_type)):
					if row.additional_salary == self.name:
						slip.remove(row)
						break

			slip.calculate_net_pay()
			slip.flags.ignore_validate = True
			slip.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Landed Cost Voucher — pull net item amounts
#
# Core ERPNext pulls `base_amount` (gross) into LCV items, which ignores both
# item-wise discounts and document-level discounts (distributed per item into
# `distributed_discount_amount` / `base_net_amount`). Use base_net_amount so the
# landed cost apportionment reflects the real paid value.
# ---------------------------------------------------------------------------

import erpnext
from erpnext.stock.doctype.landed_cost_voucher.landed_cost_voucher import LandedCostVoucher
from frappe.query_builder.custom import ConstantColumn


def get_pr_items_net(purchase_receipt):
    item = frappe.qb.DocType("Item")
    pr_item = frappe.qb.DocType(purchase_receipt.receipt_document_type + " Item")
    return (
        frappe.qb.from_(pr_item)
        .inner_join(item)
        .on(item.name == pr_item.item_code)
        .select(
            pr_item.item_code,
            pr_item.description,
            pr_item.qty,
            pr_item.base_rate,
            pr_item.base_amount,
            pr_item.base_net_rate,
            pr_item.base_net_amount,
            pr_item.name,
            pr_item.cost_center,
            pr_item.is_fixed_asset,
            ConstantColumn(purchase_receipt.receipt_document_type).as_("receipt_document_type"),
            ConstantColumn(purchase_receipt.receipt_document).as_("receipt_document"),
        )
        .where(
            (pr_item.parent == purchase_receipt.receipt_document)
            & ((item.is_stock_item == 1) | (item.is_fixed_asset == 1))
        )
        .run(as_dict=True)
    )


class CustomLandedCostVoucher(LandedCostVoucher):
    @frappe.whitelist()
    def get_items_from_purchase_receipts(self):
        self.set("items", [])
        for pr in self.get("purchase_receipts"):
            if pr.receipt_document_type and pr.receipt_document:
                pr_items = get_pr_items_net(pr)

                for d in pr_items:
                    item = self.append("items")
                    item.item_code = d.item_code
                    item.description = d.description
                    item.qty = d.qty
                    item.rate = d.base_net_rate if d.base_net_amount else d.base_rate
                    item.cost_center = d.cost_center or erpnext.get_default_cost_center(self.company)
                    item.amount = d.base_net_amount or d.base_amount
                    item.receipt_document_type = pr.receipt_document_type
                    item.receipt_document = pr.receipt_document
                    item.purchase_receipt_item = d.name
                    item.is_fixed_asset = d.is_fixed_asset


from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation


class CustomLeaveAllocation(LeaveAllocation):
	"""Annual Vacation accrual fix.

	Upstream get_existing_leave_count() filters this allocation's ledger rows
	by `company`. But Leave Ledger Entry.company is `fetch_from
	employee.company` (mutable) while LeaveAllocation.company is fixed at
	creation; when an employee changes company the two diverge and the filter
	under-counts the already-posted leaves, so every accrual over-posts.
	`transaction_name` already scopes the lookup to this allocation, so the
	company filter is redundant and is dropped here.
	"""

	def get_existing_leave_count(self):
		ledger_entries = frappe.get_all(
			"Leave Ledger Entry",
			filters={
				"transaction_type": "Leave Allocation",
				"transaction_name": self.name,
				"employee": self.employee,
				"leave_type": self.leave_type,
				"is_carry_forward": 0,
				"docstatus": 1,
			},
			fields=["SUM(leaves) as total_leaves"],
		)

		return ledger_entries[0].total_leaves if ledger_entries else 0


from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder


def _set_total_advance_paid(self):
	"""Drop the "Total advance ... cannot be greater than the Grand Total" validation.

	Upstream compared a currency-rounded advance_paid against the raw grand_total,
	so an order paid 100% in advance (advance == grand_total) trips it by a few
	fils whenever grand_total carries sub-cent precision (34,458.017 rounds up to
	34,458.02 and the strict `>` throws). Upstream removed the check in v15.73.0
	(52b9f92553, backport of #48341) - drop this override once erpnext is
	upgraded past v15.72.0.

	An order with no Advance Payment Ledger Entry rows recalculates to 0: the
	aggregate query still returns one row (NULL amount), so `advance` is always
	truthy and advance_paid is written. Stale values left behind by deleted or
	re-pointed Payment Entries are cleared by `jgb.stale_so_advance.run`.
	"""

	advance = self.calculate_total_advance_from_ledger()

	if advance:
		advance = advance[0]
		advance_paid = flt(advance.amount, self.precision("advance_paid"))

		if advance.account_currency:
			frappe.db.set_value(self.doctype, self.name, "party_account_currency", advance.account_currency)

		self.db_set("advance_paid", advance_paid)


class CustomSalesOrder(SalesOrder):
	set_total_advance_paid = _set_total_advance_paid


class CustomPurchaseOrder(PurchaseOrder):
	set_total_advance_paid = _set_total_advance_paid
