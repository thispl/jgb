# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

# Division -> Cost Center propagation.
#
# Division Account Details (child table on Division) maps each division to its
# cost center. Item rows and GL Entries were defaulting to the company default
# cost center ("Main - JGB"), so division income/costs pooled into Main.
# - apply_division_cost_center: validate hook that stamps the division's cost
#   center on the document header and item rows (only where the value is blank
#   or the company default, so deliberate per-row overrides survive).
#   Also wired to before_update_after_submit: cost_center is allow_on_submit on
#   SI/PI items and on the tax tables, and Frappe does NOT run `validate` for
#   the update_after_submit action (see Document.run_before_save_methods), so a
#   user saving a submitted document would otherwise write the stale browser
#   value (the company default) straight back over the division cost center.
# - sync_gl_cost_center: on_update_after_submit companion that realigns the
#   GL Entries of that one voucher, since ERPNext does not repost GL when an
#   allow_on_submit cost_center changes.
# - backfill_item_cost_centers: repairs the cost_center on child rows of
#   already-submitted documents. This matters because stock reposting /
#   cancel-amend regenerates GL Entries from the child rows, which would
#   otherwise silently revert a GL-only fix back to the default cost center.
#   Always run this BEFORE backfill_gl_cost_center.
# - backfill_gl_cost_center: rewrite of GL Entry.cost_center for already
#   submitted vouchers, same mechanism ERPNext uses on account merge.
#   Journal Entry is excluded on purpose: JE rows carry per-row cost centers
#   set deliberately by accountants (see report_je_cost_center_review).

import frappe
from frappe.utils import now_datetime

# vouchers that carry custom_division and post GL (or propagate to GL docs)
BACKFILL_VOUCHER_TYPES = (
	"Sales Invoice",
	"Purchase Invoice",
	"Purchase Receipt",
	"Delivery Note",
	"Payment Entry",
	"Expense Claim",
)

# parent doctypes whose submitted child rows get repaired by
# backfill_item_cost_centers. Child tables are discovered from the meta, so
# both item and tax rows (which also post GL) are covered.
ITEM_BACKFILL_DOCTYPES = (
	"Sales Order",
	"Sales Invoice",
	"Delivery Note",
	"Purchase Order",
	"Purchase Invoice",
	"Purchase Receipt",
)


def division_cost_center(division, company):
	"""Division -> cost center via Division Account Details."""
	if not division:
		return None
	return frappe.db.get_value(
		"Division Account Details", {"parent": division, "company": company}, "cost_center"
	)


def delivery_charges_account(division, company):
	"""Division -> expense account for delivery charges allocated out of a Logistics Request.

	Seeded by the add_delivery_charges_account patch; blank means "no mapping",
	and the caller falls back to the account it would have used before.
	"""
	if not division:
		return None
	return frappe.db.get_value(
		"Division Account Details",
		{"parent": division, "company": company},
		"delivery_charges_account",
	)


def apply_division_cost_center(doc, method=None):
	"""Stamp the division's cost center on header + item rows.

	Only fills rows whose cost center is blank or the company default (the
	auto-filled value); a deliberately chosen other cost center is kept.

	When running as before_update_after_submit, only allow_on_submit fields
	may be written -- Frappe's validate_update_after_submit rejects any other
	change (e.g. the SO/DN/PR header cost_center is not allow_on_submit).
	"""
	cc = division_cost_center(doc.get("custom_division"), doc.get("company"))
	if not cc:
		return

	default_cc = frappe.get_cached_value("Company", doc.company, "cost_center")
	after_submit = method == "before_update_after_submit"

	def _cc_writable(meta):
		df = meta.get_field("cost_center")
		return df and (not after_submit or df.allow_on_submit)

	if _cc_writable(doc.meta) and (
		not doc.get("cost_center") or doc.cost_center == default_cc
	):
		doc.cost_center = cc

	# every child table that carries cost_center (items AND taxes -- both post GL)
	for df in doc.meta.get_table_fields():
		if not _cc_writable(frappe.get_meta(df.options)):
			continue
		for row in doc.get(df.fieldname) or []:
			if not row.get("cost_center") or row.cost_center == default_cc:
				row.cost_center = cc


def sync_gl_cost_center(doc, method=None):
	"""Realign this voucher's GL Entries with the division cost center.

	Needed because cost_center is allow_on_submit: ERPNext lets it change on a
	submitted document without reposting the ledger. Only GL rows still on the
	company default are moved, so deliberate per-row cost centers are kept.
	"""
	cc = division_cost_center(doc.get("custom_division"), doc.get("company"))
	if not cc:
		return
	default_cc = frappe.get_cached_value("Company", doc.company, "cost_center")
	if cc == default_cc:
		return

	frappe.db.sql(
		"""
		update `tabGL Entry`
		set cost_center = %(cc)s, modified = %(now)s
		where voucher_type = %(vt)s and voucher_no = %(vno)s
			and is_cancelled = 0
			and (cost_center = %(default)s or cost_center is null or cost_center = '')
		""",
		{
			"cc": cc,
			"vt": doc.doctype,
			"vno": doc.name,
			"default": default_cc,
			"now": now_datetime(),
		},
	)


def backfill_gl_cost_center(company, dry_run=True):
	"""Rewrite GL Entry cost_center for submitted vouchers that carry a division.

	Only rows tagged with the company default cost center or blank are moved;
	rows deliberately tagged to another cost center are left untouched. Call
	with dry_run=False to apply. A snapshot of the affected rows is written to
	`zbackup_gle_cost_center` before any update.
	"""
	default_cc = frappe.get_cached_value("Company", company, "cost_center")
	divisions = {
		r.parent: r.cost_center
		for r in frappe.get_all(
			"Division Account Details",
			filters={"company": company},
			fields=["parent", "cost_center"],
		)
		if r.cost_center and r.cost_center != default_cc
	}
	if not divisions:
		return {"updated": 0, "note": "no division cost centers mapped"}

	report = {}
	for voucher_type in BACKFILL_VOUCHER_TYPES:
		table = f"tab{voucher_type}"
		vouchers = frappe.db.sql(
			f"""
			select name, custom_division from `{table}`
			where company = %(company)s and docstatus = 1
				and custom_division in %(divs)s
			""",
			{"company": company, "divs": tuple(divisions)},
			as_dict=True,
		)
		for v in vouchers:
			target = divisions[v.custom_division]
			params = {
				"cc": target,
				"vt": voucher_type,
				"vno": v.name,
				"default": default_cc,
				"now": now_datetime(),
			}
			# count first -- frappe.db.sql returns () for UPDATE, not a row count
			n = frappe.db.sql(
				"""
				select count(*) from `tabGL Entry`
				where voucher_type = %(vt)s and voucher_no = %(vno)s
					and is_cancelled = 0
					and (cost_center = %(default)s or cost_center is null or cost_center = '')
				""",
				params,
			)[0][0]
			if n and not dry_run:
				frappe.db.sql(
					"""
					update `tabGL Entry`
					set cost_center = %(cc)s, modified = %(now)s
					where voucher_type = %(vt)s and voucher_no = %(vno)s
						and is_cancelled = 0
						and (cost_center = %(default)s or cost_center is null or cost_center = '')
					""",
					params,
				)
			if n:
				report.setdefault(voucher_type, {"vouchers": 0, "rows": 0})
				report[voucher_type]["vouchers"] += 1
				report[voucher_type]["rows"] += n
	return {"dry_run": dry_run, "default_cc": default_cc, "by_voucher_type": report}


def snapshot_gl_cost_center(company):
	"""Save current cost_center of every non-cancelled GL row of the company."""
	frappe.db.sql(
		"""
		create table if not exists `zbackup_gle_cost_center` (
			gle_name varchar(140) primary key,
			cost_center varchar(140),
			voucher_type varchar(140),
			voucher_no varchar(140),
			account varchar(140),
			backed_up_at datetime
		)
		"""
	)
	frappe.db.sql(
		"""
		insert ignore into `zbackup_gle_cost_center`
		select name, cost_center, voucher_type, voucher_no, account, %(now)s
		from `tabGL Entry` where company = %(company)s and is_cancelled = 0
		""",
		{"now": now_datetime(), "company": company},
	)
	return frappe.db.sql("select count(*) from `zbackup_gle_cost_center`")[0][0]


def _cost_center_child_tables(parent):
	"""Child doctypes of `parent` that carry a cost_center field."""
	return [
		df.options
		for df in frappe.get_meta(parent).get_table_fields()
		if frappe.get_meta(df.options).has_field("cost_center")
	]


def backfill_item_cost_centers(company, dry_run=True):
	"""Repair cost_center on child rows of submitted division documents.

	Stock reposting and cancel/amend rebuild GL Entries from these rows, so a
	GL-only fix silently reverts. Only rows holding the company default cost
	center (or nothing) are moved; a deliberately chosen other cost center is
	left alone and surfaces via report_cross_division_items instead.
	"""
	default_cc = frappe.get_cached_value("Company", company, "cost_center")
	divisions = {
		r.parent: r.cost_center
		for r in frappe.get_all(
			"Division Account Details",
			filters={"company": company},
			fields=["parent", "cost_center"],
		)
		if r.cost_center and r.cost_center != default_cc
	}
	if not divisions:
		return {"updated": 0, "note": "no division cost centers mapped"}

	if not dry_run:
		snapshot_item_cost_centers(company)

	report = {}
	for parent in ITEM_BACKFILL_DOCTYPES:
		if not frappe.get_meta(parent).has_field("custom_division"):
			continue
		for child in _cost_center_child_tables(parent):
			for division, target in divisions.items():
				params = {
					"company": company,
					"division": division,
					"cc": target,
					"default": default_cc,
					"now": now_datetime(),
				}
				where = f"""
					from `tab{child}` c join `tab{parent}` p on p.name = c.parent
					where p.company = %(company)s and p.docstatus = 1
						and p.custom_division = %(division)s
						and (c.cost_center = %(default)s or c.cost_center is null
						     or c.cost_center = '')
				"""
				# count first -- frappe.db.sql returns () for UPDATE, not a row count
				n = frappe.db.sql(f"select count(*) {where}", params)[0][0]
				if n and not dry_run:
					frappe.db.sql(
						f"""
						update `tab{child}` c join `tab{parent}` p on p.name = c.parent
						set c.cost_center = %(cc)s, c.modified = %(now)s
						where p.company = %(company)s and p.docstatus = 1
							and p.custom_division = %(division)s
							and (c.cost_center = %(default)s or c.cost_center is null
							     or c.cost_center = '')
						""",
						params,
					)
				if n:
					key = f"{parent} / {child}"
					report[key] = report.get(key, 0) + n

	return {
		"dry_run": dry_run,
		"default_cc": default_cc,
		"by_table": report,
		"total_rows": sum(report.values()),
	}


def snapshot_item_cost_centers(company):
	"""Snapshot child-row cost centers before backfill_item_cost_centers."""
	frappe.db.sql(
		"""
		create table if not exists `zbackup_item_cost_center` (
			child_doctype varchar(140),
			child_name varchar(140),
			parenttype varchar(140),
			parent varchar(140),
			cost_center varchar(140),
			backed_up_at datetime,
			primary key (child_doctype, child_name)
		)
		"""
	)
	total = 0
	for parent in ITEM_BACKFILL_DOCTYPES:
		if not frappe.get_meta(parent).has_field("custom_division"):
			continue
		for child in _cost_center_child_tables(parent):
			frappe.db.sql(
				f"""
				insert ignore into `zbackup_item_cost_center`
				select %(child)s, c.name, %(parent)s, p.name, c.cost_center, %(now)s
				from `tab{child}` c join `tab{parent}` p on p.name = c.parent
				where p.company = %(company)s and p.docstatus = 1
				""",
				{"child": child, "parent": parent, "company": company, "now": now_datetime()},
			)
			total += 1
	return frappe.db.sql("select count(*) from `zbackup_item_cost_center`")[0][0]


def report_je_cost_center_review(company):
	"""Journal Entries whose division implies a cost center other than the one used.

	Returned for human review -- these are NOT auto-changed, because JE cost
	centers are set deliberately (Journal Entry requires custom_cost_center).
	"""
	default_cc = frappe.get_cached_value("Company", company, "cost_center")
	return frappe.db.sql(
		"""
		select je.name, je.posting_date, je.custom_division,
			ifnull(je.custom_cost_center, '') as je_cost_center,
			je.total_debit, ifnull(je.user_remark, '') as remark,
			je.voucher_type, count(gle.name) as gl_rows,
			group_concat(distinct gle.account order by gle.account) as accounts
		from `tabJournal Entry` je
			join `tabGL Entry` gle on gle.voucher_no = je.name
				and gle.voucher_type = 'Journal Entry' and gle.is_cancelled = 0
		join `tabDivision Account Details` dad
			on dad.parent = je.custom_division and dad.company = je.company
		where je.company = %(company)s and je.docstatus = 1
			and je.custom_division is not null and je.custom_division != ''
			and dad.cost_center != %(default)s
			and (gle.cost_center = %(default)s or gle.cost_center is null
			     or gle.cost_center = '')
		group by je.name
		order by je.total_debit desc
		""",
		{"company": company, "default": default_cc},
		as_dict=True,
	)


def report_cross_division_items(company, include_shared=False):
	"""Child rows whose cost center belongs to a different division than the doc.

	Documents on a shared division (one that maps to the company default cost
	center, i.e. "Common") are skipped by default: allocating a shared invoice
	across several division cost centers is deliberate and correct. Pass
	include_shared=True to list those allocations too.
	"""
	default_cc = frappe.get_cached_value("Company", company, "cost_center")
	divmap = {
		r.parent: r.cost_center
		for r in frappe.get_all(
			"Division Account Details", {"company": company}, ["parent", "cost_center"]
		)
	}
	shared = {d for d, cc in divmap.items() if cc == default_cc}
	rows = []
	for parent in ITEM_BACKFILL_DOCTYPES:
		if not frappe.get_meta(parent).has_field("custom_division"):
			continue
		date_field = (
			"posting_date" if frappe.get_meta(parent).has_field("posting_date") else "transaction_date"
		)
		for child in _cost_center_child_tables(parent):
			for r in frappe.db.sql(
				f"""
				select p.name as document, p.{date_field} as doc_date, p.custom_division,
					c.cost_center, count(*) as rows_affected
				from `tab{child}` c join `tab{parent}` p on p.name = c.parent
				where p.company = %(company)s and p.docstatus = 1
					and p.custom_division is not null and p.custom_division != ''
					and c.cost_center is not null and c.cost_center != ''
					and c.cost_center != %(default)s
				group by p.name, c.cost_center
				""",
				{"company": company, "default": default_cc},
				as_dict=True,
			):
				if r.custom_division in shared and not include_shared:
					continue
				expected = divmap.get(r.custom_division)
				if expected and r.cost_center != expected:
					r.update(
						{
							"doctype_name": parent,
							"child_table": child,
							"expected_cost_center": expected,
							"shared_division": r.custom_division in shared,
						}
					)
					rows.append(r)
	return rows
