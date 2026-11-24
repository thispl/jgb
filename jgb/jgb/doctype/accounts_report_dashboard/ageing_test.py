# Copyright (c) 2024, Abdulla and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe.utils import cstr, add_days, date_diff, getdate, format_date
from frappe import _, bold
from frappe.utils.csvutils import UnicodeWriter, read_csv_content
from frappe.utils.data import format_date
from frappe.utils.file_manager import get_file
from frappe.model import document
from frappe.utils.background_jobs import enqueue
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from datetime import date, timedelta, datetime
import openpyxl
from openpyxl import Workbook
import re
from frappe import _
import frappe
from frappe.model import document
from datetime import date, timedelta, datetime,time
from frappe.utils import (getdate, cint, add_months, date_diff, add_days,
    nowdate, get_datetime_str, cstr, get_datetime, now_datetime, format_datetime,today, format_date)
import math
from frappe.utils import add_months, cint, flt, getdate, time_diff_in_hours,time_diff_in_seconds
import locale


import openpyxl
import xlrd
import re
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import GradientFill, PatternFill
from six import BytesIO, string_types
import openpyxl.styles as styles
from frappe.utils import flt, fmt_money

@frappe.whitelist()
def download():
    filename = 'Accounts Receivable Aging Report'
    build_xlsx_response(filename)

@frappe.whitelist()
def download_excel():
    """Excel export matching the Accounts Aging Summary print format."""
    filename = 'Accounts Aging Summary by Sales Person'
    build_xlsx_response(filename)

def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
    args = frappe.local.form_dict
    column_widths = column_widths or []
    if wb is None:
        wb = openpyxl.Workbook()
    sheet_name = sheet_name or 'Accounts Aging Summary by Sales Person'
    ws = wb.create_sheet(sheet_name, 0)
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])
    widths = [13, 25, 20, 15, 15, 15, 15, 10, 12, 12, 12, 12]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width

    report_data = accounts_aging(args) or []

    ws.append([args.get('company') or ''])
    ws.append(['Accounts Receivable Aging Report by Sales Person'])
    if args.get("to_date"):
        report_date = format_date(args.get("to_date"))
    else:
        report_date = datetime.now().strftime('%d-%m-%Y')

    ws.append(['Report Date: ' + report_date])
    ws.append([])

    headers = [
        'Posting Date', 'Voucher No', 'Customer LPO',
        'Invoiced', 'Paid', 'Credit Note',
        'Outstanding', 'Age', '0-30', '31-60', '61-90', 'Above 90'
    ]
    ws.append(headers)

    for row in report_data:
        ws.append(row)

    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_right = Alignment(horizontal='right', vertical='bottom', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='bottom', wrap_text=True)
    customer_fill = PatternFill(start_color='E8ECF7', end_color='E8ECF7', fill_type='solid')
    header_fill = PatternFill(start_color='0F0F5C', end_color='0F0F5C', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    title_font = Font(bold=True, size=14)
    subtotal_fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
    bold_font = Font(bold=True)
    border_thin = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    for row in ws.iter_rows(min_row=1, max_row=3, min_col=1, max_col=12):
        for cell in row:
            cell.font = title_font if cell.row == 2 else bold_font
            cell.alignment = align_center
            cell.border = border_thin

    header_row_idx = 5
    for cell in ws[header_row_idx]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        cell.border = border_thin

    data_start_row = 6
    data_end_row = data_start_row + len(report_data) - 1
    for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=12):
        row_label = str(row[0].value or '')
        is_sales_person = row_label.startswith("SALESPERSON:")
        is_customer = row_label.startswith("CUSTOMER:")
        is_subtotal = row_label.startswith("Subtotal:")
        is_grand_total = row_label == "GRAND TOTAL"

        for i, cell in enumerate(row):
            cell.border = border_thin
            if is_sales_person:
                cell.font = Font(bold=True, size=14)
                cell.fill = subtotal_fill
                cell.alignment = align_center

            elif is_customer:
                cell.font = Font(bold=True, size=12, italic=True)
                cell.fill = customer_fill
                cell.alignment = align_left

            elif is_subtotal or is_grand_total:
                cell.font = bold_font
                cell.fill = subtotal_fill
                cell.alignment = align_left if i < 3 else align_right

            else:
                cell.alignment = align_left if i < 3 else (align_center if i == 2 else align_right)

        if is_sales_person or is_customer:
            ws.merge_cells(
                start_row=row[0].row,
                start_column=1,
                end_row=row[0].row,
                end_column=12
            )

        elif is_subtotal or is_grand_total:
            ws.merge_cells(
                start_row=row[0].row,
                start_column=1,
                end_row=row[0].row,
                end_column=8 
            )

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=12)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=12)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=12)

    ws.page_setup.orientation = 'landscape'

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    return xlsx_file

def build_xlsx_response(filename):
    xlsx_file = make_xlsx(filename)
    frappe.response['filename'] = filename + '.xlsx'
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'

def accounts_aging(args):
    company = args.get("company")
    to_date = args.get("to_date")
    
    # 1. Fetch Sales Orders
    so_filters = {"docstatus": 1, "company": company}
    if to_date: so_filters["transaction_date"] = ["<=", to_date]
    
    so_list = frappe.get_all("Sales Order", 
        filters=so_filters, 
        fields=["name", "transaction_date", "grand_total", "custom_sales_personuser", "customer_name"])

    if not so_list: return []

    so_names = [so.name for so in so_list]
    invoices = frappe.db.sql("""
        SELECT DISTINCT si.name, si.grand_total, si.outstanding_amount, si.is_return, sii.sales_order
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE sii.sales_order IN %s AND si.docstatus = 1
    """, (tuple(so_names),), as_dict=True)
    
    processed_data = []
    for so in so_list:
        so_invoices = [inv for inv in invoices if inv.sales_order == so.name]

        invoiced = so.grand_total  # order value

        total_credit_notes = sum(i.grand_total for i in so_invoices if i.is_return)

        total_paid = 0
        if so_invoices:
            invoice_names = [i.name for i in so_invoices]
            total_paid = frappe.db.sql("""
                SELECT SUM(per.allocated_amount) 
                FROM `tabPayment Entry Reference` per
                INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
                WHERE per.reference_name IN %s AND pe.docstatus = 1
            """, (tuple(invoice_names),))[0][0] or 0

        # Outstanding = Order value - Paid
        outstanding = invoiced - total_paid

        age = date_diff(today(), so.transaction_date)

        if round(outstanding, 2) != 0:
            processed_data.append({
                "sp": so.custom_sales_personuser or "Unassigned",
                "date": so.transaction_date,
                "so_name": so.name,
                "customer": so.customer_name,
                "invoiced": invoiced,
                "paid": total_paid,
                "cr_note": total_credit_notes,
                "outstanding": outstanding,
                "age": age,
                "aging": {
                    "0_30": outstanding if 0 <= age <= 30 else 0,
                    "31_60": outstanding if 31 <= age <= 60 else 0,
                    "61_90": outstanding if 61 <= age <= 90 else 0,
                    "above_90": outstanding if age > 90 else 0
                }
            })

    # Sort by Age (Oldest First)
    processed_data.sort(key=lambda x: x['age'], reverse=True)

    # Grouping: Salesperson -> Customer -> SO rows
    grouped = {}
    for item in processed_data:
        grouped.setdefault(item['sp'], {}).setdefault(item['customer'], []).append(item)

    # Final structure for Excel
    final_rows = []
    grand_totals = [0] * 4  # 0-30, 31-60, 61-90, Above 90

    for sp, customers in grouped.items():
        final_rows.append([f"SALESPERSON: {sp}"] + [""] * 11)
        sp_totals = [0] * 4

        for customer, items in customers.items():
            final_rows.append([f"CUSTOMER: {customer}"] + [""] * 11)

            for i in items:
                row = [
                    i['date'].strftime("%d-%m-%Y"), i['so_name'], i['customer'],
                    i['invoiced'], i['paid'], i['cr_note'], i['outstanding'], i['age'],
                    i['aging']["0_30"], i['aging']["31_60"], i['aging']["61_90"], i['aging']["above_90"]
                ]
                final_rows.append(row)
                sp_totals[0] += i['aging']["0_30"]
                sp_totals[1] += i['aging']["31_60"]
                sp_totals[2] += i['aging']["61_90"]
                sp_totals[3] += i['aging']["above_90"]

        final_rows.append(["Subtotal:"] + [""] * 7 + sp_totals)
        for idx, val in enumerate(sp_totals): grand_totals[idx] += val

    final_rows.append(["GRAND TOTAL"] + [""] * 7 + grand_totals)
    return final_rows