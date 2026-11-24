import frappe
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from io import BytesIO
from openpyxl.styles import Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
@frappe.whitelist()
def download():
    filename = "Domestic Sales"
    xlsx_file = domestic_sales_gl()
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
            si.customer,
            si.customer_name,
            COALESCE(si.tax_id, cust.tax_id) AS tax_id,
            si.net_total AS total,
            acc.tax_rate AS rate_value,
            CASE
                WHEN gl.voucher_subtype = 'Credit Note'
                    THEN -1 * gl.debit
                ELSE gl.credit
            END AS vat_amount,
            si.net_total + CASE
                WHEN gl.voucher_subtype = 'Credit Note'
                    THEN -1 * gl.debit
                ELSE gl.credit
            END AS grand_total,
            COALESCE(si.total_advance, 0) AS total_advance
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` acc
            ON acc.name = gl.account
        INNER JOIN `tabSales Invoice` si
            ON si.name = gl.voucher_no
        INNER JOIN `tabCompany` co
            ON co.name = si.company
        INNER JOIN `tabCustomer` cust
            ON cust.name = si.customer
        WHERE
            gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND gl.company = %(company)s
            AND gl.voucher_type = 'Sales Invoice'
            AND gl.is_cancelled = 0
            AND acc.account_number = '2401'
            AND si.docstatus = 1
            AND si.custom_zatca_export_invoice=0
            AND (
                si.custom_zatca_tax_category != 'Zero Rated'
                OR si.custom_zatca_tax_category IS NULL
            )

        ORDER BY si.posting_date
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
        },
        as_dict=True,
    )

    advance = frappe.db.sql(
        """
        SELECT
            CASE WHEN si.is_return = 1 THEN 1 ELSE 2 END AS is_return,
            si.name AS pi_name,
            si.posting_date AS pi_date,
            si.party,
            si.party_name,
            cust.tax_id,
            si.party_name AS customer_name,
            CASE WHEN si.is_return = 1 THEN -1 * si.total_adv ELSE si.total_adv END AS total,
            adv.rate AS rate_value,
            CASE WHEN si.is_return = 1 THEN -1 * si.total_taxes_and_charges_adv ELSE si.total_taxes_and_charges_adv END AS vat_amount,
            CASE WHEN si.is_return = 1 THEN -1 * si.grand_total_adv ELSE si.grand_total_adv END AS grand_total
        FROM `tabAdvance Sales Invoice` si
        INNER JOIN `tabCustomer` cust
            ON cust.name = si.party
        INNER JOIN `tabAdvance Taxes and Charges` as adv
            ON adv.parent=si.name
        WHERE
            si.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND si.company = %(company)s
            AND si.workflow_state = 'Approved'
            AND si.docstatus = 1


        ORDER BY si.posting_date
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
        },
        as_dict=True,
    )

    # Net ASI-allocated portions from the final Sales Invoice.
    # The ASI already posted and reported its VAT to account 2401 in the ASI's own
    # period. When the ASI is allocated against a final SI via custom_advances_copy
    # (the second table on the SI), that portion's VAT must be deducted from the
    # SI's VAT in the current period to avoid double-counting.
    # Advances received via Payment Entry (top table, account 2201, no VAT at
    # receipt) are NOT netted — the SI's full GL-posted VAT is correct for those.
    si_names = [r["pi_name"] for r in entry]
    asi_allocations = {}
    if si_names:
        alloc_rows = frappe.db.sql(
            """
            SELECT
                asi_tbl.parent AS si_name,
                asi_tbl.custom_allocated_amount AS allocated_amount,
                adv.rate AS vat_rate
            FROM `tabadvance sales invoice table` asi_tbl
            INNER JOIN `tabAdvance Taxes and Charges` adv
                ON adv.parent = asi_tbl.reference_name
            WHERE asi_tbl.parent IN %s
                AND asi_tbl.custom_allocated_amount > 0
            """,
            (tuple(si_names),),
            as_dict=True,
        )
        for ar in alloc_rows:
            asi_allocations.setdefault(ar["si_name"], []).append(ar)

    for row in entry:
        for alloc in asi_allocations.get(row["pi_name"], []):
            allocated = float(alloc.get("allocated_amount") or 0)
            rate = float(alloc.get("vat_rate") or 0) / 100
            if allocated > 0 and rate > 0:
                alloc_taxable = round(allocated / (1 + rate), 2)
                alloc_vat = round(allocated - alloc_taxable, 2)
                row["total"] = round(float(row["total"]) - alloc_taxable, 2)
                row["vat_amount"] = round(float(row["vat_amount"]) - alloc_vat, 2)
                row["grand_total"] = round(float(row["grand_total"]) - allocated, 2)
    p_entry = frappe.db.sql(
        """
        SELECT
            pe.name AS pi_name,
            pe.posting_date AS pi_date,
            gl.account AS taxes_and_charges,
            sup.customer_name,
            sup.tax_id,
            pe.paid_amount AS total,
            gl.debit AS vat_amount,
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
            AND sup.custom_place_of_supply = comp.country
        ORDER BY pe.posting_date
        """,
        {
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
        },
        as_dict=True,
    )



    return entry + p_entry + advance

def domestic_sales_gl(wb,sheet_name="Domestic Sales"):
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
    header4=[f'VAT COLLECTION REPORT ON DOMESTIC SALES -{month_year}','','','','','','','','','','']
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
    for d in get_domestic_data(args):
        rate_value = (d.rate_value or 0) / 100
        if d.grand_total<0:
            vat_type="Credit Note"
        elif d.is_return==2:
            vat_type="Advance"
        else:
            vat_type="Invoice"
        ws.append([
            sr_no,
            'LOCAL',
            d.pi_name,
            d.pi_date,
            vat_type,
            d.customer_name,
            d.tax_id,
            d.total,
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
    
    return taxable,vat_amount

