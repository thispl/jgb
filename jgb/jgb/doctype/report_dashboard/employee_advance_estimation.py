import frappe

@frappe.whitelist()
def get_previous_amounts(project_name, title_of_estimation):
    result = frappe.db.sql("""
        SELECT 
            SUM(child.advanced_received) as total_advance,
            SUM(child.expense_claimed) as total_claimed
        FROM `tabEmployee Advance` parent
        JOIN `tabEmployee Advance Estimation` child
        ON child.parent = parent.name
        WHERE parent.docstatus = 1
        AND parent.custom_reference_document_name = %s
        AND child.title_of_estimation = %s
    """, (project_name, title_of_estimation), as_dict=True)

    return {
        "total_advance": result[0].total_advance or 0,
        "total_claimed": result[0].total_claimed or 0
    }