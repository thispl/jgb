"""SRNB: are the no-receipt PI debits historical imports / late invoices?"""

import frappe

T = "2220 - Stock Received But Not Billed - JGB"


def run():
	print("PI custom fields:", [f.fieldname for f in frappe.get_meta("Purchase Invoice").fields if f.fieldname.startswith("custom_")][:30])

	rows = frappe.db.sql(
		"""SELECT gle.voucher_no, SUM(gle.debit) dr, pi.posting_date, pi.supplier,
		          pi.creation, pi.owner
		   FROM `tabGL Entry` gle JOIN `tabPurchase Invoice` pi ON pi.name=gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Invoice'
		     AND gle.debit>0 AND NOT EXISTS (
		       SELECT 1 FROM `tabPurchase Invoice Item` pii
		       WHERE pii.parent=gle.voucher_no AND IFNULL(pii.purchase_receipt,'')!='')
		   GROUP BY gle.voucher_no ORDER BY dr DESC""",
		T, as_dict=True)
	print(f"\nno-receipt-link PIs: {len(rows)}, debit {sum(r.dr for r in rows):,.2f}")

	# do PRs exist for the same purchase order?
	with_po_pr = 0
	amt_with_pr = 0
	for r in rows[:30]:
		pos = frappe.db.sql(
			"SELECT DISTINCT purchase_order FROM `tabPurchase Invoice Item` WHERE parent=%s AND IFNULL(purchase_order,'')!=''",
			r.voucher_no)
		found = 0
		for (po,) in pos:
			found += frappe.db.sql(
				"SELECT COUNT(*) FROM `tabPurchase Receipt Item` WHERE purchase_order=%s AND docstatus=1", po)[0][0]
		if found:
			with_po_pr += 1
			amt_with_pr += r.dr
		print(f"  {r.voucher_no:26s} {str(r.posting_date):10s} {r.dr:>14,.2f} PO-linked PRs={found} owner={r.owner}")
	print(f"\n  of top 30: {with_po_pr} have a submitted PR on the same PO ({amt_with_pr:,.2f})")

	# historical-import flag if present
	if frappe.db.has_column("Purchase Invoice", "custom_is_historical_import"):
		n = frappe.db.sql(
			"""SELECT COUNT(*), SUM(gle.debit) FROM `tabGL Entry` gle
			   JOIN `tabPurchase Invoice` pi ON pi.name=gle.voucher_no
			   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Invoice'
			     AND gle.debit>0 AND IFNULL(pi.custom_is_historical_import,0)=1""", T)[0]
		print(f"  historical-import PIs debiting SRNB: {n[0]}, {n[1] or 0:,.2f}")

	# creation date spread
	by_year = frappe.db.sql(
		"""SELECT YEAR(pi.creation) y, COUNT(*) n, SUM(gle.debit) dr
		   FROM `tabGL Entry` gle JOIN `tabPurchase Invoice` pi ON pi.name=gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Invoice'
		     AND gle.debit>0 AND NOT EXISTS (
		       SELECT 1 FROM `tabPurchase Invoice Item` pii
		       WHERE pii.parent=gle.voucher_no AND IFNULL(pii.purchase_receipt,'')!='')
		   GROUP BY y""", T, as_dict=True)
	print("  created-in year of no-link PIs:")
	for r in by_year:
		print(f"    {r.y}: {r.n} PIs, {r.dr:,.2f}")
