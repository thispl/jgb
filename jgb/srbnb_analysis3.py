"""SRNB (2220) balance decomposition - final numbers."""

import frappe

T = "2220 - Stock Received But Not Billed - JGB"


def s(sql, *a):
	return frappe.db.sql(sql, a)[0][0]


def run():
	pr = s("SELECT SUM(credit) FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0 AND voucher_type='Purchase Receipt'", T)
	pi = s("SELECT SUM(debit) FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0 AND voucher_type='Purchase Invoice'", T)
	je = s("SELECT SUM(debit-credit) FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0 AND voucher_type='Journal Entry'", T)
	tot = s("SELECT SUM(debit-credit) FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0", T)
	print(f"PR credits        {pr:>18,.2f}")
	print(f"PI debits         {pi:>18,.2f}")
	print(f"JE net            {je:>18,.2f}")
	print(f"TOTAL net         {tot:>18,.2f}")

	unb = frappe.db.sql(
		"""SELECT COUNT(*) n, SUM(gle.credit) cr
		   FROM `tabGL Entry` gle JOIN `tabPurchase Receipt` pr ON pr.name=gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Receipt'
		     AND pr.status!='Cancelled' AND IFNULL(pr.per_billed,0)<100""",
		T, as_dict=True)[0]
	unb_est = frappe.db.sql(
		"""SELECT SUM(gle.credit * (100-IFNULL(pr.per_billed,0))/100) est
		   FROM `tabGL Entry` gle JOIN `tabPurchase Receipt` pr ON pr.name=gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Receipt'
		     AND pr.status!='Cancelled' AND IFNULL(pr.per_billed,0)<100""",
		T)[0][0]
	print(f"\nUnbilled receipts: {unb.n} PRs, credit {unb.cr:,.2f}, unbilled portion ~{unb_est:,.2f}")

	nolink = s(
		"""SELECT SUM(gle.debit) FROM `tabGL Entry` gle
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Invoice'
		     AND gle.debit>0 AND NOT EXISTS (
		       SELECT 1 FROM `tabPurchase Invoice Item` pii
		       WHERE pii.parent=gle.voucher_no AND IFNULL(pii.purchase_receipt,'')!='')""",
		T)
	print(f"PI debits with NO receipt link: {nolink:,.2f}")

	print("\nJE nets (SUM per voucher):")
	for r in frappe.db.sql(
		"""SELECT voucher_no, posting_date, SUM(debit-credit) net, COUNT(*) n
		   FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0 AND voucher_type='Journal Entry'
		   GROUP BY voucher_no, posting_date ORDER BY net""",
		T, as_dict=True):
		print(f"  {r.voucher_no:22s} {str(r.posting_date):10s} net {r.net:>16,.2f} (n={r.n})")

	print("\nTop 10 largest single GL rows on SRNB:")
	for r in frappe.db.sql(
		"""SELECT voucher_type, voucher_no, posting_date, debit, credit, debit-credit net, remarks
		   FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0
		   ORDER BY ABS(debit-credit) DESC LIMIT 10""",
		T, as_dict=True):
		print(f"  {r.voucher_type:18s} {r.voucher_no:22s} {str(r.posting_date):10s} Dr {r.debit:>13,.2f} Cr {r.credit:>13,.2f} net {r.net:>14,.2f}  {r.remarks or ''}")
