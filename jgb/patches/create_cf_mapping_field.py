import frappe

from jgb.financial_statement import create_fs_custom_fields, populate_account_cf_mapping


def execute():
	create_fs_custom_fields()
	company = "Joint Global Business Co LLC"
	if frappe.db.exists("Company", company):
		populate_account_cf_mapping(company)
