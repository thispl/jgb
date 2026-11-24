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

from jgb.jgb.doctype.accounts_report_dashboard.report_styles import *

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
    test = build_xlsx_response(filename)
def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
    args = frappe.local.form_dict
    column_widths = column_widths or []
    if wb is None:
        wb = openpyxl.Workbook()
    ws = wb.create_sheet(sheet_name, 0)
    ws.column_dimensions['A'].width = 13
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 35
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 18
    ws.column_dimensions['F'].width = 18
    ws.column_dimensions['G'].width = 15
    ws.column_dimensions['H'].width = 20
    ws.column_dimensions['I'].width = 10
    ws.column_dimensions['J'].width = 12
    ws.column_dimensions['K'].width = 12
    ws.column_dimensions['L'].width = 12
    ws.column_dimensions['M'].width = 12
    company = args.company
    if company:
        ws.append([args.company," "," "," "," "," "," ","","","","","","",""])
    else:
        ws.append([args.company," "," "," "," "," "," ","","","","","","",""])
    ws.append(["Accounts Receivable Aging Report"," "," "," "," "," "," "])

    date = datetime.now()
    header2=["Report Date: "+date.strftime("%d-%m-%Y")]
    ws.append(header2 + [""] * 12)

    currency = frappe.db.get_value('Company', args.company, 'default_currency') or 'SAR'
    ws.append([f"Currency: {currency}"] + [""] * 12)

    ws.append(["Posting Date","Voucher Number","Customer","Sales Engineer","Invoiced Amount","Paid Amount","Credit Note","Outstanding Amount","Age(Days)","0-30","31-60","61-90","Above 90"])

    data1 = accounts_aging(args)
    for row in data1:
        ws.append(row)

    # --- Styling using shared report_styles ---
    num_cols = 13
    header_row_idx = 5
    data_start_row = 6
    data_end_row = data_start_row + len(data1) - 1

    # --- Title rows (rows 1-3) ---
    apply_title_rows(ws, num_cols, "Accounts Receivable Aging Report",
                     company=args.get('company'),
                     report_date=date.strftime("%d-%m-%Y"))

    # --- Header row (row 5) ---
    apply_header_row(ws, header_row_idx, num_cols)

    # --- Data rows styling ---
    alt_row = False
    for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=num_cols):
        row_label = str(row[0].value or '')
        is_subtotal = row_label.startswith("Subtotal:")
        is_grand_total = row_label == "GRAND TOTAL"

        for i, cell in enumerate(row):
            cell.border = border_thin

            if is_grand_total:
                cell.font = grand_total_font
                cell.fill = grand_total_fill
                cell.alignment = align_left if i < 4 else align_right
                if i >= 4:
                    cell.number_format = currency_format

            elif is_subtotal:
                cell.font = subtotal_font
                cell.fill = subtotal_fill
                cell.alignment = align_left if i < 4 else align_right
                if i >= 4:
                    cell.number_format = currency_format

            else:
                # Regular data row
                cell.font = data_font
                if i < 2:
                    cell.alignment = align_left
                elif i == 2:
                    cell.alignment = align_left
                else:
                    cell.alignment = align_right
                if i >= 4:
                    cell.number_format = currency_format
                if alt_row:
                    cell.fill = alt_row_fill

        if is_subtotal or is_grand_total:
            ws.merge_cells(
                start_row=row[0].row,
                start_column=1,
                end_row=row[0].row,
                end_column=4
            )
            alt_row = False
        else:
            alt_row = not alt_row

    # --- Page setup ---
    setup_page(ws, orientation='landscape')

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    return xlsx_file
def build_xlsx_response(filename):
    xlsx_file = make_xlsx(filename)
    frappe.response['filename'] = filename + '.xlsx'
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'


def accounts_aging(args):
    data = []
    conditions = ""
    values = [args.company]

    if args.get("to_date"):
        conditions += " AND posting_date <= %s "
        values.append(args.to_date)
    
    grand_in = grand_paid = grand_cn = grand_out = 0.0
    grand_0_30 = grand_31_60 = grand_61_90 = grand_above = 0.0
    customers = frappe.db.sql(f"""
        SELECT DISTINCT customer
        FROM `tabSales Invoice`
        WHERE company = %s
        AND docstatus = 1
        AND is_return = 0
        {conditions}
    """, values, as_dict=True)
    
    for cust in customers:
        in_amount = 0
        paid_amount = 0
        credit_note = 0
        out_amount = 0
        age_0_30 = 0
        age_31_60 = 0
        age_61_90 = 0
        age_above_90 = 0
        customer = cust.customer
        customer_name = frappe.db.get_value("Customer", customer, "customer_name")
        company = args.company
        in_amt, paid_amt, cn_amt, out_amt = 0, 0, 0, 0
        a0_30, a31_60, a61_90, above = 0, 0, 0, 0
        combined_data = []
        si_conditions = ""
        si_values = [company, customer]

        if args.get("to_date"):
            si_conditions += " AND posting_date <= %s "
            si_values.append(args.to_date)

        si_list = frappe.db.sql(f"""
            SELECT * FROM `tabSales Invoice`
            WHERE company = %s
            AND customer = %s
            AND docstatus = 1
            AND is_return = 0
            {si_conditions}
            ORDER BY posting_date ASC
        """, si_values, as_dict=True)

        for i in si_list:
            # Credit notes (returns) against this invoice - via return_against or custom_return_reason (Zoho migration)
            result = frappe.db.sql("""
                SELECT sum(base_grand_total) as total 
                FROM `tabSales Invoice` 
                WHERE company = %s AND docstatus = 1 AND is_return = 1
                AND (
                    return_against = %s
                    OR (custom_return_reason = %s AND (return_against IS NULL OR return_against = ''))
                )
            """, (company, i.name, i.name))
            return_amount = result[0][0] if result and result[0][0] else 0
            
            # Payments from Payment Entry
            pay = frappe.db.sql("""
                SELECT per.allocated_amount, per.exchange_rate
                FROM `tabPayment Entry Reference` AS per
                LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
                WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
            """, (company, i.name), as_dict=True)
            pe_amount = sum(j["allocated_amount"] * (j["exchange_rate"] or 1) for j in pay)

            # Payments from Journal Entry (direct JE payments against invoice, excluding credit-note linkage JEs)
            je_pay = frappe.db.sql("""
                SELECT (jva.credit - jva.debit) AS amount
                FROM `tabJournal Entry Account` AS jva
                LEFT JOIN `tabJournal Entry` AS jv ON jva.parent = jv.name
                WHERE jv.docstatus = 1
                AND jva.reference_type = 'Sales Invoice'
                AND jva.reference_name = %s
                AND NOT EXISTS (
                    SELECT 1
                    FROM `tabJournal Entry Account` AS jva2
                    LEFT JOIN `tabSales Invoice` AS si ON jva2.reference_name = si.name
                    WHERE jva2.parent = jv.name
                    AND jva2.reference_type = 'Sales Invoice'
                    AND si.is_return = 1
                    AND si.return_against = %s
                )
            """, (i.name, i.name), as_dict=True)
            je_amount = sum(j["amount"] for j in je_pay if j["amount"])

            value = pe_amount + je_amount

            if value and return_amount:
                outstanding = i.base_grand_total - value + return_amount
            elif value:
                outstanding = i.base_grand_total - value
            elif return_amount:
                outstanding = i.base_grand_total + return_amount
            else:
                outstanding = i.base_grand_total

            out_amount += outstanding
            age = date_diff(today(), i.posting_date) if i.posting_date else 0

            if abs(outstanding) > 0.01:
                if value:
                    paid_amount += value
                if return_amount:
                    credit_note += return_amount
                in_amount += i.base_grand_total

                if 0 <= age <= 30:
                    age_0_30 += outstanding
                elif 31 <= age <= 60:
                    age_31_60 += outstanding
                elif 61 <= age <= 90:
                    age_61_90 += outstanding
                else:
                    age_above_90 += outstanding

                combined_data.append({
                    'posting_date': i.posting_date,
                    'name': i.name,
                    'sales_person': i.custom_sales_personuser if i.custom_sales_personuser else '',
                    'po_no': i.po_no if i.po_no else '-',
                    'grand_total': i.base_grand_total,
                    'paid_amount': value if value else 0,
                    'credit_note': return_amount if return_amount else 0,
                    'outstanding': outstanding if outstanding else 0,
                    'age': age,
                    'oustanding_0_30':outstanding if 0 <= age <= 30 else 0,
                    'oustanding_31_60':outstanding if 31 <= age <= 60 else 0,
                    'oustanding_61_90':outstanding if 61 <= age <= 90 else 0,
                    'oustanding_above_90':outstanding if age > 90 else 0,
                })

        # Fetch standalone credit notes (returns with no return_against and no valid custom_return_reason match)
        sales_conditions = ""
        sales_values = [company, customer, company]

        if args.get("to_date"):
            sales_conditions += " AND posting_date <= %s "
            sales_values.append(args.to_date)

        sales = frappe.db.sql(f"""
            SELECT * FROM `tabSales Invoice`
            WHERE company = %s
            AND customer = %s
            AND docstatus = 1
            AND is_return = 1
            AND (return_against IS NULL OR return_against = '')
            AND (
                custom_return_reason IS NULL
                OR custom_return_reason = ''
                OR custom_return_reason NOT IN (
                    SELECT name FROM `tabSales Invoice`
                    WHERE company = %s AND docstatus = 1 AND is_return = 0
                )
            )
            {sales_conditions}
            ORDER BY posting_date ASC
        """, sales_values, as_dict=True)

        for i in sales:
            pay = frappe.db.sql("""
                SELECT per.allocated_amount, per.exchange_rate
                FROM `tabPayment Entry Reference` AS per
                LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
                WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
            """, (company, i.name), as_dict=True)

            value = sum(j["allocated_amount"] * (j["exchange_rate"] or 1) for j in pay)

            if value:
                outstanding = i.base_grand_total - value
            else:
                outstanding = i.base_grand_total

            out_amount += outstanding
            age = date_diff(today(), i.posting_date) if i.posting_date else 0

            if abs(outstanding) > 0.01:
                if value:
                    paid_amount += value
                if i.base_grand_total:
                    credit_note += i.base_grand_total
                in_amount += i.base_grand_total

                if 0 <= age <= 30:
                    age_0_30 += outstanding
                elif 31 <= age <= 60:
                    age_31_60 += outstanding
                elif 61 <= age <= 90:
                    age_61_90 += outstanding
                else:
                    age_above_90 += outstanding


                combined_data.append({
                    'posting_date': i.posting_date,
                    'name': i.name,
                    'po_no': i.po_no if i.po_no else '-',
                    'grand_total': i.base_grand_total,
                    'paid_amount': value if value else 0,
                    'credit_note': i.grand_total if i.grand_total else 0,
                    'outstanding': outstanding if outstanding else 0,
                    'age': age,
                    'oustanding_0_30':outstanding if 0 <= age <= 30 else 0,
                    'oustanding_31_60':outstanding if 31 <= age <= 60 else 0,
                    'oustanding_61_90':outstanding if 61 <= age <= 90 else 0,
                    'oustanding_above_90':outstanding if age > 90 else 0,
                })

        # Append individual transaction rows for this customer
        combined_data = sorted(combined_data, key=lambda x: x['posting_date'])
        for entry in combined_data:
            if abs(entry['outstanding']) > 0.01:
                data.append([
                    entry['posting_date'].strftime("%d-%m-%Y") if hasattr(entry['posting_date'], 'strftime') else entry['posting_date'],
                    entry['name'], f"{customer} : {customer_name}", entry.get('sales_person', ''), round(entry['grand_total'], 2),
                    round(entry['paid_amount'], 2), round(entry['credit_note'], 2),
                    round(entry['outstanding'], 2), entry['age'],
                    round(entry['oustanding_0_30'], 2), round(entry['oustanding_31_60'], 2),
                    round(entry['oustanding_61_90'], 2), round(entry['oustanding_above_90'], 2)
                ])

        # Append Subtotal row for this customer
        data.append([
            f"Subtotal: {customer_name}",
            '', '', '', round(in_amount, 2), round(paid_amount, 2), round(credit_note, 2),
            round(out_amount, 2), '', round(age_0_30, 2), round(age_31_60, 2),
            round(age_61_90, 2), round(age_above_90, 2)
        ])
        
        # Add to Grand Totals
        grand_in += in_amount
        grand_paid += paid_amount
        grand_cn += credit_note
        grand_out += out_amount
        grand_0_30 += age_0_30
        grand_31_60 += age_31_60
        grand_61_90 += age_61_90
        grand_above += age_above_90

    # Append Final Total row
    data.append([
        'GRAND TOTAL', '', '', '', round(grand_in, 2), round(grand_paid, 2),
        round(grand_cn, 2), round(grand_out, 2), '',
        round(grand_0_30, 2), round(grand_31_60, 2), round(grand_61_90, 2), round(grand_above, 2)
    ])

    return data

