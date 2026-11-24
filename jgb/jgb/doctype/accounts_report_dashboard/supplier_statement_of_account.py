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
    filename = 'Supplier Statement of Account'
    build_xlsx_response(filename)

def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
    args = frappe.local.form_dict
    column_widths = column_widths or []
    if wb is None:
        wb = openpyxl.Workbook()
		 
    ws = wb.create_sheet(sheet_name, 0)
    ws.column_dimensions['A'].width = 13
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 25 
    ws.column_dimensions['D'].width = 40
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 15 
    ws.column_dimensions['G'].width = 15 

    # company = frappe.db.get_value('Company', {'name': args.company_multiselect.split(',')[0]}, 'parent_company')
    # if company:
    #     ws.append([company, " ", " ", " ", " ", " ", " ", "", "", "", ""])
    #     ws.append([args.company, " ", " ", " ", " ", " ", " ", "", "", "", ""])
    # else:
    ws.append([args.company, " ", " ", " ", " ", " ", " ", "", "", "", ""]) 
    ws.append(["", " ", " ", " ", " ", " ", " ", "", "", "", ""])
    ws.append(["Supplier Statement of Account", " ", " ", " ", " ", " ", " "])

    from_date_str = args.from_date
    from_date_obj = datetime.strptime(from_date_str, "%Y-%m-%d")
    formatted_from_date = from_date_obj.strftime("%d-%m-%Y")

    to_date_str = args.to_date
    to_date_obj = datetime.strptime(to_date_str, "%Y-%m-%d")
    formatted_to_date = to_date_obj.strftime("%d-%m-%Y")

    header3 = ["For the Period: " + formatted_from_date + " to " + formatted_to_date]
    ws.append(header3 + [""] * 7)
    # supplier = frappe.db.get_value('Supplier Statement of Account', {"name": args.name}, ['supplier'])
    supplier = args.supplier
    supplier_name = frappe.db.get_value("Supplier",args.supplier,"supplier_name")

    header4 = ['Supplier: ' + (supplier_name or 'All')]
    ws.append(header4 + [""] * 7)
    currency = args.get('currency') or frappe.db.get_value('Company', args.company, 'default_currency') or 'SAR'
    ws.append([f'Currency: {currency}'])
    currency = frappe.db.get_value('Company',args.company,'default_currency')
    ws.append(['Date', 'Voucher Type', 'Voucher No', 'Remarks', f'Debit({currency})', f'Credit({currency})', f'Balance({currency})'])

    data1 = get_data(args)
    for row in data1:
        ws.append(row)
    
    # --- Styling using shared report_styles ---
    num_cols = 7
    header_row_idx = 7
    data_start_row = 8
    data_end_row = data_start_row + len(data1) - 1

    # Title rows: row 1 (company), row 3 (title), rows 4-5 (period / supplier info)
    for cell in ws[1]:
        cell.font = company_font
        cell.alignment = align_center
    for cell in ws[3]:
        cell.font = title_font
        cell.alignment = align_center
    for row_idx in (4, 5):
        for cell in ws[row_idx]:
            cell.font = date_font
            cell.alignment = align_center

    # Header row (row 7) - dark navy fill with white bold text
    apply_header_row(ws, header_row_idx, num_cols)

    # Data rows
    alt_row = False
    for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=num_cols):
        row_label = str(row[0].value or '')
        is_company_label = row_label.startswith('Company:')
        is_opening = 'Opening Balance' in row_label
        is_total = row_label == 'Total'
        is_closing = 'Closing Balance' in row_label
        is_subtotal = is_opening or is_total
        is_grand_total = is_closing

        for i, cell in enumerate(row):
            cell.border = border_thin

            if is_company_label:
                cell.font = bold_font
                cell.alignment = align_left

            elif is_grand_total:
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
                cell.font = data_font
                cell.alignment = align_left if i < 4 else align_right
                if i >= 4:
                    cell.number_format = currency_format
                if alt_row:
                    cell.fill = alt_row_fill

        # Merges for special rows
        if is_company_label:
            ws.merge_cells(start_row=row[0].row, start_column=1, end_row=row[0].row, end_column=6)
            alt_row = False
        elif is_total:
            ws.merge_cells(start_row=row[0].row, start_column=1, end_row=row[0].row, end_column=4)
            alt_row = False
        elif is_subtotal:
            ws.merge_cells(start_row=row[0].row, start_column=1, end_row=row[0].row, end_column=6)
            alt_row = False
        elif is_grand_total:
            ws.merge_cells(start_row=row[0].row, start_column=1, end_row=row[0].row, end_column=6)
            alt_row = False
        else:
            alt_row = not alt_row

    # Merge title rows
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=num_cols)
    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=num_cols)
    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=num_cols)
    ws.merge_cells(start_row=6, start_column=1, end_row=6, end_column=num_cols)

    # Row heights
    ws.row_dimensions[1].height = 22
    ws.row_dimensions[3].height = 28
    ws.row_dimensions[4].height = 20
    ws.row_dimensions[5].height = 20
    ws.row_dimensions[header_row_idx].height = 25

    # Page setup - landscape, fit to width
    setup_page(ws, 'landscape')

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    return xlsx_file

def build_xlsx_response(filename):
    xlsx_file = make_xlsx(filename)
    frappe.response['filename'] = filename + '.xlsx'
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'

def get_data(args):
    data = []
    # supplier = frappe.db.get_value('Supplier Statement of Account', {"name": args.name}, ['supplier'])
    supplier = args.supplier
    company = args.company
    if supplier:
        gl_entry = frappe.db.sql("""
            SELECT voucher_type, voucher_no, posting_date,party_type, party, SUM(debit) AS debit, SUM(credit) AS credit
            FROM `tabGL Entry`
            WHERE company = %s AND posting_date BETWEEN %s AND %s AND is_cancelled = 0 AND party = %s
            GROUP BY voucher_no
            ORDER BY posting_date
            """, (company, args.from_date, args.to_date, supplier), as_dict=True)

        gle = frappe.db.sql("""
            SELECT SUM(debit) AS opening_debit, SUM(credit) AS opening_credit
            FROM `tabGL Entry`
            WHERE company = %s AND (posting_date < %s OR (IFNULL(is_opening, 'No') = 'Yes' AND posting_date >= %s)) AND party = %s AND is_cancelled = 0 and party_type='Supplier'                """, (company, args.from_date, args.to_date,supplier), as_dict=True)
    else:
        gl_entry = frappe.db.sql("""
            SELECT voucher_type, voucher_no, posting_date, party_type, party,SUM(debit) AS debit, SUM(credit) AS credit
            FROM `tabGL Entry`
            WHERE company = %s AND posting_date BETWEEN %s AND %s AND is_cancelled = 0
            GROUP BY voucher_no
            ORDER BY posting_date
            """, (company, args.from_date, args.to_date), as_dict=True)

        gle = frappe.db.sql("""
            SELECT SUM(debit) AS opening_debit, SUM(credit) AS opening_credit
            FROM `tabGL Entry`
            WHERE company = %s AND (posting_date < %s OR (IFNULL(is_opening, 'No') = 'Yes' AND posting_date >= %s)) AND is_cancelled = 0 and party_type='Supplier'
            """, (company, args.from_date, args.to_date), as_dict=True)

    opening_balance = 0
    t_p_debit = 0
    t_p_credit = 0
    for g in gle:
        if not g.opening_debit:
            g.opening_debit = 0
        if not g.opening_credit:
            g.opening_credit = 0
        t_p_debit += g.opening_debit
        t_p_credit += g.opening_credit
        opening_balance = t_p_credit -  t_p_debit 
        ob = float(fmt_money(round(opening_balance, 2)).replace(',', ''))

    data.append(['Company: ' + company])
    data.append(['Opening Balance', "", "", "", "", "", ob])

    balance = opening_balance
    for i in gl_entry:
        row = []
        balance += (i.credit - i.debit)
        if i.voucher_type == "Payment Entry":
            ref_no = frappe.db.get_value("Payment Entry", {"name": i.voucher_no}, ['reference_no'])
            check_no = ref_no if ref_no else ''
        else:
            check_no = ''

        if i.voucher_type == "Payment Entry":
            ref_no = frappe.db.get_value("Payment Entry",{"name":i.voucher_no},['reference_no'])
            if ref_no:
                check_no = ref_no
            else:
                check_no = ''
        else:
            check_no = ''
        if i.voucher_type == "Purchase Invoice":
            remarks = ''
            invoice = frappe.get_doc("Purchase Invoice",i.voucher_no)
            for k in invoice.items:
                dn = frappe.db.get_value("Purchase Receipt",{"name":k.purchase_receipt},["supplier_delivery_note"])
                po = k.purchase_order

                if dn and po:
                    remarks = f"DN No.{dn} & PO No.{po}"
                elif dn:
                    remarks = f"DN No.{dn}"
                elif po:
                    remarks =f"PO No.{po}"
        elif i.voucher_type == "Journal Entry":
            remarks = ''
            remark = frappe.db.get_value("Journal Entry", {"name": i.voucher_no},['user_remark'])
            other_remark=frappe.db.get_value("Journal Entry", {"name": i.voucher_no}, "remark")
            cheque_no = frappe.db.get_value("Journal Entry", {"name": i.voucher_no},['cheque_no'])
            if remark:
                remarks = remark
            elif cheque_no:
                check_no = cheque_no
            else:
                if other_remark:
                    remarks=other_remark
        else:
            remarks = ''

        row.append(i.posting_date.strftime("%d-%m-%Y"))
        row.append(i.voucher_type)
        row.append(i.voucher_no)
        row.append(f"{remarks}{check_no}")
        row.append(float(fmt_money(round(i.debit, 2)).replace(',', '')) or 0)
        row.append(float(fmt_money(round(i.credit, 2)).replace(',', '')) or 0)
        row.append(float(fmt_money(round(balance, 2)).replace(',', '')) or 0)
        data.append(row)

    tp_credit = 0
    tp_debit = 0
    for i in gl_entry:
        tp_credit += i.credit
        t_p_credit += i.credit
        tp_debit += i.debit
        t_p_debit += i.debit

    data.append(["Total", "", "", "", float(fmt_money(round(tp_debit, 2)).replace(',', '')), float(fmt_money(round(tp_credit, 2)).replace(',', '')), ''])
    data.append(['Closing Balance', "", "", "", "", "", float(fmt_money(round(balance, 2)).replace(',', ''))])
    data.append([''])

    # Currency conversion
    base_currency = frappe.db.get_value('Company', company, 'default_currency') or 'SAR'
    target_currency = args.get('currency') or base_currency
    if target_currency and target_currency != base_currency:
        exchange_rate = _get_supplier_exchange_rate(base_currency, target_currency)
        if exchange_rate and exchange_rate != 1:
            # Amount columns: 4(debit), 5(credit), 6(balance)
            for row in data:
                if isinstance(row, list):
                    for idx in [4, 5, 6]:
                        if idx < len(row) and isinstance(row[idx], (int, float)) and row[idx] != 0:
                            row[idx] = round(row[idx] * exchange_rate, 2)

    return data


def _get_supplier_exchange_rate(from_currency, to_currency):
    """Get exchange rate between any two currencies."""
    if from_currency == to_currency:
        return 1.0
    def _direct(frm, to):
        r = frappe.db.sql("SELECT exchange_rate FROM `tabCurrency Exchange` WHERE from_currency=%s AND to_currency=%s ORDER BY date DESC LIMIT 1", (frm, to))
        return flt(r[0][0]) if r and r[0][0] else None
    rate = _direct(from_currency, to_currency)
    if rate: return rate
    rate = _direct(to_currency, from_currency)
    if rate: return 1.0 / rate
    if from_currency != "SAR" and to_currency != "SAR":
        r1 = _direct(from_currency, "SAR"); r2 = _direct(to_currency, "SAR")
        if r1 and r2: return r1 / r2
    if from_currency != "USD" and to_currency != "USD":
        r1 = _direct(from_currency, "USD") or (_direct("USD", from_currency) and 1.0/_direct("USD", from_currency))
        r2 = _direct(to_currency, "USD") or (_direct("USD", to_currency) and 1.0/_direct("USD", to_currency))
        if r1 and r2: return r1 / r2
    return 1.0
