# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, format_date, getdate
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook import Workbook


class FinancialReportDashboard(Document):
	pass


def fmt_money(val):
	try:
		return f"{flt(val):,.2f}"
	except (ValueError, TypeError):
		return str(val) if val is not None else ""


def fmt_pct(val):
	return "" if val is None else f"{flt(val):,.2f}%"


def frd_report(doc):
	"""Render-ready data for the Financial Report Dashboard print formats.

	Runs the real Script Report engines so the PDF always matches the on-screen
	report for the same filters.
	"""
	if doc.report == "Project Profitability":
		return _profitability_data(doc)
	if doc.report == "Inventory Schedule":
		return _inventory_data(doc)
	return _statement_data(doc)


def _statement_data(doc):
	from jgb.jgb.report.financial_statements.financial_statements import execute

	columns, rows, _c, _m, _s = execute(
		{
			"company": doc.company,
			"from_date": doc.from_date,
			"to_date": doc.to_date,
			"statement": doc.report,
			"report_type": doc.get("report_type") or "Summary",
			"include_details": cint(doc.show_account_details),
		}
	)

	amount_cols = [c for c in columns[1:] if not c.get("hidden")]

	out = []
	for r in rows:
		out.append(
			{
				"label": r.get("particulars") or "",
				"cells": [r.get(c["fieldname"]) for c in amount_cols],
				# kept for the fixed 2-column print formats (Summary mode)
				"current": r.get("current"),
				"previous": r.get("previous"),
				"indent": cint(r.get("indent")),
				"bold": bool(r.get("bold")),
				"header": bool(r.get("header")),
			}
		)

	return {
		"kind": "statement",
		"headers": [columns[0]["label"]] + [c["label"] for c in amount_cols],
		"rows": out,
	}


def _inventory_data(doc):
	from jgb.jgb.report.inventory_schedule.inventory_schedule import execute

	columns, rows, _c, _m, _s = execute(
		{
			"company": doc.company,
			"to_date": doc.to_date,
			"division": doc.get("division"),
			"report_type": doc.get("report_type") or "Summary",
		}
	)

	amount_cols = [c for c in columns[1:] if not c.get("hidden")]

	out = []
	for r in rows:
		out.append(
			{
				"label": r.get("particulars") or "",
				"cells": [r.get(c["fieldname"]) for c in amount_cols],
				"indent": cint(r.get("indent")),
				"bold": bool(r.get("bold")),
				"header": bool(r.get("header")),
			}
		)

	return {
		"kind": "statement",
		"headers": [columns[0]["label"]] + [c["label"] for c in amount_cols],
		"rows": out,
	}


def _profitability_data(doc):
	from jgb.jgb.report.jgb_project_profitability.jgb_project_profitability import execute

	_columns, rows = execute(
		{
			"company": doc.company,
			"from_date": doc.from_date,
			"to_date": doc.to_date,
			"project": doc.project,
			"sales_order": doc.sales_order,
			"customer": doc.customer,
			"division": doc.division,
		}
	)

	out = []
	for r in rows:
		out.append(
			{
				"total": bool(r.get("is_total")),
				"unallocated": bool(r.get("is_unallocated")),
				"eva_positive": (r.get("est_vs_actual") or 0) >= 0,
				"cells": [
					r.get("project") or "",
					r.get("sales_order") or "",
					r.get("customer_name") or r.get("customer") or "",
					r.get("division") or "",
					fmt_money(r.get("revenue")),
					fmt_money(r.get("material")),
					fmt_money(r.get("additional")),
					fmt_money(r.get("delivery")),
					fmt_money(r.get("other")),
					fmt_money(r.get("gross_profit")),
					fmt_money(r.get("net_profit")),
					fmt_pct(r.get("profit_pct")),
					fmt_money(r.get("estimation")),
					fmt_pct(r.get("est_vs_actual")),
				],
			}
		)

	return {
		"kind": "table",
		"headers": [
			"Project #",
			"SO #",
			"Customer",
			"Division",
			"Revenue",
			"Material Cost",
			"Addl. Cost",
			"Delivery & Dist.",
			"Other Costs",
			"Gross Profit",
			"Net Profit",
			"Profit %",
			"Estimation",
			"Est. vs Actual %",
		],
		"widths": ["12%", "7%", "12%", "7%", "7%", "7%", "6%", "7%", "6%", "7%", "7%", "5%", "7%", "6%"],
		"rows": out,
	}


# ---------------------------------------------------------------------------
# Styled Excel download (mirrors the PDF print formats)
# ---------------------------------------------------------------------------

NAVY = "1F3864"
LIGHT_BLUE = "D9E1F2"
GREEN = "1A7F37"
RED = "C0392B"


@frappe.whitelist()
def download(
	report,
	company=None,
	from_date=None,
	to_date=None,
	project=None,
	sales_order=None,
	customer=None,
	division=None,
	report_type=None,
	show_account_details=0,
):
	"""Styled .xlsx export for the Financial Report Dashboard."""
	if not company:
		frappe.throw(frappe._("Kindly choose the company."))

	doc = frappe._dict(
		report=report,
		company=company,
		from_date=from_date,
		to_date=to_date,
		project=project,
		sales_order=sales_order,
		customer=customer,
		division=division,
		report_type=report_type,
		show_account_details=cint(show_account_details),
	)
	data = frd_report(doc)

	wb = Workbook()
	ws = wb.active
	ws.title = report

	thin = Side(style="thin", color="D0D0D0")
	border = Border(left=thin, right=thin, top=thin, bottom=thin)
	navy_fill = PatternFill("solid", fgColor=NAVY)
	light_fill = PatternFill("solid", fgColor=LIGHT_BLUE)
	header_font = Font(bold=True, color="FFFFFF", size=9)
	total_font = Font(bold=True, color="FFFFFF", size=9)
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
	row_i = title(period, sub_font, row_i) + 1

	headers = data["headers"]
	for col_i, h in enumerate(headers, start=1):
		c = ws.cell(row=row_i, column=col_i, value=h)
		c.font = header_font
		c.fill = navy_fill
		c.border = border
		c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
	header_row = row_i
	row_i += 1

	if data["kind"] == "statement":
		_write_statement_rows(ws, row_i, data, border, bold_font, base_font, navy_fill,
		                      header_font, light_fill)
	else:
		_write_profitability_rows(ws, row_i, data, border, navy_fill, total_font, base_font)

	# column widths + freeze header
	num_cols = len(headers)
	if data["kind"] == "statement":
		widths = [55] + [18] * (num_cols - 1)
	else:
		widths = [38, 16, 26, 16] + [13] * (num_cols - 4)
	for i, w in enumerate(widths[:num_cols], start=1):
		ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
	ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

	from frappe.desk.utils import provide_binary_file
	from io import BytesIO

	out = BytesIO()
	wb.save(out)
	filename = f"{report} - {company} - {from_date} to {to_date}"
	provide_binary_file(filename, "xlsx", out.getvalue())


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
		frappe.log_error("Letterhead image embed failed", "FRD Excel")
		return False


def _write_statement_rows(ws, start, data, border, bold_font, base_font, navy_fill,
                          header_font, light_fill):
	row_i = start
	num_cols = len(data["headers"])
	for r in data["rows"]:
		if r["header"]:
			c = ws.cell(row=row_i, column=1, value=r["label"])
			c.font = header_font
			c.fill = navy_fill
			for col_i in range(1, num_cols + 1):
				ws.cell(row=row_i, column=col_i).fill = navy_fill
				ws.cell(row=row_i, column=col_i).border = border
			row_i += 1
			continue
		cells = [(r["label"], Alignment(horizontal="left", indent=r["indent"]), None)]
		cells += [
			(val, Alignment(horizontal="right"), "#,##0.00") for val in r["cells"]
		]
		for col_i, (val, align, numfmt) in enumerate(cells, start=1):
			c = ws.cell(row=row_i, column=col_i, value=val)
			c.border = border
			c.alignment = align
			c.font = bold_font if r["bold"] else base_font
			if r["bold"]:
				c.fill = light_fill
			if numfmt and val is not None:
				c.number_format = numfmt
		row_i += 1


def _write_profitability_rows(ws, start, data, border, navy_fill, total_font, base_font):
	row_i = start
	num_cols = len(data["headers"])
	green_font = Font(size=9, bold=True, color=GREEN)
	red_font = Font(size=9, bold=True, color=RED)
	grey_fill = PatternFill("solid", start_color="F2F2F2")
	unalloc_font = Font(size=9, italic=True, color="555555")

	for r in data["rows"]:
		for col_i, val in enumerate(r["cells"], start=1):
			c = ws.cell(row=row_i, column=col_i, value=val)
			c.border = border
			c.alignment = Alignment(
				horizontal="left" if col_i <= 4 else "right",
				wrap_text=True,
				vertical="top",
			)
			if r["total"]:
				c.fill = navy_fill
				c.font = total_font
			elif col_i == num_cols:
				c.font = green_font if r["eva_positive"] else red_font
			elif r.get("unallocated"):
				c.fill = grey_fill
				c.font = unalloc_font
			else:
				c.font = base_font
		row_i += 1
