# Copyright (c) 2024, Abdulla and contributors
# For license information, please see license.txt

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
from datetime import date, timedelta, datetime, time
from frappe.utils import (getdate, cint, add_months, date_diff, add_days,
    nowdate, get_datetime_str, cstr, get_datetime, now_datetime, format_datetime, today, format_date)
import math
from frappe.utils import add_months, cint, flt, getdate, time_diff_in_hours, time_diff_in_seconds
import locale

import openpyxl
import xlrd
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import GradientFill, PatternFill
from six import BytesIO, string_types
import openpyxl.styles as styles
from frappe.utils import flt, fmt_money


@frappe.whitelist()
def download():
    filename = 'Accounts Receivable Summary by Sales Person'
    build_xlsx_response(filename)

@frappe.whitelist()
def download_excel():
    """Excel export for Accounts Receivable Summary by Sales Person (customer-wise, no aging)."""
    filename = 'Accounts Receivable Summary by Sales Person'
    build_xlsx_response(filename)

def fmt_currency(value):
    """Format number as currency with thousands separator and 2 decimals."""
    try:
        if value is None or value == '' or value == 0:
            return 0
        val = float(value)
        if val == 0:
            return 0
        return val
    except (ValueError, TypeError):
        return value

def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
    args = frappe.local.form_dict
    column_widths = column_widths or []
    if wb is None:
        wb = openpyxl.Workbook()
    sheet_name = sheet_name or 'Accounts Receivable Summary by Sales Person'
    ws = wb.create_sheet(sheet_name, 0)
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])
    widths = [18, 35, 18, 18, 18, 18]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width

    report_data = accounts_receivable_summary(args) or []

    # --- Title rows ---
    ws.append([args.get('company') or ''])
    ws.append(['Accounts Receivable Summary by Sales Person'])
    if args.get("to_date"):
        report_date = format_date(args.get("to_date"))
    else:
        report_date = datetime.now().strftime('%d-%m-%Y')

    ws.append(['Report Date: ' + report_date])
    currency = frappe.db.get_value('Company', args.get("company"), 'default_currency') or 'SAR'
    ws.append([f'Currency: {currency}'])

    headers = [
        'Customer Code', 'Customer Name',
        'Invoiced', 'Paid', 'Credit Note', 'Outstanding'
    ]
    ws.append(headers)

    for row in report_data:
        ws.append(row)

    # --- Styling ---
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_right = Alignment(horizontal='right', vertical='center', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='center', wrap_text=True)

    # Color palette
    header_fill = PatternFill(start_color='1F3864', end_color='1F3864', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=11, name='Calibri')
    title_font = Font(bold=True, size=16, color='1F3864', name='Calibri')
    company_font = Font(bold=True, size=12, color='1F3864', name='Calibri')
    date_font = Font(bold=True, size=10, color='404040', name='Calibri')
    subtotal_fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
    subtotal_font = Font(bold=True, size=11, color='1F3864', name='Calibri')
    grand_total_fill = PatternFill(start_color='1F3864', end_color='1F3864', fill_type='solid')
    grand_total_font = Font(bold=True, size=12, color='FFFFFF', name='Calibri')
    salesperson_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    salesperson_font = Font(bold=True, size=13, color='FFFFFF', name='Calibri')
    alt_row_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    data_font = Font(size=10, name='Calibri')
    bold_font = Font(bold=True, size=11, name='Calibri')
    border_thin = Border(
        left=Side(style='thin', color='B4B4B4'),
        right=Side(style='thin', color='B4B4B4'),
        top=Side(style='thin', color='B4B4B4'),
        bottom=Side(style='thin', color='B4B4B4')
    )

    # Number format for currency columns
    currency_format = '#,##0.00;[Red](#,##0.00);-'

    # --- Apply title styling (rows 1-3) ---
    for row in ws.iter_rows(min_row=1, max_row=1, min_col=1, max_col=6):
        for cell in row:
            cell.font = company_font
            cell.alignment = align_center
    for row in ws.iter_rows(min_row=2, max_row=2, min_col=1, max_col=6):
        for cell in row:
            cell.font = title_font
            cell.alignment = align_center
    for row in ws.iter_rows(min_row=3, max_row=3, min_col=1, max_col=6):
        for cell in row:
            cell.font = date_font
            cell.alignment = align_center

    # --- Header row styling (row 5) ---
    header_row_idx = 5
    for cell in ws[header_row_idx]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        cell.border = border_thin

    # --- Data rows styling ---
    data_start_row = 6
    data_end_row = data_start_row + len(report_data) - 1
    alt_row = False

    for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=6):
        row_label = str(row[0].value or '')
        is_sales_person = row_label.startswith("SALESPERSON:")
        is_subtotal = row_label.startswith("Subtotal:")
        is_grand_total = row_label == "GRAND TOTAL"

        for i, cell in enumerate(row):
            cell.border = border_thin

            if is_sales_person:
                cell.font = salesperson_font
                cell.fill = salesperson_fill
                cell.alignment = align_center

            elif is_grand_total:
                cell.font = grand_total_font
                cell.fill = grand_total_fill
                cell.alignment = align_left if i < 2 else align_right
                if i >= 2:
                    cell.number_format = currency_format

            elif is_subtotal:
                cell.font = subtotal_font
                cell.fill = subtotal_fill
                cell.alignment = align_left if i < 2 else align_right
                if i >= 2:
                    cell.number_format = currency_format

            else:
                # Regular data row
                cell.font = data_font
                cell.alignment = align_left if i < 2 else align_right
                if i >= 2:
                    cell.number_format = currency_format
                # Alternating row colors
                if alt_row:
                    cell.fill = alt_row_fill

        if is_sales_person:
            ws.merge_cells(
                start_row=row[0].row,
                start_column=1,
                end_row=row[0].row,
                end_column=6
            )
            alt_row = False

        elif is_subtotal or is_grand_total:
            ws.merge_cells(
                start_row=row[0].row,
                start_column=1,
                end_row=row[0].row,
                end_column=2
            )
            alt_row = False

        else:
            alt_row = not alt_row

    # Merge title rows
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=6)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)

    # Row heights
    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 28
    ws.row_dimensions[3].height = 20
    ws.row_dimensions[5].height = 25

    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    return xlsx_file

def build_xlsx_response(filename):
    xlsx_file = make_xlsx(filename)
    frappe.response['filename'] = filename + '.xlsx'
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'


def accounts_receivable_summary(args):
    """Accounts Receivable Summary by Sales Person, clubbed customer-wise (no aging)."""
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

    sales_persons = frappe.db.sql(f"""
        SELECT DISTINCT si.custom_sales_personuser as sales_person
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Person` sp
            ON sp.name = si.custom_sales_personuser
        {conditions}
        """, values, as_dict=True)

    for sp in sales_persons:
        sales_person = sp.sales_person

        sp_in = 0
        sp_paid = 0
        sp_cn = 0
        sp_out = 0
        company = args.company
        region = args.get("region") or None
        to_date = args.get("to_date") or None

        # customer_totals: { customer_code: { 'name': ..., 'in': ..., 'paid': ..., 'cn': ..., 'out': ... } }
        customer_totals = {}

        # --- Sales Invoices (is_return = 0) ---
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

            if abs(outstanding) > 0.01:
                cust = i.customer
                if cust not in customer_totals:
                    customer_totals[cust] = {
                        'customer_name': frappe.db.get_value("Customer", cust, "customer_name"),
                        'in': 0, 'paid': 0, 'cn': 0, 'out': 0
                    }
                if value:
                    customer_totals[cust]['paid'] += value
                if return_amount:
                    customer_totals[cust]['cn'] += return_amount
                customer_totals[cust]['in'] += i.base_grand_total
                customer_totals[cust]['out'] += outstanding

                sp_in += i.base_grand_total
                if value:
                    sp_paid += value
                if return_amount:
                    sp_cn += return_amount
                sp_out += outstanding

        # --- Standalone Credit Notes (is_return = 1, no return_against, no valid custom_return_reason match) ---
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

            value = sum(j["allocated_amount"] * (j["exchange_rate"] or 1) for j in pay)

            if value:
                outstanding = i.base_grand_total - value
            else:
                outstanding = i.base_grand_total

            if abs(outstanding) > 0.01:
                cust = i.customer
                if cust not in customer_totals:
                    customer_totals[cust] = {
                        'customer_name': frappe.db.get_value("Customer", cust, "customer_name"),
                        'in': 0, 'paid': 0, 'cn': 0, 'out': 0
                    }
                if value:
                    customer_totals[cust]['paid'] += value
                if i.base_grand_total:
                    customer_totals[cust]['cn'] += i.base_grand_total
                customer_totals[cust]['in'] += i.base_grand_total
                customer_totals[cust]['out'] += outstanding

                if value:
                    sp_paid += value
                if i.base_grand_total:
                    sp_cn += i.base_grand_total
                sp_in += i.base_grand_total
                sp_out += outstanding

        # --- Output: SALESPERSON header, customer rows, subtotal ---
        # Filter customers with non-zero outstanding
        active_customers = {
            k: v for k, v in customer_totals.items()
            if abs(v['out']) > 0.01
        }

        if active_customers:
            data.append([f"SALESPERSON: {sales_person}"] + [''] * 5)

            for cust_code in sorted(active_customers.keys()):
                ct = active_customers[cust_code]
                data.append([
                    cust_code,
                    ct['customer_name'],
                    round(ct['in'], 2),
                    round(ct['paid'], 2),
                    round(ct['cn'], 2),
                    round(ct['out'], 2),
                ])

            data.append([
                f"Subtotal: {sales_person}",
                '', round(sp_in, 2), round(sp_paid, 2), round(sp_cn, 2),
                round(sp_out, 2)
            ])

        grand_in += sp_in
        grand_paid += sp_paid
        grand_cn += sp_cn
        grand_out += sp_out

    # Append Final Total row
    data.append([
        'GRAND TOTAL', '', round(grand_in, 2), round(grand_paid, 2),
        round(grand_cn, 2), round(grand_out, 2)
    ])

    return data
