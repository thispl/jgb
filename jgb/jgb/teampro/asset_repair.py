import frappe
from frappe.utils import getdate

@frappe.whitelist()
def load_repair_summary(doc, method=None):

    doc.set("custom_repair_summary", [])

    if not doc.asset:
        return

    repairs = frappe.get_all(
        "Asset Repair",
        filters={
            "asset": doc.asset,
            "docstatus": 1,
            "name": ["!=", doc.name]
        },
        fields=[
            "name",
            "failure_date",
            "repair_status",
			"asset"
			
        ],
        order_by="failure_date desc"
    )

    for repair in repairs:
        repair_doc = frappe.get_doc("Asset Repair", repair.name)

        estimated_cost = 0
        actual_cost = 0
        remarks = []

        for row in repair_doc.custom_asset_estimation_details:
            estimated_cost += row.estimated_amount or 0
            actual_cost += row.actual_amount or 0

            if row.error_description:
                remarks.append(row.error_description)

        doc.append("custom_repair_summary", {
			"asset": repair.asset,
            "repair_date": getdate(repair.failure_date) if repair.failure_date else None,
            "repair_status": repair.repair_status,
            "estimated_cost": estimated_cost,
            "actual_cost": actual_cost,
            "remarks": ", ".join(remarks)
        })




@frappe.whitelist()
def send_workflow_email(doc, method=None):
    if not doc.has_value_changed("workflow_state"):
        return

    if doc.workflow_state == "Pending for HR Manager":
        send_email_to_role(
            role="HR Manager",
            subject=f"Asset Repair {doc.name} - Pending for HR Manager",
            message=f"""
			<p>Dear Sir/Madam,</p>
			<p>
				Asset Repair
				<a href="{frappe.utils.get_url()}/app/asset-repair/{doc.name}">
				<b>{doc.name}</b>
				</a>
				is pending for your approval for Asset <b>{doc.asset}</b>. Please review and take the necessary action.
			</p>
			<p>Regards,<br>ERPNext</p>
			"""
        )

    elif doc.workflow_state == "Pending for Chief Acc. Verification":
        send_email_to_role(
            role="Regional Accountant",
            subject=f"Asset Repair {doc.name} - Pending for Chief Acc. Verification",
            message=f"""
			<p>Dear Sir/Madam,</p>
			<p>
				Asset Repair
				<a href="{frappe.utils.get_url()}/app/asset-repair/{doc.name}">
				<b>{doc.name}</b>
				</a>
				is pending for your approval for Asset <b>{doc.asset}</b>. Please review and take the necessary action.
			</p>
			<p>Regards,<br>ERPNext</p>
			"""
        )

    elif doc.workflow_state == "Approved":
        if doc.custom_custodian:
            email = frappe.db.get_value("Employee", doc.custom_custodian, "user_id")

            if email:
                frappe.sendmail(
                    recipients=[email],
                    subject=f"Asset Repair {doc.name} Approved",
                    message=f"""
					<p>Dear {doc.custom_custodian_name},</p>

					<p>
					Asset Repair
					<a href="{frappe.utils.get_url()}/app/asset-repair/{doc.name}">
					<b>{doc.name}</b>
					</a>
					has been approved for Asset <b>{doc.asset}</b>.
					</p>

					<p>Regards,<br>ERPNext</p>
					"""
                )



def send_email_to_role(role, subject, message):
    users = frappe.get_all(
        "Has Role",
        filters={"role": role},
        pluck="parent"
    )

    emails = []
    for user in users:
        email = frappe.db.get_value("User", user, "email")
        if email:
            emails.append(email)

    if emails:
        frappe.sendmail(
            recipients=emails,
            subject=subject,
            message=message
        )

