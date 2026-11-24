"""Analyse the SRNB (2220) balance: what is it made of, and why does it not clear?

Run: bench --site erp.jgbksa.com execute jgb.srbnb_analysis.run
"""

import frappe

TARGET = "2220 - Stock Received But Not Billed - JGB"


def q(sql, *args):
	return frappe.db.sql(sql, args, as_dict=True)


def run():
	print("\n=== 1. By voucher type (is_cancelled=0, excl. Period Closing Voucher) ===")
	for r in q(
		"""SELECT voucher_type, COUNT(*) cnt, SUM(debit) dr, SUM(credit) cr,
		          SUM(debit-credit) net, MIN(posting_date) first, MAX(posting_date) last
		   FROM `tabGL Entry`
		   WHERE account=%s AND is_cancelled=0 AND voucher_type!='Period Closing Voucher'
		   GROUP BY voucher_type ORDER BY net""",
		TARGET,
	):
		print(
			f"  {r.voucher_type:22s} n={r.cnt:5d}  Dr {r.dr:>16,.2f}  Cr {r.cr:>16,.2f}"
			f"  net {r.net:>16,.2f}   {r.first} .. {r.last}"
		)

	print("\n=== 2. Cancelled entries still on the account ===")
	for r in q(
		"""SELECT voucher_type, COUNT(*) cnt, SUM(debit-credit) net
		   FROM `tabGL Entry` WHERE account=%s AND is_cancelled=1
		   GROUP BY voucher_type""",
		TARGET,
	):
		print(f"  {r.voucher_type:22s} n={r.cnt:5d}  net {r.net:>16,.2f}")

	print("\n=== 3. Monthly movement (is_cancelled=0) ===")
	for r in q(
		"""SELECT DATE_FORMAT(posting_date, '%%Y-%%m') m, SUM(debit) dr, SUM(credit) cr,
		          SUM(debit-credit) net
		   FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0
		   GROUP BY m ORDER BY m""",
		TARGET,
	):
		print(f"  {r.m}  Dr {r.dr:>16,.2f}  Cr {r.cr:>16,.2f}  net {r.net:>16,.2f}")

	print("\n=== 4. Purchase Receipt credits vs their billed status ===")
	pr = q(
		"""SELECT gle.voucher_no, SUM(gle.credit) cr, pr.status, pr.per_billed,
		          pr.grand_total, pr.posting_date, pr.supplier
		   FROM `tabGL Entry` gle
		   LEFT JOIN `tabPurchase Receipt` pr ON pr.name = gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Receipt'
		   GROUP BY gle.voucher_no ORDER BY cr DESC""",
		TARGET,
	)
	tot = sum(r.cr or 0 for r in pr)
	print(f"  PRs crediting SRNB: {len(pr)}, total credit {tot:,.2f}")
	buckets = {}
	for r in pr:
		pb = float(r.per_billed or 0)
		key = "cancelled" if r.status == "Cancelled" else ("not billed (0%)" if pb == 0 else ("partly billed" if pb < 100 else "fully billed"))
		b = buckets.setdefault(key, [0, 0.0])
		b[0] += 1
		b[1] += r.cr or 0
	for k, v in sorted(buckets.items(), key=lambda x: -x[1][1]):
		print(f"    {k:18s} n={v[0]:4d}  credit {v[1]:>16,.2f}")
	print("  Top 10 PRs by credit:")
	for r in pr[:10]:
		print(
			f"    {r.voucher_no:22s} {str(r.posting_date):10s} {r.supplier or '?'[:28]:28s}"
			f" credit {r.cr:>14,.2f}  billed {r.per_billed}%  status={r.status}"
		)

	print("\n=== 5. Purchase Invoice debits to SRNB (the clearing leg) ===")
	pi = q(
		"""SELECT gle.voucher_no, SUM(gle.debit) dr, SUM(gle.credit) cr,
		          pi.status, pi.posting_date, pi.supplier, pi.grand_total
		   FROM `tabGL Entry` gle
		   LEFT JOIN `tabPurchase Invoice` pi ON pi.name = gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Invoice'
		   GROUP BY gle.voucher_no ORDER BY dr DESC""",
		TARGET,
	)
	print(f"  PIs touching SRNB: {len(pi)}, debit {sum(r.dr or 0 for r in pi):,.2f}, credit {sum(r.cr or 0 for r in pi):,.2f}")

	print("\n=== 6. Stock Entry / Journal Entry / Landed Cost / other ===")
	for r in q(
		"""SELECT voucher_type, voucher_no, posting_date, SUM(debit-credit) net, COUNT(*) n
		   FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0
		     AND voucher_type NOT IN ('Purchase Receipt','Purchase Invoice','Period Closing Voucher')
		   GROUP BY voucher_type, voucher_no ORDER BY ABS(SUM(debit-credit)) DESC LIMIT 25""",
		TARGET,
	):
		print(f"  {r.voucher_type:24s} {r.voucher_no:24s} {str(r.posting_date):10s} net {r.net:>14,.2f} (n={r.n})")

	print("\n=== 7. Receipts with NO Purchase Invoice clearing them ===")
	# PR credits not offset by a PI debit for the same PO/PR in the same period
	unbilled = q(
		"""SELECT gle.voucher_no, SUM(gle.credit) cr, pr.per_billed, pr.status, pr.posting_date
		   FROM `tabGL Entry` gle
		   JOIN `tabPurchase Receipt` pr ON pr.name = gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Receipt'
		     AND pr.status='Submitted' AND IFNULL(pr.per_billed,0) < 100
		   GROUP BY gle.voucher_no ORDER BY cr DESC""",
		TARGET,
	)
	print(f"  Submitted PRs not fully billed: {len(unbilled)}, credit {sum(r.cr or 0 for r in unbilled):,.2f}")
	for r in unbilled[:15]:
		print(f"    {r.voucher_no:22s} {str(r.posting_date):10s} credit {r.cr:>14,.2f} billed {r.per_billed}%")

	print("\n=== 8. PRs fully billed but SRNB not cleared (PI posted elsewhere) ===")
	suspect = q(
		"""SELECT gle.voucher_no, SUM(gle.credit) cr, pr.per_billed, pr.posting_date
		   FROM `tabGL Entry` gle
		   JOIN `tabPurchase Receipt` pr ON pr.name = gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Receipt'
		     AND pr.status='Submitted' AND IFNULL(pr.per_billed,0) >= 100
		   GROUP BY gle.voucher_no ORDER BY cr DESC""",
		TARGET,
	)
	print(f"  Fully-billed PRs still holding a SRNB credit: {len(suspect)}, credit {sum(r.cr or 0 for r in suspect):,.2f}")
	for r in suspect[:15]:
		print(f"    {r.voucher_no:22s} {str(r.posting_date):10s} credit {r.cr:>14,.2f} billed {r.per_billed}%")
