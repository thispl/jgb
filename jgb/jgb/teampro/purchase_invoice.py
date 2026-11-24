import frappe
import re

@frappe.whitelist()
def get_purchase_item_tax_template(company, zatca_category):
	"""Resolve the purchase-side Item Tax Template for a ZATCA tax category.

	Uses the same naming-convention map as claudion4saudi's
	update_pi_item_tax_templates so the client-side default and the
	server-side hook stay in sync. Returns the template name and its
	item_tax_rate map.
	"""
	from claudion4saudi.sales_invoice_hooks import _get_template_for_category
	from erpnext.stock.get_item_details import get_item_tax_map

	template = _get_template_for_category(company, zatca_category, is_purchase=True)
	if not template:
		return None

	return {
		"item_tax_template": template,
		"item_tax_rate": get_item_tax_map(company, template, as_json=True),
	}


@frappe.whitelist()
def get_cost_center_for_division(division=None, company=None):
	keyword = extract_keyword_from_division(division)

	if not keyword or not company:
		return ""

	cost_center = frappe.db.sql("""
		SELECT name FROM `tabCost Center`
		WHERE company = %s
		  AND is_group = 0
		  AND name LIKE %s
		LIMIT 1
	""", (
		company,
		f"%{keyword}%",
	), as_dict=0)

	return cost_center[0][0] if cost_center else ""


def extract_keyword_from_division(division):
	# Custom logic to extract from full name like "HVAC Division - (HVA)"
	match = re.search(r'([A-Za-z\s]+)\s+Division', division)
	if match:
		return match.group(1).strip()
	# fallback
	return division.split('-')[0].strip()



@frappe.whitelist()
def check_for_zatca_category(doc,method):
	if doc.custom_zatca_tax_category=='' and doc.workflow_state=='Approved':
		frappe.throw('<b>ZATCA Tax Category</b> is mandatory')



@frappe.whitelist()
def preserve_item_tax_template_before_validate(doc, method=None):
	"""
	Runs as before_validate hook (after claudion4saudi's update_pi_item_tax_templates).
	Saves the user's per-item tax template selection so it can be restored after
	ERPNext's validate_item_tax_template overwrites it.
	
	IMPORTANT: This hook runs AFTER claudion4saudi's hook in the before_validate chain.
	At this point, claudion4saudi has already set all items to the document-level ZATCA template.
	We need to detect if the user had manually set different templates per item.
	
	Since we can't know the user's original selection after claudion4saudi overwrites it,
	we use a different approach: we check if items have DIFFERENT tax templates set
	(which means the user manually changed them) and preserve those.
	"""
	# Store the current state (post-claudion4saudi, pre-ERPNext-validate)
	# If items have different templates, the user has manually overridden them
	if not hasattr(doc, '_user_tax_template_selection'):
		doc._user_tax_template_selection = {}
		for item in doc.items:
			if item.item_code and item.item_tax_template:
				doc._user_tax_template_selection[item.name or item.idx] = item.item_tax_template




@frappe.whitelist()
def update_zatca_category(doc,method):
	if doc.custom_zatca_tax_category=='' and doc.total_taxes_and_charges==0 and not doc.custom_logistics_request:
		frappe.msgprint('<b>ZATCA Tax Category</b> updated as Zero Rated')
		doc.custom_zatca_tax_category='Zero Rated'
		doc.custom_exemption_reason_code='VATEX-SA-32'


from frappe.utils import flt, cint


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def purchase_item_tax_template_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for `item_tax_template` on Purchase Invoice rows.

	ERPNext's default query limits choices to templates listed in the item's /
	item group's Item Tax rules matching the doc tax_category, which leaves the
	dropdown empty for items without matching rules. This lists every enabled
	Item Tax Template whose tax account belongs to the company and is a
	purchase-side (non-Liability) account, so any row can be switched to e.g.
	Zero / Exempted / OOS manually.
	"""
	company = (filters or {}).get("company")
	return frappe.db.sql(
		"""
		SELECT DISTINCT itt.name
		FROM `tabItem Tax Template` itt
		JOIN `tabItem Tax Template Detail` ittd ON ittd.parent = itt.name
		JOIN `tabAccount` acc ON acc.name = ittd.tax_type
		WHERE itt.disabled = 0
		  AND acc.company = %(company)s
		  AND (acc.root_type != 'Liability' OR itt.name LIKE '%%Purchase%%')
		  AND itt.name LIKE %(txt)s
		ORDER BY itt.name
		LIMIT %(page_len)s OFFSET %(start)s
		""",
		{
			"company": company,
			"txt": "%%%s%%" % txt,
			"page_len": cint(page_len),
			"start": cint(start),
		},
	)


@frappe.whitelist()
def preserve_item_tax_template(doc, method=None):
	"""Restore user-selected item_tax_template after ERPNext validate overwrites it"""
	if hasattr(doc, '_user_tax_template_selection'):
		import json
		from erpnext.stock.get_item_details import get_item_tax_map
		
		changed = False
		for item in doc.items:
			key = item.name or item.idx
			saved_template = doc._user_tax_template_selection.get(key)
			if saved_template and item.item_tax_template != saved_template:
				template_company = frappe.db.get_value("Item Tax Template", saved_template, "company")
				if template_company == doc.company:
					item.item_tax_template = saved_template
					item.item_tax_rate = get_item_tax_map(
						company=doc.company,
						item_tax_template=saved_template,
						as_json=True,
					)
					changed = True
		
		if changed:
			# Manually recalculate tax amounts without calling calculate_taxes_and_totals
			# (which would re-trigger validate_item_tax_template and overwrite again)
			for tax in doc.taxes:
				item_wise_detail = {}
				total_tax_amount = 0.0
				
				for item in doc.items:
					item_tax_map = json.loads(item.item_tax_rate) if item.item_tax_rate else {}
					tax_rate = item_tax_map.get(tax.account_head, tax.rate)
					
					if tax.charge_type == "On Net Total":
						tax_amount = flt(item.net_amount * tax_rate / 100.0, tax.precision("tax_amount"))
					else:
						tax_amount = flt(tax.tax_amount, tax.precision("tax_amount"))
					
					item_wise_detail[item.item_code] = [tax_rate, tax_amount]
					total_tax_amount += tax_amount
				
				tax.item_wise_tax_detail = json.dumps(item_wise_detail)
				tax.tax_amount = total_tax_amount
				tax.tax_amount_after_discount_amount = total_tax_amount
				tax.base_tax_amount = total_tax_amount
				tax.base_tax_amount_after_discount_amount = total_tax_amount
				tax.total = flt(doc.net_total + total_tax_amount, tax.precision("total"))
				tax.base_total = tax.total
			
			# Update doc totals
			doc.total_taxes_and_charges = sum(t.tax_amount for t in doc.taxes)
			doc.base_total_taxes_and_charges = doc.total_taxes_and_charges
			doc.grand_total = flt(doc.net_total + doc.total_taxes_and_charges, doc.precision("grand_total"))
			doc.base_grand_total = doc.grand_total

