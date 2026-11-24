import frappe


def run(names="SOJGBKSA3061-1", account="1105 - Vat Asset - JGB", apply=0):
	"""Remove stray purchase-VAT tax rows from submitted Sales Orders.

	These rows get auto-inserted by erpnext's add_taxes_from_tax_template during
	'Update Items' when an item carries a purchase Item Tax Template (1105 - Vat
	Asset). taxes is not allow_on_submit, so save with the same validation bypass
	the insert path used. Rollback data is in zbackup_so3061_*_fix tables.
	"""
	results = {}
	for name in [n.strip() for n in names.split(",")]:
		doc = frappe.get_doc("Sales Order", name)
		stray = [t for t in doc.taxes if t.account_head == account]
		results[name] = {
			"stray_rows": len(stray),
			"total_taxes_before": doc.total_taxes_and_charges,
			"grand_total_before": doc.grand_total,
		}
		if not int(apply):
			continue

		for t in stray:
			doc.remove(t)
		doc.flags.ignore_validate_update_after_submit = True
		# update_after_submit saves skip validate(), so recalc explicitly
		doc.calculate_taxes_and_totals()
		if stray or doc.has_value_changed("total_taxes_and_charges"):
			doc.set_total_in_words()
			doc.set_payment_schedule()
			doc.save(ignore_permissions=True)
		results[name]["total_taxes_after"] = doc.total_taxes_and_charges
		results[name]["grand_total_after"] = doc.grand_total

	frappe.db.commit()
	return results
