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
from jgb.jgb.doctype.accounts_report_dashboard.report_styles import *

@frappe.whitelist()
def download():
    filename = 'Accounts Receivable Aging Report'
    build_xlsx_response(filename)

@frappe.whitelist()
def download_excel():
    """Excel export matching the Accounts Aging Summary print format."""
    filename = 'Accounts Aging Summary by Sales Person'
    build_xlsx_response(filename)

NUM_COLS = 14          # total columns in the report
TEXT_COLS = 5         # first 5 columns are text (left-aligned)
AMOUNT_START = 6      # 1-based column index where currency columns begin

def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
    args = frappe.local.form_dict
    column_widths = column_widths or []
    if wb is None:
        wb = openpyxl.Workbook()
    sheet_name = sheet_name or 'Accounts Aging Summary by Sales Person'
    ws = wb.create_sheet(sheet_name, 0)
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])
    widths = [13, 25, 15, 25, 15, 15, 15, 15, 12, 12, 12, 12, 12, 12]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width

    report_data = accounts_aging(args) or []

    # --- Title rows ---
    ws.append([args.get('company') or ''])
    ws.append(['Accounts Receivable Aging Report by Sales Person'])
    if args.get("to_date"):
        report_date = format_date(args.get("to_date"))
    else:
        report_date = datetime.now().strftime('%d-%m-%Y')

    ws.append(['Report Date: ' + report_date])
    currency = frappe.db.get_value('Company', args.get("company"), 'default_currency') or 'SAR'
    ws.append([f'Currency: {currency}'])

    headers = [
        'Posting Date', 'Voucher No', 'Customer Code', 'Customer Name', 'Customer LPO',
        'Invoiced', 'Paid', 'Credit Note',
        'Outstanding', 'Age', '0-30', '31-60', '61-90', 'Above 90'
    ]
    ws.append(headers)

    for row in report_data:
        ws.append(row)

    # --- Styling (using shared report_styles helpers) ---
    apply_title_rows(ws, NUM_COLS,
                     'Accounts Receivable Aging Report by Sales Person',
                     company=args.get('company') or '',
                     report_date=report_date)

    # --- Header row styling (row 5) ---
    header_row_idx = 5
    apply_header_row(ws, header_row_idx, NUM_COLS)

    # --- Data rows styling ---
    data_start_row = 6
    data_end_row = data_start_row + len(report_data) - 1
    alt_row = False

    for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row,
                            min_col=1, max_col=NUM_COLS):
        row_label = str(row[0].value or '')
        is_sales_person = row_label.startswith("SALESPERSON:")
        is_customer_subtotal = row_label.startswith("Customer Subtotal:")
        is_subtotal = row_label.startswith("Subtotal:")
        is_grand_total = row_label == "GRAND TOTAL"

        style_data_row(row, NUM_COLS, TEXT_COLS,
                       is_subtotal=is_subtotal,
                       is_grand_total=is_grand_total,
                       is_salesperson=is_sales_person,
                       is_customer_subtotal=is_customer_subtotal,
                       alt_row=alt_row and not (is_sales_person or is_subtotal or is_customer_subtotal or is_grand_total))

        if is_sales_person:
            ws.merge_cells(
                start_row=row[0].row,
                start_column=1,
                end_row=row[0].row,
                end_column=NUM_COLS
            )
            alt_row = False

        elif is_customer_subtotal or is_subtotal or is_grand_total:
            ws.merge_cells(
                start_row=row[0].row,
                start_column=1,
                end_row=row[0].row,
                end_column=TEXT_COLS
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
    conditions = ""
    values = [args.company]

    conditions = "WHERE si.company = %s AND si.docstatus = 1"
    values = [args.company]

    if args.sales_person:
        conditions += " AND si.custom_sales_personuser = %s"
        values.append(args.sales_person)

    if args.region:
        conditions += " AND sp.custom_territory = %s"
        values.append(args.region)

    if args.to_date:
        conditions += " AND si.posting_date <= %s"
        values.append(args.to_date)

    data = []
    
    grand_in = grand_paid = grand_cn = grand_out = 0.0
    grand_0_30 = grand_31_60 = grand_61_90 = grand_above = 0.0
    
    customers = frappe.db.sql(f"""
        SELECT DISTINCT si.custom_sales_personuser as sales_person
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Person` sp
            ON sp.name = si.custom_sales_personuser
        {conditions}
        """, values, as_dict=True)
    for sp in customers:
        sales_person = sp.sales_person
        

        in_amount = 0
        paid_amount = 0
        credit_note = 0
        out_amount = 0
        age_0_30 = 0
        age_31_60 = 0
        age_61_90 = 0
        age_above_90 = 0
        company = args.company
        in_amt, paid_amt, cn_amt, out_amt = 0, 0, 0, 0
        a0_30, a31_60, a61_90, above = 0, 0, 0, 0
        combined_data = []
        region = args.get("region") or None
        to_date = args.get("to_date") or None

        si_list = frappe.db.sql("""
            SELECT si.*
            FROM `tabSales Invoice` si
            INNER JOIN `tabSales Person` sp
                ON sp.name = si.custom_sales_personuser
            WHERE si.company = %s
            AND si.docstatus = 1
            AND si.is_return = 0
            AND si.custom_sales_personuser = %s
            AND (%s IS NULL OR sp.custom_territory = %s)
            AND (%s IS NULL OR si.posting_date <= %s)
            ORDER BY si.posting_date
        """, (
            company,
            sales_person,
            region, region,
            to_date, to_date
        ), as_dict=True)
        

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
                    'customer_code': i.customer,
                    'customer_name': frappe.db.get_value("Customer", i.customer, "customer_name"),
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
        sales = frappe.db.sql("""
            SELECT *
            FROM `tabSales Invoice`
            WHERE company = %s
            AND custom_sales_personuser = %s
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
            AND (%s IS NULL OR posting_date <= %s)
            ORDER BY posting_date ASC
        """, (
            company,
            sales_person,
            company,
            to_date, to_date
        ), as_dict=True)

        for i in sales:
            pay = frappe.db.sql("""
                SELECT per.allocated_amount, per.exchange_rate
                FROM `tabPayment Entry Reference` AS per
                LEFT JOIN `tabPayment Entry` AS pe ON per.parent = pe.name
                WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
            """, (company, i.name), as_dict=True)

            value = sum(j.allocated_amount * (j.exchange_rate or 1) for j in pay)

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
                    'customer_code': i.customer,
                    'customer_name': frappe.db.get_value("Customer", i.customer, "customer_name"),
                    'po_no': i.po_no if i.po_no else '-',
                    'grand_total': i.base_grand_total,
                    'paid_amount': value if value else 0,
                    'credit_note': i.base_grand_total if i.base_grand_total else 0,
                    'outstanding': outstanding if outstanding else 0,
                    'age': age,
                    'oustanding_0_30':outstanding if 0 <= age <= 30 else 0,
                    'oustanding_31_60':outstanding if 31 <= age <= 60 else 0,
                    'oustanding_61_90':outstanding if 61 <= age <= 90 else 0,
                    'oustanding_above_90':outstanding if age > 90 else 0,
                })

        # Filter out entries with near-zero outstanding (paid/closed invoices)
        filtered_data = [entry for entry in combined_data if abs(entry['outstanding']) > 0.01]

        # Append individual transaction rows for this sales person, grouped by customer
        filtered_data = sorted(filtered_data, key=lambda x: (x.get('customer_code', ''), x['posting_date']))
        if filtered_data:
            data.append([f"SALESPERSON: {sales_person}"] + [''] * 13)

        # Group entries by customer and add customer-wise subtotals
        cust_in = cust_paid = cust_cn = cust_out = 0.0
        cust_0_30 = cust_31_60 = cust_61_90 = cust_above = 0.0
        current_customer = None

        for entry in filtered_data:

            entry_customer = entry.get('customer_code', '')
            # When customer changes, emit subtotal for previous customer
            if current_customer is not None and entry_customer != current_customer:
                if abs(cust_out) > 0.01:
                    cust_name = frappe.db.get_value("Customer", current_customer, "customer_name") or current_customer
                    data.append([
                        f"Customer Subtotal: {current_customer} - {cust_name}",
                        '', '', '', '', round(cust_in, 2), round(cust_paid, 2), round(cust_cn, 2),
                        round(cust_out, 2), '', round(cust_0_30, 2), round(cust_31_60, 2),
                        round(cust_61_90, 2), round(cust_above, 2)
                    ])
                cust_in = cust_paid = cust_cn = cust_out = 0.0
                cust_0_30 = cust_31_60 = cust_61_90 = cust_above = 0.0

            current_customer = entry_customer

            data.append([
                entry['posting_date'].strftime("%d-%m-%Y") if hasattr(entry['posting_date'], 'strftime') else entry['posting_date'],
                entry['name'], entry.get('customer_code', ''), entry.get('customer_name', ''), entry['po_no'], round(entry['grand_total'], 2),
                round(entry['paid_amount'], 2), round(entry['credit_note'], 2),
                round(entry['outstanding'], 2), entry['age'],
                round(entry['oustanding_0_30'], 2), round(entry['oustanding_31_60'], 2),
                round(entry['oustanding_61_90'], 2), round(entry['oustanding_above_90'], 2)
            ])

            cust_in += entry['grand_total']
            cust_paid += entry['paid_amount']
            cust_cn += entry['credit_note']
            cust_out += entry['outstanding']
            cust_0_30 += entry['oustanding_0_30']
            cust_31_60 += entry['oustanding_31_60']
            cust_61_90 += entry['oustanding_61_90']
            cust_above += entry['oustanding_above_90']

        # Emit subtotal for the last customer
        if current_customer is not None and abs(cust_out) > 0.01:
            cust_name = frappe.db.get_value("Customer", current_customer, "customer_name") or current_customer
            data.append([
                f"Customer Subtotal: {current_customer} - {cust_name}",
                '', '', '', '', round(cust_in, 2), round(cust_paid, 2), round(cust_cn, 2),
                round(cust_out, 2), '', round(cust_0_30, 2), round(cust_31_60, 2),
                round(cust_61_90, 2), round(cust_above, 2)
            ])

        # Append Subtotal row for this sales person
        if filtered_data:
            data.append([
                f"Subtotal: {sales_person}",
                '', '', '', '', round(in_amount, 2), round(paid_amount, 2), round(credit_note, 2),
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
        'GRAND TOTAL', '', '', '', '', round(grand_in, 2), round(grand_paid, 2), 
        round(grand_cn, 2), round(grand_out, 2), '',
        round(grand_0_30, 2), round(grand_31_60, 2), round(grand_61_90, 2), round(grand_above, 2)
    ])

    return data

