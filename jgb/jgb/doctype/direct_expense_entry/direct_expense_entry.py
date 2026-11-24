# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import flt, getdate
import erpnext
from erpnext.accounts.general_ledger import make_gl_entries

class DirectExpenseEntry(Document):
	def validate(self):
		self.validate_company()
		self.validate_accounts()
		self.calculate_total_amount()

	def validate_company(self):
		if not self.company:
			self.company = frappe.db.get_default("company") or frappe.defaults.get_user_default("Company")
		if not self.company:
			throw(_("Company is required."))

	def validate_accounts(self):
		# Ensure bank_cash_account is valid
		if not self.bank_cash_account:
			throw(_("Cash/Bank Account is required."))
		
		bank_cash_details = frappe.db.get_value(
			"Account",
			self.bank_cash_account,
			["company", "account_type", "is_group", "disabled"],
			as_dict=True
		)
		if not bank_cash_details:
			throw(_("Account {0} does not exist.").format(self.bank_cash_account))
		if bank_cash_details.company != self.company:
			throw(_("Cash/Bank Account {0} does not belong to Company {1}.").format(self.bank_cash_account, self.company))
		if bank_cash_details.is_group == 1:
			throw(_("Cash/Bank Account {0} cannot be a Group Account.").format(self.bank_cash_account))
		if bank_cash_details.disabled == 1:
			throw(_("Cash/Bank Account {0} is disabled.").format(self.bank_cash_account))
		if bank_cash_details.account_type not in ("Bank", "Cash"):
			# Standard ERPNext warning or restriction, let's make it a throw to keep data clean
			frappe.msgprint(_("Warning: Selected Cash/Bank Account is not configured with type Bank or Cash."))

		# Ensure there are expenses listed
		if not self.get("expenses"):
			throw(_("Please add at least one row in the Expenses table."))

		for row in self.get("expenses"):
			if not row.expense_account:
				throw(_("Expense Account is required in row {0}.").format(row.idx))
			
			expense_details = frappe.db.get_value(
				"Account",
				row.expense_account,
				["company", "root_type", "is_group", "disabled"],
				as_dict=True
			)
			if not expense_details:
				throw(_("Expense Account {0} in row {1} does not exist.").format(row.expense_account, row.idx))
			if expense_details.company != self.company:
				throw(_("Expense Account {0} in row {1} does not belong to Company {2}.").format(row.expense_account, row.idx, self.company))
			if expense_details.is_group == 1:
				throw(_("Expense Account {0} in row {1} cannot be a Group Account.").format(row.expense_account, row.idx))
			if expense_details.disabled == 1:
				throw(_("Expense Account {0} in row {1} is disabled.").format(row.expense_account, row.idx))
			if expense_details.root_type != "Expense":
				throw(_("Account {0} in row {1} is not an Expense Account.").format(row.expense_account, row.idx))

			if flt(row.amount) <= 0:
				throw(_("Amount must be greater than zero in row {0}.").format(row.idx))

		# Validate tax account if tax is included
		if self.include_tax:
			if not self.tax_account:
				throw(_("Tax Account is required when Include Tax is enabled."))

			tax_account_details = frappe.db.get_value(
				"Account",
				self.tax_account,
				["company", "is_group", "disabled"],
				as_dict=True
			)
			if not tax_account_details:
				throw(_("Tax Account {0} does not exist.").format(self.tax_account))
			if tax_account_details.company != self.company:
				throw(_("Tax Account {0} does not belong to Company {1}.").format(self.tax_account, self.company))
			if tax_account_details.is_group == 1:
				throw(_("Tax Account {0} cannot be a Group Account.").format(self.tax_account))
			if tax_account_details.disabled == 1:
				throw(_("Tax Account {0} is disabled.").format(self.tax_account))

			if flt(self.tax_amount) < 0:
				throw(_("Tax Amount must be zero or positive."))

	def calculate_total_amount(self):
		total = 0.0
		for row in self.get("expenses"):
			total += flt(row.amount)
		if self.include_tax:
			total += flt(self.tax_amount)
		self.total_amount = total

	def on_submit(self):
		self.make_gl_entries(cancel=False)

	def before_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry",)

	def on_cancel(self):
		self.make_gl_entries(cancel=True)

	def make_gl_entries(self, cancel=False):
		gl_entries = []
		company_currency = erpnext.get_company_currency(self.company)

		# 1. Debit Entries (Expense Accounts)
		for row in self.get("expenses"):
			row_remarks = row.description or self.remarks or _("Direct Expense Entry")
			account_currency = frappe.db.get_value("Account", row.expense_account, "account_currency") or company_currency

			gl_entries.append(frappe._dict({
				"company": self.company,
				"posting_date": self.posting_date,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"remarks": row_remarks,
				"account": row.expense_account,
				"party_type": None,
				"party": None,
				"against": self.bank_cash_account,
				"debit": flt(row.amount),
				"debit_in_account_currency": flt(row.amount),
				"credit": 0.0,
				"credit_in_account_currency": 0.0,
				"account_currency": account_currency,
				"cost_center": row.cost_center or frappe.db.get_value("Company", self.company, "cost_center"),
				"project": row.project,
				"is_opening": "No"
			}))

		# 2. Tax Entry (Tax Account) - only when tax is included
		if self.include_tax and flt(self.tax_amount) > 0:
			tax_account_currency = frappe.db.get_value("Account", self.tax_account, "account_currency") or company_currency
			tax_remarks = self.remarks or _("Direct Expense Entry - Tax")

			gl_entries.append(frappe._dict({
				"company": self.company,
				"posting_date": self.posting_date,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"remarks": tax_remarks,
				"account": self.tax_account,
				"party_type": None,
				"party": None,
				"against": self.bank_cash_account,
				"debit": flt(self.tax_amount),
				"debit_in_account_currency": flt(self.tax_amount),
				"credit": 0.0,
				"credit_in_account_currency": 0.0,
				"account_currency": tax_account_currency,
				"cost_center": frappe.db.get_value("Company", self.company, "cost_center"),
				"project": None,
				"is_opening": "No"
			}))

		# 3. Credit Entry (Cash/Bank Account)
		unique_expense_accounts = list(set(row.expense_account for row in self.get("expenses")))
		against_accounts = ", ".join(unique_expense_accounts)

		if self.include_tax and flt(self.tax_amount) > 0:
			against_accounts += ", " + self.tax_account

		bank_cash_currency = frappe.db.get_value("Account", self.bank_cash_account, "account_currency") or company_currency
		gl_remarks = self.remarks or _("Direct Expense Entry")

		gl_entries.append(frappe._dict({
			"company": self.company,
			"posting_date": self.posting_date,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"remarks": gl_remarks,
			"account": self.bank_cash_account,
			"party_type": None,
			"party": None,
			"against": against_accounts,
			"debit": 0.0,
			"debit_in_account_currency": 0.0,
			"credit": flt(self.total_amount),
			"credit_in_account_currency": flt(self.total_amount),
			"account_currency": bank_cash_currency,
			# Parent transaction's cost center fallback to company cost center if not explicitly set
			"cost_center": frappe.db.get_value("Company", self.company, "cost_center"),
			"project": None,
			"is_opening": "No"
		}))

		# Submit entries to General Ledger using standard ERPNext API
		make_gl_entries(gl_entries, cancel=cancel)
