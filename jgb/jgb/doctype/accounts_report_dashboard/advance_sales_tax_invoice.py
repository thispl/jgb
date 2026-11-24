# Copyright (c) 2026, Antigravity and contributors
# For license information, please see license.txt

import frappe
import html
from frappe.utils import getdate, today, date_diff, flt, format_date
from datetime import datetime
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl import Workbook
from six import BytesIO


def _format_date(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d-%m-%Y")
    return value


def _get_report_date(args):
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    if from_date and to_date:
        return f"{format_date(from_date)} - {format_date(to_date)}"
    elif from_date:
        return format_date(from_date)
    elif to_date:
        return format_date(to_date)
    return format_date(today())


def _get_to_date(args):
    return getdate(args.get("to_date")) if args.get("to_date") else getdate(today())


@frappe.whitelist()
def download():
    """Endpoint to download the Advance Sales Tax Invoice report as an Excel file."""
    filename = "Advance Sales Tax Invoice Report"
    build_xlsx_response(filename)


@frappe.whitelist()
def download_pdf():
    """Endpoint to download the Advance Sales Tax Invoice report as a PDF."""
    from frappe.utils.pdf import get_pdf
    args = frappe.local.form_dict
    html = get_print_html(args)
    pdf = get_pdf(html)
    frappe.response["filename"] = "Advance Sales Tax Invoice Report.pdf"
    frappe.response["filecontent"] = pdf
    frappe.response["type"] = "binary"


def build_xlsx_response(filename):
    xlsx_file = make_xlsx()
    frappe.response["filename"] = filename + ".xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"


def make_xlsx(sheet_name="Advance Sales Tax Invoice", wb=None):
    args = frappe.local.form_dict

    if wb is None:
        wb = Workbook()
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])
    ws = wb.create_sheet(sheet_name, 0)

    # Column widths matching Advance Received from Customer layout
    ws.column_dimensions["A"].width = 13
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 25
    ws.column_dimensions["E"].width = 20
    ws.column_dimensions["F"].width = 20
    ws.column_dimensions["G"].width = 15
    ws.column_dimensions["H"].width = 20
    ws.column_dimensions["I"].width = 12
    ws.column_dimensions["J"].width = 12
    ws.column_dimensions["K"].width = 12
    ws.column_dimensions["L"].width = 12
    ws.column_dimensions["M"].width = 15

    company = args.get("company") or frappe.defaults.get_user_default("Company") or frappe.get_all("Company", limit=1)[0].name
    args["company"] = company
    report_date = _get_report_date(args)

    headers = [
        "Posting Date",
        "Voucher Number",
        "Sales Engineer",
        "Reference / Remarks",
        "Advance Received",
        "Allocated Amount",
        "Credit Note",
        "Unallocated Amount",
        "Age(Days)",
        "0-30",
        "31-60",
        "61-90",
        "Above 90",
    ]

    ws.append([company] + [""] * 12)
    ws.append(["Advance Sales Tax Invoice Report"] + [""] * 12)
    ws.append(["Report Date: " + report_date] + [""] * 12)
    currency = frappe.db.get_value('Company', company, 'default_currency') or 'SAR'
    ws.append([f"Currency: {currency}"] + [""] * 12)
    ws.append(headers)

    data_rows = get_data(args)
    for row in data_rows:
        ws.append(row)

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_right = Alignment(horizontal="right", vertical="bottom", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="bottom", wrap_text=True)

    # Company, Title, Date rows
    for r in range(1, 4):
        for cell in ws[r]:
            cell.font = Font(bold=True)
            cell.alignment = align_center

    # Header row
    header_fill = PatternFill(fgColor="0F0F5C", fill_type="solid")
    for cell in ws[4]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = align_center

    max_row = ws.max_row

    # Data row alignment
    for r in range(5, max_row):
        cell_a = ws.cell(row=r, column=1).value
        if cell_a and str(cell_a).startswith("Subtotal:"):
            continue
        ws.cell(row=r, column=1).alignment = align_left
        ws.cell(row=r, column=2).alignment = align_left
        ws.cell(row=r, column=3).alignment = align_center
        ws.cell(row=r, column=4).alignment = align_left
        for col in range(5, 14):
            ws.cell(row=r, column=col).alignment = align_right

    # Subtotal rows
    subtotal_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    bold_font = Font(bold=True)
    for r in range(5, max_row):
        cell_a = ws.cell(row=r, column=1).value
        if cell_a and str(cell_a).startswith("Subtotal:"):
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
            for col in range(1, 14):
                cell = ws.cell(row=r, column=col)
                cell.fill = subtotal_fill
                cell.font = bold_font
                if col >= 5:
                    cell.alignment = align_right
                else:
                    cell.alignment = align_left

    # Grand total row
    ws.merge_cells(start_row=max_row, start_column=1, end_row=max_row, end_column=4)
    for col in range(1, 14):
        cell = ws.cell(row=max_row, column=col)
        cell.font = bold_font
        cell.alignment = align_right if col >= 5 else align_center

    # Borders
    border_thin = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    for row in ws.iter_rows(min_row=1, max_row=max_row, min_col=1, max_col=13):
        for cell in row:
            cell.border = border_thin

    # Merge top headers
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=13)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=13)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=13)

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    return xlsx_file


def get_data(args, include_customer_header=False):
    """Return report rows for Advance Sales Tax Invoice documents."""
    company = args.get("company")
    if not company:
        company = frappe.defaults.get_user_default("Company") or frappe.get_all("Company", limit=1)[0].name

    to_date = _get_to_date(args)
    from_date = getdate(args.get("from_date")) if args.get("from_date") else None
    customer_filter = args.get("customer")

    # Build filters
    filters = {
        "docstatus": 1,
        "company": company,
        "party_type": "Customer",
        "payment_type": "Receive",
    }

    if from_date and to_date:
        filters["posting_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["posting_date"] = [">=", from_date]
    elif to_date:
        filters["posting_date"] = ["<=", to_date]

    if customer_filter:
        filters["party"] = customer_filter

    asi_records = frappe.db.get_all(
        "Advance Sales Invoice",
        filters=filters,
        fields=[
            "name",
            "posting_date",
            "party",
            "party_name",
            "sales_order",
            "grand_total",
            "total",
            "total_taxes_and_charges",
            "paid_amount",
            "received_amount",
            "remarks",
        ],
        order_by="posting_date, name",
    )

    if not asi_records:
        return []

    asi_names = [r.name for r in asi_records]

    # References to Sales Orders from the ASI
    references = frappe.db.get_all(
        "Payment Entry Reference",
        filters={"parenttype": "Advance Sales Invoice", "parent": ["in", asi_names], "reference_doctype": "Sales Order"},
        fields=["parent", "reference_name"],
    )
    ref_map = {}
    for ref in references:
        if ref.parent not in ref_map:
            ref_map[ref.parent] = ref.reference_name

    # Fetch Sales Engineer from Sales Order
    so_names = [v for v in ref_map.values() if v]
    sales_person_map = {}
    if so_names:
        for so in frappe.db.get_all("Sales Order", filters={"name": ["in", so_names]}, fields=["name", "custom_sales_person"]):
            sales_person_map[so.name] = so.custom_sales_person

    # Allocations from Sales Invoices referencing these ASIs (only submitted, posted <= to_date)
    allocations = frappe.db.sql(
        """
        SELECT
            at.reference_name AS asi_name,
            COALESCE(at.custom_allocated_amount, at.advance_amount) AS allocated_amount,
            si.posting_date AS invoice_posting_date
        FROM `tabadvance sales invoice table` at
        INNER JOIN `tabSales Invoice` si ON si.name = at.parent
        WHERE at.reference_name IN %(asi_names)s
            AND at.parenttype = 'Sales Invoice'
            AND si.docstatus = 1
            AND si.posting_date <= %(to_date)s
        """,
        {"asi_names": asi_names, "to_date": to_date},
        as_dict=True,
    )

    allocation_map = {}
    for row in allocations:
        allocation_map.setdefault(row.asi_name, []).append(row)

    # Group by customer
    customer_rows = {}
    for asi in asi_records:
        customer_rows.setdefault(asi.party, []).append(asi)

    data = []
    grand_totals = {
        "advance": 0.0,
        "allocated": 0.0,
        "credit": 0.0,
        "outstanding": 0.0,
        "0_30": 0.0,
        "31_60": 0.0,
        "61_90": 0.0,
        "above_90": 0.0,
    }

    for customer in sorted(customer_rows.keys()):
        customer_asis = customer_rows[customer]
        customer_name = customer_asis[0].party_name or customer
        if include_customer_header:
            data.append([f"Customer: {customer_name}"] + [""] * 12)

        cust_totals = {
            "advance": 0.0,
            "allocated": 0.0,
            "credit": 0.0,
            "outstanding": 0.0,
            "0_30": 0.0,
            "31_60": 0.0,
            "61_90": 0.0,
            "above_90": 0.0,
        }

        for asi in customer_asis:
            advance_received = flt(asi.grand_total)
            if not advance_received:
                advance_received = flt(asi.paid_amount) or flt(asi.received_amount)

            # Allocations posted before or on to_date
            allocated = 0.0
            for alloc in allocation_map.get(asi.name, []):
                allocated += flt(alloc.allocated_amount)

            credit_note = 0.0
            unallocated = max(0.0, advance_received - allocated - credit_note)
            posting_date = getdate(asi.posting_date)
            age_days = date_diff(to_date, posting_date) if to_date and posting_date else 0

            bucket_0_30 = unallocated if age_days <= 30 else 0
            bucket_31_60 = unallocated if 31 <= age_days <= 60 else 0
            bucket_61_90 = unallocated if 61 <= age_days <= 90 else 0
            bucket_above_90 = unallocated if age_days > 90 else 0

            sales_engineer = ""
            so_ref = ref_map.get(asi.name)
            if so_ref and sales_person_map.get(so_ref):
                sales_engineer = sales_person_map.get(so_ref)

            reference = so_ref or asi.sales_order or asi.remarks or "-"

            row = [
                _format_date(asi.posting_date),
                asi.name,
                sales_engineer,
                reference,
                round(advance_received, 2),
                round(allocated, 2),
                round(credit_note, 2),
                round(unallocated, 2),
                age_days,
                round(bucket_0_30, 2),
                round(bucket_31_60, 2),
                round(bucket_61_90, 2),
                round(bucket_above_90, 2),
            ]
            data.append(row)

            cust_totals["advance"] += advance_received
            cust_totals["allocated"] += allocated
            cust_totals["credit"] += credit_note
            cust_totals["outstanding"] += unallocated
            cust_totals["0_30"] += bucket_0_30
            cust_totals["31_60"] += bucket_31_60
            cust_totals["61_90"] += bucket_61_90
            cust_totals["above_90"] += bucket_above_90

        # Subtotal row
        data.append(
            [
                f"Subtotal: {customer_name}",
                "",
                "",
                "",
                round(cust_totals["advance"], 2),
                round(cust_totals["allocated"], 2),
                round(cust_totals["credit"], 2),
                round(cust_totals["outstanding"], 2),
                "",
                round(cust_totals["0_30"], 2),
                round(cust_totals["31_60"], 2),
                round(cust_totals["61_90"], 2),
                round(cust_totals["above_90"], 2),
            ]
        )

        for k in grand_totals:
            grand_totals[k] += cust_totals[k]

    # Grand total row
    data.append(
        [
            "GRAND TOTAL",
            "",
            "",
            "",
            round(grand_totals["advance"], 2),
            round(grand_totals["allocated"], 2),
            round(grand_totals["credit"], 2),
            round(grand_totals["outstanding"], 2),
            "",
            round(grand_totals["0_30"], 2),
            round(grand_totals["31_60"], 2),
            round(grand_totals["61_90"], 2),
            round(grand_totals["above_90"], 2),
        ]
    )

    return data


def get_print_html(args):
    """Return HTML rendering of the Advance Sales Tax Invoice report."""
    company = args.get("company") or ""
    if not company:
        company = frappe.defaults.get_user_default("Company") or ""

    report_date = _get_report_date(args)
    rows = get_data(args, include_customer_header=True)

    headers = [
        "Posting Date",
        "Voucher Number",
        "Sales Engineer",
        "Reference / Remarks",
        "Advance Received",
        "Allocated Amount",
        "Credit Note",
        "Unallocated Amount",
        "Age(Days)",
        "0-30",
        "31-60",
        "61-90",
        "Above 90",
    ]

    widths = [7, 10, 8, 13, 9, 9, 6, 9, 5, 6, 6, 6, 6]
    colgroup = "".join([f'<col style="width:{w}%" />' for w in widths])

    def format_cell(val, col_idx=None):
        if val is None or val == "":
            return ""
        if col_idx == 8:
            return str(int(val))
        if isinstance(val, (int, float)):
            return f"{val:,.2f}"
        return html.escape(str(val))

    html_rows = []
    for row in rows:
        first = row[0]
        if isinstance(first, str) and first.startswith("Customer:"):
            html_rows.append(
                f'<tr><td class="customer-header" colspan="13" style="font-weight:bold;background:#E6E6E6;text-align:left;padding:4px;">'
                f'{html.escape(first)}</td></tr>'
            )
        elif isinstance(first, str) and first.startswith("Subtotal:"):
            cells = [f'<td class="subtotal" colspan="4" style="font-weight:bold;background:#D9E1F2;text-align:left;padding:4px;">{html.escape(first)}</td>']
            for i, val in enumerate(row[4:], start=4):
                cells.append(f'<td class="subtotal" style="font-weight:bold;background:#D9E1F2;text-align:right;padding:4px;">{format_cell(val, i)}</td>')
            html_rows.append("<tr>" + "".join(cells) + "</tr>")
        elif isinstance(first, str) and first == "GRAND TOTAL":
            cells = [f'<td class="grandtotal" colspan="4" style="font-weight:bold;text-align:center;padding:4px;">{html.escape(first)}</td>']
            for i, val in enumerate(row[4:], start=4):
                cells.append(f'<td class="grandtotal" style="font-weight:bold;text-align:right;padding:4px;">{format_cell(val, i)}</td>')
            html_rows.append("<tr>" + "".join(cells) + "</tr>")
        else:
            cells = []
            for idx, val in enumerate(row):
                align = "left" if idx <= 3 else "right"
                cells.append(f'<td style="text-align:{align};padding:4px;">{format_cell(val, idx)}</td>')
            html_rows.append("<tr>" + "".join(cells) + "</tr>")

    header_cells = "".join([f'<th style="text-align:center;background:#0F0F5C;color:white;font-weight:bold;padding:4px;">{html.escape(h)}</th>' for h in headers])

    css = """
    <style>
        .print-format { max-width: none !important; margin: 2mm; }
        table { width: 100%; table-layout: fixed; border-collapse: collapse; }
        th, td { border: 1px solid #000; padding: 2px; font-size: 8px; word-wrap: break-word; vertical-align: middle; }
        th { background-color: #0F0F5C; color: white; font-weight: bold; text-align: center; }
        td { text-align: right; }
        .customer-header { font-weight: bold; background-color: #E6E6E6; text-align: left; padding-left: 6px; }
        .subtotal { font-weight: bold; background-color: #D9E1F2; }
        .grandtotal { font-weight: bold; }
    </style>
    """

    output = f"""
    <meta name="pdfkit-orientation" content="Landscape" />
    <div style="text-align:center;">
        <h3>{html.escape(company)}</h3>
        <h4>Advance Sales Tax Invoice Report</h4>
        <h4><b>Report Date : </b>{report_date}</h4>
    </div>
    """
    output += css
    output += f"""
    <table border="1" cellspacing="0" cellpadding="0">
        <colgroup>{colgroup}</colgroup>
        <thead>
            <tr>{header_cells}</tr>
        </thead>
        <tbody>
            {''.join(html_rows)}
        </tbody>
    </table>
    """
    return output
