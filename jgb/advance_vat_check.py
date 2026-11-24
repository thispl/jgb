"""Read-only health check for advance receipts, their VAT and ZATCA allocation.

Checks (from_date defaults to 2026-01-01):
  A. Advance Payment Entries still booked with a VAT tax row (policy: full/gross).
  B. Sales Invoices where the two advance tables disagree
     (total_advance vs the ZATCA allocated amount in custom_advances_copy).
  C. ZATCA advance rows with a missing / "Not submitted" UUID.
  D. Advance Sales Invoices whose VAT is not recognised in 2401
     (neither on the Payment Entry nor by an "Advance VAT" JV).

Run:
  bench --site <site> execute jgb.advance_vat_check.run
  bench --site <site> execute jgb.advance_vat_check.run --kwargs "{'from_date': '2026-01-01'}"
"""

import frappe
from frappe.utils import flt

ADVANCE_ACCOUNTS_LIKE = "22%"
VAT_ACCOUNT_LIKE = "2401%"
BAD_UUIDS = ("", "not submitted", "null", "none")


def run(from_date="2026-01-01"):
	result = {"a_pe_vat_split": [], "b_table_mismatch": [], "c_bad_uuid": [], "d_vat_missing": []}

	for pe in frappe.db.sql(
		"""
		select name, posting_date, party, paid_amount, total_taxes_and_charges
		from `tabPayment Entry`
		where docstatus = 1 and payment_type = 'Receive'
		  and posting_date >= %s
		  and paid_from like %s
		  and total_taxes_and_charges > 0
		order by posting_date
		""",
		(from_date, ADVANCE_ACCOUNTS_LIKE),
		as_dict=True,
	):
		result["a_pe_vat_split"].append(pe)

	# Map each advance invoice to the Payment Entry that carries the receipt, so the
	# bottom table can be compared with the advance portion actually allocated to the
	# invoice (which may sit in the SI's own table or on the PE reference).
	asi_pes = {}
	for asi in frappe.db.sql(
		"""select name, party, paid_from, grand_total, total_taxes_and_charges
		   from `tabAdvance Sales Invoice` where docstatus = 1""",
		as_dict=True,
	):
		pe = frappe.db.sql(
			"""select name from `tabPayment Entry`
			   where docstatus = 1 and party = %s and paid_from like %s
			     and (abs(paid_amount - %s) < 0.05 or abs(paid_amount - %s) < 0.05)
			   order by posting_date desc limit 1""",
			(asi.party, ADVANCE_ACCOUNTS_LIKE, asi.grand_total, flt(asi.grand_total) - flt(asi.total_taxes_and_charges)),
		)
		if pe:
			asi_pes[asi.name] = pe[0][0]

	for si in frappe.db.sql(
		"""
		select si.name, si.posting_date, si.total_advance,
		       (select sum(case when a.custom_allocated_amount > 0
		                        then a.custom_allocated_amount else a.advance_amount end)
		        from `tabadvance sales invoice table` a where a.parent = si.name) bottom
		from `tabSales Invoice` si
		where si.docstatus = 1 and ifnull(si.is_return, 0) = 0
		  and si.posting_date >= %s
		  and exists (select 1 from `tabadvance sales invoice table` a where a.parent = si.name)
		  and not exists (select 1 from `tabSales Invoice` cn
		                  where cn.return_against = si.name and cn.docstatus = 1 and cn.is_return = 1)
		order by si.posting_date
		""",
		(from_date,),
		as_dict=True,
	):
		asi_backed_pes = set(asi_pes.values())
		asi_pe_refs = 0.0
		for row in frappe.db.sql(
			"""select r.parent, r.allocated_amount from `tabPayment Entry Reference` r
			   join `tabPayment Entry` pe on pe.name = r.parent and pe.docstatus = 1
			   where r.reference_doctype = 'Sales Invoice' and r.reference_name = %s""",
			(si.name,),
			as_dict=True,
		):
			if row.parent in asi_backed_pes:
				asi_pe_refs += flt(row.allocated_amount)

		asi_top = 0.0
		for row in frappe.db.sql(
			"""select reference_name, allocated_amount from `tabSales Invoice Advance`
			   where parent = %s and reference_type = 'Payment Entry'""",
			(si.name,),
			as_dict=True,
		):
			if row.reference_name in asi_backed_pes:
				asi_top += flt(row.allocated_amount)

		applied = max(asi_pe_refs, asi_top)
		if abs(flt(si.bottom) - applied) > 0.05:
			result["b_table_mismatch"].append(
				{"name": si.name, "posting_date": si.posting_date, "bottom": flt(si.bottom),
				 "advance_applied": applied, "total_advance": flt(si.total_advance)}
			)

	for row in frappe.db.sql(
		"""
		select a.parent, a.reference_name, a.uuid, si.posting_date
		from `tabadvance sales invoice table` a
		join `tabSales Invoice` si on si.name = a.parent
		where si.docstatus = 1 and si.posting_date >= %s
		  and not exists (select 1 from `tabSales Invoice` cn
		                  where cn.return_against = si.name and cn.docstatus = 1 and cn.is_return = 1)
		order by si.posting_date
		""",
		(from_date,),
		as_dict=True,
	):
		if (row.uuid or "").strip().lower() in BAD_UUIDS:
			result["c_bad_uuid"].append(row)

	for asi in frappe.db.sql(
		"""
		select name, posting_date, party, paid_from, grand_total, total_taxes_and_charges
		from `tabAdvance Sales Invoice`
		where docstatus = 1 and ifnull(is_return, 0) = 0 and posting_date >= %s
		order by posting_date
		""",
		(from_date,),
		as_dict=True,
	):
		pe_vat = flt(
			frappe.db.sql(
				"""
				select sum(total_taxes_and_charges) from `tabPayment Entry`
				where docstatus = 1 and party = %s and paid_from = %s
				  and (abs(paid_amount - %s) < 0.05 or abs(paid_amount - %s) < 0.05)
				""",
				(asi.party, asi.paid_from, asi.grand_total, flt(asi.grand_total) - flt(asi.total_taxes_and_charges)),
			)[0][0]
		)
		jv_vat = flt(
			frappe.db.sql(
				"""
				select sum(g.credit - g.debit)
				from `tabGL Entry` g
				join `tabJournal Entry` je on je.name = g.voucher_no
				where g.account like %s and g.is_cancelled = 0 and je.docstatus = 1
				  and je.remark like %s
				""",
				(VAT_ACCOUNT_LIKE, f"%{asi.name}%"),
			)[0][0]
		)
		asi_vat = flt(
			frappe.db.sql(
				"""
				select sum(credit - debit) from `tabGL Entry`
				where account like %s and is_cancelled = 0
				  and voucher_no = %s and voucher_type = 'Advance Sales Invoice'
				""",
				(VAT_ACCOUNT_LIKE, asi.name),
			)[0][0]
		)
		if abs((pe_vat + jv_vat + asi_vat) - flt(asi.total_taxes_and_charges)) > 0.02:
			result["d_vat_missing"].append(
				{
					"name": asi.name,
					"posting_date": asi.posting_date,
					"expected_vat": flt(asi.total_taxes_and_charges),
					"vat_in_gl": pe_vat + jv_vat + asi_vat,
				}
			)

	for key, rows in result.items():
		print(f"\n== {key}: {len(rows)}")
		for r in rows:
			print("  ", dict(r))
	return result
