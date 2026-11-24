# Copyright (c) 2026, JGB and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import date_diff, formatdate, nowdate


def send_compliance_expiry_alerts():
	"""
	Daily scheduled task:
	1. Updates days_left and status in the DB for all active compliance documents.
	2. Trigger conditions for email alerts:
	   - Exactly 60 days before expiry (Advance Notice)
	   - Exactly 30 days before expiry (30-day Notice)
	   - 15 days or fewer (Daily reminder until renewal / overdue)
	3. Sends consolidated summary to HR/System Managers and direct alerts to Custodians.
	"""
	current_date = nowdate()

	# Fetch all renewable records
	records = frappe.get_all(
		"Legal Compliance Monitor",
		filters={"renewability": "Renewable"},
		fields=[
			"name",
			"name_of_licence",
			"reference_number",
			"category",
			"company",
			"expiry_date",
			"days_left",
			"custodian",
			"custodian_name",
			"custodian_email",
			"status",
		],
	)

	if not records:
		return

	alert_docs = []
	custodian_docs_map = {}

	# Update current days_left and status dynamically
	for doc in records:
		if not doc.expiry_date:
			continue

		diff = date_diff(doc.expiry_date, current_date)
		new_status = "Valid"
		if diff < 0:
			new_status = "Expired"
		elif diff <= 30:
			new_status = "Expiring Soon"

		# Update database if values changed
		if doc.days_left != diff or doc.status != new_status:
			frappe.db.set_value(
				"Legal Compliance Monitor",
				doc.name,
				{"days_left": diff, "status": new_status},
				update_modified=False,
			)
			doc.days_left = diff
			doc.status = new_status

		# Trigger Condition: 60 days, 30 days, or <= 15 days (daily)
		if diff == 60 or diff == 30 or diff <= 15:
			alert_docs.append(doc)

			# Map to custodian email if available
			if doc.custodian_email and "@" in doc.custodian_email:
				custodian_docs_map.setdefault(doc.custodian_email, []).append(doc)

	if not alert_docs:
		return

	# Sort by expiry_date ascending
	alert_docs.sort(key=lambda x: x.expiry_date or "9999-12-31")

	# 1. Send consolidated summary to Management / HR
	send_management_summary(alert_docs)

	# 2. Send direct personalized email alerts to each Custodian
	send_custodian_alerts(custodian_docs_map)


def get_status_badge(days_left, status):
	"""Helper to format readable status badge with color."""
	if days_left < 0:
		return f"{abs(days_left)} days overdue ({status})", "#dc3545"
	elif days_left == 0:
		return "Expires Today!", "#dc3545"
	elif days_left <= 15:
		return f"{days_left} days left (Urgent)", "#e03131"
	elif days_left == 30:
		return "30 days left (Due Soon)", "#fd7e14"
	elif days_left == 60:
		return "60 days left (Advance Notice)", "#2f9e44"
	else:
		return f"{days_left} days left ({status})", "#495057"


def send_management_summary(alert_docs):
	"""Sends a full summary table of all triggered documents to HR/System Managers."""
	recipients = get_compliance_recipients()
	if not recipients:
		return

	table_rows = ""
	for doc in alert_docs:
		badge_text, badge_color = get_status_badge(doc.days_left, doc.status)
		table_rows += f"""
			<tr>
				<td style="border: 1px solid #dee2e6; padding: 8px 12px;">{doc.name}</td>
				<td style="border: 1px solid #dee2e6; padding: 8px 12px; font-weight: 500;">{doc.name_of_licence or ''}</td>
				<td style="border: 1px solid #dee2e6; padding: 8px 12px;">{doc.reference_number or '-'}</td>
				<td style="border: 1px solid #dee2e6; padding: 8px 12px;">{doc.category or '-'}</td>
				<td style="border: 1px solid #dee2e6; padding: 8px 12px;">{doc.company or '-'}</td>
				<td style="border: 1px solid #dee2e6; padding: 8px 12px;">{formatdate(doc.expiry_date)}</td>
				<td style="border: 1px solid #dee2e6; padding: 8px 12px; color: {badge_color}; font-weight: 600;">
					{badge_text}
				</td>
				<td style="border: 1px solid #dee2e6; padding: 8px 12px;">{doc.custodian_name or 'Unassigned'}</td>
			</tr>
		"""

	message = f"""
		<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #212529;">
			<h3 style="color: #212529; margin-bottom: 8px;">Legal Compliance &amp; License Expiry Notice</h3>
			<p style="margin-bottom: 16px; color: #6c757d;">
				The following compliance documents/licenses have reached renewal alert thresholds (60 days, 30 days, or &le; 15 days daily reminder).
			</p>
			<table style="border-collapse: collapse; width: 100%; font-size: 13px; text-align: left;">
				<thead>
					<tr style="background-color: #f8f9fa;">
						<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Doc ID</th>
						<th style="border: 1px solid #dee2e6; padding: 10px 12px;">License Name</th>
						<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Ref #</th>
						<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Category</th>
						<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Company</th>
						<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Expiry Date</th>
						<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Status / Days Left</th>
						<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Custodian</th>
					</tr>
				</thead>
				<tbody>
					{table_rows}
				</tbody>
			</table>
			<p style="margin-top: 20px; font-size: 12px; color: #adb5bd;">
				This is an automated notification generated daily by Legal Compliance Monitor.
			</p>
		</div>
	"""

	frappe.sendmail(
		recipients=recipients,
		subject="[Alert] Legal Compliance Documents Expiry Notification",
		message=message,
		now=True,
	)


def send_custodian_alerts(custodian_docs_map):
	"""Sends direct personalized email alerts to each Custodian for their assigned documents."""
	for email, docs in custodian_docs_map.items():
		custodian_name = docs[0].custodian_name or "Custodian"
		table_rows = ""
		for doc in docs:
			badge_text, badge_color = get_status_badge(doc.days_left, doc.status)
			table_rows += f"""
				<tr>
					<td style="border: 1px solid #dee2e6; padding: 8px 12px;">{doc.name}</td>
					<td style="border: 1px solid #dee2e6; padding: 8px 12px; font-weight: 500;">{doc.name_of_licence or ''}</td>
					<td style="border: 1px solid #dee2e6; padding: 8px 12px;">{doc.reference_number or '-'}</td>
					<td style="border: 1px solid #dee2e6; padding: 8px 12px;">{doc.company or '-'}</td>
					<td style="border: 1px solid #dee2e6; padding: 8px 12px;">{formatdate(doc.expiry_date)}</td>
					<td style="border: 1px solid #dee2e6; padding: 8px 12px; color: {badge_color}; font-weight: 600;">
						{badge_text}
					</td>
				</tr>
			"""

		message = f"""
			<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #212529;">
				<h3 style="color: #212529; margin-bottom: 8px;">Action Required: Compliance Document Renewal</h3>
				<p style="margin-bottom: 12px;">Dear <strong>{custodian_name}</strong>,</p>
				<p style="margin-bottom: 16px; color: #495057;">
					You are assigned as the custodian for the following document(s) due for renewal. Please initiate the renewal process:
				</p>
				<table style="border-collapse: collapse; width: 100%; font-size: 13px; text-align: left;">
					<thead>
						<tr style="background-color: #f8f9fa;">
							<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Doc ID</th>
							<th style="border: 1px solid #dee2e6; padding: 10px 12px;">License Name</th>
							<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Ref #</th>
							<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Company</th>
							<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Expiry Date</th>
							<th style="border: 1px solid #dee2e6; padding: 10px 12px;">Status / Days Left</th>
						</tr>
					</thead>
					<tbody>
						{table_rows}
					</tbody>
				</table>
				<p style="margin-top: 20px; font-size: 12px; color: #adb5bd;">
					This is an automated notification generated by Legal Compliance Monitor.
				</p>
			</div>
		"""

		frappe.sendmail(
			recipients=[email],
			subject=f"[Renewal Alert] Compliance Documents Expiry Notification - {custodian_name}",
			message=message,
			now=True,
		)


def get_compliance_recipients():
	"""Get list of active emails for System Managers and HR Managers."""
	recipients = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["System Manager", "HR Manager"]], "parenttype": "User"},
		fields=["parent"],
	)

	emails = set()
	for r in recipients:
		user = r.parent
		if user not in ("Administrator", "Guest") and frappe.db.get_value("User", user, "enabled"):
			email = frappe.db.get_value("User", user, "email") or user
			if email and "@" in email:
				emails.add(email)

	return list(emails)
