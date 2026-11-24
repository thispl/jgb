# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import format_date

from jgb.jgb.report.monthly_time_summary.monthly_time_summary import (
	day_abbr,
	fmt_duration,
	fmt_punches,
	get_attendance_map,
	get_checkin_map,
	get_dates,
	get_employees,
	get_holiday_map,
	validate_filters,
)


def execute(filters=None) -> tuple:
	filters = frappe._dict(filters or {})
	_validate_individual(filters)

	emp, day_rows, totals = get_individual_rows(filters)
	columns = get_columns()
	data = [dict(r) for r in day_rows]

	data.append(
		{
			"date": None,
			"day": "",
			"status": _totals_label(totals),
			"in_time": "",
			"out_time": "",
			"timings": "",
			"lunch": fmt_duration(totals["break_min"]) if totals["break_min"] >= 0.5 else "",
			"hours": round(totals["total_hours"], 2),
			"bold": 1,
		}
	)

	return columns, data, _employee_message(emp, filters), None, _report_summary(totals)


def _validate_individual(filters):
	validate_filters(filters)
	if not filters.employee:
		frappe.throw(_("Please select an employee for the Individual Time Summary."))


def get_individual_rows(filters):
	"""Returns (employee, day_rows, totals) — one dict per date in range.

	day_rows: {date, day, status, in_time, out_time, hours, cls}
	"""
	dates = get_dates(filters)
	employees = get_employees(filters)
	if not employees:
		frappe.throw(_("Employee not found for the selected company."))
	emp = employees[0]

	attendance = get_attendance_map(filters).get(emp.name, {})
	checkins = get_checkin_map(filters, employees).get(emp.name, {})
	holiday_map, default_holiday_list = get_holiday_map(filters, employees)
	holidays = holiday_map.get(emp.holiday_list or default_holiday_list, {})

	rows = []
	totals = {
		"total_hours": 0.0,
		"present": 0.0,
		"absent": 0.0,
		"leave": 0.0,
		"holiday": 0.0,
		"unmarked": 0.0,
		"break_min": 0.0,
	}

	for d in dates:
		employed = emp.date_of_joining <= d and (
			not emp.relieving_date or emp.relieving_date >= d
		)
		status = attendance.get(d)
		chk = checkins.get(d)

		if not employed:
			status_txt, cls = "—", "na"
		elif status:
			status_txt, cls = status, status
		elif d in holidays:
			status_txt = "Weekly Off" if holidays[d] else "Holiday"
			cls = "off"
			totals["holiday"] += 1
		else:
			status_txt, cls = "Unmarked", "u"
			totals["unmarked"] += 1

		if status in ("Present", "Work From Home"):
			totals["present"] += 1
		elif status == "Half Day":
			totals["present"] += 0.5
			totals["leave"] += 0.5
		elif status == "Absent":
			totals["absent"] += 1
		elif status == "On Leave":
			totals["leave"] += 1

		hours = chk["hours"] if chk else 0.0
		totals["total_hours"] += hours
		break_min = chk["break_min"] if chk else 0.0
		totals["break_min"] += break_min

		rows.append(
			{
				"date": d,
				"day": day_abbr[d.weekday()],
				"status": status_txt,
				"cls": cls,
				"in_time": chk["in"].strftime("%H:%M") if chk else "",
				"out_time": chk["out"].strftime("%H:%M") if chk and chk["out"] else "",
				"timings": fmt_punches(chk["punches"]) if chk else "",
				"lunch": fmt_duration(break_min) if break_min >= 0.5 else "",
				"hours": round(hours, 2) or "",
			}
		)

	return emp, rows, totals


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 110},
		{"label": _("Day"), "fieldname": "day", "fieldtype": "Data", "width": 60},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("In"), "fieldname": "in_time", "fieldtype": "Data", "width": 70},
		{"label": _("Out"), "fieldname": "out_time", "fieldtype": "Data", "width": 70},
		{"label": _("All Timings"), "fieldname": "timings", "fieldtype": "Data", "width": 220},
		{"label": _("Lunch Break"), "fieldname": "lunch", "fieldtype": "Data", "width": 90},
		{"label": _("Hours"), "fieldname": "hours", "fieldtype": "Float", "width": 80},
	]


def _totals_label(totals):
	parts = [
		f"P {totals['present']:g}",
		f"A {totals['absent']:g}",
		f"L {totals['leave']:g}",
		f"H/WO {totals['holiday']:g}",
		f"Unmarked {totals['unmarked']:g}",
	]
	return "   |   ".join(parts)


def _employee_message(emp, filters):
	return f"""
		<span style='font-weight:600'>{emp.name} — {emp.employee_name}</span>
		<span style='padding-left:15px'>{emp.designation or ''}</span>
		<span style='padding-left:15px'>{emp.department or ''}</span>
		<span style='padding-left:15px'>{emp.branch or ''}</span>
		<span style='padding-left:15px'>{format_date(filters.from_date)} to {format_date(filters.to_date)}</span>
	"""


def _report_summary(totals):
	return [
		{"value": round(totals["total_hours"], 2), "label": _("Total Hours"), "datatype": "Float"},
		{"value": totals["present"], "label": _("Present"), "indicator": "Green"},
		{"value": totals["absent"], "label": _("Absent"), "indicator": "Red"},
		{"value": totals["leave"], "label": _("On Leave"), "indicator": "Blue"},
		{"value": totals["holiday"], "label": _("Holiday/WO"), "indicator": "Grey"},
		{"value": totals["unmarked"], "label": _("Unmarked"), "indicator": "Orange"},
	]
