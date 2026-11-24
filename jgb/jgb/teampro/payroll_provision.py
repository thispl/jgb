# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt
"""Monthly payroll-on-cost auto-provision.

Creates one DRAFT Journal Entry per company per month that accrues the
employer payroll-on-cost components: EOSB, GOSI, Vacation Airfare and
Leave Pay. Finance reviews the drafts and submits them.

Amounts mirror the "MANPOWER FORMAT PAYROLL ON COST" workbook:

	EOSB      = (Basic + HRA) / 2 / 12   while service <= 5 years
	          = (Basic + HRA) / 12       after 5 years
	GOSI      = (Basic + HRA) x 11.75%   (Saudi)
	          = (Basic + HRA) x 2%       (non-Saudi)
	Airfare   = Employee.custom_travel_allowance / 12
	Leave Pay = Basic / 12

Debit  -> payroll expense accounts
Credit -> provision (liability) accounts

The cost center follows the employee's division (Division Account Details,
falling back to a name match and finally the company Main cost center) and
the provision line carries the employee party so each accrual is traceable.
"""

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_last_day, getdate

# component key -> (label, expense account_number, provision account_number)
COMPONENTS = {
	"EOSB": ("Provision for EOSB", "5108", "2235"),
	"GOSI": ("Provision for GOSI", "5152", "2231"),
	"Airfare": ("Provision for Vacation Airfare", "5110", "2233"),
	"Leave": ("Provision for Leave Pay", "5109", "2232"),
}

GOSI_SAUDI_RATE = 0.1175
GOSI_NON_SAUDI_RATE = 0.02

# division -> cost-center keyword, used when Division Account Details has no row
DIVISION_CC_KEYWORD = {
	"Filtration Division (FRD)": "Filtration",
	"HVAC Division - (HVA)": "HVAC",
	"Misting (MST)": "Misting",
	"Valves and Pipeline (VLP)": "Valves",
	"Waterworks Division (WTR)": "Waterworks",
}


def get_company_account(company, account_number):
	"""Return the company's ledger account for an account number, or None."""
	return frappe.db.get_value(
		"Account",
		{"company": company, "account_number": account_number, "is_group": 0},
		"name",
	)


def get_division_cost_center(company, division):
	"""Resolve the cost center for a division within a company."""
	if division:
		cc = frappe.db.get_value(
			"Division Account Details",
			{"parent": division, "company": company},
			"cost_center",
		)
		if cc:
			return cc

	keyword = DIVISION_CC_KEYWORD.get(division)
	if keyword:
		cc = frappe.db.get_value(
			"Cost Center",
			{"company": company, "is_group": 0, "name": ["like", f"%{keyword}%"]},
			"name",
		)
		if cc:
			return cc

	abbr = frappe.get_cached_value("Company", company, "abbr")
	return frappe.db.get_value(
		"Cost Center",
		{"company": company, "is_group": 0, "name": f"Main - {abbr}"},
		"name",
	)


def is_saudi(employee):
	return (employee.custom_nationality or "").strip() == "Saudi Arabia"


def years_of_service(date_of_joining, on_date):
	if not date_of_joining:
		return 0.0
	return (getdate(on_date) - getdate(date_of_joining)).days / 365.0


def compute_amounts(employee, on_date):
	"""Monthly provision amount for each component for one employee."""
	basic = flt(employee.custom_basic)
	hra = flt(employee.custom_hra)
	wage = basic + hra
	years = years_of_service(employee.date_of_joining, on_date)

	if not employee.date_of_joining:
		eosb = 0.0
	elif years <= 5:
		eosb = wage / 2 / 12
	else:
		eosb = wage / 12

	gosi_rate = GOSI_SAUDI_RATE if is_saudi(employee) else GOSI_NON_SAUDI_RATE

	return {
		"EOSB": eosb,
		"GOSI": wage * gosi_rate,
		"Airfare": flt(employee.custom_travel_allowance) / 12,
		"Leave": basic / 12,
	}


def _get_employees(company):
	return frappe.get_all(
		"Employee",
		filters={"company": company, "status": "Active"},
		fields=[
			"name",
			"employee_name",
			"custom_basic",
			"custom_hra",
			"custom_division",
			"custom_travel_allowance",
			"custom_nationality",
			"date_of_joining",
		],
	)


def build_provision_entry(company, posting_date, submit=False, dry_run=False):
	"""Create (or report on) the monthly provision Journal Entry for a company."""
	month = getdate(posting_date).strftime("%Y-%m")
	remark = _("Monthly Payroll Provision - {0}").format(month)

	existing = frappe.db.exists(
		"Journal Entry",
		{"company": company, "user_remark": remark, "docstatus": ["!=", 2]},
	)
	if existing:
		return {"company": company, "skipped": True, "journal_entry": existing}

	accounts = {
		key: (get_company_account(company, exp), get_company_account(company, prov))
		for key, (label, exp, prov) in COMPONENTS.items()
	}
	missing = [COMPONENTS[key][0] for key, (exp, prov) in accounts.items() if not exp or not prov]
	if missing:
		frappe.throw(
			_("Missing expense/provision account for {0}: {1}").format(company, ", ".join(missing))
		)

	rows = []
	total = 0.0
	for emp in _get_employees(company):
		amounts = compute_amounts(emp, posting_date)
		if sum(amounts.values()) <= 0:
			continue

		cc = get_division_cost_center(company, emp.custom_division)
		for key, amount in amounts.items():
			if amount <= 0:
				continue
			exp_acct, prov_acct = accounts[key]
			label = COMPONENTS[key][0]
			row_remark = f"{emp.employee_name} - {label}"
			rows.append((exp_acct, cc, amount, 0, None, row_remark))
			rows.append((prov_acct, cc, 0, amount, emp.name, row_remark))
			total += amount

	if not rows:
		return {"company": company, "skipped": True, "reason": "no amounts to provision"}

	if dry_run:
		return {"company": company, "lines": len(rows), "total": total}

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.company = company
	je.posting_date = posting_date
	je.is_system_generated = 1
	je.user_remark = remark
	for account, cc, debit, credit, party, row_remark in rows:
		row = {"account": account, "cost_center": cc, "user_remark": row_remark}
		if debit:
			row["debit_in_account_currency"] = debit
		if credit:
			row["credit_in_account_currency"] = credit
		if party:
			row["party_type"] = "Employee"
			row["party"] = party
		je.append("accounts", row)

	je.insert()
	if submit:
		je.submit()

	return {"company": company, "journal_entry": je.name, "lines": len(rows), "total": total}


@frappe.whitelist()
def create_monthly_provision(posting_date=None, company=None, submit=False, dry_run=False):
	"""Provision the payroll-on-cost components for a month.

	Defaults to the last day of the previous month for every company that has
	active employees. Pass ``company`` to restrict, ``dry_run`` to preview.
	"""
	posting_date = (
		getdate(posting_date) if posting_date else get_last_day(add_months(getdate(), -1))
	)
	submit = bool(int(submit)) if isinstance(submit, str) else bool(submit)
	dry_run = bool(int(dry_run)) if isinstance(dry_run, str) else bool(dry_run)

	if company:
		companies = [company]
	else:
		companies = [
			r[0]
			for r in frappe.db.sql(
				"select distinct company from `tabEmployee` "
				"where status = 'Active' and ifnull(company, '') != ''"
			)
		]

	results = []
	for comp in companies:
		try:
			results.append(
				build_provision_entry(comp, posting_date, submit=submit, dry_run=dry_run)
			)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(), f"Payroll provision failed - {comp}"
			)
			results.append({"company": comp, "error": True})

	return results


def scheduled_monthly_provision():
	"""Monthly scheduler entry point: draft provision entries for the last month."""
	create_monthly_provision(submit=False)
