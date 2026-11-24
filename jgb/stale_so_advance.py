"""One-off: clear stale Sales Order.advance_paid values.

advance_paid is only recalculated when a Payment Entry / Journal Entry is
submitted or cancelled against the order: PaymentEntry.update_advance_paid()
walks its *current* references and calls set_total_advance_paid() only for
doctypes in `advance_payment_doctypes` (Sales Order, Purchase Order, ...).
When a PE is re-pointed at another doctype (e.g. an Advance Sales Invoice)
before being cancelled/deleted, the order is skipped and keeps the old value
forever - e.g. SOJGBKSA3412 kept 24,535 from deleted PE JGB-HVA-PE-2026-00854.

Run:
	bench --site erp.jgbksa.com execute jgb.stale_so_advance.run            # audit
	bench --site erp.jgbksa.com execute jgb.stale_so_advance.run --kwargs "{'apply': 1}"
"""

import frappe
from frappe.utils import flt

BACKUP = "zbackup_so_advance_paid"


def _expected_advance(so):
	# None when the order has no Advance Payment Ledger Entry rows at all
	return flt(so.calculate_total_advance_from_ledger()[0].amount, so.precision("advance_paid"))


def _mismatches(names=None):
	rows = frappe.db.sql(
		"""SELECT name, advance_paid, modified FROM `tabSales Order`
		   WHERE docstatus = 1 AND advance_paid != 0""",
		as_dict=True,
	)
	if names:
		names = names.split(",") if isinstance(names, str) else names
		rows = [r for r in rows if r.name in names]
	out = []
	for r in rows:
		expected = _expected_advance(frappe.get_doc("Sales Order", r.name))
		if flt(r.advance_paid, 2) != flt(expected, 2):
			out.append((r, expected))
	return out


def run(apply=0, names=None):
	bad = _mismatches(names)
	print(f"{len(bad)} submitted Sales Orders have advance_paid != ledger")
	for r, expected in bad:
		print(f"  {r.name:22s} stored {flt(r.advance_paid):>14,.2f}  ledger {expected:>14,.2f}  modified {r.modified}")

	if not bad:
		return
	if not int(apply):
		print('\nAudit only. Re-run with --kwargs "{\'apply\': 1}" to fix.')
		return

	names = ", ".join(frappe.db.escape(r.name) for r, _ in bad)
	frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{BACKUP}`")
	frappe.db.sql_ddl(
		f"CREATE TABLE `{BACKUP}` AS SELECT name, advance_paid, modified, modified_by "
		f"FROM `tabSales Order` WHERE name IN ({names})"
	)
	print(f"backup -> {BACKUP}")

	for r, _ in bad:
		frappe.get_doc("Sales Order", r.name).set_total_advance_paid()
	frappe.db.commit()

	for r, _ in bad:
		print(f"  {r.name}: {flt(r.advance_paid):,.2f} -> {flt(frappe.db.get_value('Sales Order', r.name, 'advance_paid')):,.2f}")

	left = _mismatches(names)
	print(f"verify: {len(left)} mismatches left")
