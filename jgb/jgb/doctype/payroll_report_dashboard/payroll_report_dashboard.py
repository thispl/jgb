# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import datetime
import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, today
from frappe.utils.csvutils import build_csv_response
from six import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side


class PayrollReportDashboard(Document):
    pass


@frappe.whitelist()
def download_dynamic_wps_report(from_date=None, to_date=None, company=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "WPS Report"

    thin = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    company_name = company or "Joint Global Business Co LLC"
    
    ws["A1"] = "Bank"
    ws["A1"].alignment = Alignment(horizontal="center")
    ws["A1"].border = thin

    ws["B1"] = "Account Number"
    ws["B1"].alignment = Alignment(horizontal="center")
    ws["B1"].border = thin

    ws["C1"] = "Total Salary"
    ws["C1"].alignment = Alignment(horizontal="center")
    ws["C1"].border = thin

    ws["D1"] = "Transaction Reference"
    ws["D1"].alignment = Alignment(horizontal="center")
    ws["D1"].border = thin

    ws["E1"] = "Employee Name"
    ws["E1"].alignment = Alignment(horizontal="center")
    ws["E1"].border = thin

    ws["F1"] = "National ID/Iqama ID"
    ws["F1"].alignment = Alignment(horizontal="center")
    ws["F1"].border = thin

    ws["G1"] = "Employee Address"
    ws["G1"].alignment = Alignment(horizontal="center")
    ws["G1"].border = thin

    ws["H1"] = "Basic Salary"
    ws["H1"].alignment = Alignment(horizontal="center")
    ws["H1"].border = thin

    ws["I1"] = "Housing Allowance"
    ws["I1"].alignment = Alignment(horizontal="center")
    ws["I1"].border = thin

    ws["J1"] = "Other Earnings"
    ws["J1"].alignment = Alignment(horizontal="center")
    ws["J1"].border = thin

    ws["K1"] = "Deductions"
    ws["K1"].alignment = Alignment(horizontal="center")
    ws["K1"].border = thin
    
    column_widths = {
        "A": 15,   
        "B": 20,   
        "C": 15,   
        "D": 25,   
        "E": 35,   
        "F": 20,   
        "G": 35,   
        "H": 15,   
        "I": 18,  
        "J": 18,  
        "K": 15    
    }

    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width
    
    from_date_obj = datetime.datetime.strptime(from_date, "%Y-%m-%d").date()
    month_year_label = "Salary " + from_date_obj.strftime("%b %Y")
    
    filters = {"start_date": from_date, "end_date": to_date, 'docstatus': ('!=', 2)}
    if company:
        filters["company"] = company
    frappe.log_error('filters', filters)
    salary_slips = frappe.get_all(
        "Salary Slip",
        filters=filters,
        fields=["name", "employee", "employee_name", "gross_pay", "designation", "payment_days"]
    )
    
    row = 2  

    for slip in salary_slips:
        ss = frappe.get_doc("Salary Slip", slip.name)

        basic_salary = 0
        housing_allowance = 0
        other_earnings = 0
        total_deductions = 0

        for earning in ss.earnings:
            if earning.salary_component.lower() == "basic":
                basic_salary = earning.amount
            elif earning.salary_component.lower() in ["housing allowance", "hra"]:
                housing_allowance = earning.amount
            else:
                other_earnings += earning.amount

        for ded in ss.deductions:
            total_deductions += ded.amount

        ws[f"A{row}"] = frappe.db.get_value("Employee", {"name": ss.employee}, "custom_bank_short_code") or ""        
        ws[f"B{row}"] = frappe.db.get_value("Employee", {"name": ss.employee}, "bank_ac_no") or ""
        ws[f"C{row}"] = ss.net_pay
        ws[f"D{row}"] = month_year_label
        ws[f"E{row}"] = ss.employee_name
        ws[f"F{row}"] = frappe.db.get_value("Employee", {"name": ss.employee}, "custom_iqama_id") or ""
        ws[f"G{row}"] = frappe.db.get_value("Employee", {"name": ss.employee}, "current_address") or ""
        ws[f"H{row}"] = basic_salary
        ws[f"I{row}"] = housing_allowance
        ws[f"J{row}"] = other_earnings
        ws[f"K{row}"] = total_deductions

        right_align_columns = ["C", "F", "H", "I", "J", "K"]

        for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            cell = ws[f"{col}{row}"]
            cell.border = thin
            if col in right_align_columns:
                cell.alignment = Alignment(horizontal="right")
            else:
                cell.alignment = Alignment(horizontal="left")
        row += 1        

    file_data = BytesIO()
    wb.save(file_data)
    file_data.seek(0)
    frappe.local.response.filename = "WPS Report.xlsx"
    frappe.local.response.filecontent = file_data.getvalue()
    frappe.local.response.type = "download"


@frappe.whitelist()
def download_bank_statements_report(from_date=None, to_date=None, company=None):
    args = frappe.local.form_dict
    from_date = from_date or args.get("from_date")
    to_date = to_date or args.get("to_date")
    company = company or args.get("company")

    headers = [
        "Bank",
        "Account Number",
        "Total Salary",
        "Transaction Reference",
        "Employee Name",
        "National ID/Iqama ID",
        "Employee Address",
        "Basic Salary",
        "Housing Allowance",
        "Other Earnings",
        "Deductions",
    ]

    # Query matching Salary Slips
    filters = {"docstatus": ("!=", 2)}
    if from_date and to_date:
        filters["start_date"] = (">=", from_date)
        filters["end_date"] = ("<=", to_date)
    elif from_date:
        filters["start_date"] = (">=", from_date)
    elif to_date:
        filters["end_date"] = ("<=", to_date)

    if company:
        filters["company"] = company

    salary_slips = frappe.get_all(
        "Salary Slip",
        filters=filters,
        fields=["name", "employee", "employee_name", "start_date", "net_pay", "total_deduction"],
        order_by="employee asc"
    )

    def format_num(val):
        if val is None or val == "":
            return 0
        v = flt(val)
        if v == int(v):
            return int(v)
        return round(v, 2)

    csv_data = [headers]

    for slip in salary_slips:
        ss = frappe.get_doc("Salary Slip", slip.name)

        emp_details = frappe.db.get_value(
            "Employee",
            {"name": ss.employee},
            ["bank_name", "custom_bank_short_code", "bank_ac_no", "custom_iqama_id", "current_address", "employee_name"],
            as_dict=True
        ) or {}

        bank = emp_details.get("custom_bank_short_code") or emp_details.get("bank_name") or ""
        account_number = emp_details.get("bank_ac_no") or ""
        total_salary = format_num(ss.net_pay)

        ref_date = getdate(ss.start_date) if ss.start_date else (getdate(from_date) if from_date else getdate(today()))
        transaction_reference = f"Salary {ref_date.strftime('%b %Y')}"

        employee_name = ss.employee_name or emp_details.get("employee_name") or ""
        national_id = emp_details.get("custom_iqama_id") or ""
        employee_address = emp_details.get("current_address") or ""

        basic_salary = 0.0
        housing_allowance = 0.0
        other_earnings = 0.0

        for earning in getattr(ss, "earnings", []):
            comp = (earning.salary_component or "").strip().lower()
            if comp == "basic":
                basic_salary += flt(earning.amount)
            elif comp in ["housing allowance", "hra"]:
                housing_allowance += flt(earning.amount)
            else:
                other_earnings += flt(earning.amount)

        total_deduction = flt(ss.total_deduction or 0.0)

        csv_data.append([
            bank,
            str(account_number),
            total_salary,
            transaction_reference,
            employee_name,
            str(national_id) if national_id else "",
            employee_address,
            format_num(basic_salary),
            format_num(housing_allowance),
            format_num(other_earnings),
            format_num(total_deduction),
        ])

    build_csv_response(csv_data, "Bank Statement")
