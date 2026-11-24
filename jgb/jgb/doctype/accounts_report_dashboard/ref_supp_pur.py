import frappe
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from io import BytesIO
from openpyxl.styles import Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
@frappe.whitelist()
def download():
    filename = "Domestic Purchase"
    xlsx_file = make_xlsx()
    frappe.response["filename"] = filename + ".xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"

def get_domestic_data(args):
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    company = args.get("company")

    gl_entries = frappe.db.sql(
        """
        SELECT
            gl.voucher_no AS expense_claim
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` acc
            ON acc.name = gl.account
        WHERE
            gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND gl.company = %(company)s
            AND gl.voucher_subtype = 'Expense Claim'
            AND gl.debit > 0
            AND gl.is_cancelled = 0
            AND acc.account_number = '1105'
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
        },
        as_dict=True,
    )

    if not gl_entries:
        return []

    expense_claims = tuple({d.expense_claim for d in gl_entries})

    data = frappe.db.sql(
        """
        SELECT
            ec.name AS expense_claim,
            ec.posting_date AS pi_date,
            ecd.custom_supplier AS supplier,
            ecd.custom_supplier_name AS supplier_name,
            SUM(ecd.amount) AS total,
            SUM(ecd.custom_tax_amount) AS vat_amount
        FROM `tabExpense Claim` ec
        INNER JOIN `tabExpense Claim Detail` ecd
            ON ecd.parent = ec.name
        
        WHERE
            ec.name IN %(expense_claims)s
            AND ec.docstatus = 1
            AND ecd.custom_supplier IS NOT NULL
            AND ecd.custom_tax_amount > 0
        GROUP BY
            ec.name,
            ecd.custom_supplier
        ORDER BY
            ec.posting_date
        """,
        {
            "expense_claims": expense_claims
        },
        as_dict=True,
    )
    jv_data = frappe.db.sql(
        """
        SELECT
            je.name AS expense_claim,
            je.posting_date AS pi_date,
            jed.custom_ref_supplier_vat AS tax_id,
            MAX(jed.custom_ref_supplier) AS supplier,
            MAX(jed.custom_ref_supplier_name) AS supplier_name,
            SUM(CASE WHEN acc.account_number != '1105' THEN jed.debit_in_account_currency ELSE 0 END) AS total,
            SUM(CASE WHEN acc.account_number = '1105' THEN jed.debit_in_account_currency ELSE 0 END) AS vat_amount
        FROM `tabJournal Entry` je
        INNER JOIN `tabJournal Entry Account` jed ON jed.parent = je.name
        INNER JOIN `tabAccount` acc ON jed.account = acc.name
        WHERE
            je.docstatus = 1
            AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND je.company = %(company)s
        GROUP BY
            je.name
        HAVING
            SUM(CASE WHEN acc.account_number = '1105' AND jed.debit_in_account_currency > 0 THEN 1 ELSE 0 END) > 0
        ORDER BY
            je.posting_date
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
        },
        as_dict=True,
    )
    return data + jv_data


def ref_supp_pur(wb,sheet_name="Domestic Purchase(Ref Supplier)"):
    NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'
    args = frappe.local.form_dict
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    company = args.get("company")

    # wb = openpyxl.Workbook()
    # ws = wb.active
    # ws.title = sheet_name
    ws = wb.create_sheet(sheet_name)
    address = frappe.db.sql(
        """
        SELECT
            a.address_line1,
            a.custom_building_number,
            a.city,
            a.country
        FROM `tabAddress` a
        INNER JOIN `tabDynamic Link` dl
            ON dl.parent = a.name
        WHERE
            a.is_your_company_address = 1
            AND dl.link_doctype = 'Company'
            AND dl.link_name = %s
        LIMIT 1
        """,
        (company,),
        as_dict=True
    )

    address = address[0] if address else None

    address_parts = []
    if address:
        if address.address_line1:
            address_parts.append(address.address_line1)
        if address.custom_building_number:
            address_parts.append(address.custom_building_number)
        if address.city:
            address_parts.append(address.city)
        if address.country:
            address_parts.append(address.country)

    address_text = ", ".join(address_parts)
    vat_id=frappe.db.get_value('Company',company,'tax_id')
    header1=['Company Name','','','',company]
    header2=['Address','','','',address_text]
    header3=['VAT ID','','','',vat_id]
    month_year = datetime.strptime(from_date, "%Y-%m-%d").strftime("%b %Y").upper()
    header4=[f'VAT PAID REPORT ON PURCHASE (REF) -{month_year}','','','','','','','','','','','','','']
    headers = ["SL NO:", "Category","Date","Purchase/RetNo","Inv No","Inv Date","VAT LAW","Supplier Name","Supplier VAT No","Invoice Value","TAXABLE AMOUNT","VAT RATE","VAT AMOUNT","TOTAL"]
    ws.append(header1)
    ws.append(header2)
    ws.append(header3)
    ws.append(header4)
    ws.append(headers)

    for i in range(1,4):
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=4)
        ws.merge_cells(start_row=i, start_column=5, end_row=i, end_column=14)
        
    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=14)

    taxable = 0
    vat_amount=0
    total_amnt=0
    sr_no=1
    for d in get_domestic_data(args):
        rate_value = 15 / 100
        grand_total=d.total or 0+ d.vat_amount or 0
        grand_total=grand_total+d.vat_amount
        ws.append([
            sr_no,
            'LOCAL',
            d.pi_date,
            d.expense_claim,
            d.expense_claim,
            d.pi_date,
            "STD RATED",
            d.supplier_name,
            d.tax_id,
            d.total,
            d.total,
            rate_value,
            d.vat_amount,
            grand_total
        ])
        sr_no+=1
        taxable += d.total or 0
        vat_amount += d.vat_amount or 0
        total_amnt += grand_total or 0
        amount_cols = [10, 11, 13, 14]  
        for col in amount_cols:
            cell = ws.cell(row=ws.max_row, column=col)
            cell.number_format = NUMBER_FORMAT
        cell = ws.cell(row=ws.max_row, column=12)
        cell.number_format = '0%'

    ws.append(["Total", "", "", "", "","","","","","",taxable,"",vat_amount,total_amnt])
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 13
    ws.column_dimensions['H'].width = 25
    ws.column_dimensions['I'].width = 20
    ws.column_dimensions['J'].width = 20
    ws.column_dimensions['K'].width = 15
    ws.column_dimensions['L'].width = 15
    ws.column_dimensions['M'].width = 15
    ws.column_dimensions['N'].width = 15
    dark_blue_fill = PatternFill("solid", fgColor="1F4E79")
    white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=14)
    left_align = Alignment(horizontal="left", vertical="center")
    light_blue_fill = PatternFill("solid", fgColor="DDEBF7") 
    value_font = Font(bold=True, size=16, name="Calibri")
    center_align = Alignment(horizontal="center", vertical="center")
    for row in range(1, 4):
        for col in range(1, 5):  
            cell = ws.cell(row=row, column=col)
            cell.fill = dark_blue_fill
            cell.font = white_bold_font
            cell.alignment = left_align
        for col in range(5, 15):  
            cell = ws.cell(row=row, column=col)
            cell.fill = light_blue_fill
            cell.font = value_font
            cell.alignment = left_align
    for col in range(1, 15):
        cell = ws.cell(row=4, column=col)
        cell.fill = dark_blue_fill
        cell.font = white_bold_font
        cell.alignment = center_align
    light_blue_fill = PatternFill("solid", fgColor="9BC2E6")
    header_font = Font(bold=True, name="Calibri", size=11)
    for col in range(1, 15): 
        cell = ws.cell(row=5, column=col)
        cell.fill = light_blue_fill
        cell.font = header_font
        cell.alignment = center_align
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )
    last_row = ws.max_row
    ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=9)
    white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
    for col in range(1, 15):
        cell = ws.cell(row=last_row, column=col)
        cell.fill = dark_blue_fill
        cell.font = white_bold_font
        
    
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=14):
        for cell in row:
            cell.border = thin_border
    for row in range(1, ws.max_row + 1):
        ws[f"H{row}"].alignment = Alignment(wrap_text=True)
    last_row = ws.max_row
    for col in [11, 13, 14]:  
        cell = ws.cell(row=last_row, column=col)
        cell.number_format = NUMBER_FORMAT
        cell.font = white_bold_font
    # xlsx_file = BytesIO()
    # wb.save(xlsx_file)
    # xlsx_file.seek(0)
    return taxable,vat_amount

