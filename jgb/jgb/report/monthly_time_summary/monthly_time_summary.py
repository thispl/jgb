# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cstr, flt, getdate

# a wider range makes the matrix unreadable on screen / PDF
MAX_RANGE_DAYS = 62

status_map = {
	"Present": "P",
	"Absent": "A",
	"Half Day": "HD",
	"Work From Home": "WFH",
	"On Leave": "L",
	"Holiday": "H",
	"Weekly Off": "WO",
}

# used to collapse duplicate attendance rows for the same employee/day
status_rank = {"Present": 5, "Work From Home": 4, "Half Day": 3, "Absent": 2, "On Leave": 1}

day_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def execute(filters=None) -> tuple:
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	dates = get_dates(filters)
	employees = get_employees(filters)
	if not employees:
		frappe.msgprint(_("No employees found for this criteria."), alert=True, indicator="orange")
		return [], [], None, None

	matrix = build_matrix(filters, employees, dates)
	columns = get_columns(dates)
	data = get_data(employees, dates, matrix)

	return columns, data, get_message(), None


def validate_filters(filters):
	if not filters.company:
		frappe.throw(_("Please select a company."))
	if not (filters.from_date and filters.to_date):
		frappe.throw(_("Please select a date range."))

	filters.from_date = getdate(filters.from_date)
	filters.to_date = getdate(filters.to_date)

	if filters.to_date < filters.from_date:
		frappe.throw(_("To Date cannot be before From Date."))
	if (filters.to_date - filters.from_date).days + 1 > MAX_RANGE_DAYS:
		frappe.throw(
			_("Please narrow the date range to {0} days or less for a readable time summary.").format(
				MAX_RANGE_DAYS
			)
		)


def get_dates(filters):
	dates = []
	d = filters.from_date
	while d <= filters.to_date:
		dates.append(d)
		d += timedelta(days=1)
	return dates


def get_employees(filters):
	"""Everyone employed for any part of the range (active, or relieved within it)."""
	conds = "AND name = %(employee)s" if filters.employee else ""
	return frappe.db.sql(
		f"""
		SELECT name, employee_name, department, branch, designation, holiday_list,
		       date_of_joining, relieving_date
		FROM `tabEmployee`
		WHERE company = %(company)s
		  AND date_of_joining <= %(to_date)s
		  AND IFNULL(relieving_date, '9999-12-31') >= %(from_date)s
		  {conds}
		ORDER BY CAST(name AS UNSIGNED), name
		""",
		filters,
		as_dict=1,
	)


def get_attendance_map(filters):
	"""employee -> {date: status} — duplicate rows collapsed by status rank."""
	conds = "AND employee = %(employee)s" if filters.employee else ""
	rows = frappe.db.sql(
		f"""
		SELECT employee, attendance_date, status
		FROM `tabAttendance`
		WHERE docstatus = 1 AND company = %(company)s
		  AND attendance_date BETWEEN %(from_date)s AND %(to_date)s
		  {conds}
		""",
		filters,
		as_dict=1,
	)
	amap = {}
	for r in rows:
		current = amap.setdefault(r.employee, {}).get(r.attendance_date)
		if current is None or status_rank.get(r.status, 0) > status_rank.get(current, 0):
			amap[r.employee][r.attendance_date] = r.status
	return amap


def get_checkin_map(filters, employees):
	"""employee -> {date: {in, out, hours, punches, break_min}}

	hours = last - first check-in span (gross). break_min = midday breaks:
	sum of OUT->IN gaps plus flagged lunch durations not covered by a gap.
	"""
	names = [e.name for e in employees]
	if not names:
		return {}
	rows = frappe.db.sql(
		"""
		SELECT employee, DATE(time) AS d, time, log_type,
		       custom_is_lunch, custom_lunch_duration
		FROM `tabEmployee Checkin`
		WHERE employee IN %(names)s
		  AND time BETWEEN %(start)s AND %(end)s
		ORDER BY employee, time
		""",
		{
			"names": names,
			"start": f"{filters.from_date} 00:00:00",
			"end": f"{filters.to_date} 23:59:59",
		},
		as_dict=1,
	)
	by_day = {}
	for r in rows:
		by_day.setdefault(r.employee, {}).setdefault(r.d, []).append(r)

	cmap = {}
	for emp, days in by_day.items():
		for d, punches in days.items():
			first = punches[0]["time"]
			last = punches[-1]["time"]
			cmap.setdefault(emp, {})[d] = {
				"in": first,
				"out": last if len(punches) > 1 else None,
				"hours": max((last - first).total_seconds() / 3600.0, 0)
				if len(punches) > 1
				else 0.0,
				"punches": punches,
				"break_min": _break_minutes(punches),
			}
	return cmap


def _break_minutes(punches):
	"""Midday break minutes: OUT->IN gaps, plus flagged lunch durations on
	IN punches not preceded by an OUT (avoids double counting)."""
	brk = 0.0
	for i, p in enumerate(punches):
		if i and punches[i - 1]["log_type"] == "OUT" and p["log_type"] == "IN":
			brk += (p["time"] - punches[i - 1]["time"]).total_seconds() / 60
		elif p["custom_lunch_duration"]:
			brk += flt(p["custom_lunch_duration"])
	return brk


def fmt_punches(punches):
	"""'08:32 I · 12:49 O · 14:29 I · 18:39 O' — lunch-return punches marked (L)."""
	parts = []
	for p in punches:
		tag = "I" if p["log_type"] == "IN" else ("O" if p["log_type"] == "OUT" else "")
		txt = p["time"].strftime("%H:%M") + (f" {tag}" if tag else "")
		if p["custom_is_lunch"]:
			txt += " (L)"
		parts.append(txt)
	return " · ".join(parts)


def fmt_duration(minutes):
	"""Minutes -> 'H:MM' duration display."""
	m = int(round(minutes))
	return f"{m // 60}:{m % 60:02d}"


def get_holiday_map(filters, employees):
	"""holiday_list -> {date: weekly_off}; also returns the company default list."""
	lists = {e.holiday_list for e in employees if e.holiday_list}
	default = frappe.db.get_value("Company", filters.company, "default_holiday_list")
	if default:
		lists.add(default)
	hmap = {}
	if lists:
		rows = frappe.db.sql(
			"""
			SELECT parent, holiday_date, weekly_off FROM `tabHoliday`
			WHERE parent IN %(lists)s AND holiday_date BETWEEN %(from)s AND %(to)s
			""",
			{"lists": list(lists), "from": filters.from_date, "to": filters.to_date},
			as_dict=1,
		)
		for r in rows:
			hmap.setdefault(r.parent, {})[r.holiday_date] = r.weekly_off
	return hmap, default


def build_matrix(filters, employees, dates):
	"""employee -> {cells: {date: {text, cls}}, counters...}"""
	attendance = get_attendance_map(filters)
	checkins = get_checkin_map(filters, employees)
	holiday_map, default_holiday_list = get_holiday_map(filters, employees)

	matrix = {}
	for emp in employees:
		row = {
			"cells": {},
			"total_hours": 0.0,
			"present": 0.0,
			"absent": 0.0,
			"leave": 0.0,
			"holiday": 0.0,
			"unmarked": 0.0,
		}
		emp_att = attendance.get(emp.name, {})
		emp_chk = checkins.get(emp.name, {})
		holidays = holiday_map.get(emp.holiday_list or default_holiday_list, {})

		for d in dates:
			cell = {"text": "", "cls": ""}
			employed = emp.date_of_joining <= d and (
				not emp.relieving_date or emp.relieving_date >= d
			)
			if not employed:
				cell["cls"] = "na"
				row["cells"][d] = cell
				continue

			status = emp_att.get(d)
			chk = emp_chk.get(d)

			if chk:
				# check-in times win the cell; attendance status still drives counters
				if chk["out"]:
					text = f'{chk["in"].strftime("%H:%M")} - {chk["out"].strftime("%H:%M")}'
				else:
					text = chk["in"].strftime("%H:%M")
				cell = {"text": text, "cls": "time9" if chk["hours"] >= 9 else "time"}
				row["total_hours"] += chk["hours"]
			elif status:
				cell = {"text": status_map.get(status, ""), "cls": status}
			elif d in holidays:
				cell = {"text": "WO" if holidays[d] else "H", "cls": "off"}
				row["holiday"] += 1
			else:
				cell = {"text": "", "cls": "unmarked"}
				row["unmarked"] += 1

			if status in ("Present", "Work From Home"):
				row["present"] += 1
			elif status == "Half Day":
				row["present"] += 0.5
				row["leave"] += 0.5
			elif status == "Absent":
				row["absent"] += 1
			elif status == "On Leave":
				row["leave"] += 1

			row["cells"][d] = cell
		matrix[emp.name] = row
	return matrix


def get_columns(dates):
	columns = [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 120,
		},
		{
			"label": _("Region"),
			"fieldname": "region",
			"fieldtype": "Link",
			"options": "Branch",
			"width": 100,
		},
	]
	for d in dates:
		columns.append(
			{
				"label": f"{d.day:02d} {day_abbr[d.weekday()]}",
				"fieldname": d.isoformat(),
				"fieldtype": "Data",
				"width": 95,
			}
		)
	columns.extend(
		[
			{"label": _("Total Hours"), "fieldname": "total_hours", "fieldtype": "Float", "width": 90},
			{"label": _("Present"), "fieldname": "present", "fieldtype": "Float", "width": 75},
			{"label": _("Absent"), "fieldname": "absent", "fieldtype": "Float", "width": 75},
			{"label": _("On Leave"), "fieldname": "on_leave", "fieldtype": "Float", "width": 80},
			{"label": _("Holiday/WO"), "fieldname": "holiday", "fieldtype": "Float", "width": 95},
			{"label": _("Unmarked"), "fieldname": "unmarked", "fieldtype": "Float", "width": 85},
		]
	)
	return columns


def get_data(employees, dates, matrix):
	data = []
	for emp in employees:
		m = matrix.get(emp.name)
		if not m:
			continue
		row = {
			"employee": emp.name,
			"employee_name": emp.employee_name,
			"department": emp.department,
			"region": emp.branch,
			"total_hours": m["total_hours"],
			"present": m["present"],
			"absent": m["absent"],
			"on_leave": m["leave"],
			"holiday": m["holiday"],
			"unmarked": m["unmarked"],
		}
		for d in dates:
			row[d.isoformat()] = m["cells"][d]["text"]
		data.append(row)
	return data


def get_message() -> str:
	message = """
		<span style='border-left: 2px solid #318AD8; padding-right: 12px; padding-left: 5px; margin-right: 3px;'>
			<span style='color:#318AD8'>HH:MM - HH:MM</span> — &ge;9h worked
		</span>
		<span style='border-left: 2px solid #E67E22; padding-right: 12px; padding-left: 5px; margin-right: 3px;'>
			<span style='color:#E67E22'>HH:MM - HH:MM</span> — &lt;9h worked
		</span>
	"""
	colors = {
		"P": "green",
		"A": "red",
		"HD": "orange",
		"L": "#318AD8",
		"WFH": "green",
		"H": "#8d99ae",
		"WO": "#8d99ae",
	}
	labels = {
		"P": "Present",
		"A": "Absent",
		"HD": "Half Day",
		"L": "On Leave",
		"WFH": "Work From Home",
		"H": "Holiday",
		"WO": "Weekly Off",
	}
	for abbr, label in labels.items():
		message += f"""
			<span style='border-left: 2px solid {colors[abbr]}; padding-right: 12px; padding-left: 5px; margin-right: 3px;'>
				{label} - {abbr}
			</span>
		"""
	return message
