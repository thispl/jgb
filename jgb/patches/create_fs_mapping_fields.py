import frappe

from jgb.financial_statement import populate_account_fs_mapping


def execute():
	company = "Joint Global Business Co LLC"
	if frappe.db.exists("Company", company):
		populate_account_fs_mapping(company)
