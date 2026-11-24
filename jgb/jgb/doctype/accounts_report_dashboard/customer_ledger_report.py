from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, add_days, date_diff, getdate, format_date
from frappe import _, bold
from frappe.utils.csvutils import UnicodeWriter, read_csv_content
from frappe.utils.data import format_date
from frappe.utils.file_manager import get_file
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue

from datetime import date, timedelta, datetime
import openpyxl
from openpyxl import Workbook
import re
from frappe import _
import frappe
from frappe.model.document import Document
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

from jgb.jgb.doctype.accounts_report_dashboard.report_styles import *


@frappe.whitelist()
def download():
    filename = 'Customer Ledger Summary'
    test = build_xlsx_response(filename)
    
def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
    args = frappe.local.form_dict
    column_widths = column_widths or []
    if wb is None:
        wb = openpyxl.Workbook()
        
def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
    args = frappe.local.form_dict
    column_widths = column_widths or []
    if wb is None:
        wb = openpyxl.Workbook()

    ws = wb.create_sheet(sheet_name, 0)
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 50
    company = frappe.db.get_value('Company',{'name':args.company},'parent_company')
    if(company):
        ws.append([company," "," "," "," "," "," ","","","",""])
        ws.append([args.company," "," "," "," "," "," ","","","",""])
    else:
        ws.append([args.company," "," "," "," "," "," ","","","",""])
        ws.append([""," "," "," "," "," "," ","","","",""])
    ws.append(["Customer Ledger Summary Report"," "," "," ","",""])
    from_date_str = args.from_date
    from_date_obj = datetime.strptime(from_date_str, "%Y-%m-%d")
    formatted_from_date = from_date_obj.strftime("%d-%m-%Y")
    to_date_str = args.to_date
    to_date_obj = datetime.strptime(to_date_str, "%Y-%m-%d")
    formatted_to_date = to_date_obj.strftime("%d-%m-%Y")
    header3=["For the Period From: "+ formatted_from_date +" "+"to"+" "+formatted_to_date]
    ws.append(header3 + [""] * 5)
    currency = frappe.db.get_value('Company', args.company, 'default_currency') or 'SAR'
    ws.append([f'Currency: {currency}'])
    customer_name = frappe.db.get_value("Customer",args.customer,"customer_name")

    ws.append(["Customer Name",customer_name,"","Currency",args.currency,""])
    ws.append(['Date','Voucher No','Voucher Type','Narration',"Debit","Credit"])
    ws.append(['','','','','',''])
    data1= get_data(args)
    for row in data1:
        ws.append(row)

    # --- Styling using shared report_styles ---
    num_cols = 6
    text_cols = 4  # Date, Voucher No, Voucher Type, Narration
    entries_count = len(data1) - 2  # last 2 rows are "No. of Entries:" and "Total"
    data_start_row = 9               # first entry row (after title+header+blank)
    entries_end_row = data_start_row + entries_count - 1
    subtotal_row_idx = data_start_row + entries_count        # "No. of Entries:"
    grand_total_row_idx = data_start_row + entries_count + 1  # "Total"
    last_row = grand_total_row_idx

    # Title rows: row 1-2 company, row 3 title, row 4 date
    for cell in ws[1]:
        cell.font = company_font
        cell.alignment = align_center
    for cell in ws[2]:
        cell.font = company_font
        cell.alignment = align_center
    for cell in ws[3]:
        cell.font = title_font
        cell.alignment = align_center
    for cell in ws[4]:
        cell.font = date_font
        cell.alignment = align_center

    # Customer info row (row 6)
    for cell in ws[6]:
        cell.font = bold_font
        cell.alignment = align_center
        cell.border = border_thin

    # Header row (row 7) - dark navy fill, white bold text
    apply_header_row(ws, 7, num_cols)

    # Blank spacer row (row 8) - borders only
    for cell in ws[8]:
        cell.border = border_thin

    # Data rows with alternating row colors
    alt_row = False
    if entries_count > 0:
        for row in ws.iter_rows(min_row=data_start_row, max_row=entries_end_row, min_col=1, max_col=num_cols):
            for i, cell in enumerate(row):
                cell.border = border_thin
                cell.font = data_font
                cell.alignment = align_left if i < text_cols else align_right
                if i >= text_cols:
                    cell.number_format = currency_format
                if alt_row:
                    cell.fill = alt_row_fill
            alt_row = not alt_row

    # Subtotal row ("No. of Entries:") - light blue fill, dark blue bold
    for i, cell in enumerate(ws[subtotal_row_idx]):
        cell.border = border_thin
        cell.font = subtotal_font
        cell.fill = subtotal_fill
        cell.alignment = align_left if i < text_cols else align_right
        if i >= text_cols:
            cell.number_format = currency_format

    # Grand total row ("Total") - dark navy fill, white bold
    for i, cell in enumerate(ws[grand_total_row_idx]):
        cell.border = border_thin
        cell.font = grand_total_font
        cell.fill = grand_total_fill
        cell.alignment = align_left if i < text_cols else align_right
        if i >= text_cols:
            cell.number_format = currency_format

    # Thin grey borders on all cells
    for row in ws.iter_rows(min_row=1, max_row=last_row, min_col=1, max_col=num_cols):
        for cell in row:
            cell.border = border_thin

    # Merge cells (preserve original layout)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=num_cols)
    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=num_cols)
    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=num_cols)
    ws.merge_cells(start_row=6, start_column=2, end_row=6, end_column=3)
    ws.merge_cells(start_row=6, start_column=5, end_row=6, end_column=6)
    ws.merge_cells(start_row=8, start_column=1, end_row=8, end_column=num_cols)
    ws.merge_cells(start_row=subtotal_row_idx, start_column=2, end_row=subtotal_row_idx, end_column=num_cols)
    ws.merge_cells(start_row=grand_total_row_idx, start_column=1, end_row=grand_total_row_idx, end_column=4)

    # Row heights
    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[3].height = 28
    ws.row_dimensions[4].height = 20
    ws.row_dimensions[7].height = 25

    # Page setup: landscape, fit to width
    setup_page(ws, 'landscape')

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    return xlsx_file

def get_data(args):
    row2=[]
    row3=[]
    data=[]
    credit=0
    debit=0
    currency = frappe.db.get_all("GL Entry", {'against': args.customer,'is_cancelled':0}, ['name', 'posting_date', 'account_currency', 'voucher_type', 'remarks', 'credit_in_account_currency', 'debit_in_account_currency'], order_by="posting_date")
    for cur in currency:
        row1=[]
        credit +=cur.credit_in_account_currency
        debit +=cur.debit_in_account_currency
        row1+=[cur.posting_date.strftime("%d-%m-%Y"),cur.name,cur.voucher_type,cur.remarks,float(fmt_money(cur.debit_in_account_currency).replace(',', '')),float(fmt_money(cur.credit_in_account_currency).replace(',', ''))]
        data.append(row1)
    count = frappe.db.count("GL Entry",{'against':args.customer})
    row2+=["No. of Entries:",count,"","","",""]
    row3+=["Total","","","",debit,credit]
    data.append(row2)
    data.append(row3)
    return data
    
    

def build_xlsx_response(filename):
    xlsx_file = make_xlsx(filename)
    frappe.response['filename'] = filename + '.xlsx'
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'
