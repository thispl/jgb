# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

# "JGB Project Profitability" report.
# One row per Project / Sales Order, with actuals taken from project-tagged
# GL Entries bucketed into Material Cost (COGS), Additional Cost (COS),
# Delivery & Distribution Charges and Other Costs, compared against the
# Estimation total captured on the Sales Order (Estimation Details table).

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_year_start, nowdate

from jgb.financial_statement import (
	ACCOUNT_MAPPING,
	FS_CATEGORY_FIELD,
	FS_SUBCATEGORY_FIELD,
)

DELIVERY_ACCOUNT_PREFIX = "delivery & distribution charges"

# Income accounts under a group like "4100 - Other Income" are non-operating
# (forex gain/loss, gain on asset disposal, round off). The FS mapping lumps them
# into Revenue/Sales, but they must not inflate project Revenue -- they are
# treated as Other Costs instead (a net debit is a loss, a net credit a gain).
NON_OPERATING_INCOME_GROUP = "%other income%"

# GL postings that carry no Project cannot be attributed to any project row.
# They are reported as one synthetic row per division (derived from the GL cost
# center) so that the report totals tie to the Trial Balance.
UNALLOCATED_LABEL = "Unallocated (no project)"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	currency = frappe.get_cached_value("Company", filters.company, "default_currency") or "SAR"
	account_buckets = get_account_buckets(filters.company)
	gl_totals = get_gl_totals(filters, account_buckets)
	unallocated = get_unallocated_totals(filters, account_buckets)
	rows = build_rows(filters, gl_totals, unallocated, currency)
	columns = get_columns(filters)

	return columns, rows


def validate_filters(filters):
	if not filters.company:
		filters.company = frappe.defaults.get_user_default("Company")
	if not filters.company or not frappe.db.exists("Company", filters.company):
		frappe.throw(_("Please select a valid Company"))

	filters.from_date = getdate(filters.get("from_date") or get_year_start(nowdate()))
	filters.to_date = getdate(filters.get("to_date") or nowdate())
	if filters.to_date < filters.from_date:
		frappe.throw(_("To Date cannot be before From Date"))


def get_account_buckets(company):
	"""Map every leaf account to a cost/revenue bucket.

	Buckets: revenue, material, additional, delivery, other (expense), None
	(everything else, e.g. balance-sheet accounts).
	"""
	meta = frappe.get_meta("Account")
	has_fields = meta.has_field(FS_CATEGORY_FIELD) and meta.has_field(FS_SUBCATEGORY_FIELD)

	fields = ["name", "account_name", "account_number", "root_type"]
	if has_fields:
		fields += [FS_CATEGORY_FIELD, FS_SUBCATEGORY_FIELD]

	accounts = frappe.get_all(
		"Account", filters={"company": company, "is_group": 0}, fields=fields + ["lft", "rgt"]
	)
	non_operating_ranges = frappe.get_all(
		"Account",
		filters={
			"company": company,
			"is_group": 1,
			"root_type": "Income",
			"account_name": ("like", NON_OPERATING_INCOME_GROUP),
		},
		fields=["lft", "rgt"],
	)

	def is_non_operating_income(acc):
		return any(g.lft < acc.lft and acc.rgt < g.rgt for g in non_operating_ranges)

	buckets = {}
	for acc in accounts:
		cat = sub = None
		if has_fields:
			cat = (acc.get(FS_CATEGORY_FIELD) or "").strip() or None
			sub = (acc.get(FS_SUBCATEGORY_FIELD) or "").strip() or None
		if not (cat and sub):
			seed = ACCOUNT_MAPPING.get((acc.account_number or "").strip())
			if seed:
				cat, sub = seed

		is_delivery = (acc.account_name or "").strip().lower().startswith(
			DELIVERY_ACCOUNT_PREFIX
		)

		if acc.root_type == "Income":
			buckets[acc.name] = "other" if is_non_operating_income(acc) else "revenue"
		elif is_delivery and cat == "Cost of Goods Sold":
			buckets[acc.name] = "delivery"
		elif cat == "Cost of Goods Sold" and sub == "Cost of Goods Sold":
			buckets[acc.name] = "material"
		elif cat == "Cost of Goods Sold" and sub == "Direct Expenses":
			buckets[acc.name] = "additional"
		elif acc.root_type == "Expense":
			buckets[acc.name] = "other"
		else:
			buckets[acc.name] = None

	return buckets


def get_gl_totals(filters, account_buckets):
	"""Per-project sums per bucket from project-tagged GL Entries in the period."""
	result = frappe.db.sql(
		"""
		select gle.project, gle.account, sum(gle.debit) as debit, sum(gle.credit) as credit
		from `tabGL Entry` gle
		where gle.company = %(company)s
			and gle.is_cancelled = 0
			and gle.voucher_type != 'Period Closing Voucher'
			and gle.posting_date between %(from_date)s and %(to_date)s
			and gle.project is not null and gle.project != ''
		group by gle.project, gle.account
		""",
		filters,
		as_dict=True,
	)

	totals = {}
	for row in result:
		bucket = account_buckets.get(row.account)
		if not bucket:
			continue
		entry = totals.setdefault(
			row.project,
			frappe._dict(
				revenue=0.0, material=0.0, additional=0.0, delivery=0.0, other=0.0
			),
		)
		if bucket == "revenue":
			entry.revenue += flt(row.credit) - flt(row.debit)
		else:
			entry[bucket] += flt(row.debit) - flt(row.credit)

	return totals


def get_cost_center_divisions(company):
	"""Cost center -> Division, from the Division Account Details child table."""
	return {
		row.cost_center: row.division
		for row in frappe.db.sql(
			"""
			select cad.cost_center, cad.parent as division
			from `tabDivision Account Details` cad
			where cad.company = %(company)s and ifnull(cad.cost_center, '') != ''
			""",
			{"company": company},
			as_dict=True,
		)
	}


def get_unallocated_totals(filters, account_buckets):
	"""GL in the period with no Project tag, bucketed per division.

	Returns one entry per division (plus one for postings with no usable cost
	center) so the report can show what the Trial Balance contains but no
	project row can carry.
	"""
	# A specific project / SO / customer cannot be reconciled against untagged
	# postings, so those filters suppress the unallocated rows entirely.
	if filters.get("project") or filters.get("sales_order") or filters.get("customer"):
		return []

	result = frappe.db.sql(
		"""
		select ifnull(gle.cost_center, '') as cost_center, gle.account,
			sum(gle.debit) as debit, sum(gle.credit) as credit
		from `tabGL Entry` gle
		where gle.company = %(company)s
			and gle.is_cancelled = 0
			and gle.voucher_type != 'Period Closing Voucher'
			and gle.posting_date between %(from_date)s and %(to_date)s
			and (gle.project is null or gle.project = '')
		group by gle.cost_center, gle.account
		""",
		filters,
		as_dict=True,
	)

	cc_divisions = get_cost_center_divisions(filters.company)
	per_division = {}

	for row in result:
		bucket = account_buckets.get(row.account)
		if not bucket:
			continue
		division = cc_divisions.get(row.cost_center) or row.cost_center or None
		entry = per_division.setdefault(
			division,
			frappe._dict(revenue=0.0, material=0.0, additional=0.0, delivery=0.0, other=0.0),
		)
		if bucket == "revenue":
			entry.revenue += flt(row.credit) - flt(row.debit)
		else:
			entry[bucket] += flt(row.debit) - flt(row.credit)

	rows = []
	for division, amounts in per_division.items():
		if filters.get("division") and division != filters.division:
			continue
		if not any(flt(amounts.get(k)) for k in ("revenue", "material", "additional", "delivery", "other")):
			continue
		amounts.division = division
		rows.append(amounts)

	rows.sort(key=lambda r: r.division or "")
	return rows


def get_project_cost_center_divisions(company, projects):
	"""Division per project, derived from the GL cost center of its postings.

	Fallback for projects that have no Sales Order (or whose SO has no
	`custom_division`): the division filter reads the SO, so without this a
	direct project could never appear in a division-filtered run even though
	its postings carry a division cost center.
	"""
	if not projects:
		return {}

	rows = frappe.db.sql(
		"""
		select ge.project, cad.parent as division, count(*) as n
		from `tabGL Entry` ge
		join `tabDivision Account Details` cad
			on cad.cost_center = ge.cost_center and cad.company = %(company)s
		where ge.company = %(company)s
			and ge.is_cancelled = 0
			and ge.project in %(projects)s
			and ifnull(ge.cost_center, '') != ''
		group by ge.project, cad.parent
		""",
		{"company": company, "projects": tuple(projects)},
		as_dict=True,
	)

	best = {}
	for row in rows:
		current = best.get(row.project)
		if not current or row.n > current[1]:
			best[row.project] = (row.division, row.n)

	return {project: division for project, (division, _n) in best.items()}


def get_projects(filters):
	"""All projects of the company with their linked Sales Order (if any).

	Left-joined on purpose: projects created directly (no Sales Order) and
	projects whose Sales Order was later cancelled still carry GL postings and
	must not silently drop out of the profitability figures.

	Division comes from `Sales Order.custom_division`, falling back to the
	division of the project's GL cost center for projects without a usable SO.
	"""
	conditions = ["p.company = %(company)s"]
	if filters.get("project"):
		conditions.append("p.name = %(project)s")
	if filters.get("sales_order"):
		conditions.append("so.name = %(sales_order)s")
	if filters.get("customer"):
		conditions.append("so.customer = %(customer)s")

	projects = frappe.db.sql(
		f"""
		select
			p.name as project,
			p.status as project_status,
			so.name as sales_order,
			so.docstatus as so_docstatus,
			so.transaction_date,
			so.customer,
			so.customer_name,
			so.custom_division as division,
			(
				select sum(ed.value) from `tabEstimation Details` ed
				where ed.parent = so.name and ed.parenttype = 'Sales Order'
			) as estimation
		from `tabProject` p
		left join `tabSales Order` so on so.name = p.sales_order
		where {' and '.join(conditions)}
		order by so.transaction_date, so.name, p.name
		""",
		filters,
		as_dict=True,
	)

	without_division = [p.project for p in projects if not p.division]
	if without_division:
		fallback = get_project_cost_center_divisions(filters.company, without_division)
		for project in projects:
			if not project.division:
				project.division = fallback.get(project.project)

	if filters.get("division"):
		projects = [p for p in projects if p.division == filters.division]

	return projects


def build_rows(filters, gl_totals, unallocated, currency):
	rows = []
	totals = frappe._dict(
		revenue=0.0,
		material=0.0,
		additional=0.0,
		delivery=0.0,
		other=0.0,
		gross_profit=0.0,
		net_profit=0.0,
		estimation=0.0,
	)

	def add_row(**kwargs):
		revenue = flt(kwargs.get("revenue"))
		material = flt(kwargs.get("material"))
		additional = flt(kwargs.get("additional"))
		delivery = flt(kwargs.get("delivery"))
		other = flt(kwargs.get("other"))
		total_cost = material + additional + delivery + other
		estimation = flt(kwargs.get("estimation"))
		net_profit = revenue - total_cost

		rows.append(
			frappe._dict(
				project=kwargs.get("project"),
				sales_order=kwargs.get("sales_order"),
				customer=kwargs.get("customer"),
				customer_name=kwargs.get("customer_name"),
				division=kwargs.get("division"),
				transaction_date=kwargs.get("transaction_date"),
				project_status=kwargs.get("project_status"),
				revenue=revenue,
				material=material,
				additional=additional,
				delivery=delivery,
				other=other,
				gross_profit=revenue - material,
				net_profit=net_profit,
				profit_pct=flt(net_profit / revenue * 100.0, 2) if revenue else None,
				estimation=estimation,
				est_vs_actual=(
					flt((estimation - total_cost) / estimation * 100.0, 2)
					if estimation
					else None
				),
				currency=currency,
				is_unallocated=kwargs.get("is_unallocated", 0),
			)
		)

		totals.revenue += revenue
		totals.material += material
		totals.additional += additional
		totals.delivery += delivery
		totals.other += other
		totals.gross_profit += revenue - material
		totals.net_profit += net_profit
		totals.estimation += estimation

	for so in get_projects(filters):
		gl = gl_totals.get(so.project) or frappe._dict()
		in_period = (
			so.so_docstatus == 1
			and so.transaction_date
			and filters.from_date <= getdate(so.transaction_date) <= filters.to_date
		)
		has_activity = any(
			flt(gl.get(k)) for k in ("revenue", "material", "additional", "delivery", "other")
		)
		if not (in_period or has_activity):
			continue

		add_row(
			project=so.project,
			sales_order=so.sales_order,
			customer=so.customer,
			customer_name=so.customer_name,
			division=so.division,
			transaction_date=so.transaction_date,
			project_status=so.project_status,
			revenue=gl.revenue,
			material=gl.material,
			additional=gl.additional,
			delivery=gl.delivery,
			other=gl.other,
			estimation=so.estimation,
		)

	for entry in unallocated:
		add_row(
			project=(
				f"{_(UNALLOCATED_LABEL)} - {entry.division}"
				if entry.division
				else _(UNALLOCATED_LABEL)
			),
			division=entry.division,
			project_status=_("Unallocated"),
			revenue=entry.revenue,
			material=entry.material,
			additional=entry.additional,
			delivery=entry.delivery,
			other=entry.other,
			is_unallocated=1,
		)

	if rows:
		total_cost_all = totals.material + totals.additional + totals.delivery + totals.other
		rows.append(
			frappe._dict(
				project=_("Total"),
				revenue=totals.revenue,
				material=totals.material,
				additional=totals.additional,
				delivery=totals.delivery,
				other=totals.other,
				gross_profit=totals.gross_profit,
				net_profit=totals.net_profit,
				profit_pct=(
					flt(totals.net_profit / totals.revenue * 100.0, 2)
					if totals.revenue
					else None
				),
				estimation=totals.estimation,
				est_vs_actual=(
					flt(
						(totals.estimation - total_cost_all) / totals.estimation * 100.0, 2
					)
					if totals.estimation
					else None
				),
				currency=currency,
				is_total=1,
			)
		)

	return rows


def get_columns(filters):
	return [
		{
			"label": _("Project #"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 280,
		},
		{
			"label": _("SO #"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 170,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120,
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 240,
		},
		{
			"label": _("Division"),
			"fieldname": "division",
			"fieldtype": "Link",
			"options": "Division",
			"width": 120,
		},
		{
			"label": _("SO Date"),
			"fieldname": "transaction_date",
			"fieldtype": "Date",
			"width": 115,
		},
		{
			"label": _("Project Status"),
			"fieldname": "project_status",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Revenue"),
			"fieldname": "revenue",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Material Cost (COGS)"),
			"fieldname": "material",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Additional Cost (COS)"),
			"fieldname": "additional",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Delivery & Dist. Charges"),
			"fieldname": "delivery",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Other Costs"),
			"fieldname": "other",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110,
		},
		{
			"label": _("Gross Profit"),
			"fieldname": "gross_profit",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Net Profit"),
			"fieldname": "net_profit",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Profit %"),
			"fieldname": "profit_pct",
			"fieldtype": "Percent",
			"width": 90,
		},
		{
			"label": _("Estimation"),
			"fieldname": "estimation",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Est. vs Actual %"),
			"fieldname": "est_vs_actual",
			"fieldtype": "Percent",
			"width": 110,
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]
