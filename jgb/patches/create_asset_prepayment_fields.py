# Custom fields for the Asset Prepayment feature (mirrors depreciation):
# - Asset: "Prepayment Details" block after the depreciation schedule section
# - Asset Category Account: prepaid + prepayment-expense accounts, next to the
#   depreciation accounts
# - Journal Entry voucher_type: adds "Prepayment Entry" option

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Asset": [
				{
					"fieldname": "custom_prepayment_section",
					"fieldtype": "Section Break",
					"label": "Prepayment Details",
					"insert_after": "depreciation_schedule_view",
				},
				{
					"fieldname": "custom_is_prepaid",
					"fieldtype": "Check",
					"label": "Has Prepayment",
					"insert_after": "custom_prepayment_section",
					"allow_on_submit": 1,
				},
				{
					"fieldname": "custom_prepaid_amount",
					"fieldtype": "Currency",
					"label": "Prepaid Amount",
					"options": "Company:company:default_currency",
					"insert_after": "custom_is_prepaid",
					"depends_on": "custom_is_prepaid",
					"allow_on_submit": 1,
				},
				{
					"fieldname": "custom_prepayment_start_date",
					"fieldtype": "Date",
					"label": "Prepayment Start Date",
					"insert_after": "custom_prepaid_amount",
					"depends_on": "custom_is_prepaid",
					"allow_on_submit": 1,
				},
				{
					"fieldname": "custom_prepayment_cb",
					"fieldtype": "Column Break",
					"insert_after": "custom_prepayment_start_date",
				},
				{
					"fieldname": "custom_total_number_of_prepayments",
					"fieldtype": "Int",
					"label": "Total Number of Prepayments",
					"insert_after": "custom_prepayment_cb",
					"depends_on": "custom_is_prepaid",
					"allow_on_submit": 1,
				},
				{
					"fieldname": "custom_frequency_of_prepayment",
					"fieldtype": "Int",
					"label": "Frequency of Prepayment (Months)",
					"insert_after": "custom_total_number_of_prepayments",
					"depends_on": "custom_is_prepaid",
					"allow_on_submit": 1,
				},
				{
					"fieldname": "custom_opening_amortized_prepayment",
					"fieldtype": "Currency",
					"label": "Opening Amortized Prepayment",
					"options": "Company:company:default_currency",
					"insert_after": "custom_frequency_of_prepayment",
					"depends_on": "custom_is_prepaid",
					"allow_on_submit": 1,
				},
				{
					"fieldname": "custom_prepaid_cb",
					"fieldtype": "Column Break",
					"insert_after": "custom_opening_amortized_prepayment",
				},
				{
					"fieldname": "custom_prepaid_amortized",
					"fieldtype": "Currency",
					"label": "Amortized Prepayment",
					"options": "Company:company:default_currency",
					"insert_after": "custom_prepaid_cb",
					"read_only": 1,
					"depends_on": "custom_is_prepaid",
				},
				{
					"fieldname": "custom_prepaid_balance",
					"fieldtype": "Currency",
					"label": "Prepaid Balance",
					"options": "Company:company:default_currency",
					"insert_after": "custom_prepaid_amortized",
					"read_only": 1,
					"depends_on": "custom_is_prepaid",
				},
				{
					"fieldname": "custom_prepayment_schedule_view",
					"fieldtype": "HTML",
					"label": "Prepayment Schedule",
					"insert_after": "custom_prepaid_balance",
					"depends_on": "custom_is_prepaid",
				},
			],
			"Asset Category Account": [
				{
					"fieldname": "custom_prepaid_account",
					"fieldtype": "Link",
					"label": "Prepaid Account",
					"options": "Account",
					"insert_after": "capital_work_in_progress_account",
				},
				{
					"fieldname": "custom_prepayment_expense_account",
					"fieldtype": "Link",
					"label": "Prepayment Expense Account",
					"options": "Account",
					"insert_after": "custom_prepaid_account",
				},
			],
		}
	)

	# add "Prepayment Entry" to Journal Entry voucher_type options
	options = frappe.get_meta("Journal Entry").get_field("voucher_type").options.split("\n")
	if "Prepayment Entry" not in options:
		options.append("Prepayment Entry")
		frappe.make_property_setter(
			{
				"doctype": "Journal Entry",
				"fieldname": "voucher_type",
				"property": "options",
				"value": "\n".join(options),
				"property_type": "Text",
			},
			validate_fields_for_doctype=False,
		)
