# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import json
import uuid

import frappe


def execute():
	"""Add an 'Attendance Report Dashboard' shortcut to the HR workspace."""
	if not frappe.db.exists("Workspace", "HR"):
		return

	ws = frappe.get_doc("Workspace", "HR")

	if not any(s.link_to == "Attendance Report Dashboard" for s in ws.shortcuts):
		ws.append(
			"shortcuts",
			{
				"type": "DocType",
				"link_to": "Attendance Report Dashboard",
				"label": "Attendance Report Dashboard",
				"color": "Grey",
			},
		)

	content = json.loads(ws.content)
	if not any(
		b.get("type") == "shortcut"
		and b.get("data", {}).get("shortcut_name") == "Attendance Report Dashboard"
		for b in content
	):
		# place after the existing shortcut blocks (before the Reports & Masters header)
		idx = 0
		for i, b in enumerate(content):
			if b.get("type") == "shortcut":
				idx = i + 1
		content.insert(
			idx,
			{
				"id": uuid.uuid4().hex[:10],
				"type": "shortcut",
				"data": {"shortcut_name": "Attendance Report Dashboard", "col": 3},
			},
		)

	ws.content = json.dumps(content)
	ws.flags.ignore_version = True
	ws.save()
