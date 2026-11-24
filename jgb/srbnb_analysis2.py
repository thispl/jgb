"""Follow-up: why does the SRNB (2220) balance not clear?

Run: bench --site erp.jgbksa.com execute jgb.srbnb_analysis2.run
"""

import frappe

TARGET = "2220 - Stock Received But Not Billed - JGB"


def q(sql, *args):
	return frappe.db.sql(sql, args, as_dict=True)


def run():
	print("\n=== A. Receipts not yet billed (legitimately sitting in SRNB) ===")
	for r in q(
		"""SELECT gle.voucher_no, SUM(gle.credit) cr, pr.status, pr.per_billed,
		          pr.posting_date, pr.supplier
		   FROM `tabGL Entry` gle
		   JOIN `tabPurchase Receipt` pr ON pr.name = gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Receipt'
		     AND pr.status != 'Cancelled' AND IFNULL(pr.per_billed,0) < 100
		   GROUP BY gle.voucher_no ORDER BY cr DESC""",
		TARGET,
	):
		print(
			f"  {r.voucher_no:22s} {str(r.posting_date):10s} credit {r.cr:>14,.2f}"
			f"  billed {r.per_billed:6.2f}%  {r.status:14s} {r.supplier or ''}"
		)

	print("\n=== B. Fully-billed receipts still holding a SRNB credit (clearing missing) ===")
	rows = q(
		"""SELECT gle.voucher_no, SUM(gle.credit) cr, pr.per_billed, pr.posting_date, pr.supplier
		   FROM `tabGL Entry` gle
		   JOIN `tabPurchase Receipt` pr ON pr.name = gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Receipt'
		     AND pr.status != 'Cancelled' AND IFNULL(pr.per_billed,0) >= 100
		   GROUP BY gle.voucher_no ORDER BY cr DESC""",
		TARGET,
	)
	print(f"  count={len(rows)} total credit={sum(r.cr or 0 for r in rows):,.2f}")
	for r in rows[:20]:
		print(f"  {r.voucher_no:22s} {str(r.posting_date):10s} credit {r.cr:>14,.2f} billed {r.per_billed:6.2f}% {r.supplier or ''}")

	print("\n=== C. Purchase Invoices debiting SRNB with no linked receipt ===")
	rows = q(
		"""SELECT gle.voucher_no, SUM(gle.debit) dr, pi.posting_date, pi.supplier, pi.grand_total,
		          pi.is_return,
		          (SELECT COUNT(*) FROM `tabPurchase Invoice Item` pii
		            WHERE pii.parent=gle.voucher_no AND IFNULL(pii.purchase_receipt,'')!='') linked_rows
		   FROM `tabGL Entry` gle
		   JOIN `tabPurchase Invoice` pi ON pi.name = gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Invoice'
		     AND gle.debit > 0
		   GROUP BY gle.voucher_no ORDER BY dr DESC""",
		TARGET,
	)
	no_link = [r for r in rows if not r.linked_rows]
	print(f"  PIs debiting SRNB: {len(rows)}, debit {sum(r.dr or 0 for r in rows):,.2f}")
	print(f"  of which with NO receipt-linked row: {len(no_link)}, debit {sum(r.dr or 0 for r in no_link):,.2f}")
	for r in no_link[:20]:
		print(f"  {r.voucher_no:22s} {str(r.posting_date):10s} debit {r.dr:>14,.2f} return={r.is_return} {r.supplier or ''}")

	print("\n=== D. Journal Entries on SRNB (details) ===")
	jes = q(
		"""SELECT DISTINCT voucher_no FROM `tabGL Entry`
		   WHERE account=%s AND is_cancelled=0 AND voucher_type='Journal Entry'""",
		TARGET,
	)
	for j in jes:
		doc = frappe.get_doc("Journal Entry", j.voucher_no)
		gle = frappe.db.sql(
			"SELECT debit-credit net FROM `tabGL Entry` WHERE account=%s AND voucher_no=%s AND is_cancelled=0",
			(TARGET, j.voucher_no),
		)[0][0]
		print(f"\n  {doc.name}  {doc.posting_date}  docstatus={doc.docstatus}  net {gle:,.2f}")
		print(f"    remark: {doc.user_remark or doc.remark or ''}")
		print(f"    owner={doc.owner} created={doc.creation}")
		for row in doc.accounts:
			print(
				f"      Dr {row.debit_in_account_currency:>14,.2f} Cr {row.credit_in_account_currency:>14,.2f}"
				f"  {row.account}  cc={row.cost_center or ''}  party={row.party or ''}"
			)

	print("\n=== E. Reconciliation identity ===")
	for label, sql, args in [
		("PR credits", "SELECT SUM(credit) FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0 AND voucher_type='Purchase Receipt'", (TARGET,)),
		("PI debits", "SELECT SUM(debit) FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0 AND voucher_type='Purchase Invoice'", (TARGET,)),
		("PI credits", "SELECT SUM(credit) FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0 AND voucher_type='Purchase Invoice'", (TARGET,)),
		("JE net", "SELECT SUM(debit-credit) FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0 AND voucher_type='Journal Entry'", (TARGET,)),
		("TOTAL net", "SELECT SUM(debit-credit) FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0", (TARGET,)),
	]:
		print(f"  {label:12s} {frappe.db.sql(sql, args)[0][0]:>18,.2f}")
