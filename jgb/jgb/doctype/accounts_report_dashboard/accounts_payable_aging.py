
import frappe
from frappe.model.document import Document
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


def get_exchange_rate(from_currency, to_currency):
    """Get exchange rate between any two currencies.
    Tries: direct rate -> reverse rate -> cross rate via SAR -> cross rate via USD."""
    if from_currency == to_currency:
        return 1.0

    def _get_direct_rate(frm, to):
        r = frappe.db.sql("""
            SELECT exchange_rate FROM `tabCurrency Exchange`
            WHERE from_currency = %s AND to_currency = %s
            ORDER BY date DESC LIMIT 1
        """, (frm, to))
        return flt(r[0][0]) if r and r[0][0] else None

    # 1. Direct rate: from -> to
    rate = _get_direct_rate(from_currency, to_currency)
    if rate:
        return rate

    # 2. Reverse rate: to -> from, then invert
    rate = _get_direct_rate(to_currency, from_currency)
    if rate:
        return 1.0 / rate

    # 3. Cross rate via SAR: from -> SAR, then SAR -> to
    if from_currency != "SAR" and to_currency != "SAR":
        rate_from_sar = _get_direct_rate(from_currency, "SAR")
        rate_to_sar = _get_direct_rate(to_currency, "SAR")
        if rate_from_sar and rate_to_sar:
            # from -> SAR = rate_from_sar, SAR -> to = 1/rate_to_sar
            return rate_from_sar / rate_to_sar

    # 4. Cross rate via USD: from -> USD, then USD -> to
    if from_currency != "USD" and to_currency != "USD":
        rate_from_usd = _get_direct_rate(from_currency, "USD") or (_get_direct_rate("USD", from_currency) and 1.0 / _get_direct_rate("USD", from_currency))
        rate_to_usd = _get_direct_rate(to_currency, "USD") or (_get_direct_rate("USD", to_currency) and 1.0 / _get_direct_rate("USD", to_currency))
        if rate_from_usd and rate_to_usd:
            return rate_from_usd / rate_to_usd

    frappe.msgprint(f"No exchange rate found for {from_currency} -> {to_currency}. Using 1.0")
    return 1.0


@frappe.whitelist()
def download_payable_aging():
    filename = "Accounts Payable Aging Report"
    build_payable_xlsx_response(filename)


def build_payable_xlsx_response(filename):
    xlsx_file = make_payable_xlsx(filename)

    frappe.response["filename"] = filename + ".xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"


def make_payable_xlsx(data, sheet_name=None, wb=None, column_widths=None):

    args = frappe.local.form_dict

    if wb is None:
        wb = openpyxl.Workbook()

    ws = wb.create_sheet("Payable Aging", 0)

    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 18
    ws.column_dimensions['F'].width = 18
    ws.column_dimensions['G'].width = 18
    ws.column_dimensions['H'].width = 12
    ws.column_dimensions['I'].width = 15
    ws.column_dimensions['J'].width = 15
    ws.column_dimensions['K'].width = 15
    ws.column_dimensions['L'].width = 15

    company = args.company
    supplier = args.supplier
    supplier_name=frappe.db.get_value("Supplier",supplier,"supplier_name") if supplier else None
    ws.append([company or "", "", "", "", "", "", "", "", "", "", "", ""])
    ws.append(["Accounts Payable Aging Report", "", "", "", "", "", "", "", "", "", "", ""])

    report_date = datetime.now().strftime("%d-%m-%Y")
    ws.append([f"Report Date : {report_date}", "", "", "", "", "", "", "", "", "", "", ""])

    ws.append([f"Supplier : {supplier_name or 'All'}", "", "", "", "", "", "", "", "", "", "", ""])

    currency = args.get('currency') or frappe.db.get_value('Company', args.company, 'default_currency') or 'SAR'
    ws.append([f"Currency: {currency}"])

    ws.append([
        "Posting Date",
        "Voucher Number",
        "Bill No",
        "Invoice Amount",
        "Paid Amount",
        "Debit Note",
        "Outstanding Amount",
        "Age(Days)",
        "0-30",
        "31-60",
        "61-90",
        "Above 90"
    ])

    aging_data = get_payable_aging_report_data(args)

    for row in aging_data:
        ws.append(row)

    # --- Styling ---
    num_cols = 12
    text_cols = 3  # Posting Date, Voucher Number, Bill No
    amount_cols = [4, 5, 6, 7, 9, 10, 11, 12]  # currency columns (skip Age at col 8)

    # --- Title rows (rows 1-4) ---
    for cell in ws[1]:
        cell.font = company_font
        cell.alignment = align_center
        cell.border = border_thin
    for cell in ws[2]:
        cell.font = title_font
        cell.alignment = align_center
        cell.border = border_thin
    for cell in ws[3]:
        cell.font = date_font
        cell.alignment = align_center
        cell.border = border_thin
    for cell in ws[4]:
        cell.font = company_font
        cell.alignment = align_center
        cell.border = border_thin

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=num_cols)
    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=num_cols)

    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 28
    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 20

    # --- Header row (row 6) ---
    header_row_idx = 6
    apply_header_row(ws, header_row_idx, num_cols)

    # --- Data rows ---
    data_start_row = 7
    total_row = len(aging_data) + 6
    alt_row = False

    for row in ws.iter_rows(min_row=data_start_row, max_row=total_row, min_col=1, max_col=num_cols):
        row_label = str(row[0].value or '')
        is_total = row_label == "Total"
        is_subtotal = row_label.startswith("Supplier Subtotal:")

        for i, cell in enumerate(row):
            cell.border = border_thin

            if is_total:
                cell.font = grand_total_font
                cell.fill = grand_total_fill
                cell.alignment = align_left if i < text_cols else align_right
                if (i + 1) in amount_cols:
                    cell.number_format = currency_format
            elif is_subtotal:
                cell.font = subtotal_font
                cell.fill = subtotal_fill
                cell.alignment = align_left if i < text_cols else align_right
                if (i + 1) in amount_cols:
                    cell.number_format = currency_format
            else:
                cell.font = data_font
                cell.alignment = align_left if i < text_cols else align_right
                if (i + 1) in amount_cols:
                    cell.number_format = currency_format
                if alt_row:
                    cell.fill = alt_row_fill

        if is_total or is_subtotal:
            ws.merge_cells(
                start_row=row[0].row,
                start_column=1,
                end_row=row[0].row,
                end_column=text_cols
            )
            alt_row = False
        else:
            alt_row = not alt_row

    ws.row_dimensions[header_row_idx].height = 25

    # --- Page setup ---
    setup_page(ws, orientation='landscape')

    xlsx_file = BytesIO()
    wb.save(xlsx_file)

    return xlsx_file


def get_payable_aging_report_data(args):

    data = []

    invoice_amount = 0
    paid_amount = 0
    debit_note = 0
    outstanding_amount = 0

    age_0_30 = 0
    age_31_60 = 0
    age_61_90 = 0
    age_above_90 = 0

    combined_data = []

    supplier = args.supplier
    company = args.company

    # Forex Gain/Loss account for the company (deductions against this account
    # should not be treated as unallocated advance payments in the aging report)
    forex_gl_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_name": "Forex Gain/Loss"},
        "name",
    )

    if supplier:
        suppliers = [frappe._dict({"name": supplier, "supplier_name": frappe.db.get_value("Supplier", supplier, "supplier_name")})]
    else:
        suppliers = frappe.db.sql("""
            SELECT DISTINCT pi.supplier AS name, s.supplier_name
            FROM `tabPurchase Invoice` pi
            LEFT JOIN `tabSupplier` s ON s.name = pi.supplier
            WHERE pi.company = %s AND pi.docstatus = 1 AND pi.is_return = 0
            ORDER BY s.supplier_name
        """, (company,), as_dict=True)

    for sup in suppliers:

        sup_invoice_amount = 0
        sup_paid_amount = 0
        sup_debit_note = 0
        sup_outstanding_amount = 0
        sup_age_0_30 = 0
        sup_age_31_60 = 0
        sup_age_61_90 = 0
        sup_age_above_90 = 0
        sup_has_data = False

        pi_list = frappe.db.sql("""
            SELECT *
            FROM `tabPurchase Invoice`
            WHERE company=%s
            AND supplier=%s
            AND docstatus=1
            AND is_return=0
            ORDER BY posting_date ASC
        """, (company, sup.name), as_dict=True)

        for pi in pi_list:

            # Purchase Return Amount
            return_amount = frappe.db.sql("""
                SELECT SUM(base_grand_total)
                FROM `tabPurchase Invoice`
                WHERE company=%s
                AND return_against=%s
                AND docstatus=1
            """, (company, pi.name))[0][0] or 0

            # Purchase Return Document
            return_docs = frappe.db.sql("""
                SELECT name
                FROM `tabPurchase Invoice`
                WHERE company=%s
                AND return_against=%s
                AND docstatus=1
            """, (company, pi.name), as_dict=True)

            return_payments = []

            if return_docs:
                return_payments = frappe.db.sql("""
                    SELECT per.allocated_amount
                    FROM `tabPayment Entry Reference` per
                    LEFT JOIN `tabPayment Entry` pe
                        ON pe.name = per.parent
                    WHERE pe.company=%s
                    AND per.reference_name=%s
                    AND pe.docstatus=1
                """, (company, return_docs[0]["name"]), as_dict=True)

            # PI Payments
            payments = frappe.db.sql("""
                SELECT per.allocated_amount
                FROM `tabPayment Entry Reference` per
                LEFT JOIN `tabPayment Entry` pe
                    ON pe.name = per.parent
                WHERE pe.company=%s
                AND per.reference_name=%s
                AND pe.docstatus=1
            """, (company, pi.name), as_dict=True)

            value = (
                sum(d["allocated_amount"] for d in payments)
                + sum(d["allocated_amount"] for d in return_payments)
            )

            # Journal Entries
            jv_entries = frappe.db.sql("""
                SELECT
                    debit_in_account_currency,
                    credit_in_account_currency
                FROM `tabJournal Entry Account` jea
                LEFT JOIN `tabJournal Entry` je
                    ON je.name = jea.parent
                WHERE je.company=%s
                AND jea.reference_name=%s
                AND je.docstatus=1
            """, (company, pi.name), as_dict=True)

            for jv in jv_entries:

                if jv.debit_in_account_currency:
                    value += jv.debit_in_account_currency

                if jv.credit_in_account_currency:
                    value -= jv.credit_in_account_currency

            # Outstanding
            if value and return_amount:
                outstanding = pi.base_grand_total - value + return_amount

            elif value:
                outstanding = pi.base_grand_total - value

            elif return_amount:
                outstanding = pi.base_grand_total + return_amount

            else:
                outstanding = pi.base_grand_total

            outstanding_amount += outstanding

            age = date_diff(today(), pi.posting_date) if pi.posting_date else 0

            if round(outstanding, 2) != 0:

                invoice_amount += pi.base_grand_total
                sup_invoice_amount += pi.base_grand_total

                if value:
                    paid_amount += value
                    sup_paid_amount += value

                if return_amount:
                    debit_note += return_amount
                    sup_debit_note += return_amount

                if 0 <= age <= 30:
                    age_0_30 += outstanding
                    sup_age_0_30 += outstanding

                elif 31 <= age <= 60:
                    age_31_60 += outstanding
                    sup_age_31_60 += outstanding

                elif 61 <= age <= 90:
                    age_61_90 += outstanding
                    sup_age_61_90 += outstanding

                else:
                    age_above_90 += outstanding
                    sup_age_above_90 += outstanding

                sup_outstanding_amount += outstanding
                sup_has_data = True

                combined_data.append({
                    "posting_date": pi.posting_date,
                    "name": pi.name,
                    "bill_no": pi.bill_no or "-",
                    "invoice_amount": pi.base_grand_total,
                    "paid_amount": value,
                    "debit_note": return_amount,
                    "outstanding": outstanding,
                    "age": age,
                    "out_0_30": outstanding if 0 <= age <= 30 else 0,
                    "out_31_60": outstanding if 31 <= age <= 60 else 0,
                    "out_61_90": outstanding if 61 <= age <= 90 else 0,
                    "out_above_90": outstanding if age > 90 else 0
                })

        # Fetch advance Payment Entries (unallocated payments to this supplier)
        pe_advances = frappe.db.sql("""
            SELECT pe.name, pe.posting_date, pe.reference_no, pe.paid_from,
                   pe.base_paid_amount,
                   (SELECT COALESCE(SUM(per.allocated_amount), 0)
                    FROM `tabPayment Entry Reference` per
                    WHERE per.parent = pe.name) as allocated
            FROM `tabPayment Entry` pe
            WHERE pe.company = %s
            AND pe.docstatus = 1
            AND pe.payment_type = 'Pay'
            AND pe.party_type = 'Supplier'
            AND pe.party = %s
            HAVING allocated < pe.base_paid_amount
            ORDER BY pe.posting_date ASC
        """, (company, sup.name), as_dict=True)

        for pe in pe_advances:
            # Skip Payment Entries that have a deduction against the
            # Forex Gain/Loss account (e.g. 4101 - Forex Gain/Loss - JGB).
            # These are not real advance payments and should not appear
            # as outstanding rows in the aging report.
            if forex_gl_account and frappe.db.exists(
                "Payment Entry Deduction",
                {"parent": pe.name, "account": forex_gl_account},
            ):
                continue

            unallocated = pe.base_paid_amount - pe.allocated
            if round(unallocated, 2) == 0:
                continue

            # Get bank name from Account paid_from -> account_name
            bank_name = ""
            if pe.paid_from:
                acc_name = frappe.db.get_value("Account", pe.paid_from, "account_name") or ""
                # account_name format: "Bank- SNB-04900000412303" or "Bank- SAB - SASABB242164895001"
                if acc_name:
                    # Extract bank name after "Bank- "
                    bank_name = acc_name.replace("Bank- ", "").strip() if "Bank-" in acc_name else acc_name

            voucher_no = f"{pe.name}\n{bank_name} - {pe.reference_no or ''}" if bank_name else f"{pe.name}\n{pe.reference_no or ''}"

            age = date_diff(today(), pe.posting_date) if pe.posting_date else 0
            outstanding = -unallocated  # negative = advance/credit with supplier

            paid_amount += unallocated
            sup_paid_amount += unallocated
            outstanding_amount += outstanding
            sup_outstanding_amount += outstanding
            sup_has_data = True

            if 0 <= age <= 30:
                age_0_30 += outstanding
                sup_age_0_30 += outstanding
            elif 31 <= age <= 60:
                age_31_60 += outstanding
                sup_age_31_60 += outstanding
            elif 61 <= age <= 90:
                age_61_90 += outstanding
                sup_age_61_90 += outstanding
            else:
                age_above_90 += outstanding
                sup_age_above_90 += outstanding

            combined_data.append({
                "posting_date": pe.posting_date,
                "name": voucher_no,
                "bill_no": pe.name,
                "invoice_amount": 0,
                "paid_amount": unallocated,
                "debit_note": 0,
                "outstanding": outstanding,
                "age": age,
                "out_0_30": outstanding if 0 <= age <= 30 else 0,
                "out_31_60": outstanding if 31 <= age <= 60 else 0,
                "out_61_90": outstanding if 61 <= age <= 90 else 0,
                "out_above_90": outstanding if age > 90 else 0
            })

        # Add supplier subtotal row (only when showing all suppliers)
        if not supplier and sup_has_data:
            combined_data = sorted(
                combined_data,
                key=lambda x: x["posting_date"]
            )

            for row in combined_data:

                data.append([
                    row["posting_date"].strftime("%d-%m-%Y"),
                    row["name"],
                    row["bill_no"],
                    round(row["invoice_amount"], 2),
                    round(row["paid_amount"], 2),
                    round(row["debit_note"], 2),
                    round(row["outstanding"], 2),
                    row["age"],
                    round(row["out_0_30"], 2),
                    round(row["out_31_60"], 2),
                    round(row["out_61_90"], 2),
                    round(row["out_above_90"], 2)
                ])

            data.append([
                f"Supplier Subtotal: {sup.supplier_name}",
                "",
                "",
                round(sup_invoice_amount, 2),
                round(sup_paid_amount, 2),
                round(sup_debit_note, 2),
                round(sup_outstanding_amount, 2),
                "",
                round(sup_age_0_30, 2),
                round(sup_age_31_60, 2),
                round(sup_age_61_90, 2),
                round(sup_age_above_90, 2)
            ])

            combined_data = []

    # Single supplier case - just output the rows
    if supplier:
        combined_data = sorted(
            combined_data,
            key=lambda x: x["posting_date"]
        )

        for row in combined_data:

            data.append([
                row["posting_date"].strftime("%d-%m-%Y"),
                row["name"],
                row["bill_no"],
                round(row["invoice_amount"], 2),
                round(row["paid_amount"], 2),
                round(row["debit_note"], 2),
                round(row["outstanding"], 2),
                row["age"],
                round(row["out_0_30"], 2),
                round(row["out_31_60"], 2),
                round(row["out_61_90"], 2),
                round(row["out_above_90"], 2)
            ])

    data.append([
        "Total",
        "",
        "",
        round(invoice_amount, 2),
        round(paid_amount, 2),
        round(debit_note, 2),
        round(outstanding_amount, 2),
        "",
        round(age_0_30, 2),
        round(age_31_60, 2),
        round(age_61_90, 2),
        round(age_above_90, 2)
    ])

    # Currency conversion: if currency is not base currency (SAR), convert amounts
    base_currency = frappe.db.get_value('Company', company, 'default_currency') or 'SAR'
    target_currency = args.get('currency') or base_currency

    if target_currency and target_currency != base_currency:
        # Get exchange rate: 1 base_currency = X target_currency
        exchange_rate = get_exchange_rate(base_currency, target_currency)
        if exchange_rate and exchange_rate != 1:
            amount_indices = [3, 4, 5, 6, 8, 9, 10, 11]  # invoice, paid, debit, outstanding, 0-30, 31-60, 61-90, above 90
            for row in data:
                for idx in amount_indices:
                    if isinstance(row[idx], (int, float)) and row[idx] != 0:
                        row[idx] = round(row[idx] * exchange_rate, 2)

    return data