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
    filename = 'Statement of Account'
    build_xlsx_response(filename)

def make_xlsx(data, sheet_name=None, wb=None, column_widths=None):
    args = frappe.local.form_dict
    column_widths = column_widths or []
    if wb is None:
        wb = openpyxl.Workbook()
		 
    ws = wb.create_sheet(sheet_name, 0)
    ws.column_dimensions['A'].width = 13
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 20 
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 15 
    ws.column_dimensions['G'].width = 15 

    company = args.company
    if company:
        ws.append([company, " ", " ", " ", " ", " ", " ", "", "", "", ""])
        ws.append([args.company, " ", " ", " ", " ", " ", " ", "", "", "", ""])
    else:
        ws.append([args.company, " ", " ", " ", " ", " ", " ", "", "", "", ""]) 
        ws.append(["", " ", " ", " ", " ", " ", " ", "", "", "", ""])
    ws.append(["Statement of Account", " ", " ", " ", " ", " ", " "])

    from_date_str = args.from_date
    from_date_obj = datetime.strptime(from_date_str, "%Y-%m-%d")
    formatted_from_date = from_date_obj.strftime("%d-%m-%Y")

    to_date_str = args.to_date
    to_date_obj = datetime.strptime(to_date_str, "%Y-%m-%d")
    formatted_to_date = to_date_obj.strftime("%d-%m-%Y")

    header3 = ["For the Period: " + formatted_from_date + " to " + formatted_to_date]
    ws.append(header3 + [""] * 7)
    customer = args.customer
    if not args.customer:
        customer='-'
    customer_name= frappe.db.get_value("Customer",args.customer,"customer_name")
    header4 = ['Customer: ' + (customer_name or 'All')]
    ws.append(header4 + [""] * 7)
    currency = frappe.db.get_value('Company', args.company, 'default_currency') or 'SAR'
    ws.append([f'Currency: {currency}'])
    currency = frappe.db.get_value('Company',args.company,'default_currency')
    ws.append(['Date', 'Voucher Type', 'Voucher No', 'Remarks', f'Debit({currency})', f'Credit({currency})', f'Balance({currency})'])

    data1 = get_data(args)
    for row in data1:
        ws.append(row)
    
    # --- Styling using shared report_styles ---
    num_cols = 7
    text_cols = 4  # first 4 columns are text; last 3 (Debit, Credit, Balance) are amounts

    # Title rows: row 1 (company), row 2 (company), row 3 (title), row 4 (period), row 5 (customer)
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
    for cell in ws[5]:
        cell.font = date_font
        cell.alignment = align_center

    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[3].height = 28
    ws.row_dimensions[4].height = 20
    ws.row_dimensions[5].height = 20

    # Header row (row 7) - dark navy fill with white bold text
    apply_header_row(ws, 7, num_cols)

    # Data rows (row 8 onwards)
    data_start_row = 8
    data_end_row = len(data1) + 7
    alt_row = False

    for row in ws.iter_rows(min_row=data_start_row, max_row=data_end_row, min_col=1, max_col=num_cols):
        row_label = str(row[0].value or '')
        is_company = row_label.startswith('Company:')
        is_opening = 'Opening Balance' in row_label
        is_closing = 'Closing Balance' in row_label
        is_total = row_label == 'Total'
        is_grand_total = is_closing
        is_subtotal = is_opening or is_total

        for i, cell in enumerate(row):
            cell.border = border_thin

            if is_company:
                cell.font = bold_font
                cell.alignment = align_left

            elif is_grand_total:
                cell.font = grand_total_font
                cell.fill = grand_total_fill
                cell.alignment = align_left if i < text_cols else align_right
                if i >= text_cols:
                    cell.number_format = currency_format

            elif is_subtotal:
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

        if is_company or is_grand_total or is_subtotal:
            alt_row = False
        else:
            alt_row = not alt_row

    # Thin grey borders on title/spacer rows (1-6)
    for row in ws.iter_rows(min_row=1, max_row=6, min_col=1, max_col=num_cols):
        for cell in row:
            cell.border = border_thin

    # Merge title rows and spacer
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=7)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=7)
    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=7)
    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=7)
    ws.merge_cells(start_row=6, start_column=1, end_row=6, end_column=7)
    ws.merge_cells(start_row=8, start_column=1, end_row=8, end_column=6)
    ws.merge_cells(start_row=len(data1) + 6, start_column=1, end_row=len(data1) + 6, end_column=4)
    ws.merge_cells(start_row=len(data1) + 7, start_column=1, end_row=len(data1) + 7, end_column=6)

    # Page setup - landscape, fit to width
    setup_page(ws, orientation='landscape')

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
    customer =args.customer

    company=args.company
    receivable_accounts = """(account IN (
        SELECT name FROM `tabAccount`
        WHERE company = %s AND account_type = 'Receivable' AND root_type = 'Asset'
    ) OR account = (
        SELECT default_advance_received_account FROM `tabCompany` WHERE name = %s
    ))"""

    if customer:
        gl_entry = frappe.db.sql("""
            SELECT voucher_type, voucher_no, posting_date,party_type, party, SUM(debit) AS debit, SUM(credit) AS credit
            FROM `tabGL Entry`
            WHERE company = %s AND posting_date BETWEEN %s AND %s AND is_cancelled = 0 AND party = %s
            AND {0}
            GROUP BY voucher_no
            ORDER BY posting_date
            """.format(receivable_accounts), (company, args.from_date, args.to_date, customer, company, company), as_dict=True)

        gle = frappe.db.sql("""
            SELECT SUM(debit) AS opening_debit, SUM(credit) AS opening_credit
            FROM `tabGL Entry`
            WHERE company = %s AND (posting_date < %s OR (IFNULL(is_opening, 'No') = 'Yes' AND posting_date >= %s)) AND party = %s AND is_cancelled = 0 and party_type='Customer'
            AND {0}
            """.format(receivable_accounts), (company, args.from_date, args.to_date, customer, company, company), as_dict=True)
    else:
        gl_entry = frappe.db.sql("""
            SELECT voucher_type, voucher_no, posting_date,party_type, party, SUM(debit) AS debit, SUM(credit) AS credit
            FROM `tabGL Entry`
            WHERE company = %s AND posting_date BETWEEN %s AND %s AND is_cancelled = 0
            AND {0}
            GROUP BY voucher_no
            ORDER BY posting_date
            """.format(receivable_accounts), (company, args.from_date, args.to_date, company, company), as_dict=True)

        gle = frappe.db.sql("""
            SELECT SUM(debit) AS opening_debit, SUM(credit) AS opening_credit
            FROM `tabGL Entry`
            WHERE company = %s AND (posting_date < %s OR (IFNULL(is_opening, 'No') = 'Yes' AND posting_date >= %s)) AND is_cancelled = 0 and party_type='Customer'
            AND {0}
            """.format(receivable_accounts), (company, args.from_date, args.to_date, company, company), as_dict=True)

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
        opening_balance = t_p_debit - t_p_credit
        ob = float(fmt_money(round(opening_balance, 2)).replace(',', ''))

    data.append(['Company: ' + company])
    data.append(['Opening Balance', "", "", "", "", "", ob])

    balance = opening_balance
    for i in gl_entry:
        row =[]
        remarks = ""
        check_no = ""
        balance += (i.debit -i.credit)
        voucher_type_display = i.voucher_type 
        if i.voucher_type == "Payment Entry":
            ref_no = frappe.db.get_value("Payment Entry",{"name":i.voucher_no},['reference_no'])
            if ref_no:
                check_no = ref_no
            else:
                check_no = ''
            payment_entry = frappe.db.get_all("Payment Entry",{"name": i.voucher_no},["party_type", "party_name"])
            if payment_entry:
                r = payment_entry[0]
                if r.get("party_type") == "Employee":
                    party_name = r.get("party_name") or ''
                    remarks = f"{party_name}"
        else:
            check_no = ''
        if i.voucher_type == "Sales Invoice":
            remarks = ''
            remark = frappe.db.get_all("Sales Invoice", filters={"name": i.voucher_no}, fields=['*'])

            if remark:
                remark_data = remark[0]
                dn = remark_data.get('delivery_note', '')
                po = remark_data.get('po_no', '')
                ref_no = remark_data.get('custom_supplier_ref_') or ''
                return_doc=remark_data.get('is_return', '')
                if return_doc:
                    voucher_type_display = "Credit Note"

                if dn and po:
                    remarks = f"DN No.{dn} & LPO No.{po}"
                elif dn:
                    remarks = f"DN No.{dn}"
                elif po:
                    remarks =f"{ref_no} LPO No.{po}"
                else:
                    remarks=f"{ref_no}"
        elif i.voucher_type == "Journal Entry":
            remarks = ''
            remark = frappe.db.get_value("Journal Entry", {"name": i.voucher_no}, "user_remark")
            other_remark=frappe.db.get_value("Journal Entry", {"name": i.voucher_no}, "remark")
            cheque_no = frappe.db.get_value("Journal Entry", {"name": i.voucher_no}, "cheque_no")
            
            if cheque_no:
                po_no = frappe.db.get_value("Advance Invoice", {"name": cheque_no}, "po_no")
            else:
                po_no = " "
            if remark and cheque_no:
                remarks = f"LPO No.{po_no} {remark}" if po_no else ''
                check_no = cheque_no
            elif remark:
                remarks = remark
            elif cheque_no:
                remarks = f"LPO No.{po_no}" if po_no else ''
                check_no = cheque_no
            else:
                if other_remark:
                    remarks=other_remark
                else:
                    if i.party:
                        account = frappe.db.get_value("GL Entry",{"voucher_no": i.voucher_no,"party": i.party},"account")
                        if account and "salary" in account.lower():
                            remarks = "Salary"
        elif i.voucher_type == "Expense Claim":
            employee_name = frappe.db.get_value("Expense Claim",i.voucher_no,"employee")
            remarks = employee_name or ''
        elif i.party:
            account = frappe.db.get_value("GL Entry",{"voucher_no": i.voucher_no,"party": i.party},"account")
            if account and "salary" in account.lower():
                remarks = "Salary"
        else:
            remarks = ''

        row.append(i.posting_date.strftime("%d-%m-%Y"))
        row.append(voucher_type_display)
        row.append(i.voucher_no)
        row.append(f"{remarks}{check_no}")
        row.append(float(fmt_money(round(i.debit, 2)).replace(',', '')) or "-")
        row.append(float(fmt_money(round(i.credit, 2)).replace(',', '')) or "-")
        row.append(float(fmt_money(round(balance, 2)).replace(',', '')) or "-")
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

    return data
