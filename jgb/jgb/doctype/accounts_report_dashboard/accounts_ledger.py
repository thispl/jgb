from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, add_days, date_diff, getdate, format_date
from frappe import _, bold
from frappe.utils.csvutils import UnicodeWriter, read_csv_content
from frappe.utils.data import format_date
from frappe.utils.file_manager import get_file
from frappe.model import document
from frappe.utils.background_jobs import enqueue

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

from jgb.jgb.doctype.accounts_report_dashboard.report_styles import *

@frappe.whitelist()
def download():
    filename = 'Accounts Ledger Summary Report'
    limit = frappe.db
    test = build_xlsx_response(filename)
def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
    args = frappe.local.form_dict
    column_widths = column_widths or []
    if wb is None:
        wb = openpyxl.Workbook()
    ws = wb.create_sheet(sheet_name, 0)
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 20
    ws.column_dimensions['H'].width = 10
    ws.column_dimensions['I'].width = 10
    ws.column_dimensions['J'].width = 10
    ws.column_dimensions['K'].width = 10
    data2=for_limit(args)
    company = frappe.db.get_value('Company',{'name':args.company},'parent_company')
    if(company):
        ws.append([company," "," "," "," "," "," ","","","",""])
        ws.append([args.company," "," "," "," "," "," ","","","",""])
    else:
        ws.append([args.company," "," "," "," "," "," ","","","",""])
        ws.append([""," "," "," "," "," "," ","","","",""])
    customer_name = frappe.db.get_value("Customer",args.customer,"customer_name")
    ws.append(['','SOA :',customer_name,'','','Credit Limit :',str(data2)])
    date = datetime.now()
    ws.append(['','Division :',args.company,'','','Posting Date :',date.strftime("%d-%m-%Y")])
    from_date_str = args.from_date
    from_date_obj = datetime.strptime(from_date_str, "%Y-%m-%d")
    formatted_from_date = from_date_obj.strftime("%d-%m-%Y")
    ws.append(['','Due Date Untill :',formatted_from_date])
    currency = frappe.db.get_value('Company', args.company, 'default_currency') or 'SAR'
    ws.append([f'Currency: {currency}'])
    currency = frappe.db.get_value('Company',args.company,'default_currency')
    ws.append(['Invoice No','Date','Age',f'Account {currency}',f'Paid {currency}',f'Credit Note {currency}',f'Outstanding {currency}','0-30','31-60','61-90','91-Above'])
    data1= accounts_ledger(args)
    for row in data1:
        ws.append(row)

    # --- Styling (shared palette from report_styles) ---
    num_cols = 11
    header_row_idx = 7
    data_start_row = 8
    data_end_row = data_start_row + len(data1) - 1
    text_cols = 3  # Invoice No, Date, Age

    # Title rows (row 1: parent company, row 2: company)
    for cell in ws[1]:
        cell.font = company_font
        cell.alignment = align_center
    for cell in ws[2]:
        cell.font = company_font
        cell.alignment = align_center

    # Info rows (rows 3-5: SOA / Division / Due Date)
    for row in ws.iter_rows(min_row=3, max_row=5, min_col=1, max_col=num_cols):
        for cell in row:
            cell.font = date_font

    # Header row styling (row 7) - dark navy fill, white bold text
    apply_header_row(ws, header_row_idx, num_cols)

    # Data rows styling
    alt_row = False
    for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=num_cols):
        row_label = str(row[0].value or '')
        is_total = row_label == 'Total'

        for i, cell in enumerate(row):
            cell.border = border_thin

            if is_total:
                cell.font = subtotal_font
                cell.fill = subtotal_fill
                cell.alignment = align_left if i < text_cols else align_right
                if i >= text_cols:
                    cell.number_format = currency_format
            else:
                cell.font = data_font
                cell.alignment = align_left if i < text_cols else align_right
                if i >= text_cols:
                    cell.number_format = currency_format
                if alt_row:
                    cell.fill = alt_row_fill

        if is_total:
            ws.merge_cells(
                start_row=row[0].row,
                start_column=1,
                end_row=row[0].row,
                end_column=text_cols
            )
            alt_row = False
        else:
            alt_row = not alt_row

    # Thin grey borders on all cells (title + info + header + data)
    for row in ws.iter_rows(min_row=1, max_row=data_end_row, min_col=1, max_col=num_cols):
        for cell in row:
            cell.border = border_thin

    # Merges (unchanged from original layout)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=11)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=11)
    ws.merge_cells(start_row=3, start_column=3, end_row=3, end_column=4)
    ws.merge_cells(start_row=3, start_column=7, end_row=3, end_column=8)
    ws.merge_cells(start_row=4, start_column=3, end_row=4, end_column=4)
    ws.merge_cells(start_row=4, start_column=7, end_row=4, end_column=8)
    ws.merge_cells(start_row=5, start_column=3, end_row=5, end_column=4)
    ws.merge_cells(start_row=5, start_column=7, end_row=5, end_column=8)
    ws.merge_cells(start_row=6, start_column=1, end_row=6, end_column=11)

    # Row heights
    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[header_row_idx].height = 25

    # Page setup - landscape, fit to width
    setup_page(ws)

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    return xlsx_file
def build_xlsx_response(filename):
    xlsx_file = make_xlsx(filename)
    frappe.response['filename'] = filename + '.xlsx'
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'

def for_limit(args):
        for_limit= frappe.db.get_value("Customer Credit Limit", {"parent": args.customer},["credit_limit"])
        return for_limit


    
def accounts_ledger(args):
    data=[]
    total_amount = 0
    total_paid = 0
    total_credit_note = 0
    total_outstanding = 0
    total_0_30 = 0
    total_31_60 = 0
    total_61_90 = 0
    total_91_above = 0
    if args.customer:
        sales_invoices = frappe.get_all("Sales Invoice", {'company': args.company, 'customer': args.customer, 'docstatus':1}, ['posting_date', 'name', 'total', 'outstanding_amount'],order_by="posting_date")
    else:
        sales_invoices = frappe.get_all("Sales Invoice", {'company': args.company, 'docstatus':1}, ['posting_date', 'name', 'total', 'outstanding_amount'],order_by="posting_date")
    if sales_invoices:
        for i in sales_invoices:
            days = date_diff(args.from_date, i.posting_date)
            if 0 <= days <= 120:
                total_amount += i.total
                total_outstanding += i.outstanding_amount
                row = [
                      i.name,i.posting_date.strftime("%d-%m-%Y"),days,float(fmt_money(round(i.total, 2)).replace(',', '')),'-','-',float(fmt_money(round(i.outstanding_amount, 2)).replace(',', '')),
                      float(fmt_money(round(i.total, 2)).replace(',', '')) if 0 <= days <= 30 else '-',
                      float(fmt_money(round(i.total, 2)).replace(',', '')) if 31 <= days <= 60 else '-',
                      float(fmt_money(round(i.total, 2)).replace(',', '')) if 61 <= days <= 90 else '-',
                      float(fmt_money(round(i.total, 2)).replace(',', '')) if 91 <= days <= 120 else '-'
                ]
                data.append(row)
                if 0 <= days <= 30:
                    total_0_30 += i.total
                if 31 <= days <= 60:
                    total_31_60 += i.total
                if 61 <= days <= 90:
                    total_61_90 += i.total
                if 91 <= days <= 120:
                    total_91_above += i.total
        data.append([
            'Total','','',float(fmt_money(round(total_amount, 2)).replace(',', '')),'-','-',
             float(fmt_money(round(total_outstanding, 2)).replace(',', '')),
             float(fmt_money(round(total_0_30, 2)).replace(',', '')),
             float(fmt_money(round(total_31_60, 2)).replace(',', '')),
             float(fmt_money(round(total_61_90, 2)).replace(',', '')),
             float(fmt_money(round(total_91_above, 2)).replace(',', ''))
        ])
    return data
