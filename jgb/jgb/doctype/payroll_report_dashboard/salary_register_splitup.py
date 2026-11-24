import frappe
import datetime as py_datetime
from frappe.model.document import Document
from frappe.utils import getdate, flt
from six import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import calendar
from calendar import monthrange

import datetime
from datetime import datetime
import openpyxl
from openpyxl.styles import PatternFill, Font, Border, Side

from openpyxl import Workbook
@frappe.whitelist()
def download_all():
	
	wb = openpyxl.Workbook()

	wb.remove(wb.active)
	download_dynamic_salary_report_visa(wb)
	download_dynamic_salary_report_non_visa(wb)
	expense_excel_visa(wb)
	expense_excel_non_visa(wb)
	advance_excel_visa(wb)
	advance_excel_non_visa(wb)
	vacation_excel_visa(wb)
	vacation_excel_non_visa(wb)
	traffic_fines_excel_visa(wb)
	traffic_fines_excel_non_visa(wb)
	summary_details(wb)

	xlsx_file = BytesIO()
	wb.save(xlsx_file)
	xlsx_file.seek(0)

	frappe.response["filename"] = "Salary Register.xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"

from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def summary_details(wb):
	# Fetch runtime form dict dates and company configuration
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	# Construct the base DB filters identical to your salary sheets
	base_filters = {
		"start_date": (">=", from_date),
		"end_date": ("<=", to_date),
		"docstatus": ("!=", 2)
	}
	if company:
		base_filters["company"] = company

	visa_filters = base_filters.copy()
	visa_filters["custom_emp_category"] = "Visa"
	visa_total = frappe.db.get_value("Salary Slip", visa_filters, "SUM(net_pay)") or 0.0

	non_visa_filters = base_filters.copy()
	non_visa_filters["custom_emp_category"] = "Non Visa"
	non__visa_total = frappe.db.get_value("Salary Slip", non_visa_filters, "SUM(net_pay)") or 0.0

	not_set_filters = base_filters.copy()
	not_set_filters["custom_emp_category"] = None
	not_set_total = frappe.db.get_value("Salary Slip", not_set_filters, "SUM(net_pay)") or 0.0

	ws = wb.create_sheet("Summary Details")
	ws.views.sheetView[0].showGridLines = True

	font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
	font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
	font_bold = Font(name="Calibri", size=11, bold=True)
	font_regular = Font(name="Calibri", size=11)
	
	fill_title = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid") # Dark Blue
	fill_header = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid") # Slate Gray
	fill_accent = PatternFill(start_color="E9F0FA", end_color="E9F0FA", fill_type="solid") # Ice Blue

	thin_border = Border(
		left=Side(style='thin', color='BFBFBF'),
		right=Side(style='thin', color='BFBFBF'),
		top=Side(style='thin', color='BFBFBF'),
		bottom=Side(style='thin', color='BFBFBF')
	)
	
	double_bottom_border = Border(
		left=Side(style='thin', color='BFBFBF'),
		right=Side(style='thin', color='BFBFBF'),
		top=Side(style='thin', color='BFBFBF'),
		bottom=Side(style='double', color='000000')
	)

	ws.append([]) # Blank spacer row
	ws.append(["Salary Summary Report"])
	ws.merge_cells("A2:C2")
	title_cell = ws["A2"]
	title_cell.font = font_title
	title_cell.fill = fill_title
	title_cell.alignment = Alignment(horizontal="center", vertical="center")
	ws.row_dimensions[2].height = 35

	# 3. Add Table Headers
	ws.append(["Employee Category", "Description", "Total Net Salary Pay"])
	ws.row_dimensions[3].height = 25
	for col_idx in range(1, 4):
		cell = ws.cell(row=3, column=col_idx)
		cell.font = font_header
		cell.fill = fill_header
		cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left", vertical="center")
		cell.border = thin_border

	# 4. Add Data Rows
	data_rows = [
		["Visa", "Total Net Pay for Visa Registered Staff", visa_total],
		["Non-Visa", "Total Net Pay for Non-Visa Registered Staff", non__visa_total],
		["Not Set", "Total Net Pay for Unassigned Categories", not_set_total],
	]
	tot_net_pay=visa_total+non__visa_total+not_set_total
	for item in data_rows:
		ws.append(item)
		current_row = ws.max_row
		ws.row_dimensions[current_row].height = 20
		
		# Alignment and formatting
		ws.cell(row=current_row, column=1).font = font_bold
		ws.cell(row=current_row, column=2).font = font_regular
		
		val_cell = ws.cell(row=current_row, column=3)
		val_cell.font = font_regular
		val_cell.number_format = '#,##0.00'
		val_cell.alignment = Alignment(horizontal="right")
		
		for col_idx in range(1, 4):
			ws.cell(row=current_row, column=col_idx).border = thin_border

	# 5. Grand Total Row utilizing native Excel formulas
	total_row = ws.max_row + 1
	ws.cell(row=total_row, column=1, value="Grand Total").font = font_bold
	ws.cell(row=total_row, column=2, value="Sum of all Categories").font = font_regular
	
	grand_total_cell = ws.cell(row=total_row, column=3, value=tot_net_pay)
	grand_total_cell.font = font_bold
	grand_total_cell.number_format = '#,##0.00'
	grand_total_cell.alignment = Alignment(horizontal="right")

	ws.row_dimensions[total_row].height = 22
	for col_idx in range(1, 4):
		c = ws.cell(row=total_row, column=col_idx)
		c.fill = fill_accent
		c.border = double_bottom_border

	# Auto-fit column widths cleanly
	for col in ws.columns:
		max_len = max(len(str(cell.value or '')) for cell in col)
		col_letter = openpyxl.utils.get_column_letter(col[0].column)
		ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

@frappe.whitelist()
def download_dynamic_salary_report_visa(wb, sheet_name='Salary Register(Visa)'):
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	# --- 1. FETCH DATA AND RESOLVE DYNAMIC COLUMNS FIRST ---
	filters = {
		"start_date": (">=", from_date), 
		"end_date": ("<=", to_date),
		"docstatus": ("!=", 2),
		"custom_emp_category": 'Visa'
	}
	if company:
		filters["company"] = company

	salary_slips = frappe.get_all(
		"Salary Slip",
		filters=filters,
		fields=["name", "employee", "employee_name", "designation", "payment_days", "net_pay", "custom_division"],
		order_by="employee"
	)

	earnings_components = []
	deductions_components = []

	if salary_slips:
		slip_names = [slip.name for slip in salary_slips]
		
		salary_details = frappe.get_all(
			"Salary Detail",
			filters={"parent": ("in", slip_names)},
			fields=["salary_component"]
		)
		
		unique_earnings = set()
		unique_deductions = set()
		
		for detail in salary_details:
			component_type = frappe.db.get_value('Salary Component', detail.salary_component, 'type')
			if component_type == "Earning":
				unique_earnings.add(detail.salary_component)
			elif component_type == "Deduction":
				unique_deductions.add(detail.salary_component)
		unique_earnings.add("Other Pay")
		fixed_order = ["Basic", "HRA", "Transport", "Travel Allowance", "Other Pay"]
		earnings_components = sorted(list(unique_earnings))
		fixed_in_earnings = [c for c in earnings_components if c in fixed_order]
		others_in_earnings = [c for c in earnings_components if c not in fixed_order]

		fixed_in_earnings.sort(key=lambda x: fixed_order.index(x))
		others_in_earnings.sort()

		earnings_components = fixed_in_earnings + others_in_earnings
		
		deductions_components = sorted(list(unique_deductions))

	
	base_headings = ["Sl No", "Employee Name", "Employee No.", "Designation", "Region", "Division", "Date of Joining",
					 "Basic Salary", "HRA", "Transport", "Travel Allowance", "Other Pay", "No. of Days Worked"]
	
	# Grid markers
	earning_start = len(base_headings) + 1
	earning_end = earning_start + len(earnings_components) - 1 if earnings_components else earning_start
	total_earnings_col = earning_end + 1

	deduction_start = total_earnings_col + 1
	deduction_end = deduction_start + len(deductions_components) - 1 if deductions_components else deduction_start
	total_deductions_col = deduction_end + 1

	ns_col = total_deductions_col + 1
	remark_col = ns_col + 1
	total_columns = remark_col

	statement_end_col = max(10, int(total_columns * 0.7))

	
	ws = wb.create_sheet(sheet_name)
	thin = Border(
		left=Side(style='thin'), right=Side(style='thin'),
		top=Side(style='thin'), bottom=Side(style='thin')
	)

	ws.append([""])  # Row 1

	
	company_name = company or "Joint Global Business Co LLC"
	ws.append([company_name])
	ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_columns)  
	cell = ws.cell(row=2, column=1)
	cell.font = Font(bold=True, size=14)
	cell.alignment = Alignment(horizontal="center", vertical="center")

	
	from_dt = getdate(from_date)
	to_dt = getdate(to_date)
	total_days = calendar.monthrange(from_dt.year, from_dt.month)[1]
	statement_text = f"Salary Statement for the Period: {from_dt.strftime('%d/%m/%Y')} To {to_dt.strftime('%d/%m/%Y')}"
	total_days_text = f"Total Days: {total_days}"
	
	ws.append([statement_text])
	ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=statement_end_col)  
	cell = ws.cell(row=3, column=1)
	cell.font = Font(bold=True)
	cell.alignment = Alignment(horizontal="center", vertical="center")
	
	ws.merge_cells(start_row=3, start_column=statement_end_col + 1, end_row=3, end_column=total_columns)  
	cell = ws.cell(row=3, column=statement_end_col + 1, value=total_days_text)
	cell.font = Font(bold=True)
	cell.alignment = Alignment(horizontal="center", vertical="center")

	
	header_row = 4

	def set_border_for_range(ws, start_row, start_col, end_row, end_col, border):
		for r in range(start_row, end_row + 1):
			for c in range(start_col, end_col + 1):
				ws.cell(row=r, column=c).border = border

	
	for i, heading in enumerate(base_headings, start=1):
		ws.merge_cells(start_row=header_row, start_column=i, end_row=header_row+1, end_column=i)
		c = ws.cell(row=header_row, column=i, value=heading)
		c.font = Font(bold=True)
		c.alignment = Alignment(horizontal="center", vertical="center")
		set_border_for_range(ws, header_row, i, header_row+1, i, thin)

	
	ws.merge_cells(start_row=header_row, start_column=earning_start, end_row=header_row, end_column=total_earnings_col)
	c = ws.cell(row=header_row, column=earning_start, value="Additions")
	c.font = Font(bold=True)
	c.alignment = Alignment(horizontal="center")
	set_border_for_range(ws, header_row, earning_start, header_row, total_earnings_col, thin)

	
	ws.merge_cells(start_row=header_row, start_column=deduction_start, end_row=header_row, end_column=total_deductions_col)
	c = ws.cell(row=header_row, column=deduction_start, value="Deductions")
	c.font = Font(bold=True)
	c.alignment = Alignment(horizontal="center")
	set_border_for_range(ws, header_row, deduction_start, header_row, total_deductions_col, thin)

	
	ws.merge_cells(start_row=header_row, start_column=ns_col, end_row=header_row+1, end_column=ns_col)
	c = ws.cell(row=header_row, column=ns_col, value="Net Salary")
	c.font = Font(bold=True)
	c.alignment = Alignment(horizontal="center", vertical="center")
	set_border_for_range(ws, header_row, ns_col, header_row+1, ns_col, thin)

	
	ws.merge_cells(start_row=header_row, start_column=remark_col, end_row=header_row+1, end_column=remark_col)
	c = ws.cell(row=header_row, column=remark_col, value="Remark")
	c.font = Font(bold=True)
	c.alignment = Alignment(horizontal="center", vertical="center")
	set_border_for_range(ws, header_row, remark_col, header_row+1, remark_col, thin)

	
	for idx, comp in enumerate(earnings_components, start=earning_start):
		c = ws.cell(row=header_row+1, column=idx, value=comp)
		c.font = Font(bold=True)
		c.alignment = Alignment(horizontal="center")
		c.border = thin

	ws.cell(row=header_row+1, column=total_earnings_col, value="Total Earnings").font = Font(bold=True)
	ws.cell(row=header_row+1, column=total_earnings_col).alignment = Alignment(horizontal="center")
	ws.cell(row=header_row+1, column=total_earnings_col).border = thin

	for idx, comp in enumerate(deductions_components, start=deduction_start):
		c = ws.cell(row=header_row+1, column=idx, value=comp)
		c.font = Font(bold=True)
		c.alignment = Alignment(horizontal="center")
		c.border = thin

	ws.cell(row=header_row+1, column=total_deductions_col, value="Total Deductions").font = Font(bold=True)
	ws.cell(row=header_row+1, column=total_deductions_col).alignment = Alignment(horizontal="center")
	ws.cell(row=header_row+1, column=total_deductions_col).border = thin

	
	total_transport = 0
	total_other_pay = 0
	data_start_row = header_row + 2
	row = data_start_row

	for sl_no, slip in enumerate(salary_slips, start=1):
		doc = frappe.get_doc("Salary Slip", slip.name)
		
		# Pull Employee Data fields
		doj = frappe.db.get_value("Employee", slip.employee, "date_of_joining") or ""
		doj = getdate(doj).strftime("%d-%m-%Y") if doj else ""
		base_basic = flt(frappe.db.get_value("Employee", slip.employee, "custom_basic") or 0)
		base_hra = flt(frappe.db.get_value("Employee", slip.employee, "custom_hra") or 0)
		base_trans = flt(frappe.db.get_value("Employee", slip.employee, "custom_transport") or 0)
		base_travel = flt(frappe.db.get_value("Employee", slip.employee, "custom_travel_allowance") or 0) # New Field
		base_other = flt(frappe.db.get_value("Employee", slip.employee, "custom_other_pay") or 0)
		division = slip.custom_division or frappe.db.get_value("Employee", slip.employee, "custom_division") or ""
		region = frappe.db.get_value("Employee", slip.employee, "custom_region") or ""
		
		annual_leave_days = frappe.db.count("Attendance", {
			'attendance_date': ('between', (from_date, to_date)),
			'docstatus': 1,
			'status': 'On Leave',
			'leave_type': 'Annual Vacation',
			'employee': slip.employee
		})
		
		attendance_summary = frappe.db.sql("""
			SELECT status, leave_type, COUNT(*) AS cnt
			FROM `tabAttendance`
			WHERE employee = %s AND docstatus = 1 AND attendance_date BETWEEN %s AND %s
			GROUP BY status, leave_type
		""", (slip.employee, from_date, to_date), as_dict=True)
		
		summary_map = {}
		for att in attendance_summary:
			key = (att.leave_type or "Leave") if att.status == "On Leave" else att.status
			summary_map[key] = summary_map.get(key, 0) + att.cnt

		remarks = ", ".join([f"{k} - {v}" for k, v in summary_map.items()])
		worked_days = (slip.payment_days or 0)
		if worked_days < 0:
			worked_days=0
		total_transport += base_trans
		total_other_pay += base_other

		# Map Earnings maps dynamically
		earnings = {comp: 0 for comp in earnings_components}
		# if "Basic" in earnings: earnings["Basic"] = base_basic
		# if "HRA" in earnings: earnings["HRA"] = base_hra
		
		for e in getattr(doc, "earnings", []):
			if e.salary_component in earnings:
				earnings[e.salary_component] += flt(e.amount)

		# Map Deductions maps dynamically
		deductions = {d: 0 for d in deductions_components}
		for d in getattr(doc, "deductions", []):
			if d.salary_component in deductions:
				deductions[d.salary_component] += flt(d.amount)

		total_earnings_row = sum(earnings.values())
		total_deductions_row = sum(deductions.values())
		net_salary = flt(slip.net_pay or (total_earnings_row - total_deductions_row))

		# Build payload row array sequentially matching header coordinates
		row_data = [
			sl_no, slip.employee_name, slip.employee, slip.designation, region, division, doj,
			base_basic, base_hra, base_trans,base_travel, base_other, worked_days
		]

		for comp in earnings_components:
			row_data.append(earnings.get(comp, 0))
		row_data.append(total_earnings_row)

		for comp in deductions_components:
			row_data.append(deductions.get(comp, 0))
		row_data.append(total_deductions_row)

		row_data.append(net_salary)
		row_data.append(remarks)

		ws.append(row_data)

		for col in range(1, total_columns + 1):
			c = ws.cell(row=row, column=col)
			c.border = thin
			if col in [2, 4, remark_col]:
				c.alignment = Alignment(horizontal="left")
			elif col in [1, 3, 5, 6, 7]:
				c.alignment = Alignment(horizontal="center")
			else:
				c.alignment = Alignment(horizontal="right")
				if col != 12:  # Worked days format protection
					c.number_format = '#,##0.00'
		row += 1

	# --- 6. RENDER DYNAMIC TOTALS SUMMARY ROW ---
	total_row = row
	ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=7)
	t_cell = ws.cell(row=total_row, column=1, value="TOTAL")
	t_cell.font = Font(bold=True)
	t_cell.alignment = Alignment(horizontal="center")

	# Generate Excel Formula References Across Columns Dynamic Range
	for col in range(1, total_columns + 1):
		c = ws.cell(row=total_row, column=col)
		c.border = thin
		
		if col < 8:
			continue  # Covered by MERGE block
			
		col_letter = get_column_letter(col)
		
		if col in [8, 9, 11, total_earnings_col, total_deductions_col, ns_col] or (earning_start <= col <= earning_end) or (deduction_start <= col <= deduction_end):
			# Safe dynamic calculations utilizing native Excel SUM ranges
			c.value = f"=SUM({col_letter}{data_start_row}:{col_letter}{total_row-1})"
			c.font = Font(bold=True)
			c.alignment = Alignment(horizontal="right")
			c.number_format = '#,##0.00'
		elif col == 10:
			c.value = total_transport
			c.font = Font(bold=True)
			c.alignment = Alignment(horizontal="right")
			c.number_format = '#,##0.00'
		elif col == 12:
			c.value = total_other_pay
			c.font = Font(bold=True)
			c.alignment = Alignment(horizontal="right")
			c.number_format = '#,##0.00'
		elif col == 13:
			# Worked Days total formula summary line
			c.value = f"=SUM({col_letter}{data_start_row}:{col_letter}{total_row-1})"
			c.font = Font(bold=True)
			c.alignment = Alignment(horizontal="right")
			c.number_format = '#,##0'

	# --- 7. AUTO-FIT SHEET COLUMN WIDTH SETTINGS ---
	# Apply standard defaults for the base set, then auto-pad structural dynamically appended columns
	base_widths = {1: 6, 2: 30, 3: 12, 4: 35, 5: 12, 6: 24, 7: 15, 8: 14, 9: 14, 10: 14, 11: 14, 12: 16}
	for col_idx in range(1, total_columns + 1):
		col_letter = get_column_letter(col_idx)
		if col_idx in base_widths:
			ws.column_dimensions[col_letter].width = base_widths[col_idx]
		elif col_idx == remark_col:
			ws.column_dimensions[col_letter].width = 35
		else:
			ws.column_dimensions[col_letter].width = 15


@frappe.whitelist()
def download_dynamic_salary_report_non_visa(wb, sheet_name='Salary Register(Non Visa)'):
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	filters = {
		"start_date": (">=", from_date), 
		"end_date": ("<=", to_date),
		"docstatus": ("!=", 2),
		"custom_emp_category": 'Non Visa'
	}
	if company:
		filters["company"] = company

	salary_slips = frappe.get_all(
		"Salary Slip",
		filters=filters,
		fields=["name", "employee", "employee_name", "designation", "payment_days", "net_pay", "custom_division"],
		order_by="employee"
	)

	earnings_components = []
	deductions_components = []

	if salary_slips:
		slip_names = [slip.name for slip in salary_slips]
		
		salary_details = frappe.get_all(
			"Salary Detail",
			filters={"parent": ("in", slip_names)},
			fields=["salary_component"]
		)
		
		unique_earnings = set()
		unique_deductions = set()
		
		for detail in salary_details:
			component_type = frappe.db.get_value('Salary Component', detail.salary_component, 'type')
			if component_type == "Earning":
				unique_earnings.add(detail.salary_component)
			elif component_type == "Deduction":
				unique_deductions.add(detail.salary_component)
		unique_earnings.add("Other Pay")
		fixed_order = ["Basic", "HRA", "Transport", "Travel Allowance", "Other Pay"]
		earnings_components = sorted(list(unique_earnings))
		fixed_in_earnings = [c for c in earnings_components if c in fixed_order]
		others_in_earnings = [c for c in earnings_components if c not in fixed_order]

		fixed_in_earnings.sort(key=lambda x: fixed_order.index(x))
		others_in_earnings.sort()

		earnings_components = fixed_in_earnings + others_in_earnings	
		frappe.log_error("fixed_in_earnings",fixed_in_earnings)
		frappe.log_error("others_in_earnings",others_in_earnings)
		deductions_components = sorted(list(unique_deductions))

	
	base_headings = ["Sl No", "Employee Name", "Employee No.", "Designation", "Region", "Division", "Date of Joining",
					 "Basic Salary", "HRA", "Transport","Travel Allowance", "Other Pay", "No. of Days Worked"]
	
	# Grid markers
	# earning_start = len(base_headings) + 1
	# earning_end = earning_start + len(earnings_components) - 1 if earnings_components else earning_start
	# total_earnings_col = earning_end + 1

	# deduction_start = total_earnings_col + 1
	# deduction_end = deduction_start + len(deductions_components) - 1 if deductions_components else deduction_start
	# total_deductions_col = deduction_end + 1

	# ns_col = total_deductions_col + 1
	# remark_col = ns_col + 1
	# total_columns = remark_col

	# Grid markers
	earning_start = len(base_headings) + 1
	if earnings_components:
		earning_end = earning_start + len(earnings_components) - 1
		total_earnings_col = earning_end + 1
	else:
		earning_end = earning_start - 1
		total_earnings_col = earning_start

	deduction_start = total_earnings_col + 1
	if deductions_components:
		deduction_end = deduction_start + len(deductions_components) - 1
		total_deductions_col = deduction_end + 1
	else:
		deduction_end = deduction_start - 1
		total_deductions_col = deduction_start

	ns_col = total_deductions_col + 1
	remark_col = ns_col + 1
	total_columns = remark_col

	statement_end_col = max(10, int(total_columns * 0.7))

	
	ws = wb.create_sheet(sheet_name)
	thin = Border(
		left=Side(style='thin'), right=Side(style='thin'),
		top=Side(style='thin'), bottom=Side(style='thin')
	)

	ws.append([""])  # Row 1

	
	company_name = company or "Joint Global Business Co LLC"
	ws.append([company_name])
	ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_columns)  
	cell = ws.cell(row=2, column=1)
	cell.font = Font(bold=True, size=14)
	cell.alignment = Alignment(horizontal="center", vertical="center")

	
	from_dt = getdate(from_date)
	to_dt = getdate(to_date)
	total_days = calendar.monthrange(from_dt.year, from_dt.month)[1]
	statement_text = f"Salary Statement for the Period: {from_dt.strftime('%d/%m/%Y')} To {to_dt.strftime('%d/%m/%Y')}"
	total_days_text = f"Total Days: {total_days}"
	
	ws.append([statement_text])
	ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=statement_end_col)  
	cell = ws.cell(row=3, column=1)
	cell.font = Font(bold=True)
	cell.alignment = Alignment(horizontal="center", vertical="center")
	
	ws.merge_cells(start_row=3, start_column=statement_end_col + 1, end_row=3, end_column=total_columns)  
	cell = ws.cell(row=3, column=statement_end_col + 1, value=total_days_text)
	cell.font = Font(bold=True)
	cell.alignment = Alignment(horizontal="center", vertical="center")

	
	header_row = 4

	def set_border_for_range(ws, start_row, start_col, end_row, end_col, border):
		for r in range(start_row, end_row + 1):
			for c in range(start_col, end_col + 1):
				ws.cell(row=r, column=c).border = border

	
	for i, heading in enumerate(base_headings, start=1):
		ws.merge_cells(start_row=header_row, start_column=i, end_row=header_row+1, end_column=i)
		c = ws.cell(row=header_row, column=i, value=heading)
		c.font = Font(bold=True)
		c.alignment = Alignment(horizontal="center", vertical="center")
		set_border_for_range(ws, header_row, i, header_row+1, i, thin)

	
	ws.merge_cells(start_row=header_row, start_column=earning_start, end_row=header_row, end_column=total_earnings_col)
	c = ws.cell(row=header_row, column=earning_start, value="Additions")
	c.font = Font(bold=True)
	c.alignment = Alignment(horizontal="center")
	set_border_for_range(ws, header_row, earning_start, header_row, total_earnings_col, thin)

	
	ws.merge_cells(start_row=header_row, start_column=deduction_start, end_row=header_row, end_column=total_deductions_col)
	c = ws.cell(row=header_row, column=deduction_start, value="Deductions")
	c.font = Font(bold=True)
	c.alignment = Alignment(horizontal="center")
	set_border_for_range(ws, header_row, deduction_start, header_row, total_deductions_col, thin)

	
	ws.merge_cells(start_row=header_row, start_column=ns_col, end_row=header_row+1, end_column=ns_col)
	c = ws.cell(row=header_row, column=ns_col, value="Net Salary")
	c.font = Font(bold=True)
	c.alignment = Alignment(horizontal="center", vertical="center")
	set_border_for_range(ws, header_row, ns_col, header_row+1, ns_col, thin)

	
	ws.merge_cells(start_row=header_row, start_column=remark_col, end_row=header_row+1, end_column=remark_col)
	c = ws.cell(row=header_row, column=remark_col, value="Remark")
	c.font = Font(bold=True)
	c.alignment = Alignment(horizontal="center", vertical="center")
	set_border_for_range(ws, header_row, remark_col, header_row+1, remark_col, thin)

	
	for idx, comp in enumerate(earnings_components, start=earning_start):
		c = ws.cell(row=header_row+1, column=idx, value=comp)
		c.font = Font(bold=True)
		c.alignment = Alignment(horizontal="center")
		c.border = thin

	ws.cell(row=header_row+1, column=total_earnings_col, value="Total Earnings").font = Font(bold=True)
	ws.cell(row=header_row+1, column=total_earnings_col).alignment = Alignment(horizontal="center")
	ws.cell(row=header_row+1, column=total_earnings_col).border = thin

	for idx, comp in enumerate(deductions_components, start=deduction_start):
		c = ws.cell(row=header_row+1, column=idx, value=comp)
		c.font = Font(bold=True)
		c.alignment = Alignment(horizontal="center")
		c.border = thin

	ws.cell(row=header_row+1, column=total_deductions_col, value="Total Deductions").font = Font(bold=True)
	ws.cell(row=header_row+1, column=total_deductions_col).alignment = Alignment(horizontal="center")
	ws.cell(row=header_row+1, column=total_deductions_col).border = thin

	
	total_transport = 0
	total_other_pay = 0
	data_start_row = header_row + 2
	row = data_start_row

	for sl_no, slip in enumerate(salary_slips, start=1):
		doc = frappe.get_doc("Salary Slip", slip.name)
		
		# Pull Employee Data fields
		doj = frappe.db.get_value("Employee", slip.employee, "date_of_joining") or ""
		doj = getdate(doj).strftime("%d-%m-%Y") if doj else ""
		base_basic = flt(frappe.db.get_value("Employee", slip.employee, "custom_basic") or 0)
		base_hra = flt(frappe.db.get_value("Employee", slip.employee, "custom_hra") or 0)
		base_trans = flt(frappe.db.get_value("Employee", slip.employee, "custom_transport") or 0)
		base_travel = flt(frappe.db.get_value("Employee", slip.employee, "custom_travel_allowance") or 0) 
		base_other = flt(frappe.db.get_value("Employee", slip.employee, "custom_other_pay") or 0)
		division = slip.custom_division or frappe.db.get_value("Employee", slip.employee, "custom_division") or ""
		region = frappe.db.get_value("Employee", slip.employee, "custom_region") or ""
		
		annual_leave_days = frappe.db.count("Attendance", {
			'attendance_date': ('between', (from_date, to_date)),
			'docstatus': 1,
			'status': 'On Leave',
			'leave_type': 'Annual Vacation',
			'employee': slip.employee
		})
		
		attendance_summary = frappe.db.sql("""
			SELECT status, leave_type, COUNT(*) AS cnt
			FROM `tabAttendance`
			WHERE employee = %s AND docstatus = 1 AND attendance_date BETWEEN %s AND %s
			GROUP BY status, leave_type
		""", (slip.employee, from_date, to_date), as_dict=True)
		
		summary_map = {}
		for att in attendance_summary:
			key = (att.leave_type or "Leave") if att.status == "On Leave" else att.status
			summary_map[key] = summary_map.get(key, 0) + att.cnt

		remarks = ", ".join([f"{k} - {v}" for k, v in summary_map.items()])
		worked_days = (slip.payment_days or 0)
		
		total_transport += base_trans
		total_other_pay += base_other

		# Map Earnings maps dynamically
		earnings = {comp: 0 for comp in earnings_components}

		for e in getattr(doc, "earnings", []):
			if e.salary_component in earnings:
				earnings[e.salary_component] += flt(e.amount)

		# Map Deductions maps dynamically
		deductions = {d: 0 for d in deductions_components}
		for d in getattr(doc, "deductions", []):
			if d.salary_component in deductions:
				deductions[d.salary_component] += flt(d.amount)

		total_earnings_row = sum(earnings.values())
		total_deductions_row = sum(deductions.values())
		net_salary = flt(slip.net_pay or (total_earnings_row - total_deductions_row))

		# Build payload row array sequentially matching header coordinates
		row_data = [
			sl_no, slip.employee_name, slip.employee, slip.designation, region, division, doj,
			base_basic, base_hra, base_trans, base_travel,base_other, worked_days
		]

		for comp in earnings_components:
			row_data.append(earnings.get(comp, 0))
		row_data.append(total_earnings_row)

		for comp in deductions_components:
			row_data.append(deductions.get(comp, 0))
		row_data.append(total_deductions_row)

		row_data.append(net_salary)
		row_data.append(remarks)

		ws.append(row_data)

		# Apply specific row formats
		for col in range(1, total_columns + 1):
			c = ws.cell(row=row, column=col)
			c.border = thin
			if col in [2, 4, remark_col]:
				c.alignment = Alignment(horizontal="left")
			elif col in [1, 3, 5, 6, 7]:
				c.alignment = Alignment(horizontal="center")
			else:
				c.alignment = Alignment(horizontal="right")
				if col != 12:  # Worked days format protection
					c.number_format = '#,##0.00'
		row += 1

	# --- 6. RENDER DYNAMIC TOTALS SUMMARY ROW ---
	total_row = row
	ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=7)
	t_cell = ws.cell(row=total_row, column=1, value="TOTAL")
	t_cell.font = Font(bold=True)
	t_cell.alignment = Alignment(horizontal="center")

	# Generate Excel Formula References Across Columns Dynamic Range
	for col in range(1, total_columns + 1):
		c = ws.cell(row=total_row, column=col)
		c.border = thin
		
		if col < 8:
			continue  # Covered by MERGE block
			
		col_letter = get_column_letter(col)
		
		if col in [8, 9, 11, total_earnings_col, total_deductions_col, ns_col] or (earning_start <= col <= earning_end) or (deduction_start <= col <= deduction_end):
			# Safe dynamic calculations utilizing native Excel SUM ranges
			c.value = f"=SUM({col_letter}{data_start_row}:{col_letter}{total_row-1})"
			c.font = Font(bold=True)
			c.alignment = Alignment(horizontal="right")
			c.number_format = '#,##0.00'
		elif col == 10:
			c.value = total_transport
			c.font = Font(bold=True)
			c.alignment = Alignment(horizontal="right")
			c.number_format = '#,##0.00'
		elif col == 12:
			c.value = total_other_pay
			c.font = Font(bold=True)
			c.alignment = Alignment(horizontal="right")
			c.number_format = '#,##0.00'
		elif col == 13:
			# Worked Days total formula summary line
			c.value = f"=SUM({col_letter}{data_start_row}:{col_letter}{total_row-1})"
			c.font = Font(bold=True)
			c.alignment = Alignment(horizontal="right")
			c.number_format = '#,##0'

	# --- 7. AUTO-FIT SHEET COLUMN WIDTH SETTINGS ---
	# Apply standard defaults for the base set, then auto-pad structural dynamically appended columns
	base_widths = {1: 6, 2: 30, 3: 12, 4: 35, 5: 12, 6: 24, 7: 15, 8: 14, 9: 14, 10: 14, 11: 14, 12: 16}
	for col_idx in range(1, total_columns + 1):
		col_letter = get_column_letter(col_idx)
		if col_idx in base_widths:
			ws.column_dimensions[col_letter].width = base_widths[col_idx]
		elif col_idx == remark_col:
			ws.column_dimensions[col_letter].width = 35
		else:
			ws.column_dimensions[col_letter].width = 15


	
def get_expense_data_visa(args):
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	additional_salaries = frappe.db.sql("""
		SELECT
			asr.name AS additional_salary_name,
			asr.employee,
			asr.employee_name,
			asr.company,
			asr.payroll_date,
			emp.custom_division,
			emp.custom_region
		FROM
			`tabAdditional Salary` asr
		INNER JOIN `tabEmployee` emp
			ON emp.name = asr.employee
		WHERE
			asr.docstatus = 1
			AND asr.payroll_date BETWEEN %s AND %s
			AND asr.company = %s
			AND asr.salary_component = 'Monthly Expenses'
			AND emp.custom_employee_category = 'Visa'
		""", 
		(from_date, to_date, company), as_dict=True)
	
	result = []

	for asr in additional_salaries:
		expense_details = frappe.db.sql("""
			SELECT expense_id, expense_amount
			FROM `tabExpense Split Up`
			WHERE parent = %s
		""", (asr['additional_salary_name']), as_dict=True)

		if expense_details:
			for detail in expense_details:
				result.append({
					'employee': asr['employee'],
					'employee_name': asr['employee_name'],
					'expense_id': detail['expense_id'],
					'expense_amount': detail['expense_amount'],
					'payroll_date': asr['payroll_date'],
					'company': asr['company'],
					'division': asr['custom_division'],
					'region': asr['custom_region']
				})

	return result

def get_expense_data_non_visa(args):
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	additional_salaries = frappe.db.sql("""
		SELECT
			asr.name AS additional_salary_name,
			asr.employee,
			asr.employee_name,
			asr.company,
			asr.payroll_date,
			emp.custom_division,
			emp.custom_region
		FROM
			`tabAdditional Salary` asr
		INNER JOIN `tabEmployee` emp
			ON emp.name = asr.employee
		WHERE
			asr.docstatus = 1
			AND asr.payroll_date BETWEEN %s AND %s
			AND asr.company = %s
			AND asr.salary_component = 'Monthly Expenses'
			AND emp.custom_employee_category = 'Non Visa'
		""", 
		(from_date, to_date, company), as_dict=True)
	
	result = []

	for asr in additional_salaries:
		expense_details = frappe.db.sql("""
			SELECT expense_id, expense_amount
			FROM `tabExpense Split Up`
			WHERE parent = %s
		""", (asr['additional_salary_name']), as_dict=True)

		if expense_details:
			for detail in expense_details:
				result.append({
					'employee': asr['employee'],
					'employee_name': asr['employee_name'],
					'expense_id': detail['expense_id'],
					'expense_amount': detail['expense_amount'],
					'payroll_date': asr['payroll_date'],
					'company': asr['company'],
					'division': asr['custom_division'],
					'region': asr['custom_region']
				})

	return result

def expense_excel_visa(wb, sheet_name="Expense Claim Breakup (Visa)"):
	NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'
	
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	ws = wb.create_sheet(sheet_name)
	formatted_from_date = py_datetime.datetime.strptime(from_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	formatted_to_date = py_datetime.datetime.strptime(to_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	header1 = [f'Expense Claim Addition for the period {formatted_from_date} - {formatted_to_date}', '', '', '', '', '', '']
	header2 = ['Sr No', 'Employee', 'Employee Name', 'Region', 'Division', 'Amount', 'Expense Claim ID']
	
	ws.append(header1)
	ws.append(header2)
	
	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
	
	light_blue_fill = PatternFill("solid", fgColor="ADD8E6") 
	dark_blue_fill = PatternFill("solid", fgColor="1F4E79") 
	white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
	black_bold_font = Font(bold=True, color="000000", name="Calibri", size=10)
	
	for col in range(1, 8):  
		ws.cell(row=1, column=col).fill = light_blue_fill
		ws.cell(row=1, column=col).font = black_bold_font
	
	for col in range(1, 8):  
		ws.cell(row=2, column=col).fill = dark_blue_fill
		ws.cell(row=2, column=col).font = white_bold_font

	sr_no = 1
	total_amnt = 0  

	for d in get_expense_data_visa(args):        
		ws.append([
			sr_no,
			d['employee'],        
			d['employee_name'],       
			d['region'] or '',
			d['division'] or '',
			d['expense_amount'],      
			d['expense_id'],
		])
		
		sr_no += 1
		total_amnt += d['expense_amount'] or 0
		
		cell = ws.cell(row=ws.max_row, column=6)
		cell.number_format = NUMBER_FORMAT
		
	ws.append(["Total", "", "", "", "", total_amnt, ""])

	cell = ws.cell(row=ws.max_row, column=6)
	cell.number_format = NUMBER_FORMAT
	cell.font = Font(bold=True, color="000000")

	ws.column_dimensions['A'].width = 5
	ws.column_dimensions['B'].width = 12
	ws.column_dimensions['C'].width = 25
	ws.column_dimensions['D'].width = 14
	ws.column_dimensions['E'].width = 28
	ws.column_dimensions['F'].width = 15
	ws.column_dimensions['G'].width = 25
	
	thin_border = Border(
		left=Side(border_style="thin", color="000000"),
		right=Side(border_style="thin", color="000000"),
		top=Side(border_style="thin", color="000000"),
		bottom=Side(border_style="thin", color="000000")
	)
	
	for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
		for cell in row:
			cell.border = thin_border
	last_row = ws.max_row
	ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=3)

def expense_excel_non_visa(wb, sheet_name="Expense Claim Breakup (Non Visa)"):
	NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'
	
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	ws = wb.create_sheet(sheet_name)
	formatted_from_date = py_datetime.datetime.strptime(from_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	formatted_to_date = py_datetime.datetime.strptime(to_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	header1 = [f'Expense Claim Addition for the period {formatted_from_date} - {formatted_to_date}', '', '', '', '', '', '']
	header2 = ['Sr No', 'Employee', 'Employee Name', 'Region', 'Division', 'Amount', 'Expense Claim ID']
	
	ws.append(header1)
	ws.append(header2)
	
	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
	
	light_blue_fill = PatternFill("solid", fgColor="ADD8E6") 
	dark_blue_fill = PatternFill("solid", fgColor="1F4E79") 
	white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
	black_bold_font = Font(bold=True, color="000000", name="Calibri", size=10)
	
	for col in range(1, 8):  
		ws.cell(row=1, column=col).fill = light_blue_fill
		ws.cell(row=1, column=col).font = black_bold_font
	
	for col in range(1, 8):  
		ws.cell(row=2, column=col).fill = dark_blue_fill
		ws.cell(row=2, column=col).font = white_bold_font

	sr_no = 1
	total_amnt = 0  

	for d in get_expense_data_non_visa(args):        
		ws.append([
			sr_no,
			d['employee'],        
			d['employee_name'],       
			d['region'] or '',
			d['division'] or '',
			d['expense_amount'],      
			d['expense_id'],
		])
		
		sr_no += 1
		total_amnt += d['expense_amount'] or 0
		
		cell = ws.cell(row=ws.max_row, column=6)
		cell.number_format = NUMBER_FORMAT
		
	ws.append(["Total", "", "", "", "", total_amnt, ""])

	cell = ws.cell(row=ws.max_row, column=6)
	cell.number_format = NUMBER_FORMAT
	cell.font = Font(bold=True, color="000000")

	ws.column_dimensions['A'].width = 5
	ws.column_dimensions['B'].width = 12
	ws.column_dimensions['C'].width = 25
	ws.column_dimensions['D'].width = 14
	ws.column_dimensions['E'].width = 28
	ws.column_dimensions['F'].width = 15
	ws.column_dimensions['G'].width = 25
	
	thin_border = Border(
		left=Side(border_style="thin", color="000000"),
		right=Side(border_style="thin", color="000000"),
		top=Side(border_style="thin", color="000000"),
		bottom=Side(border_style="thin", color="000000")
	)
	
	for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
		for cell in row:
			cell.border = thin_border
	last_row = ws.max_row
	ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=3)
	
	
def get_loan_data_visa(args):
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	additional_salaries = frappe.db.sql("""
		SELECT
			asr.employee,
			asr.employee_name,
			asr.amount,
			asr.ref_docname,
			emp.custom_division,
			emp.custom_region
		FROM
			`tabAdditional Salary` asr
		INNER JOIN `tabEmployee` emp
			ON emp.name = asr.employee
		WHERE
			asr.docstatus = 1
			AND (
				(asr.is_recurring = 0 AND asr.payroll_date BETWEEN %s AND %s)
				OR
				(asr.is_recurring = 1 AND %s BETWEEN asr.from_date AND asr.to_date)
			)
			AND asr.ref_doctype = 'Employee Advance'
			AND asr.company = %s
			AND asr.salary_component = 'Loan / Advance'
			AND emp.custom_employee_category = 'Visa'
			
		""",
		(from_date, to_date, from_date, company),
		as_dict=True
	)

	result = []
	for asr in additional_salaries:
		result.append({
			"employee": asr.employee,
			"employee_name": asr.employee_name,
			"ref_docname": asr.ref_docname,
			"amount": asr.amount,
			"division": asr.custom_division,
			"region": asr.custom_region,
		})

	return result

def get_loan_data_non_visa(args):
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	additional_salaries = frappe.db.sql("""
		SELECT
			asr.employee,
			asr.employee_name,
			asr.amount,
			asr.ref_docname,
			emp.custom_division,
			emp.custom_region
		FROM
			`tabAdditional Salary` asr
		INNER JOIN `tabEmployee` emp
			ON emp.name = asr.employee
		WHERE
			asr.docstatus = 1
			AND (
				(asr.is_recurring = 0 AND asr.payroll_date BETWEEN %s AND %s)
				OR
				(asr.is_recurring = 1 AND %s BETWEEN asr.from_date AND asr.to_date)
			)
			AND asr.ref_doctype = 'Employee Advance'
			AND asr.company = %s
			AND asr.salary_component = 'Loan / Advance'
			AND emp.custom_employee_category = 'Non Visa'
			
		""",
		(from_date, to_date, from_date, company),
		as_dict=True
	)

	result = []
	for asr in additional_salaries:
		result.append({
			"employee": asr.employee,
			"employee_name": asr.employee_name,
			"ref_docname": asr.ref_docname,
			"amount": asr.amount,
			"division": asr.custom_division,
			"region": asr.custom_region,
		})

	return result

def advance_excel_visa(wb, sheet_name="Employee Advance Breakup (Visa)"):
	NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'
	
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	ws = wb.create_sheet(sheet_name)
	formatted_from_date = py_datetime.datetime.strptime(from_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	formatted_to_date = py_datetime.datetime.strptime(to_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	header1 = [f'Employee Advance Deduction for the period {formatted_from_date} - {formatted_to_date}', '', '', '', '', '', '']
	header2 = ['Sr No', 'Employee', 'Employee Name', 'Region', 'Division', 'Amount', 'Employee Advance ID']
	
	ws.append(header1)
	ws.append(header2)
	
	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
	
	light_blue_fill = PatternFill("solid", fgColor="ADD8E6") 
	dark_blue_fill = PatternFill("solid", fgColor="1F4E79") 
	white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
	black_bold_font = Font(bold=True, color="000000", name="Calibri", size=10)
	
	for col in range(1, 8):  
		ws.cell(row=1, column=col).fill = light_blue_fill
		ws.cell(row=1, column=col).font = black_bold_font
	
	for col in range(1, 8):  
		ws.cell(row=2, column=col).fill = dark_blue_fill
		ws.cell(row=2, column=col).font = white_bold_font

	sr_no = 1
	total_amnt = 0  

	for d in get_loan_data_visa(args):        
		ws.append([
			sr_no,
			d['employee'],        
			d['employee_name'],       
			d['region'] or '',
			d['division'] or '',
			d['amount'],      
			d['ref_docname'],
		])
		
		sr_no += 1
		total_amnt += d['amount'] or 0
		
		cell = ws.cell(row=ws.max_row, column=6)
		cell.number_format = NUMBER_FORMAT
		
	ws.append(["Total", "", "", "", "", total_amnt, ""])

	cell = ws.cell(row=ws.max_row, column=6)
	cell.number_format = NUMBER_FORMAT
	cell.font = Font(bold=True, color="000000")

	ws.column_dimensions['A'].width = 5
	ws.column_dimensions['B'].width = 12
	ws.column_dimensions['C'].width = 25
	ws.column_dimensions['D'].width = 14
	ws.column_dimensions['E'].width = 28
	ws.column_dimensions['F'].width = 15
	ws.column_dimensions['G'].width = 25
	
	thin_border = Border(
		left=Side(border_style="thin", color="000000"),
		right=Side(border_style="thin", color="000000"),
		top=Side(border_style="thin", color="000000"),
		bottom=Side(border_style="thin", color="000000")
	)
	
	for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
		for cell in row:
			cell.border = thin_border
	last_row = ws.max_row
	ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=3)

def advance_excel_non_visa(wb, sheet_name="Employee Advance Breakup (Non Visa)"):
	NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'
	
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	ws = wb.create_sheet(sheet_name)
	formatted_from_date = py_datetime.datetime.strptime(from_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	formatted_to_date = py_datetime.datetime.strptime(to_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	header1 = [f'Employee Advance Deduction for the period {formatted_from_date} - {formatted_to_date}', '', '', '', '', '', '']
	header2 = ['Sr No', 'Employee', 'Employee Name', 'Region', 'Division', 'Amount', 'Employee Advance ID']
	
	ws.append(header1)
	ws.append(header2)
	
	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
	
	light_blue_fill = PatternFill("solid", fgColor="ADD8E6") 
	dark_blue_fill = PatternFill("solid", fgColor="1F4E79") 
	white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
	black_bold_font = Font(bold=True, color="000000", name="Calibri", size=10)
	
	for col in range(1, 8):  
		ws.cell(row=1, column=col).fill = light_blue_fill
		ws.cell(row=1, column=col).font = black_bold_font
	
	for col in range(1, 8):  
		ws.cell(row=2, column=col).fill = dark_blue_fill
		ws.cell(row=2, column=col).font = white_bold_font

	sr_no = 1
	total_amnt = 0  

	for d in get_loan_data_non_visa(args):        
		ws.append([
			sr_no,
			d['employee'],        
			d['employee_name'],       
			d['region'] or '',
			d['division'] or '',
			d['amount'],      
			d['ref_docname'],
		])
		
		sr_no += 1
		total_amnt += d['amount'] or 0
		
		cell = ws.cell(row=ws.max_row, column=6)
		cell.number_format = NUMBER_FORMAT
		
	ws.append(["Total", "", "", "", "", total_amnt, ""])

	cell = ws.cell(row=ws.max_row, column=6)
	cell.number_format = NUMBER_FORMAT
	cell.font = Font(bold=True, color="000000")

	ws.column_dimensions['A'].width = 5
	ws.column_dimensions['B'].width = 12
	ws.column_dimensions['C'].width = 25
	ws.column_dimensions['D'].width = 14
	ws.column_dimensions['E'].width = 28
	ws.column_dimensions['F'].width = 15
	ws.column_dimensions['G'].width = 25
	
	thin_border = Border(
		left=Side(border_style="thin", color="000000"),
		right=Side(border_style="thin", color="000000"),
		top=Side(border_style="thin", color="000000"),
		bottom=Side(border_style="thin", color="000000")
	)
	
	for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
		for cell in row:
			cell.border = thin_border
	last_row = ws.max_row
	ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=3)

def vacation_excel_visa(wb, sheet_name="Employee Vacation Breakup (Visa)"):
	NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'
	
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	ws = wb.create_sheet(sheet_name)
	formatted_from_date = py_datetime.datetime.strptime(from_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	formatted_to_date = py_datetime.datetime.strptime(to_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	header1 = [f'Employee Vacation Paid for the period {formatted_from_date} - {formatted_to_date}', '', '', '', '', '', '']
	header2 = ['Sr No', 'Employee', 'Employee Name', 'Region', 'Division', 'Amount', 'Leave Application ID']
	
	ws.append(header1)
	ws.append(header2)
	
	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
	
	light_blue_fill = PatternFill("solid", fgColor="ADD8E6") 
	dark_blue_fill = PatternFill("solid", fgColor="1F4E79") 
	white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
	black_bold_font = Font(bold=True, color="000000", name="Calibri", size=10)
	
	for col in range(1, 8):  
		ws.cell(row=1, column=col).fill = light_blue_fill
		ws.cell(row=1, column=col).font = black_bold_font
	
	for col in range(1, 8):  
		ws.cell(row=2, column=col).fill = dark_blue_fill
		ws.cell(row=2, column=col).font = white_bold_font

	sr_no = 1
	total_amnt = 0  

	for d in get_vacation_data_visa(args):        
		ws.append([
			sr_no,
			d['employee'],        
			d['employee_name'],       
			d['region'] or '',
			d['division'] or '',
			d['amount'],      
			d['ref_docname'],
		])
		
		sr_no += 1
		total_amnt += d['amount'] or 0
		
		cell = ws.cell(row=ws.max_row, column=6)
		cell.number_format = NUMBER_FORMAT
		
	ws.append(["Total", "", "", "", "", total_amnt, ""])

	cell = ws.cell(row=ws.max_row, column=6)
	cell.number_format = NUMBER_FORMAT
	cell.font = Font(bold=True, color="000000")

	ws.column_dimensions['A'].width = 5
	ws.column_dimensions['B'].width = 12
	ws.column_dimensions['C'].width = 25
	ws.column_dimensions['D'].width = 14
	ws.column_dimensions['E'].width = 28
	ws.column_dimensions['F'].width = 15
	ws.column_dimensions['G'].width = 25
	
	thin_border = Border(
		left=Side(border_style="thin", color="000000"),
		right=Side(border_style="thin", color="000000"),
		top=Side(border_style="thin", color="000000"),
		bottom=Side(border_style="thin", color="000000")
	)
	
	for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
		for cell in row:
			cell.border = thin_border
	last_row = ws.max_row
	ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=3)

def vacation_excel_non_visa(wb, sheet_name="Employee Vacation Breakup (Non Visa)"):
	NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'
	
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	ws = wb.create_sheet(sheet_name)
	formatted_from_date = py_datetime.datetime.strptime(from_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	formatted_to_date = py_datetime.datetime.strptime(to_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	header1 = [f'Employee Vacation Paid for the period {formatted_from_date} - {formatted_to_date}', '', '', '', '', '', '']
	header2 = ['Sr No', 'Employee', 'Employee Name', 'Region', 'Division', 'Amount', 'Leave Application ID']
	
	ws.append(header1)
	ws.append(header2)
	
	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
	
	light_blue_fill = PatternFill("solid", fgColor="ADD8E6") 
	dark_blue_fill = PatternFill("solid", fgColor="1F4E79") 
	white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
	black_bold_font = Font(bold=True, color="000000", name="Calibri", size=10)
	
	for col in range(1, 8):  
		ws.cell(row=1, column=col).fill = light_blue_fill
		ws.cell(row=1, column=col).font = black_bold_font
	
	for col in range(1, 8):  
		ws.cell(row=2, column=col).fill = dark_blue_fill
		ws.cell(row=2, column=col).font = white_bold_font

	sr_no = 1
	total_amnt = 0  

	for d in get_vacation_data_non_visa(args):        
		ws.append([
			sr_no,
			d['employee'],        
			d['employee_name'],       
			d['region'] or '',
			d['division'] or '',
			d['amount'],      
			d['ref_docname'],
		])
		
		sr_no += 1
		total_amnt += d['amount'] or 0
		
		cell = ws.cell(row=ws.max_row, column=6)
		cell.number_format = NUMBER_FORMAT
		
	ws.append(["Total", "", "", "", "", total_amnt, ""])

	cell = ws.cell(row=ws.max_row, column=6)
	cell.number_format = NUMBER_FORMAT
	cell.font = Font(bold=True, color="000000")

	ws.column_dimensions['A'].width = 5
	ws.column_dimensions['B'].width = 12
	ws.column_dimensions['C'].width = 25
	ws.column_dimensions['D'].width = 14
	ws.column_dimensions['E'].width = 28
	ws.column_dimensions['F'].width = 15
	ws.column_dimensions['G'].width = 25
	
	thin_border = Border(
		left=Side(border_style="thin", color="000000"),
		right=Side(border_style="thin", color="000000"),
		top=Side(border_style="thin", color="000000"),
		bottom=Side(border_style="thin", color="000000")
	)
	
	for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
		for cell in row:
			cell.border = thin_border
	last_row = ws.max_row
	ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=3)
def get_vacation_data_visa(args):
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	additional_salaries = frappe.db.sql("""
		SELECT
			asr.employee,
			asr.employee_name,
			asr.amount,
			asr.ref_docname,
			emp.custom_division,
			emp.custom_region
		FROM
			`tabAdditional Salary` asr
		INNER JOIN `tabEmployee` emp
			ON emp.name = asr.employee
		WHERE
			asr.docstatus = 1
			AND asr.payroll_date BETWEEN %s AND %s
			AND asr.company = %s
			AND asr.salary_component = 'Vacation Pay'
			AND emp.custom_employee_category = 'Visa'
		""",
		(from_date, to_date, company),
		as_dict=True
	)

	result = []
	for asr in additional_salaries:
		result.append({
			"employee": asr.employee,
			"employee_name": asr.employee_name,
			"ref_docname": asr.ref_docname,
			"amount": asr.amount,
			"division": asr.custom_division,
			"region": asr.custom_region,
		})

	return result

def get_vacation_data_non_visa(args):
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	additional_salaries = frappe.db.sql("""
		SELECT
			asr.employee,
			asr.employee_name,
			asr.amount,
			asr.ref_docname,
			emp.custom_division,
			emp.custom_region
		FROM
			`tabAdditional Salary` asr
		INNER JOIN `tabEmployee` emp
			ON emp.name = asr.employee
		WHERE
			asr.docstatus = 1
			AND asr.payroll_date BETWEEN %s AND %s
			AND asr.company = %s
			AND asr.salary_component = 'Vacation Pay'
			AND emp.custom_employee_category = 'Non Visa'
		""",
		(from_date, to_date, company),
		as_dict=True
	)

	result = []
	for asr in additional_salaries:
		result.append({
			"employee": asr.employee,
			"employee_name": asr.employee_name,
			"ref_docname": asr.ref_docname,
			"amount": asr.amount,
			"division": asr.custom_division,
			"region": asr.custom_region,
		})

	return result

def traffic_fines_excel_visa(wb, sheet_name="Traffic Fines Breakup (Visa)"):
	NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'
	
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	ws = wb.create_sheet(sheet_name)
	formatted_from_date = py_datetime.datetime.strptime(from_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	formatted_to_date = py_datetime.datetime.strptime(to_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	header1 = [f'Fines Deducted for the period {formatted_from_date} - {formatted_to_date}', '', '', '', '', '']
	header2 = ['Sr No', 'Employee', 'Employee Name', 'Region', 'Division', 'Amount']
	
	ws.append(header1)
	ws.append(header2)
	
	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
	
	light_blue_fill = PatternFill("solid", fgColor="ADD8E6") 
	dark_blue_fill = PatternFill("solid", fgColor="1F4E79") 
	white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
	black_bold_font = Font(bold=True, color="000000", name="Calibri", size=10)
	
	for col in range(1, 7):  
		ws.cell(row=1, column=col).fill = light_blue_fill
		ws.cell(row=1, column=col).font = black_bold_font
	
	for col in range(1, 7):  
		ws.cell(row=2, column=col).fill = dark_blue_fill
		ws.cell(row=2, column=col).font = white_bold_font

	sr_no = 1
	total_amnt = 0  

	for d in get_fine_data_visa(args):
		ws.append([
			sr_no,
			d['employee'],
			d['employee_name'],
			d['region'] or '',
			d['division'] or '',
			d['amount'],
		])

		sr_no += 1
		total_amnt += d['amount'] or 0

		ws.cell(row=ws.max_row, column=6).number_format = NUMBER_FORMAT

		
	ws.append(["Total", "", "", "", "", total_amnt])

	cell = ws.cell(row=ws.max_row, column=6)
	cell.number_format = NUMBER_FORMAT
	cell.font = Font(bold=True, color="000000")

	ws.column_dimensions['A'].width = 5
	ws.column_dimensions['B'].width = 12
	ws.column_dimensions['C'].width = 25
	ws.column_dimensions['D'].width = 14
	ws.column_dimensions['E'].width = 28
	ws.column_dimensions['F'].width = 15
	
	thin_border = Border(
		left=Side(border_style="thin", color="000000"),
		right=Side(border_style="thin", color="000000"),
		top=Side(border_style="thin", color="000000"),
		bottom=Side(border_style="thin", color="000000")
	)
	
	for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
		for cell in row:
			cell.border = thin_border
	last_row = ws.max_row
	ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=3)

def traffic_fines_excel_non_visa(wb, sheet_name="Traffic Fines Breakup (Non Visa)"):
	NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'
	
	args = frappe.local.form_dict
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	ws = wb.create_sheet(sheet_name)
	formatted_from_date = py_datetime.datetime.strptime(from_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	formatted_to_date = py_datetime.datetime.strptime(to_date, '%Y-%m-%d').strftime('%d/%m/%Y')
	header1 = [f'Fines Deducted for the period {formatted_from_date} - {formatted_to_date}', '', '', '', '', '']
	header2 = ['Sr No', 'Employee', 'Employee Name', 'Region', 'Division', 'Amount']
	
	ws.append(header1)
	ws.append(header2)
	
	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
	
	light_blue_fill = PatternFill("solid", fgColor="ADD8E6") 
	dark_blue_fill = PatternFill("solid", fgColor="1F4E79") 
	white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
	black_bold_font = Font(bold=True, color="000000", name="Calibri", size=10)
	
	for col in range(1, 7):  
		ws.cell(row=1, column=col).fill = light_blue_fill
		ws.cell(row=1, column=col).font = black_bold_font
	
	for col in range(1, 7):  
		ws.cell(row=2, column=col).fill = dark_blue_fill
		ws.cell(row=2, column=col).font = white_bold_font

	sr_no = 1
	total_amnt = 0  

	for d in get_fine_data_non_visa(args):
		ws.append([
			sr_no,
			d['employee'],
			d['employee_name'],
			d['region'] or '',
			d['division'] or '',
			d['amount'],
		])

		sr_no += 1
		total_amnt += d['amount'] or 0

		ws.cell(row=ws.max_row, column=6).number_format = NUMBER_FORMAT

		
	ws.append(["Total", "", "", "", "", total_amnt])

	cell = ws.cell(row=ws.max_row, column=6)
	cell.number_format = NUMBER_FORMAT
	cell.font = Font(bold=True, color="000000")

	ws.column_dimensions['A'].width = 5
	ws.column_dimensions['B'].width = 12
	ws.column_dimensions['C'].width = 25
	ws.column_dimensions['D'].width = 14
	ws.column_dimensions['E'].width = 28
	ws.column_dimensions['F'].width = 15
	
	thin_border = Border(
		left=Side(border_style="thin", color="000000"),
		right=Side(border_style="thin", color="000000"),
		top=Side(border_style="thin", color="000000"),
		bottom=Side(border_style="thin", color="000000")
	)
	
	for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
		for cell in row:
			cell.border = thin_border
	last_row = ws.max_row
	ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=3)
def get_fine_data_visa(args):
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	additional_salaries = frappe.db.sql("""
		SELECT
			asr.employee,
			asr.employee_name,
			asr.amount,                         
			asr.ref_docname,
			emp.custom_division,
			emp.custom_region
																
		FROM
			`tabAdditional Salary` asr
		INNER JOIN `tabEmployee` emp
			ON emp.name = asr.employee
		WHERE
			asr.docstatus=1
			AND (
				(asr.is_recurring = 0 AND asr.payroll_date BETWEEN %s AND %s)
				OR
				(asr.is_recurring = 1 AND %s BETWEEN asr.from_date AND asr.to_date)
			)
			AND asr.company = %s
			AND asr.salary_component = "Traffic Fines"
			AND emp.custom_employee_category = 'Visa'
		""", 
		(from_date, to_date, from_date, company), as_dict=True)
	
	result = []

	for asr in additional_salaries:
		
		result.append({
			'employee': asr['employee'],
			'employee_name': asr['employee_name'],
			'amount': asr['amount'],
			'division': asr['custom_division'],
			'region': asr['custom_region'],
		})

	return result

def get_fine_data_non_visa(args):
	from_date = args.get("from_date")
	to_date = args.get("to_date")
	company = args.get("company")

	additional_salaries = frappe.db.sql("""
		SELECT
			asr.employee,
			asr.employee_name,
			asr.amount,                         
			asr.ref_docname,
			emp.custom_division,
			emp.custom_region
																
		FROM
			`tabAdditional Salary` asr
		INNER JOIN `tabEmployee` emp
			ON emp.name = asr.employee
		WHERE
			asr.docstatus=1
			AND (
				(asr.is_recurring = 0 AND asr.payroll_date BETWEEN %s AND %s)
				OR
				(asr.is_recurring = 1 AND %s BETWEEN asr.from_date AND asr.to_date)
			)
			AND asr.company = %s
			AND asr.salary_component = "Traffic Fines"
			AND emp.custom_employee_category = 'Non Visa'
		""", 
		(from_date, to_date, from_date, company), as_dict=True)
	
	result = []

	for asr in additional_salaries:
		
		result.append({
			'employee': asr['employee'],
			'employee_name': asr['employee_name'],
			'amount': asr['amount'],
			'division': asr['custom_division'],
			'region': asr['custom_region'],
		})

	return result