import frappe

def update_ref(doc,method):
    ref_id=''
    if doc.references:
        for i in doc.references:
            if i.reference_doctype in ['Sales Invoice','Purchase Invoice','Sales Order','Purchase Order']:
                ref_doc=frappe.get_doc(i.reference_doctype,i.reference_name)
                if i.reference_doctype=='Purchase Invoice':
                    field_name='ref_doc.bill_no'
                elif i.reference_doctype=='Purchase Order':
                    field_name='ref_doc.custom_supplier_reference'
                elif i.reference_doctype=='Sales Order':
                    field_name='ref_doc.po_no'
                else:
                    field_name='ref_doc.custom_supplier_ref_'
                ref=field_name
                if ref:
                    ref_id=str(ref_id) + ',' + str(ref)
            else:
                ref_id=str(ref_id) + ',' + str(i.reference_name)
        doc.reference_no=ref_id




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
def update_leave_salary(doc,method):
	if doc.custom_leave_salary:
		if frappe.db.exists('Leave Salary',{'name':doc.custom_leave_salary,'docstatus':['!=',2]}):
			frappe.db.set_value('Leave Salary',doc.custom_leave_salary,'status','Unpaid')
			frappe.db.set_value('Leave Salary',doc.custom_leave_salary,'payment_entry_created',1)