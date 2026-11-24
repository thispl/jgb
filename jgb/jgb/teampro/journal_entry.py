import frappe
import re

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
def auto_submit_depreciation_entry(doc, method=None):
    if doc.voucher_type != "Depreciation Entry":
        return
    if not doc.meta.get_workflow():
        return
    if doc.get("workflow_state") != "Draft":
        return

    from frappe.model.workflow import apply_workflow

    original_user = frappe.session.user

    try:
        frappe.set_user("Administrator")

        je = frappe.get_doc("Journal Entry", doc.name)

        apply_workflow(je.as_dict(), "Send to CFO")


        je.reload()
        apply_workflow(je.as_dict(), "Approve")

    finally:
        frappe.set_user(original_user)




@frappe.whitelist()
def update_cost_center(doc, method):
	if frappe.flags.via_payroll_entry:
		doc.is_system_generated = 1
	if not doc.custom_cost_center and doc.voucher_type!="Depreciation Entry" and not doc.custom_leave_application and not doc.custom_ticket_reference and not doc.is_system_generated:
		frappe.throw("Kindly Select the Cost Center")
	if (doc.custom_leave_application or doc.custom_ticket_reference or doc.custom_full_and_final_settlement) and not doc.is_new() and not doc.custom_cost_center:
		frappe.throw("Kindly Select the Cost Center")
	if doc.custom_cost_center:
		for row in doc.accounts:
			row.cost_center = doc.custom_cost_center


def sync_cost_center_after_submit(doc, method=None):
	"""before_update_after_submit companion of update_cost_center.

	Journal Entry Account.cost_center is allow_on_submit, and Frappe skips
	`validate` on the update_after_submit action -- so without this a post-
	submit save would write stale row cost centers through unchecked.

	A row is only reset to custom_cost_center when the posted GL agrees with
	it (no GL row for the account, or GL already carries custom_cost_center).
	If GL was posted with the row's current -- different -- cost center, the
	row is left alone: overwriting it would diverge the document from its
	ledger. Those header-vs-GL disagreements are review items instead.
	"""
	hdr_cc = doc.get("custom_cost_center")
	if not hdr_cc:
		return

	posted = {}
	for account, cc in frappe.db.sql(
		"""select account, cost_center from `tabGL Entry`
		where voucher_type = 'Journal Entry' and voucher_no = %s
			and is_cancelled = 0""",
		doc.name,
	):
		posted.setdefault(account, set()).add(cc)

	for row in doc.accounts:
		if row.cost_center == hdr_cc:
			continue
		gle_ccs = posted.get(row.account)
		if not gle_ccs or hdr_cc in gle_ccs:
			row.cost_center = hdr_cc


def update_ticket_payment_status(doc, method):
	if not doc.custom_ticket_reference:
		return
	if not frappe.db.exists("Leave Application", doc.custom_ticket_reference):
		return
	status_map = {
		"after_insert": "JV in Draft",
		"on_submit": "Paid",
		"on_cancel": "JV Creation Pending",
		"on_trash": "JV Creation Pending"
	}
	status = status_map.get(method)
	if not status:
		return
	frappe.db.set_value("Leave Application", doc.custom_ticket_reference, "custom_ticket_payment_status", status)