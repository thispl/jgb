# Copyright (c) 2026, Antigravity and contributors
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
    """
    Controller endpoint to trigger download of the customer advance aging Excel report.
    """
    filename = 'Customer Advance Aging Report'
    build_xlsx_response(filename)

def build_xlsx_response(filename):
    xlsx_file = make_xlsx()
    frappe.response['filename'] = filename + '.xlsx'
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'

def make_xlsx(sheet_name="Advances Aging", wb=None):
    args = frappe.local.form_dict
    
    if wb is None:
        wb = openpyxl.Workbook()
    
    # Remove default sheet and create a new one to place it first
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])
    ws = wb.create_sheet(sheet_name, 0)
    
    # Set column widths matching the accounts receivable aging report format
    ws.column_dimensions['A'].width = 13  # Posting Date
    ws.column_dimensions['B'].width = 25  # Voucher Number
    ws.column_dimensions['C'].width = 20  # Sales Engineer (blank for advances)
    ws.column_dimensions['D'].width = 25  # Reference / Remarks
    ws.column_dimensions['E'].width = 20  # Total Advance Received
    ws.column_dimensions['F'].width = 20  # Allocated against Invoices
    ws.column_dimensions['G'].width = 15  # Credit Note (always 0)
    ws.column_dimensions['H'].width = 20  # Remaining Balance (Outstanding)
    ws.column_dimensions['I'].width = 12  # Age(Days)
    ws.column_dimensions['J'].width = 12  # 0-30
    ws.column_dimensions['K'].width = 12  # 31-60
    ws.column_dimensions['L'].width = 12  # 61-90
    ws.column_dimensions['M'].width = 15  # Above 90
    
    # 1. Company name header
    company = args.get("company")
    if not company:
        company = frappe.defaults.get_user_default("Company") or frappe.get_all("Company", limit=1)[0].name
    args.company = company
    
    ws.append([company, " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " "])
    
    # 2. Report title
    ws.append(["Customer Advance Aging Report", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " "])
    
    # 3. Report date
    report_date_str = args.get("to_date") or today()
    ws.append(["Report Date: " + format_date(report_date_str, "dd-MM-yyyy"), "", "", "", "", "", "", "", "", "", "", "", ""])

    currency = frappe.db.get_value('Company', company, 'default_currency') or 'SAR'
    ws.append([f"Currency: {currency}", "", "", "", "", "", "", "", "", "", "", "", ""])

    # 4. Table column headers
    ws.append([
        "Posting Date", "Voucher Number", "Sales Engineer", "Reference / Remarks", 
        "Advance Received", "Allocated Amount", "Credit Note", "Unallocated Amount", 
        "Age(Days)", "0-30", "31-60", "61-90", "Above 90"
    ])
    
    # Fetch data using advance aging calculation logic
    data_rows = customer_advances_aging(args)
    for row in data_rows:
        ws.append(row)
        
    # --- Styling using shared report_styles ---
    NUM_COLS = 13
    TEXT_COLS = 4  # A-D are text columns
    # Amount columns (E-H and J-M); skip I (Age Days) which is a plain number
    AMOUNT_COLS = [5, 6, 7, 8, 10, 11, 12, 13]

    # 1. Style title rows (company row 1, title row 2, date row 3)
    apply_title_rows(ws, NUM_COLS, "Customer Advance Aging Report", company, report_date_str)

    # 2. Style table header row (row 4)
    apply_header_row(ws, 4, NUM_COLS)

    # 3. Style data rows (row 5 to last row)
    max_row = ws.max_row
    alt_row = False

    for r in range(5, max_row + 1):
        row_label = str(ws.cell(row=r, column=1).value or '')
        is_subtotal = row_label.startswith("Subtotal:")
        is_grand_total = row_label == "GRAND TOTAL"

        row_cells = list(ws[r])
        for i, cell in enumerate(row_cells):
            cell.border = border_thin

            if is_grand_total:
                cell.font = grand_total_font
                cell.fill = grand_total_fill
                cell.alignment = align_left if i < TEXT_COLS else align_right
                if (i + 1) in AMOUNT_COLS:
                    cell.number_format = currency_format

            elif is_subtotal:
                cell.font = subtotal_font
                cell.fill = subtotal_fill
                cell.alignment = align_left if i < TEXT_COLS else align_right
                if (i + 1) in AMOUNT_COLS:
                    cell.number_format = currency_format

            else:
                # Regular data row
                cell.font = data_font
                cell.alignment = align_left if i < TEXT_COLS else align_right
                if (i + 1) in AMOUNT_COLS:
                    cell.number_format = currency_format
                # Alternating row colors
                if alt_row:
                    cell.fill = alt_row_fill

        # Merge A-D for subtotal and grand total rows
        if is_subtotal or is_grand_total:
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=TEXT_COLS)
            alt_row = False
        else:
            alt_row = not alt_row

    # 4. Page setup - landscape, fit to width
    setup_page(ws)
    
    # Save to BytesIO buffer and return
    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    return xlsx_file

def customer_advances_aging(args):
    """
    Computes all advances from Payment Entries and Journal Entries, identifies
    linked/allocated amounts to Sales Invoices, and groups them by customer
    with aging buckets.
    """
    data = []
    company = args.company
    to_date = getdate(args.to_date) if args.get("to_date") else getdate(today())
    customer_filter = args.get("customer")

    # Fetch customer names map
    customer_names = {c.name: c.customer_name for c in frappe.db.get_all("Customer", fields=["name", "customer_name"])}

    # Identify customers who have customer receipts or advance journals
    pe_custs = [r.party for r in frappe.db.get_all("Payment Entry", filters={"company": company, "docstatus": 1, "party_type": "Customer", "payment_type": "Receive"}, fields=["party"], distinct=True)]
    je_custs = [r.party for r in frappe.db.get_all(
            "Journal Entry Account",
            filters={
                "docstatus": 1,
                "party_type": "Customer",
                "account": ["in", [
                    "2201 - Advances From Customers - JGB",
                    "2202 - Advances From Customers  - Invoiced - JGB"
                ]]
            },
            fields=["party"],
            distinct=True
        )]
    customer_list = sorted(list(set(pe_custs + je_custs)))

    # if customer_filter:
    #     customer_list = [customer_filter] if customer_filter in customer_list else []

    grand_in = grand_paid = grand_out = 0.0
    grand_0_30 = grand_31_60 = grand_61_90 = grand_above = 0.0

    for customer in customer_list:
        customer_name = customer_names.get(customer, customer)
        
        # 1. Fetch customer Payment Entries (Receive) posted on or before to_date
        pe_filters = {
            "party_type": "Customer",
            "payment_type": "Receive",
            "docstatus": 1,
            "company": company,
            "party": customer,
            "posting_date": ["<=", to_date],
            "paid_from": ["in", ["2201 - Advances From Customers - JGB", "2202 - Advances From Customers  - Invoiced - JGB"]]
        }
        payment_entries = frappe.db.get_all(
            "Payment Entry",
            filters=pe_filters,
            fields=["name", "posting_date", "paid_amount", "source_exchange_rate", "remarks", "reference_no"]
        )
        pe_names = [pe.name for pe in payment_entries]

        # Fetch references to Sales Invoices for these Payment Entries
        pe_ref_map = {}
        if pe_names:
            pe_references = frappe.db.get_all(
                "Payment Entry Reference",
                filters={
                    "parent": ["in", pe_names],
                    "reference_doctype": "Sales Invoice"
                },
                fields=["parent", "reference_name", "allocated_amount"]
            )
            for ref in pe_references:
                pe_ref_map.setdefault(ref.parent, []).append(ref)

        # Fetch all Sales Invoice Advance records linking these PEs to Sales Invoices (submitted and active only)
        all_pe_sia = []
        if pe_names:
            all_pe_sia = frappe.db.sql("""
                SELECT
                    sia.reference_name,
                    sia.allocated_amount,
                    si.name AS invoice_name,
                    si.posting_date AS invoice_posting_date
                FROM
                    `tabSales Invoice Advance` sia
                INNER JOIN
                    `tabSales Invoice` si ON sia.parent = si.name
                WHERE
                    sia.reference_type = 'Payment Entry'
                    AND sia.reference_name IN %(pe_names)s
                    AND si.docstatus = 1
            """, {"pe_names": pe_names}, as_dict=True)

        sia_pe_map = {}
        advance_links = set()
        for row in all_pe_sia:
            sia_pe_map.setdefault(row.reference_name, []).append(row)
            advance_links.add((row.reference_name, row.invoice_name))

        combined_data = []

        # Totals for this customer
        cust_in = cust_paid = cust_out = 0.0
        cust_0_30 = cust_31_60 = cust_61_90 = cust_above = 0.0

        for pe in payment_entries:
            pe_name = pe.name
            posting_date = getdate(pe.posting_date)
            exchange_rate = flt(pe.source_exchange_rate) or 1.0

            # Direct invoice payment references are not advances
            direct_payments_sum = 0
            for ref in pe_ref_map.get(pe_name, []):
                if (pe_name, ref.reference_name) not in advance_links:
                    direct_payments_sum += flt(ref.allocated_amount)

            # Customer advance amount in base currency
            advance_received_party = flt(pe.paid_amount) - direct_payments_sum
            total_advance_base = advance_received_party * exchange_rate

            if total_advance_base <= 0:
                continue

            # Sum allocations against Sales Invoices posted on or before to_date
            allocated_base = 0
            for row in sia_pe_map.get(pe_name, []):
                if getdate(row.invoice_posting_date) <= to_date:
                    allocated_base += flt(row.allocated_amount) * exchange_rate

            unallocated_base = max(0.0, total_advance_base - allocated_base)
            age_days = date_diff(to_date, posting_date)

            if round(unallocated_base, 2) > 0:
                combined_data.append({
                    'posting_date': posting_date,
                    'name': pe_name,
                    'sales_person': '',
                    'po_no': pe.reference_no or '-',
                    'grand_total': total_advance_base,
                    'paid_amount': allocated_base,
                    'credit_note': 0.0,
                    'outstanding': unallocated_base,
                    'age': age_days,
                    'oustanding_0_30': unallocated_base if age_days <= 30 else 0,
                    'oustanding_31_60': unallocated_base if 31 <= age_days <= 60 else 0,
                    'oustanding_61_90': unallocated_base if 61 <= age_days <= 90 else 0,
                    'oustanding_above_90': unallocated_base if age_days > 90 else 0,
                })

        # 2. Fetch customer Journal Entries (Credit) posted on or before to_date
        je_query = """
            SELECT
                jea.name AS row_name,
                jea.parent AS parent,
                je.posting_date AS posting_date,
                jea.credit AS credit,
                jea.exchange_rate AS exchange_rate,
                je.remark AS remark
            FROM
                `tabJournal Entry Account` jea
            INNER JOIN
                `tabJournal Entry` je
                ON jea.parent = je.name
            WHERE
                jea.party_type = 'Customer'
                AND jea.credit > 0
                AND jea.account IN (
                    '2201 - Advances From Customers - JGB',
                    '2202 - Advances From Customers  - Invoiced - JGB'
                )
                AND je.docstatus = 1
                AND je.company = %(company)s
                AND je.posting_date <= %(to_date)s
                AND jea.party = %(customer)s
        """
        journal_advances = frappe.db.sql(je_query, {"company": company, "to_date": to_date, "customer": customer}, as_dict=True)
        je_names = list(set(ja.parent for ja in journal_advances))

        # Fetch Sales Invoice Advances for these Journal Entries
        all_je_sia = []
        if je_names:
            all_je_sia = frappe.db.sql("""
                SELECT
                    sia.reference_name,
                    sia.reference_row,
                    sia.allocated_amount,
                    si.posting_date AS invoice_posting_date
                FROM
                    `tabSales Invoice Advance` sia
                INNER JOIN
                    `tabSales Invoice` si ON sia.parent = si.name
                WHERE
                    sia.reference_type = 'Journal Entry'
                    AND sia.reference_name IN %(je_names)s
                    AND si.docstatus = 1
            """, {"je_names": je_names}, as_dict=True)

        sia_je_map = {}
        for row in all_je_sia:
            key = (row.reference_name, row.reference_row)
            sia_je_map.setdefault(key, []).append(row)

        for ja in journal_advances:
            posting_date = getdate(ja.posting_date)
            exchange_rate = flt(ja.exchange_rate) or 1.0

            total_advance_base = flt(ja.credit)
            allocated_base = 0
            key = (ja.parent, ja.row_name)
            for row in sia_je_map.get(key, []):
                if getdate(row.invoice_posting_date) <= to_date:
                    allocated_base += flt(row.allocated_amount) * exchange_rate

            unallocated_base = max(0.0, total_advance_base - allocated_base)
            age_days = date_diff(to_date, posting_date)

            if round(unallocated_base, 2) > 0:
                combined_data.append({
                    'posting_date': posting_date,
                    'name': ja.parent,
                    'sales_person': '',
                    'po_no': '-',
                    'grand_total': total_advance_base,
                    'paid_amount': allocated_base,
                    'credit_note': 0.0,
                    'outstanding': unallocated_base,
                    'age': age_days,
                    'oustanding_0_30': unallocated_base if age_days <= 30 else 0,
                    'oustanding_31_60': unallocated_base if 31 <= age_days <= 60 else 0,
                    'oustanding_61_90': unallocated_base if 61 <= age_days <= 90 else 0,
                    'oustanding_above_90': unallocated_base if age_days > 90 else 0,
                })

        if not combined_data:
            continue

        # Append customer individual transaction rows
        combined_data = sorted(combined_data, key=lambda x: x['posting_date'])
        for entry in combined_data:
            data.append([
                entry['posting_date'].strftime("%d-%m-%Y") if hasattr(entry['posting_date'], 'strftime') else entry['posting_date'],
                entry['name'],
                entry.get('sales_person', ''),
                entry['po_no'],
                round(entry['grand_total'], 2),
                round(entry['paid_amount'], 2),
                round(entry['credit_note'], 2),
                round(entry['outstanding'], 2),
                entry['age'],
                round(entry['oustanding_0_30'], 2),
                round(entry['oustanding_31_60'], 2),
                round(entry['oustanding_61_90'], 2),
                round(entry['oustanding_above_90'], 2)
            ])

            # Accumulate totals for customer subtotal
            cust_in += entry['grand_total']
            cust_paid += entry['paid_amount']
            cust_out += entry['outstanding']
            cust_0_30 += entry['oustanding_0_30']
            cust_31_60 += entry['oustanding_31_60']
            cust_61_90 += entry['oustanding_61_90']
            cust_above += entry['oustanding_above_90']

        # Append Subtotal row for this customer
        data.append([
            f"Subtotal: {customer_name}", 
            '', '', '', 
            round(cust_in, 2), 
            round(cust_paid, 2), 
            0.0, 
            round(cust_out, 2), 
            '', 
            round(cust_0_30, 2), 
            round(cust_31_60, 2), 
            round(cust_61_90, 2), 
            round(cust_above, 2)
        ])

        # Accumulate to Grand Totals
        grand_in += cust_in
        grand_paid += cust_paid
        grand_out += cust_out
        grand_0_30 += cust_0_30
        grand_31_60 += cust_31_60
        grand_61_90 += cust_61_90
        grand_above += cust_above

    # Append Grand Total row
    data.append([
        'GRAND TOTAL', '', '', '', 
        round(grand_in, 2), 
        round(grand_paid, 2), 
        0.0, 
        round(grand_out, 2), 
        '', 
        round(grand_0_30, 2), 
        round(grand_31_60, 2), 
        round(grand_61_90, 2), 
        round(grand_above, 2)
    ])

    return data
