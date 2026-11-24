# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, format_date, getdate
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook import Workbook


class AttendanceReportDashboard(Document):
	pass


def ard_report(doc):
	"""Render-ready data for the Attendance Report Dashboard print formats.

	Runs the real Script Report engine so the PDF always matches the on-screen
	report for the same filters.
	"""
	if isinstance(doc, dict):
		doc = frappe._dict(doc)
	if doc.report == "Individual Time Summary":
		return _individual_data(doc)
	if doc.report == "Monthly Time Summary":
		return _time_summary_data(doc)
	frappe.throw(frappe._("Unknown report: {0}").format(doc.report))


def _time_summary_data(doc):
	from jgb.jgb.report.monthly_time_summary.monthly_time_summary import (
		build_matrix,
		get_dates,
		get_employees,
		validate_filters,
	)

	filters = frappe._dict(
		company=doc.company,
		employee=doc.employee,
		from_date=doc.from_date,
		to_date=doc.to_date,
	)
	validate_filters(filters)

	dates = get_dates(filters)
	employees = get_employees(filters)
	matrix = build_matrix(filters, employees, dates)

	cls_map = {
		"time": "t",
		"time9": "t9",
		"Present": "p",
		"Work From Home": "p",
		"Absent": "a",
		"Half Day": "hd",
		"On Leave": "l",
		"off": "off",
		"unmarked": "u",
		"na": "na",
	}

	rows = []
	for emp in employees:
		m = matrix.get(emp.name)
		if not m:
			continue
		cells = []
		for d in dates:
			c = m["cells"][d]
			in_t = out_t = ""
			if c["cls"] in ("time", "time9") and " - " in c["text"]:
				in_t, out_t = c["text"].split(" - ")
			elif c["cls"] in ("time", "time9"):
				in_t = c["text"]
			cells.append(
				{"text": c["text"], "in": in_t, "out": out_t, "cls": cls_map.get(c["cls"], "")}
			)
		rows.append(
			{
				"employee": emp.name,
				"employee_name": emp.employee_name,
				"department": emp.department or "",
				"region": emp.branch or "",
				"cells": cells,
				"total_hours": f'{flt(m["total_hours"]):,.2f}',
				"present": _fmt_count(m["present"]),
				"absent": _fmt_count(m["absent"]),
				"leave": _fmt_count(m["leave"]),
				"holiday": _fmt_count(m["holiday"]),
				"unmarked": _fmt_count(m["unmarked"]),
			}
		)

	return {
		"kind": "timesheet",
		"dates": [
			{"num": f"{d.day:02d}", "dow": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d.weekday()]}
			for d in dates
		],
		"rows": rows,
	}


def _individual_data(doc):
	from jgb.jgb.report.individual_time_summary.individual_time_summary import (
		get_individual_rows,
	)
	from jgb.jgb.report.monthly_time_summary.monthly_time_summary import validate_filters

	filters = frappe._dict(
		company=doc.company,
		employee=doc.employee,
		from_date=doc.from_date,
		to_date=doc.to_date,
	)
	validate_filters(filters)
	if not filters.employee:
		frappe.throw(frappe._("Please select an employee for the Individual Time Summary."))

	from jgb.jgb.report.monthly_time_summary.monthly_time_summary import fmt_duration

	emp, day_rows, totals = get_individual_rows(filters)

	cls_map = {
		"Present": "p",
		"Work From Home": "p",
		"Absent": "a",
		"Half Day": "hd",
		"On Leave": "l",
		"off": "off",
		"u": "u",
		"na": "na",
	}

	return {
		"kind": "individual",
		"employee": {
			"id": emp.name,
			"name": emp.employee_name,
			"department": emp.department or "",
			"region": emp.branch or "",
			"designation": emp.designation or "",
			"company": doc.company,
		},
		"totals": {
			"total_hours": f'{flt(totals["total_hours"]):,.2f}',
			"present": _fmt_count(totals["present"]),
			"absent": _fmt_count(totals["absent"]),
			"leave": _fmt_count(totals["leave"]),
			"holiday": _fmt_count(totals["holiday"]),
			"unmarked": _fmt_count(totals["unmarked"]),
			"lunch": fmt_duration(totals["break_min"]) if totals["break_min"] >= 0.5 else "0:00",
		},
		"rows": [
			{
				"date": format_date(r["date"]),
				"day": r["day"],
				"status": r["status"],
				"cls": cls_map.get(r["cls"], ""),
				"in_time": r["in_time"],
				"out_time": r["out_time"],
				"timings": r["timings"],
				"lunch": r["lunch"],
				"hours": f'{flt(r["hours"]):,.2f}' if r["hours"] != "" else "",
			}
			for r in day_rows
		],
	}


def _fmt_count(val):
	v = flt(val)
	return str(int(v)) if v == int(v) else f"{v:,.1f}"


# ---------------------------------------------------------------------------
# Styled Excel download (mirrors the PDF print format)
# ---------------------------------------------------------------------------

NAVY = "1F3864"
LIGHT_BLUE = "D9E1F2"
GREEN = "1A7F37"
RED = "C0392B"
ORANGE = "E67E22"
BLUE = "318AD8"
GREY = "8D99AE"

CLS_COLOR = {
	"p": GREEN,
	"a": RED,
	"hd": ORANGE,
	"l": BLUE,
	"off": GREY,
	"t": ORANGE,  # punched but < 9h
	"t9": BLUE,  # punched and >= 9h
}
CLS_BOLD = {"p", "a", "hd", "l", "t", "t9"}


@frappe.whitelist()
def download(report, company=None, from_date=None, to_date=None, employee=None):
	"""Styled .xlsx export for the Attendance Report Dashboard."""
	if not company:
		frappe.throw(frappe._("Kindly choose the company."))

	doc = frappe._dict(
		report=report,
		company=company,
		employee=employee,
		from_date=from_date,
		to_date=to_date,
	)
	data = ard_report(doc)

	wb = Workbook()
	ws = wb.active
	ws.title = report[:31]

	thin = Side(style="thin", color="D0D0D0")
	border = Border(left=thin, right=thin, top=thin, bottom=thin)
	navy_fill = PatternFill("solid", fgColor=NAVY)
	total_fill = PatternFill("solid", fgColor=LIGHT_BLUE)
	header_font = Font(bold=True, color="FFFFFF", size=9)
	bold_font = Font(bold=True, size=9)
	base_font = Font(size=9)
	title_font = Font(bold=True, size=14, color=NAVY)
	sub_font = Font(bold=True, size=11)

	row_i = 1
	if _add_letterhead(ws, doc.company):
		row_i = 2

	def title(text, font, row_i):
		cell = ws.cell(row=row_i, column=1, value=text)
		cell.font = font
		return row_i + 1

	row_i = title(report, title_font, row_i)
	row_i = title(company, sub_font, row_i)
	period = f"{format_date(getdate(from_date))} to {format_date(getdate(to_date))}"
	if employee:
		period += f"   |   Employee: {employee}"
	row_i = title(period, sub_font, row_i)
	if data["kind"] == "timesheet":
		row_i = title(
			"HH:MM - HH:MM = First/Last check-in   |   P = Present   A = Absent   HD = Half Day   "
			"L = On Leave   WFH = Work From Home   H = Holiday   WO = Weekly Off",
			Font(size=8, italic=True, color="666666"),
			row_i,
		)

	row_i += 1

	if data["kind"] == "individual":
		header_row = _write_individual_rows(
			ws, row_i, data, border, navy_fill, total_fill, header_font, bold_font, base_font
		)
	else:
		header_row = _write_timesheet_rows(
			ws, row_i, data, border, navy_fill, total_fill, header_font, bold_font, base_font
		)

	# print-friendly page setup
	from openpyxl.worksheet.properties import PageSetupProperties

	ws.page_setup.orientation = "landscape" if data["kind"] == "timesheet" else "portrait"
	ws.page_setup.fitToWidth = 1
	ws.page_setup.fitToHeight = 0
	ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
	ws.print_title_rows = f"{header_row}:{header_row}"

	from frappe.desk.utils import provide_binary_file
	from io import BytesIO

	out = BytesIO()
	wb.save(out)
	filename = f"{report} - {company} - {from_date} to {to_date}"
	provide_binary_file(filename, "xlsx", out.getvalue())


def _write_timesheet_rows(ws, row_i, data, border, navy_fill, total_fill, header_font, bold_font, base_font):
	headers = ["Employee", "Employee Name", "Department", "Region"] + [
		f"{d['num']}\n{d['dow']}" for d in data["dates"]
	] + ["Total\nHours", "Present", "Absent", "Leave", "Hol/\nWO", "Unm."]
	for col_i, h in enumerate(headers, start=1):
		c = ws.cell(row=row_i, column=col_i, value=h)
		c.font = header_font
		c.fill = navy_fill
		c.border = border
		c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
	header_row = row_i
	ws.row_dimensions[header_row].height = 24
	row_i += 1

	num_cols = len(headers)
	for r in data["rows"]:
		cells = [
			(r["employee"], None),
			(r["employee_name"], None),
			(r["department"], None),
			(r["region"], None),
		]
		cells += [(c["text"], c["cls"]) for c in r["cells"]]
		cells += [
			(r["total_hours"], "tot"),
			(r["present"], "tot"),
			(r["absent"], "tot"),
			(r["leave"], "tot"),
			(r["holiday"], "tot"),
			(r["unmarked"], "tot"),
		]
		for col_i, (val, cls) in enumerate(cells, start=1):
			c = ws.cell(row=row_i, column=col_i, value=val)
			c.border = border
			if col_i <= 4:
				c.font = base_font
				c.alignment = Alignment(horizontal="left", vertical="center")
			elif cls == "tot":
				c.font = bold_font
				c.fill = total_fill
				c.alignment = Alignment(horizontal="center", vertical="center")
			else:
				color = CLS_COLOR.get(cls)
				c.font = Font(size=9, bold=cls in CLS_BOLD, color=color or "000000")
				c.alignment = Alignment(horizontal="center", vertical="center")
		row_i += 1

	# column widths + frozen employee columns / header
	widths = [13, 24, 18, 12] + [11] * len(data["dates"]) + [7, 8, 8, 8, 7, 7]
	for i, w in enumerate(widths[:num_cols], start=1):
		ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
	ws.freeze_panes = ws.cell(row=header_row + 1, column=5)
	return header_row


def _write_individual_rows(ws, row_i, data, border, navy_fill, total_fill, header_font, bold_font, base_font):
	"""Single-employee layout: info card, totals strip, then one row per date."""
	emp = data["employee"]
	totals = data["totals"]
	label_font = Font(bold=True, size=9, color=NAVY)

	# employee info card — label/value pairs in two columns
	info = [
		("Employee ID", emp["id"]),
		("Employee Name", emp["name"]),
		("Designation", emp["designation"]),
		("Department", emp["department"]),
		("Region", emp["region"]),
		("Company", emp["company"]),
	]
	for lbl, val in info:
		c = ws.cell(row=row_i, column=1, value=lbl)
		c.font = label_font
		c = ws.cell(row=row_i, column=2, value=val)
		c.font = base_font
		row_i += 1

	row_i += 1

	# totals strip
	strips = [
		("Total\nHours", totals["total_hours"]),
		("Lunch\nBreak", totals["lunch"]),
		("Present", totals["present"]),
		("Absent", totals["absent"]),
		("Leave", totals["leave"]),
		("Hol/\nWO", totals["holiday"]),
		("Unmarked", totals["unmarked"]),
	]
	for col_i, (lbl, _v) in enumerate(strips, start=1):
		c = ws.cell(row=row_i, column=col_i, value=lbl)
		c.font = header_font
		c.fill = navy_fill
		c.border = border
		c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
	for col_i, (_l, val) in enumerate(strips, start=1):
		c = ws.cell(row=row_i + 1, column=col_i, value=val)
		c.font = bold_font
		c.fill = total_fill
		c.border = border
		c.alignment = Alignment(horizontal="center", vertical="center")
	ws.row_dimensions[row_i].height = 22
	row_i += 3

	# date-row table
	headers = ["Date", "Day", "In", "Out", "All Timings", "Lunch\nBreak", "Hours", "Status"]
	for col_i, h in enumerate(headers, start=1):
		c = ws.cell(row=row_i, column=col_i, value=h)
		c.font = header_font
		c.fill = navy_fill
		c.border = border
		c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
	header_row = row_i
	row_i += 1

	for r in data["rows"]:
		vals = [
			r["date"],
			r["day"],
			r["in_time"],
			r["out_time"],
			r["timings"],
			r["lunch"],
			r["hours"],
			r["status"],
		]
		for col_i, val in enumerate(vals, start=1):
			c = ws.cell(row=row_i, column=col_i, value=val)
			c.border = border
			if col_i == 7:
				h = flt(r["hours"].replace(",", "") or 0)
				c.font = Font(size=9, bold=h >= 9, color=BLUE if h >= 9 else ORANGE) if r["hours"] else base_font
				c.alignment = Alignment(horizontal="center", vertical="center")
			elif col_i == 8:
				color = CLS_COLOR.get(r["cls"])
				c.font = Font(size=9, bold=bool(color), color=color or "000000")
				c.alignment = Alignment(horizontal="left", vertical="center")
			else:
				c.font = base_font
				c.alignment = Alignment(
					horizontal="left" if col_i in (1, 5) else "center", vertical="center"
				)
		row_i += 1

	for i, w in enumerate([12, 8, 9, 9, 34, 8, 9, 16], start=1):
		ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
	ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
	return header_row


def _add_letterhead(ws, company):
	"""Embed the JGB letter-head image on the first row, best effort."""
	try:
		from openpyxl.drawing.image import Image as XLImage

		image = frappe.db.get_value("Letter Head", "JGB", "image")
		if not image:
			return False
		path = frappe.get_site_path("public", image.lstrip("/")) if image.startswith("/") else image
		import os

		if not os.path.exists(path):
			return False
		img = XLImage(path)
		img.height = min(img.height, 60)
		ws.add_image(img, "A1")
		ws.row_dimensions[1].height = 46
		return True
	except Exception:
		frappe.log_error("Letterhead image embed failed", "ARD Excel")
		return False
