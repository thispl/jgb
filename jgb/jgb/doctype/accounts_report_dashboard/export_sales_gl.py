import frappe
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from io import BytesIO
from openpyxl.styles import Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime

@frappe.whitelist()
def download():
    filename = "Export Sales"
    xlsx_file = make_xlsx()
    frappe.response["filename"] = filename + ".xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"

def get_domestic_data(args):
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    company = args.get("company")

    entry = frappe.db.sql(
        """
        SELECT
            si.is_return,
            si.name AS pi_name,
            si.posting_date AS pi_date,
            gl.account AS taxes_and_charges,
            si.customer_name,
            si.tax_id,
            si.net_total AS total,
            acc.tax_rate AS rate_value,
            CASE
                WHEN gl.voucher_subtype = 'Credit Note'
                    THEN -1 * gl.debit
                ELSE gl.credit
            END AS vat_amount,
            si.base_grand_total as grand_total
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` acc
            ON acc.name = gl.account
        INNER JOIN `tabSales Invoice` si
            ON si.name = gl.voucher_no
        INNER JOIN `tabCompany` co
            ON co.name = si.company
        WHERE
            gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND gl.company = %(company)s
            AND gl.voucher_type = 'Sales Invoice'
            AND gl.is_cancelled = 0
            AND si.docstatus = 1
            AND si.custom_zatca_tax_category='Services outside scope of tax / Not subject to VAT'
        ORDER BY si.posting_date
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
        },
        as_dict=True,
    )

    p_entry = frappe.db.sql(
        """
        SELECT
            pe.name AS pi_name,
            pe.posting_date AS pi_date,
            gl.account AS taxes_and_charges,
            sup.customer_name,
            sup.tax_id,
            pe.paid_amount AS total,
            gl.credit AS vat_amount,
            acc.tax_rate AS rate_value,
            pe.paid_amount AS grand_total
        FROM `tabGL Entry` gl
        INNER JOIN `tabPayment Entry` pe
            ON pe.name = gl.voucher_no
        INNER JOIN `tabAccount` acc
            ON acc.name = gl.account
        INNER JOIN `tabCustomer` sup
            ON sup.name = pe.party
        INNER JOIN `tabCompany` comp
            ON comp.name = pe.company
        WHERE
            gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND gl.company = %(company)s
            AND gl.voucher_type = 'Payment Entry'
            AND gl.credit > 0
            AND gl.is_cancelled = 0
            AND pe.docstatus = 1
            AND pe.party_type = 'Customer'
            AND acc.account_number = '2401'
            AND sup.custom_place_of_supply != comp.country
            AND NOT EXISTS (
                SELECT 1
                FROM `tabPayment Entry Reference` per
                WHERE per.parent = pe.name
            )
        ORDER BY pe.posting_date
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
        },
        as_dict=True,
    )
    
    return entry + p_entry

def export_sales_gl(wb,sheet_name="Export Sales"):
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
    header4=[f'VAT COLLECTION REPORT ON EXPORT SALES -{month_year}','','','','','','','','','','']
    headers = ["SL NO:", "Category","Inv No","Inv Date","VAT LAW","Customer Name","Customer VAT No","TAXABLE AMOUNT","VAT RATE","VAT AMOUNT","VAT TOTAL"]
    ws.append(header1)
    ws.append(header2)
    ws.append(header3)
    ws.append(header4)
    ws.append(headers)

    for i in range(1,4):
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=4)
        ws.merge_cells(start_row=i, start_column=5, end_row=i, end_column=11)
        
    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=11)

    taxable = 0
    vat_amount=0
    total_amnt=0
    sr_no=1
    pi_list=[]
    for d in get_domestic_data(args):
        rate_value = (d.rate_value or 0) / 100
        if d.pi_name in pi_list:
            continue
        pi_list.append(d.pi_name)
        ws.append([
            sr_no,
            'FOREIGN',
            d.pi_name,
            d.pi_date,
            'Export Invoice',
            d.customer_name,
            d.tax_id,
            d.grand_total,
            rate_value,
            d.vat_amount,
            d.grand_total
        ])
        sr_no+=1
        taxable += d.total or 0
        vat_amount += d.vat_amount or 0
        total_amnt += d.grand_total or 0
        amount_cols = [11,10,8]  
        for col in amount_cols:
            cell = ws.cell(row=ws.max_row, column=col)
            cell.number_format = NUMBER_FORMAT
        cell = ws.cell(row=ws.max_row, column=9)
        cell.number_format = '0%'

    ws.append(["Total", "", "", "", "","","",taxable,"",vat_amount,total_amnt])
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 30
    ws.column_dimensions['G'].width = 17
    ws.column_dimensions['H'].width = 15
    ws.column_dimensions['I'].width = 15
    ws.column_dimensions['J'].width = 15
    ws.column_dimensions['K'].width = 15
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
        for col in range(5, 12):  
            cell = ws.cell(row=row, column=col)
            cell.fill = light_blue_fill
            cell.font = value_font
            cell.alignment = left_align
    for col in range(1, 12):
        cell = ws.cell(row=4, column=col)
        cell.fill = dark_blue_fill
        cell.font = white_bold_font
        cell.alignment = center_align
    light_blue_fill = PatternFill("solid", fgColor="9BC2E6")
    header_font = Font(bold=True, name="Calibri", size=11)
    for col in range(1, 12): 
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
    ws.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=7)
    white_bold_font = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
    for col in range(1, 12):
        cell = ws.cell(row=last_row, column=col)
        cell.fill = dark_blue_fill
        cell.font = white_bold_font
        
    
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=11):
        for cell in row:
            cell.border = thin_border
    for row in range(1, ws.max_row + 1):
        ws[f"F{row}"].alignment = Alignment(wrap_text=True)
    last_row = ws.max_row
    for col in [11, 10, 8]:  
        cell = ws.cell(row=last_row, column=col)
        cell.number_format = NUMBER_FORMAT
        cell.font = white_bold_font
    # xlsx_file = BytesIO()
    # wb.save(xlsx_file)
    # xlsx_file.seek(0)
    return taxable

