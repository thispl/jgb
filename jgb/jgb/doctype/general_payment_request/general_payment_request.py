# Copyright (c) 2026, JGB and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.party import get_party_account
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_link_to_form, getdate, nowdate


class GeneralPaymentRequest(Document):
	def validate(self):
		self.validate_mandatory_fields()
		self.validate_amount()
		self.validate_dates()
		self.set_party_name()
		self.set_division_and_cost_center()
		self.set_default_workflow_state()

	def validate_mandatory_fields(self):
		if not self.subject:
			frappe.throw(_("Subject is mandatory."))
		if not self.request_date:
			frappe.throw(_("Request Date is mandatory."))
		if not self.requested_by:
			frappe.throw(_("Requested By is mandatory."))
		if not self.company:
			frappe.throw(_("Company is mandatory."))
		if not self.party_type:
			frappe.throw(_("Party Type is mandatory."))
		if not self.party:
			frappe.throw(_("Party is mandatory."))
		if not self.due_date:
			frappe.throw(_("Due Date is mandatory."))

	def validate_amount(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be greater than 0."))

	def validate_dates(self):
		if self.due_date and self.request_date:
			if getdate(self.due_date) < getdate(self.request_date):
				frappe.throw(_("Due Date cannot be earlier than Request Date."))

	def set_party_name(self):
		if self.party_type and self.party:
			if self.party_type == "Supplier":
				self.party_name = frappe.db.get_value("Supplier", self.party, "supplier_name") or self.party
			elif self.party_type == "Employee":
				self.party_name = frappe.db.get_value("Employee", self.party, "employee_name") or self.party
			elif self.party_type == "Customer":
				self.party_name = frappe.db.get_value("Customer", self.party, "customer_name") or self.party
			elif self.party_type == "Shareholder":
				self.party_name = frappe.db.get_value("Shareholder", self.party, "title") or self.party
			else:
				self.party_name = self.party

	def set_division_and_cost_center(self):
		if not getattr(self, "division", None) and self.requested_by:
			self.division = frappe.db.get_value("Employee", self.requested_by, "custom_division")
		if not getattr(self, "cost_center", None) and getattr(self, "division", None):
			self.cost_center = frappe.db.get_value(
				"Division Account Details",
				{"parent": self.division, "company": self.company},
				"cost_center",
			)
		if not getattr(self, "cost_center", None) and self.company:
			self.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

	def set_default_workflow_state(self):
		if not self.workflow_state and self.docstatus == 0:
			self.workflow_state = "Draft"

	def on_submit(self):
		if self.workflow_state == "Approved" or self.docstatus == 1:
			self.create_payment_entry()

	def on_update_after_submit(self):
		if self.workflow_state == "Approved" and not self.payment_entry:
			self.create_payment_entry()

	def on_cancel(self):
		self.workflow_state = "Cancelled"
		if self.payment_entry and frappe.db.exists("Payment Entry", self.payment_entry):
			pe_status = frappe.db.get_value("Payment Entry", self.payment_entry, "docstatus")
			if pe_status == 1:
				frappe.throw(
					_(
						"Cannot cancel General Payment Request {0}. Linked Payment Entry {1} is already submitted. Please cancel the Payment Entry first."
					).format(self.name, get_link_to_form("Payment Entry", self.payment_entry))
				)
			elif pe_status == 0:
				frappe.delete_doc("Payment Entry", self.payment_entry, force=1)
				self.db_set("payment_entry", None)

	def create_payment_entry(self):
		# Prevent Duplicate Payment Entry Creation
		if self.payment_entry and frappe.db.exists("Payment Entry", self.payment_entry):
			return self.payment_entry

		existing_pe = frappe.db.get_value(
			"Payment Entry",
			{"reference_no": self.name, "docstatus": ["!=", 2]},
			"name",
		)
		if existing_pe:
			self.db_set("payment_entry", existing_pe)
			return existing_pe

		try:
			pe = frappe.new_doc("Payment Entry")
			pe.payment_type = "Pay"
			pe.company = self.company
			pe.posting_date = nowdate()
			pe.paid_amount = flt(self.amount)
			pe.received_amount = flt(self.amount)
			pe.target_exchange_rate = 1.0
			pe.source_exchange_rate = 1.0
			pe.reference_no = self.name
			pe.reference_date = self.request_date

			# Set Party Details
			pe.party_type = self.party_type
			pe.party = self.party
			pe.party_name = self.party_name or self.party

			# Set Division and Cost Center (Mandatory in JGB ERP)
			division = getattr(self, "division", None)
			if not division and self.requested_by:
				division = frappe.db.get_value("Employee", self.requested_by, "custom_division")
			if not division:
				division = frappe.db.get_value("Division", {}, "name")
			if division and hasattr(pe, "custom_division"):
				pe.custom_division = division

			cost_center = getattr(self, "cost_center", None)
			if not cost_center and division:
				cost_center = frappe.db.get_value(
					"Division Account Details",
					{"parent": division, "company": self.company},
					"cost_center",
				)
			if not cost_center:
				cost_center = frappe.get_cached_value("Company", self.company, "cost_center")
			if not cost_center:
				cost_center = frappe.db.get_value(
					"Cost Center", {"company": self.company, "is_group": 0}, "name"
				)

			if cost_center:
				pe.cost_center = cost_center

			# Set remarks
			remarks_text = f"Payment for General Payment Request: {self.name} ({self.subject})\nParty: {pe.party_name} ({self.party})"
			if self.remarks:
				remarks_text += f"\nRemarks: {self.remarks}"
			pe.remarks = remarks_text

			# Auto-resolve bank/cash account (Paid From)
			company_doc = frappe.get_cached_doc("Company", self.company)
			paid_from = company_doc.default_bank_account or company_doc.default_cash_account
			if not paid_from:
				paid_from = frappe.db.get_value(
					"Account",
					{"company": self.company, "account_type": ["in", ["Bank", "Cash"]], "is_group": 0},
					"name",
				)
			if paid_from:
				pe.paid_from = paid_from
				pe.paid_from_account_currency = frappe.db.get_value("Account", paid_from, "account_currency")

			# Auto-resolve Party Payable/Expense Account (Paid To)
			try:
				paid_to = get_party_account(self.party_type, self.party, self.company)
				if paid_to:
					pe.paid_to = paid_to
					pe.paid_to_account_currency = frappe.db.get_value("Account", paid_to, "account_currency")
			except Exception:
				pass

			pe.insert(ignore_permissions=True)
			self.db_set("payment_entry", pe.name)

			frappe.msgprint(
				_("Payment Entry {0} created successfully.").format(get_link_to_form("Payment Entry", pe.name)),
				alert=True,
			)
			return pe.name

		except Exception as e:
			frappe.throw(_("Failed to create Payment Entry for {0}: {1}").format(self.name, str(e)))


@frappe.whitelist()
def get_user_employee():
	"""Fetch Employee linked to current user session."""
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")
	return employee


@frappe.whitelist()
def setup_general_payment_request_workflow():
	"""Create Workflow and required Roles/States for General Payment Request."""
	# 1. Create Roles if missing
	roles = ["COA", "CFO", "HR User", "HR Manager"]
	for role in roles:
		if not frappe.db.exists("Role", role):
			r = frappe.new_doc("Role")
			r.role_name = role
			r.desk_access = 1
			r.insert(ignore_permissions=True)

	# 2. Create Workflow States if missing
	states = [
		{"state": "Draft", "doc_status": "0", "allow_edit": "HR User"},
		{"state": "Pending COA Approval", "doc_status": "0", "allow_edit": "COA"},
		{"state": "Pending CFO Approval", "doc_status": "0", "allow_edit": "CFO"},
		{"state": "Approved", "doc_status": "1", "allow_edit": "CFO"},
		{"state": "Rejected", "doc_status": "0", "allow_edit": "HR User"},
		{"state": "Cancelled", "doc_status": "2", "allow_edit": "CFO"},
	]
	for s in states:
		if not frappe.db.exists("Workflow State", s["state"]):
			ws = frappe.new_doc("Workflow State")
			ws.workflow_state_name = s["state"]
			ws.insert(ignore_permissions=True)

	# 3. Create Workflow Action Master records if missing
	actions = ["Send to COA", "Approve", "Reject", "Cancel"]
	for action in actions:
		if not frappe.db.exists("Workflow Action Master", action):
			wam = frappe.new_doc("Workflow Action Master")
			wam.workflow_action_name = action
			wam.insert(ignore_permissions=True)

	# 4. Create or update Workflow
	workflow_name = "General Payment Request Approval"
	if frappe.db.exists("Workflow", workflow_name):
		frappe.delete_doc("Workflow", workflow_name, force=1)

	wf = frappe.new_doc("Workflow")
	wf.workflow_name = workflow_name
	wf.document_type = "General Payment Request"
	wf.workflow_state_field = "workflow_state"
	wf.is_active = 1
	wf.send_email_alert = 0

	# Add States
	for s in states:
		wf.append(
			"states",
			{
				"state": s["state"],
				"doc_status": s["doc_status"],
				"allow_edit": s["allow_edit"],
			},
		)

	# Add Transitions (HR User / HR Manager -> CAO -> CFO -> Cancelled)
	transitions = [
		{
			"state": "Draft",
			"action": "Send to COA",
			"next_state": "Pending COA Approval",
			"allowed": "HR User",
		},
		{
			"state": "Draft",
			"action": "Send to COA",
			"next_state": "Pending COA Approval",
			"allowed": "HR Manager",
		},
		{
			"state": "Pending COA Approval",
			"action": "Approve",
			"next_state": "Pending CFO Approval",
			"allowed": "COA",
		},
		{
			"state": "Pending COA Approval",
			"action": "Reject",
			"next_state": "Rejected",
			"allowed": "COA",
		},
		{
			"state": "Pending CFO Approval",
			"action": "Approve",
			"next_state": "Approved",
			"allowed": "CFO",
		},
		{
			"state": "Pending CFO Approval",
			"action": "Reject",
			"next_state": "Rejected",
			"allowed": "CFO",
		},
		{
			"state": "Approved",
			"action": "Cancel",
			"next_state": "Cancelled",
			"allowed": "CFO",
		},
		{
			"state": "Approved",
			"action": "Cancel",
			"next_state": "Cancelled",
			"allowed": "COA",
		},
	]

	for t in transitions:
		wf.append("transitions", t)

	wf.insert(ignore_permissions=True)
	frappe.db.commit()

	return True
