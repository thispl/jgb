# import frappe
# from frappe import _

# @frappe.whitelist()
# def process_unpaid_claims(claim_ids, employee, from_date, to_date):
#     claim_ids = frappe.parse_json(claim_ids)
	
#     filters = {
#         'salary_component': 'Monthly Expenses',
#         'employee': employee,
#         'payroll_date': ['between', [from_date, to_date]],
#         'docstatus': ['!=',2]  # 0 means Draft
#     }
	
#     if frappe.db.exists('Additional Salary', filters):
#         doc = frappe.get_doc('Additional Salary', filters)
#     else:
#         doc = frappe.new_doc('Additional Salary')
#         doc.employee = employee
#         doc.salary_component = 'Monthly Expenses'
#         doc.payroll_date = to_date  
#         doc.overwrite_salary_structure_amount = 1

#     updated = False

#     for claim_id in claim_ids:
#         if any(row.expense_id == claim_id for row in doc.custom_expense_split_up):
#             continue
			
#         claim_data = frappe.db.get_value('Expense Claim', claim_id, ['grand_total'], as_dict=1)
		
#         if claim_data:
#             amount = claim_data.grand_total
			
#             doc.append("custom_expense_split_up", {
#                 "expense_id": claim_id,
#                 "expense_amount": amount
#             })
			
#             frappe.db.set_value(
#                 "Expense Claim",
#                 claim_id,
#                 {
#                     "status": "Paid",
#                     "custom_payment_status": "Paid"
#                 },
#                 update_modified=False
#             )
#             updated = True
	
#     if updated:
#         doc.amount = sum(row.expense_amount for row in doc.custom_expense_split_up)
#         doc.save()
#         if doc.docstatus==0:
#             doc.submit()
#         return _("Expense claims successfully processed and updated.")
#     else:
#         return _("No new claims were added (they may have already been linked).")
		

import frappe
from frappe import _

@frappe.whitelist()
def process_unpaid_claims(claim_ids, employee, from_date, to_date):
	claim_ids = frappe.parse_json(claim_ids)

	processed = []
	skipped = []

	for claim_id in claim_ids:
		# already linked to some submitted/draft Additional Salary?
		already_linked = frappe.db.sql(
			"""
			SELECT parent
			FROM `tabExpense Split Up`
			WHERE expense_id = %s
			AND parenttype = 'Additional Salary'
			AND parent IN (
				SELECT name FROM `tabAdditional Salary`
				WHERE docstatus != 2
			)
			""",
			(claim_id,)
		)
		if already_linked:
			skipped.append(claim_id)
			continue

		claim_data = frappe.db.get_value('Expense Claim', claim_id, ['grand_total'], as_dict=1)
		if not claim_data or not claim_data.grand_total:
			skipped.append(claim_id)
			continue

		amount = claim_data.grand_total

		doc = frappe.new_doc('Additional Salary')
		doc.employee = employee
		doc.salary_component = 'Monthly Expenses'
		doc.payroll_date = to_date
		doc.overwrite_salary_structure_amount = 0
		doc.amount = amount

		doc.append("custom_expense_split_up", {
			"expense_id": claim_id,
			"expense_amount": amount
		})

		doc.insert(ignore_permissions=True)
		doc.submit()

		frappe.db.set_value(
			"Expense Claim",
			claim_id,
			{
				"status": "Paid",
				"custom_payment_status": "Paid"
			},
			update_modified=False
		)
		processed.append(claim_id)

	if processed:
		msg = _("Created {0} Additional Salary document(s) for claims: {1}").format(
			len(processed), ", ".join(processed)
		)
		if skipped:
			msg += " " + _("Skipped (already linked or invalid): {0}").format(", ".join(skipped))
		return msg
	else:
		return _("No new claims were added (they may have already been linked).")



@frappe.whitelist()
def create_expense_salary(doc, method):
	salary_component = "Monthly Expenses"

	expense_claims = frappe.db.sql(
		"""
		SELECT name, grand_total
		FROM `tabExpense Claim`
		WHERE
			docstatus = 1
			AND employee = %s
			AND custom_ec_from_date BETWEEN %s AND %s
			AND IFNULL(custom_payment_status, '') != 'Paid'
		""",
		(doc.employee, doc.start_date, doc.end_date),
		as_dict=True
	)
	if not expense_claims:
		return

	for ec in expense_claims:
		if ec.grand_total <= 0:
			continue

		# check via child table whether this exact expense claim
		# is already linked to a submitted Additional Salary
		existing = frappe.db.sql(
			"""
			SELECT parent
			FROM `tabExpense Split Up`
			WHERE expense_id = %s
			AND parenttype = 'Additional Salary'
			AND parent IN (
				SELECT name FROM `tabAdditional Salary`
				WHERE docstatus = 1
			)
			""",
			(ec.name,)
		)
		if existing:
			continue

		additional_salary = frappe.get_doc({
			"doctype": "Additional Salary",
			"employee": doc.employee,
			"salary_component": salary_component,
			"amount": ec.grand_total,
			"payroll_date": doc.start_date,
			"company": doc.company,
			"overwrite_salary_structure_amount": 0,
		})

		additional_salary.append("custom_expense_split_up", {
			"expense_id": ec.name,
			"expense_amount": ec.grand_total
		})

		if additional_salary.custom_expense_split_up:
			additional_salary.insert(ignore_permissions=True)
			additional_salary.submit()

			frappe.db.set_value(
				"Expense Claim",
				ec.name,
				{
					"status": "Paid",
					"custom_payment_status": "Paid"
				},
				update_modified=False
			)
		else:
			frappe.log_error(f"No valid expense claim to append for {ec.name}", 'Expense Claim Debug')




@frappe.whitelist()
def create_pay_now_deduction(doc, method=None):
	from jgb.jgb.teampro.leave_application import reconcile_leave_deduction

	# One Leave Deduction Additional Salary per payroll period, recomputed from
	# the active Pay With Payroll annual-vacation leaves. This also cancels duplicates
	# and rows left behind by cancelled leaves, which get_additional_salaries()
	# would otherwise reject.
	reconcile_leave_deduction(doc.employee, doc.company, doc.start_date, doc.end_date)

