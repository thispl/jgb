import frappe
def before_save_employee(doc, method):
	"""
	Auto-generate Employee Number based on the last employee_number in DB
	"""
	if doc.is_new() :
		# Get the highest employee_number from all Employee records
		last_emp = frappe.db.sql("""
			SELECT MAX(CAST(employee_number AS UNSIGNED)) 
			FROM `tabEmployee`
			WHERE employee_number REGEXP '^[0-9]+$'
		""")[0][0]

		if last_emp:
			new_number = int(last_emp) + 1

		doc.employee_number = str(new_number)
		doc.name = str(new_number)




@frappe.whitelist()
def on_update_sales_person(doc, method):
	sales_person = frappe.db.get_value("Sales Person", {"employee": doc.name}, "name")
	if sales_person:
		sp = frappe.get_doc("Sales Person", sales_person)
		sp.custom_user_id = doc.user_id
		sp.custom_designation = doc.designation
		sp.custom_cell_number = doc.cell_number
		sp.custom_company = doc.company
		
		sp.save(ignore_permissions=True)
		if sp.name != doc.employee_name:
			frappe.rename_doc("Sales Person", sp.name,doc.employee_name)



@frappe.whitelist()
def disable_user_employee_status_change(doc, method):
    if not doc.user_id:
        return

    user = frappe.db.get_value("User", doc.user_id, "enabled")

    if doc.status in ["Left", "Inactive"]:
        if user == 1:
            frappe.db.set_value("User", doc.user_id, "enabled", 0)
            frappe.msgprint(f"User {doc.user_id} disabled automatically since Employee status is {doc.status}.")



from frappe import _

def notify_salary_structure_assignment(doc, method):
    frappe.msgprint(
        _(
            "Employee <b>{0}</b> has been created successfully.<br><br>"
            "Please create the <b>Salary Structure Assignment</b> for this employee."
        ).format(doc.employee_name),
        title=_("Salary Structure Assignment"),
        indicator="orange"
    )

@frappe.whitelist()
def create_salary_structure_assignment(doc,method):
	ssa = frappe.new_doc("Salary Structure Assignment")
	ssa.employee = doc.name
	ssa.salary_structure = doc.custom_salary_structure
	ssa.from_date = doc.date_of_joining
	ssa.save(ignore_permissions=True)
	ssa.submit()
	frappe.msgprint("Salary Structure Assignment created successfully: " + ssa.name)
	return ssa.name