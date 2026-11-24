import frappe
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from io import BytesIO
from openpyxl.styles import Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime


def vat_summary(wb,arg1, arg2,arg3,arg4,arg5, arg6,arg7, arg8,arg9,arg10, sheet_name="Summary"):
    NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'

    args = frappe.local.form_dict
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    company = args.get("company")

    ws = wb.create_sheet(sheet_name)

    address = frappe.db.sql(
        """
        SELECT
            a.address_line1,
            a.custom_building_number,
            a.city,
            a.country
        FROM `tabAddress` a
        INNER JOIN `tabDynamic Link` dl ON dl.parent = a.name
        WHERE
            a.is_your_company_address = 1
            AND dl.link_doctype = 'Company'
            AND dl.link_name = %s
        LIMIT 1
        """,
        (company,),
        as_dict=True
    )

    address = address[0] if address else {}
    address_text = ", ".join(
        filter(None, [
            address.get("address_line1"),
            address.get("custom_building_number"),
            address.get("city"),
            address.get("country")
        ])
    )

    vat_id = frappe.db.get_value("Company", company, "tax_id")
    period = f"{from_date} TO {to_date}"

    ws.append(["Company Name", "", "", company])
    ws.append(["Address", "", "", address_text])
    ws.append(["VAT ACCOUNT NUMBER", "", "", vat_id])
    ws.append(["TAX RETURN PERIOD", "", "", period])
    ws.append(["", "", "", "", "", ""])
    ws.append(["", "", "", "Amount (SAR)", "Adjustment (SAR)", "VAT Amount (SAR)"])

    for r in range(1, 5):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=6)

    ws.merge_cells(start_row=6, start_column=1, end_row=6, end_column=3)
    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=6)

    header_fill = PatternFill("solid", fgColor="9BC2E6")
    dark_blue_fill = PatternFill("solid", fgColor="1F4E79")
    white_font = Font(bold=True, color="FFFFFF", size=11)
    header_font = Font(bold=True, size=11)
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    for r in range(1, 6):
        for c in range(1, 7):
            cell = ws.cell(r, c)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = left
            cell.border = thin_border
        ws.row_dimensions[r].height = 28

    for c in range(1, 7):
        cell = ws.cell(6, c)
        cell.fill = dark_blue_fill
        cell.font = white_font
        cell.alignment = center
        cell.border = thin_border

    ws.row_dimensions[6].height = 32

    vat_rows = [
        ("VAT on Sales", "5%", "1-Standard Rated Sales"),
        ("VAT on Purchases", "5%", "7-Standard Rated Domestic Purchases"),
        ("", "5%", "14-Corrections From Period (Between SAR ±5000)")
    ]

    start_row = 7
    for i, row in enumerate(vat_rows):
        r = start_row + i
        ws.append([row[0], row[1], row[2], "-", "-", "-"])

        for c in range(1, 7):
            cell = ws.cell(r, c)
            cell.alignment = center
            cell.border = thin_border

        for c in (4, 5, 6):
            ws.cell(r, c).number_format = NUMBER_FORMAT

        ws.row_dimensions[r].height = 26
    def n(v):
        return v or 0

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'
    empty_row = ws.max_row + 1
    ws.append([""] * 6)
    ws.merge_cells(start_row=empty_row, start_column=1, end_row=empty_row, end_column=6)
    sales_start_row = ws.max_row + 1
    sales_rows = [
        ("1-Standard Rated Sales (15%)", arg1, "-", arg2),
        ("2-Sales on which the government bears the VAT", "-", "-", "-"),
        ("3-Zero Rated Domestic Sales", arg3, "-", "-"),
        ("4-Exports", arg4, "-", "-"),
        ("5-Exempt Sales", "-", "-", "-"),
        ("6-Total Sales", n(arg1) + n(arg3) + n(arg4), "-", arg2),
    ]

    for r in sales_rows:
        ws.append(["", r[0], "", r[1], r[2], r[3]])

        current_row = ws.max_row

        ws.merge_cells(
            start_row=current_row,
            start_column=2,
            end_row=current_row,
            end_column=3
        )

        for c in (4, 5, 6):
            ws.cell(current_row, c).number_format = NUMBER_FORMAT

        for c in range(1, 7):
            ws.cell(current_row, c).border = thin_border
    
    sales_end_row = ws.max_row

    ws.merge_cells(
        start_row=sales_start_row,
        start_column=1,
        end_row=sales_end_row,
        end_column=1
    )

    cell = ws.cell(sales_start_row, 1)
    cell.value = "VAT On Sales"
    cell.alignment = Alignment(
        horizontal="center",
        vertical="center",
        text_rotation=90   
    )
    cell.font = Font(bold=True)
    cell.border = thin_border
    empty_row = ws.max_row + 1
    ws.append([""] * 6)
    ws.merge_cells(start_row=empty_row, start_column=1, end_row=empty_row, end_column=6)
    purchase_start_row = ws.max_row + 1
    args = frappe.local.form_dict
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    company = args.get("company")
    exempt = frappe.db.sql(
        """
        SELECT
            SUM(base_grand_total) as total
        FROM `tabPurchase Invoice` pi
        WHERE
            pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND pi.company = %(company)s
            AND pi.workflow_state = 'Approved'
            AND pi.custom_zatca_tax_category = 'Exempted'
            AND pi.docstatus = 1
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
        },
        as_dict=True,
    )

    exempt_sales = exempt[0].total if exempt and exempt[0].total else 0
    purchase_rows = [
        ("7-Standard Rated Domestic Purchases", n(arg5) + n(arg7), 0, n(arg6) + n(arg8)),
        ("8-Imports Subject To VAT Paid At Customs", 0, "-", "-"),
        ("9-Imports Subject To VAT Accounted For Through Reverse Charge Mechanism", arg10, "-", "-"),
        ("10-Zero Rated Purchases", arg9, "-", "-"),
        ("11-Exempt Purchases", exempt_sales, "-", "-"),
        ("12-Total Purchases", n(arg5) + n(arg7) + n(arg10) + n(arg9), 0, n(arg6) + n(arg8) + n(exempt_sales)),
    ]

    for r in purchase_rows:
        ws.append(["", r[0], "", r[1], r[2], r[3]])
        current_row = ws.max_row

        ws.merge_cells(
            start_row=current_row,
            start_column=2,
            end_row=current_row,
            end_column=3
        )

        for c in (4, 5, 6):
            ws.cell(current_row, c).number_format = NUMBER_FORMAT

        for c in range(1, 7):
            ws.cell(current_row, c).border = thin_border

    purchase_end_row = ws.max_row

    ws.merge_cells(
        start_row=purchase_start_row,
        start_column=1,
        end_row=purchase_end_row,
        end_column=1
    )

    cell = ws.cell(purchase_start_row, 1)
    cell.value = "VAT On Purchases"
    cell.alignment = Alignment(
        horizontal="center",
        vertical="center",
        text_rotation=90  
    )
    cell.font = Font(bold=True)
    cell.border = thin_border

    empty_row = ws.max_row + 1
    ws.append([""] * 6)
    ws.merge_cells(start_row=empty_row, start_column=1, end_row=empty_row, end_column=6)
    total_vat = n(arg2) + n(arg6) + n(arg8)

    ws.append(["",  "13-Total VAT Due For Current Period", "","", "", arg2-(n(arg6) + n(arg8))])
    ws.append(["", "14-Corrections From Period (Between SAR ±15000)", "", "", "", "-"])
    ws.append(["",  "15-VAT Credit Forward From Previous Period(s)","", "", "", "-"])
    ws.append(["Net VAT Payable", "","",  "", "", arg2-(n(arg6) + n(arg8))])

    dark_blue_fill = PatternFill("solid", fgColor="1F4E79")
    white_font = Font(bold=True, color="FFFFFF")

    for c in range(1, 7):
        cell = ws.cell(ws.max_row, c)
        cell.fill = dark_blue_fill
        cell.font = white_font
        cell.border = thin_border

    ws.cell(ws.max_row, 6).number_format = NUMBER_FORMAT
    widths = {1: 18, 2: 8, 3: 45, 4: 18, 5: 20, 6: 18}
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width

    ws.freeze_panes = "A7"
    last_row = ws.max_row
    start_3rows = last_row - 3

    ws.merge_cells(
        start_row=last_row,
        start_column=1,
        end_row=last_row,
        end_column=5
    )

    for c in range(1, 6):
        ws.cell(last_row, c).border = thin_border


    ws.merge_cells(
        start_row=start_3rows,
        start_column=1,
        end_row=last_row - 1,
        end_column=1
    )

    ws.cell(start_3rows, 1).alignment = Alignment(
        horizontal="center",
        vertical="center"
    )
    ws.cell(start_3rows, 1).font = Font(bold=True)

    for r in range(start_3rows, last_row):
        ws.merge_cells(
            start_row=r,
            start_column=2,
            end_row=r,
            end_column=5
        )

        
    max_row = ws.max_row
    max_col = ws.max_column

    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            ws.cell(row=r, column=c).border = thin_border