# Copyright (c) 2026
# Backfill the "Sales Team" (Sales Person) child table on Quotation, Sales Order
# and Sales Invoice from the custom field `custom_sales_person`.
#
# The custom field stores the sales person's user email, so the value is
# resolved to a Sales Person record via: User(email) -> Employee(user_id)
# -> Sales Person(employee).
#
# Notes:
# - Quotation has no `sales_team` field in ERPNext v15, so a Custom Field
#   is created for it before backfilling.
# - Cancelled documents (docstatus = 2) are skipped.
# - Documents where the custom field is empty or cannot be mapped to an
#   active Sales Person are skipped and reported.
#
# Run manually:
#   bench --site erp.jgbksa.com execute jgb.patches.backfill_sales_team.execute
#   bench --site erp.jgbksa.com execute jgb.patches.backfill_sales_team.execute kwargs="{'dry_run': True}"

import frappe
from frappe.utils import flt

SALES_DOCTYPES = ("Quotation", "Sales Order", "Sales Invoice")
PARENTFIELD = "sales_team"
COMMIT_EVERY = 200


def execute(dry_run=False):
	if not dry_run:
		ensure_quotation_sales_team_field()

	email_map = build_email_to_sales_person_map()
	stats = {}

	for doctype in SALES_DOCTYPES:
		stats[doctype] = backfill_doctype(doctype, email_map, dry_run=dry_run)

	print_summary(stats, email_map, dry_run)


def ensure_quotation_sales_team_field():
	"""Quotation (ERPNext v15) has no sales_team Table field; add it as a Custom Field."""
	if frappe.db.exists(
		"Custom Field", {"dt": "Quotation", "fieldname": PARENTFIELD}
	):
		return

	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "Quotation",
			"fieldname": PARENTFIELD,
			"label": "Sales Team",
			"fieldtype": "Table",
			"options": "Sales Team",
			"insert_after": "custom_name_of_sales_person",
		}
	).save()
	frappe.clear_cache(doctype="Quotation")
	print("Created Custom Field 'sales_team' (Table -> Sales Team) on Quotation")


def build_email_to_sales_person_map():
	"""Map user email -> Sales Person name via Employee."""
	emails = set()
	for doctype in SALES_DOCTYPES:
		rows = frappe.get_all(
			doctype,
			filters={"custom_sales_person": ("is", "set")},
			pluck="custom_sales_person",
			distinct=True,
		)
		emails.update(e for e in rows if e)

	if not emails:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT u.name AS email, sp.name AS sales_person
		FROM `tabUser` u
		JOIN `tabEmployee` emp ON emp.user_id = u.name
		JOIN `tabSales Person` sp ON sp.employee = emp.name
		WHERE u.name IN %(emails)s
		""",
		{"emails": tuple(emails)},
		as_dict=1,
	)

	email_map = {}
	for row in rows:
		if row.email in email_map and email_map[row.email] != row.sales_person:
			print(
				f"WARNING: multiple Sales Persons for {row.email}, "
				f"keeping '{email_map[row.email]}' (ignoring '{row.sales_person}')"
			)
			continue
		email_map[row.email] = row.sales_person

	unmapped = sorted(emails - set(email_map))
	if unmapped:
		print(f"Unmappable emails (no Employee/Sales Person link): {', '.join(unmapped)}")

	return email_map


def backfill_doctype(doctype, email_map, dry_run):
	"""Insert a 100% Sales Team row on documents missing one."""
	if not frappe.get_meta(doctype).get_field(PARENTFIELD):
		print(f"Skipping {doctype}: no '{PARENTFIELD}' field")
		return {}

	docs = frappe.db.sql(
		f"""
		SELECT name, docstatus, custom_sales_person, base_net_total
		FROM `tab{doctype}`
		WHERE custom_sales_person IS NOT NULL AND custom_sales_person != ''
		  AND docstatus < 2
		  AND NOT EXISTS (
			SELECT 1 FROM `tabSales Team` st
			WHERE st.parenttype = %(doctype)s AND st.parent = `tab{doctype}`.name
		  )
		""",
		{"doctype": doctype},
		as_dict=1,
	)

	stats = {"candidates": len(docs), "backfilled": 0, "unmapped": 0}
	unmapped_emails = set()

	for i, doc in enumerate(docs, 1):
		sales_person = email_map.get(doc.custom_sales_person)
		if not sales_person:
			stats["unmapped"] += 1
			unmapped_emails.add(doc.custom_sales_person)
			continue

		if not dry_run:
			child = frappe.new_doc("Sales Team")
			child.update(
				{
					"sales_person": sales_person,
					"allocated_percentage": 100,
					"allocated_amount": flt(doc.base_net_total),
					"parent": doc.name,
					"parenttype": doctype,
					"parentfield": PARENTFIELD,
					"idx": 1,
					"docstatus": doc.docstatus,
				}
			)
			child.db_insert()

		stats["backfilled"] += 1
		if not dry_run and i % COMMIT_EVERY == 0:
			frappe.db.commit()

	if not dry_run:
		frappe.db.commit()

	if unmapped_emails:
		stats["unmapped_emails"] = sorted(unmapped_emails)

	return stats


def print_summary(stats, email_map, dry_run):
	mode = "DRY RUN - nothing written" if dry_run else "DONE"
	print(f"\n=== Backfill summary ({mode}) ===")
	for doctype, s in stats.items():
		print(
			f"{doctype}: candidates={s['candidates']}, "
			f"backfilled={s['backfilled']}, unmapped={s['unmapped']}"
		)
		for email in s.get("unmapped_emails", []):
			print(f"  unmapped: {email}")
