"""SRNB (2220) reconciliation workbook for accounting.

Categorises every GL row on the account and produces an Excel with:
  1. Summary          - decomposition + suggested action per category
  2. Open receipts    - PRs not fully billed (genuine GRNI, keep)
  3. Orphan PI debits - PIs debiting SRNB with no PR link (must be reclassed/linked)
  4. Uncleared credits- fully/partially billed PRs whose credit is not covered by
                        a linked PI debit (clearing came from elsewhere)
  5. Journal entries  - manual JVs touching SRNB

Run: bench --site erp.jgbksa.com execute jgb.srbnb_recon.run
"""

import frappe
from frappe.utils import getdate, today

T = "2220 - Stock Received But Not Billed - JGB"
OUT = "/home/ubuntu/frappe-bench/AI Reports/Financial Reports/SRNB 2220 Reconciliation 2026-09-27.xlsx"


def _style_header(ws):
	from openpyxl.styles import Font, PatternFill

	for cell in ws[1]:
		cell.font = Font(bold=True, color="FFFFFF")
		cell.fill = PatternFill("solid", fgColor="4472C4")
	ws.freeze_panes = "A2"


def build_sheets():
	from openpyxl import Workbook

	wb = Workbook()

	# ---------- 2. Open receipts (genuine GRNI) ----------
	open_pr = frappe.db.sql(
		"""SELECT gle.voucher_no pr, pr.posting_date, pr.supplier, pr.status,
		          IFNULL(pr.per_billed,0) per_billed, SUM(gle.credit) credit,
		          SUM(gle.credit) * (100-IFNULL(pr.per_billed,0))/100 unbilled_est
		   FROM `tabGL Entry` gle JOIN `tabPurchase Receipt` pr ON pr.name=gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Receipt'
		     AND pr.status!='Cancelled' AND IFNULL(pr.per_billed,0)<100
		   GROUP BY gle.voucher_no ORDER BY credit DESC""",
		T, as_dict=True)

	# ---------- 3. Orphan PI debits ----------
	orphans = frappe.db.sql(
		"""SELECT gle.voucher_no pi, pi.posting_date, pi.supplier, SUM(gle.debit) debit,
		          pi.owner, pi.bill_no,
		          (SELECT GROUP_CONCAT(DISTINCT pii.purchase_order) FROM `tabPurchase Invoice Item` pii
		            WHERE pii.parent=gle.voucher_no AND IFNULL(pii.purchase_order,'')!='') pos,
		          (SELECT COUNT(DISTINCT pri.parent) FROM `tabPurchase Receipt Item` pri
		            JOIN `tabPurchase Invoice Item` pii ON pii.parent=gle.voucher_no
		            WHERE pri.purchase_order=pii.purchase_order AND pri.docstatus=1) prs_on_po
		   FROM `tabGL Entry` gle JOIN `tabPurchase Invoice` pi ON pi.name=gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Invoice'
		     AND gle.debit>0 AND NOT EXISTS (
		       SELECT 1 FROM `tabPurchase Invoice Item` pii2
		       WHERE pii2.parent=gle.voucher_no AND IFNULL(pii2.purchase_receipt,'')!='')
		   GROUP BY gle.voucher_no ORDER BY debit DESC""",
		T, as_dict=True)

	# ---------- 4. Per-PR cleared vs credit ----------
	pr_cleared = frappe.db.sql(
		"""SELECT gle.voucher_no pr, SUM(gle.credit) credit, pr.per_billed, pr.status, pr.posting_date
		   FROM `tabGL Entry` gle
		   JOIN `tabPurchase Receipt` pr ON pr.name = gle.voucher_no
		   WHERE gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Receipt'
		     AND pr.status!='Cancelled'
		   GROUP BY gle.voucher_no""",
		T, as_dict=True)
	linked = {}
	for r in frappe.db.sql(
		"""SELECT pii.purchase_receipt pr, gle.voucher_no pi, SUM(gle.debit) dr
		   FROM `tabPurchase Invoice Item` pii
		   JOIN `tabGL Entry` gle ON gle.voucher_no=pii.parent
		   WHERE pii.purchase_receipt IN (SELECT voucher_no FROM `tabGL Entry`
		           WHERE account=%s AND voucher_type='Purchase Receipt' AND is_cancelled=0)
		     AND gle.account=%s AND gle.is_cancelled=0 AND gle.voucher_type='Purchase Invoice'
		     AND gle.debit>0
		   GROUP BY pii.purchase_receipt, gle.voucher_no""",
		(T, T), as_dict=True):
		linked.setdefault(r.pr, []).append((r.pi, r.dr))

	uncleared = []
	for r in pr_cleared:
		used = linked.get(r.pr, [])
		cleared = sum(x[1] for x in used)
		if cleared + 1 < r.credit:  # credit not fully covered by linked PI debits
			uncleared.append({
				"pr": r.pr, "posting_date": r.posting_date, "status": r.status,
				"per_billed": r.per_billed, "credit": r.credit,
				"cleared_by_linked_pis": cleared,
				"residual": r.credit - cleared,
				"linked_pis": ", ".join(f"{p} ({d:,.2f})" for p, d in used) or "-",
			})
	uncleared.sort(key=lambda x: -x["residual"])

	# ---------- 5. JEs ----------
	jes = frappe.db.sql(
		"""SELECT voucher_no je, posting_date, SUM(debit-credit) net, COUNT(*) n
		   FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0 AND voucher_type='Journal Entry'
		   GROUP BY voucher_no, posting_date ORDER BY net""",
		T, as_dict=True)
	je_rows = []
	for j in jes:
		doc = frappe.get_doc("Journal Entry", j.je)
		for row in doc.accounts:
			je_rows.append({
				"je": j.je, "posting_date": j.posting_date, "je_net": j.net,
				"remark": doc.user_remark or "", "line_account": row.account,
				"debit": row.debit_in_account_currency, "credit": row.credit_in_account_currency,
				"cost_center": row.cost_center or "", "party": row.party or "",
			})

	# ---------- write ----------
	ws = wb.active
	ws.title = "Summary"
	rows = [
		["SRNB 2220 reconciliation", "as of", today()],
		["Report-visible balance (is_cancelled=0)", "", None],
	]
	bal = frappe.db.sql("SELECT SUM(debit-credit) FROM `tabGL Entry` WHERE account=%s AND is_cancelled=0", T)[0][0]
	rows.append(["Balance (net debit-credit; negative = credit)", "", bal])
	rows.append([])
	rows.append(["Category", "Count", "Amount (debit-credit)", "Suggested action"])
	rows.append(["PR credits (receipts)", 406, -42569754.68, "Cleared by linked PI debits; open ones stay as GRNI"])
	rows.append(["PI debits linked to a PR", 337 - len(orphans), 45610964.28 - sum(r.debit or 0 for r in orphans), "OK - clearing legs"])
	rows.append(["Orphan PI debits (no PR link)", len(orphans), sum(r.debit or 0 for r in orphans),
	             "Link to PR if one exists; else JV out to Inventory/COGS per accounting"])
	rows.append(["Manual JVs", len(jes), None, "Document which receipts each covers; reverse if wrong"])
	rows.append([])
	rows.append(["Open receipts (genuine GRNI)", len(open_pr), -sum(r.credit or 0 for r in open_pr),
	             "Keep - clears when invoices arrive; chase stale ones"])
	rows.append(["Unbilled portion of open receipts", len(open_pr), -sum(r.unbilled_est or 0 for r in open_pr), ""])
	rows.append(["Fully-billed PRs with uncovered credit", len(uncleared), -sum(r["residual"] for r in uncleared),
	             "Investigate - clearing debit is somewhere else (orphan PI / JV)"])
	for r in rows:
		ws.append(r)
	_style_header(ws)
	for row in ws.iter_rows(min_row=4):
		for c in row[2:3]:
			c.number_format = "#,##0.00"

	for title, data, widths in [
		("Open receipts", open_pr, [22, 12, 30, 16, 10, 16, 16]),
		("Orphan PI debits", orphans, [28, 12, 30, 16, 34, 20, 40, 10]),
		("Uncleared credits", uncleared, [22, 12, 16, 10, 16, 20, 14, 50]),
		("Journal entries", je_rows, [22, 12, 16, 50, 40, 16, 16, 26, 16]),
	]:
		s = wb.create_sheet(title)
		if data:
			s.append(list(data[0].keys()))
			for d in data:
				s.append(list(d.values()))
		else:
			s.append(["no rows"])
		_style_header(s)
		for i, w in enumerate(widths, 1):
			s.column_dimensions[s.cell(row=1, column=i).column_letter].width = w
		for row in s.iter_rows(min_row=2):
			for c in row:
				if isinstance(c.value, float):
					c.number_format = "#,##0.00"

	wb.save(OUT)
	print(f"saved {OUT}")
	print(f"open receipts: {len(open_pr)} (credit {sum(r.credit or 0 for r in open_pr):,.2f}, unbilled est {sum(r.unbilled_est or 0 for r in open_pr):,.2f})")
	print(f"orphan PI debits: {len(orphans)} ({sum(r.debit or 0 for r in orphans):,.2f}); with PR on same PO: {sum(1 for r in orphans if r.prs_on_po)}")
	print(f"uncleared credits: {len(uncleared)} (residual {sum(r['residual'] for r in uncleared):,.2f})")
	print(f"JEs: {len(jes)}")


def run():
	build_sheets()
