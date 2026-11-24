# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SalesReportDashboard(Document):
    pass


@frappe.whitelist()
def sales_register_download_summary(from_date=None, to_date=None, company=None):

    import openpyxl
    from openpyxl.styles import Border, Side, PatternFill, Font, Alignment
    from io import BytesIO

    if not (company and from_date and to_date):
        frappe.throw("Missing required filters")

    wb = openpyxl.Workbook()
    
    first_sheet = wb.active
    is_first_sheet_used = False
    
    thin = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    header_fill = PatternFill("solid", fgColor="4f81bd")
    alt_fill = PatternFill("solid", fgColor="dce6f1")
    white_fill = PatternFill("solid", fgColor="ffffff")
    total_fill = PatternFill("solid", fgColor="f2f2f2") 

    column_widths = {
        "A": 5, "B": 15, "C": 25, "D": 15, "E": 30,
        "F": 20, "G": 13, "H": 25, "I": 65, "J": 10,
        "K": 20, "L": 30, "M": 17, "N": 45, "O": 18,
        "P": 25, "Q": 20, "R": 10, "S": 25, "T": 23,
        "U": 18, "V": 18, "W": 18, "X": 19
    }

    divisions = frappe.db.sql("""
        SELECT DISTINCT custom_division
        FROM `tabSales Invoice`
        WHERE docstatus = 1
        AND posting_date BETWEEN %s AND %s
        AND company = %s
    """, (from_date, to_date, company), as_dict=True)
    from datetime import datetime
    summary_data = {}
    ytd_data = {}
    for d in divisions:
        if not d.custom_division:
            continue

        div_details = frappe.db.sql("""
            SELECT 
                `tabDivision`.code,
                `tabDivision Account Details`.income_account
            FROM `tabDivision`
            JOIN `tabDivision Account Details`
                ON `tabDivision Account Details`.parent = `tabDivision`.name
            WHERE `tabDivision`.name = %s
            AND `tabDivision Account Details`.company = %s
        """, (d.custom_division, company), as_dict=True)

        for ds in div_details:
            div_code = ds.code
            summary_data[div_code] = {
                "sales_net": 0.0, "sales_vat": 0.0, "sales_grand": 0.0,"sales_os_amt": 0.0,
                "cn_net": 0.0, "cn_vat": 0.0, "cn_grand": 0.0, "cn_os_amt": 0.0
            }

            if not is_first_sheet_used:
                ws = first_sheet
                ws.title = div_code
                is_first_sheet_used = True
            else:
                ws = wb.create_sheet(title=div_code)

            header = [
                "S.No.", "Voucher Type", "Voucher No", "Voucher Status",
                "Sales Person User", "Region", "Posting Date", "Customer",
                "Customer Name", "Territory", "Tax Id", "Receivable Account",
                "Mode Of Payment", "Project", "Sales Order", "Delivery Note",
                "Cost Center", "Currency", ds.income_account,
                "2401 - VAT - 15 % - JGB",
                "Net Total", "Tax Total", "Grand Total", "Outstanding Amount"
            ]

            ws.append(header)

            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = Font(color="ffffff", bold=True)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin

            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width
            sr_no = 1
            invoices = frappe.db.sql("""
                SELECT *
                FROM `tabSales Invoice`
                WHERE docstatus = 1
                AND is_return = 0
                AND posting_date BETWEEN %s AND %s
                AND company = %s
                AND custom_division = %s
            """, (from_date, to_date, company, d.custom_division), as_dict=True)

            for s in invoices:
                summary_data[div_code]["sales_net"] += float(s.base_net_total or 0)
                summary_data[div_code]["sales_vat"] += float(s.custom_vat_amount or 0)
                summary_data[div_code]["sales_grand"] += float(s.base_grand_total or 0)
                summary_data[div_code]["sales_os_amt"] += abs(float(s.outstanding_amount or 0))
                month_name = frappe.utils.getdate(s.posting_date).strftime("%b").upper()

                if month_name not in ytd_data:
                    ytd_data[month_name] = {}

                if div_code not in ytd_data[month_name]:
                    ytd_data[month_name][div_code] = {
                        "net": 0,
                        "vat": 0,
                        "grand": 0
                    }

                ytd_data[month_name][div_code]["net"] += float(s.base_net_total or 0)
                ytd_data[month_name][div_code]["vat"] += float(s.custom_vat_amount or 0)
                ytd_data[month_name][div_code]["grand"] += float(s.base_grand_total or 0)
                so_dn = frappe.db.sql("""
                    SELECT DISTINCT sales_order, delivery_note
                    FROM `tabSales Invoice Item`
                    WHERE parent = %s
                """, (s.name,), as_dict=True)

                sales_orders = ", ".join(i.sales_order for i in so_dn if i.sales_order)
                delivery_notes = ", ".join(i.delivery_note for i in so_dn if i.delivery_note)

                pay_mode = frappe.db.sql("""
                    SELECT DISTINCT mode_of_payment
                    FROM `tabPayment Schedule`
                    WHERE parent = %s
                """, (s.name,), as_dict=True)

                payment_mode = ", ".join(i.mode_of_payment for i in pay_mode if i.mode_of_payment)
                region = frappe.db.get_value(
                    "Sales Person",
                    {"name": s.custom_sales_personuser},
                    "custom_territory"
                )
                ws.append([
                    sr_no, "Sales Invoice", s.name, "Submitted" if s.docstatus == 1 else "Draft",
                    s.custom_sales_personuser, region, frappe.format(s.posting_date, {"fieldtype": "Date"}),
                    s.customer, s.customer_name, s.territory, s.tax_id, s.debit_to, payment_mode,
                    s.project, sales_orders, delivery_notes, s.cost_center, s.currency,
                    s.base_net_total, s.custom_vat_amount, s.base_net_total,
                    s.custom_vat_amount, s.base_grand_total, s.outstanding_amount
                ])
                sr_no += 1
            journals = frappe.db.sql("""
                SELECT *
                FROM `tabJournal Entry`
                WHERE docstatus = 1
                AND posting_date BETWEEN %s AND %s
                AND custom_include_in_sales_register=1
                AND company = %s
                AND custom_division = %s
            """, (from_date, to_date, company, d.custom_division), as_dict=True)

            for s in journals:
                customer_jv = frappe.db.get_value("Journal Entry Account", {
                    "parent": s.name,
                    "party_type": "Customer"
                }, "party") or ""
                customer_name_jv=''
                jv_territory=''
                jv_tax_id=''
                if customer_jv:
                    customer_name_jv=frappe.db.get_value('Customer',customer_jv,'customer_name') or ''
                    jv_territory=frappe.db.get_value('Customer',customer_jv,'territory') or ''
                    jv_tax_id=frappe.db.get_value('Customer',customer_jv,'custom_vat_registration_number') or ''
                summary_data[div_code]["sales_net"] += float(s.total_debit or 0)
                summary_data[div_code]["sales_vat"] += 0
                summary_data[div_code]["sales_grand"] += float(s.total_debit or 0)
                summary_data[div_code]["sales_os_amt"] += 0
                month_name = frappe.utils.getdate(s.posting_date).strftime("%b").upper()

                if month_name not in ytd_data:
                    ytd_data[month_name] = {}

                if div_code not in ytd_data[month_name]:
                    ytd_data[month_name][div_code] = {
                        "net": 0,
                        "vat": 0,
                        "grand": 0
                    }

                ytd_data[month_name][div_code]["net"] += float(s.total_debit or 0)
                ytd_data[month_name][div_code]["vat"] += 0
                ytd_data[month_name][div_code]["grand"] += float(s.total_debit or 0)
                
                ws.append([
                    sr_no, "Journal Entry", s.name, "Submitted",
                    '', '', frappe.format(s.posting_date, {"fieldtype": "Date"}),
                    customer_jv or '', customer_name_jv or '', jv_territory, jv_tax_id,'', '',
                    '', '', '', s.custom_cost_center, 'SAR',
                    s.total_debit, 0, s.total_debit,
                    0, s.total_debit, 0
                ])
                sr_no += 1

            sales_total_row = ws.max_row + 1

            ws.append([
                "Total", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
                summary_data[div_code]["sales_net"],
                summary_data[div_code]["sales_vat"],
                summary_data[div_code]["sales_net"],
                summary_data[div_code]["sales_vat"],
                summary_data[div_code]["sales_grand"],
                summary_data[div_code]["sales_os_amt"],
            ])

            # Merge A:R
            ws.merge_cells(
                start_row=sales_total_row,
                start_column=1,
                end_row=sales_total_row,
                end_column=18
            )

            total_cell = ws.cell(sales_total_row, 1)
            total_cell.value = "Sales Total"
            total_cell.alignment = Alignment(horizontal="center", vertical="center")
            total_cell.font = Font(bold=True)

            for cell in ws[sales_total_row]:
                cell.fill = total_fill
                cell.border = thin
                cell.font = Font(bold=True)

            for col in range(19, 25):
                ws.cell(sales_total_row, col).number_format = '#,##0.00'
            credit_notes = frappe.db.sql("""
                SELECT *
                FROM `tabSales Invoice`
                WHERE docstatus = 1
                AND is_return = 1
                AND posting_date BETWEEN %s AND %s
                AND company = %s
                AND custom_division = %s
            """, (from_date, to_date, company, d.custom_division), as_dict=True)

            credit_header_row = None

            if credit_notes:
                ws.append([])
                ws.append(header)
                credit_header_row = ws.max_row

                for cell in ws[credit_header_row]:
                    cell.fill = header_fill
                    cell.font = Font(color="ffffff", bold=True)
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.border = thin

            for s in credit_notes:
                summary_data[div_code]["cn_net"] += abs(float(s.base_net_total or 0))
                summary_data[div_code]["cn_vat"] += abs(float(s.custom_vat_amount or 0))
                summary_data[div_code]["cn_grand"] += abs(float(s.base_grand_total or 0))
                summary_data[div_code]["cn_os_amt"] += abs(float(s.outstanding_amount or 0))
                
                so_dn = frappe.db.sql("""
                    SELECT DISTINCT sales_order, delivery_note
                    FROM `tabSales Invoice Item`
                    WHERE parent = %s
                """, (s.name,), as_dict=True)

                sales_orders = ", ".join(i.sales_order for i in so_dn if i.sales_order)
                delivery_notes = ", ".join(i.delivery_note for i in so_dn if i.delivery_note)

                pay_mode = frappe.db.sql("""
                    SELECT DISTINCT mode_of_payment
                    FROM `tabPayment Schedule`
                    WHERE parent = %s
                """, (s.name,), as_dict=True)

                payment_mode = ", ".join(i.mode_of_payment for i in pay_mode if i.mode_of_payment)
                region = frappe.db.get_value(
                    "Sales Person",
                    {"name": s.custom_sales_personuser},
                    "custom_territory"
                )
                ws.append([
                    sr_no, "Credit Note", s.name, "Submitted" if s.docstatus == 1 else "Draft",
                    s.custom_sales_personuser, region, frappe.format(s.posting_date, {"fieldtype": "Date"}),
                    s.customer, s.customer_name, s.territory, s.tax_id, s.debit_to, payment_mode,
                    s.project, sales_orders, delivery_notes, s.cost_center, s.currency,
                    s.base_net_total, s.custom_vat_amount, s.base_net_total,
                    s.custom_vat_amount, s.base_grand_total, s.outstanding_amount
                ])
                sr_no += 1
            if credit_notes:

                credit_total_row = ws.max_row + 1

                ws.append([
                    "Total", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
                   
                    -abs(summary_data[div_code]["cn_net"]),
                    -abs(summary_data[div_code]["cn_vat"]),
                    -abs(summary_data[div_code]["cn_net"]),
                    -abs(summary_data[div_code]["cn_vat"]),
                    -abs(summary_data[div_code]["cn_grand"]),
                    -abs(summary_data[div_code]["cn_os_amt"]),
                ])

                # Merge A:R
                ws.merge_cells(
                    start_row=credit_total_row,
                    start_column=1,
                    end_row=credit_total_row,
                    end_column=18
                )

                total_cell = ws.cell(credit_total_row, 1)
                total_cell.value = "Credit Total"
                total_cell.alignment = Alignment(horizontal="center", vertical="center")
                total_cell.font = Font(bold=True)

                for cell in ws[credit_total_row]:
                    cell.fill = total_fill
                    cell.border = thin
                    cell.font = Font(bold=True)

                for col in range(19, 25):
                    ws.cell(credit_total_row, col).number_format = '#,##0.00'
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                if credit_header_row and row[0].row in (credit_header_row - 1, credit_header_row):
                    continue
                for cell in row:
                    cell.border = thin
                    cell.fill = alt_fill if row[0].row % 2 == 0 else white_fill

            ws.freeze_panes = "A2"

    if not is_first_sheet_used:
        first_sheet.title = "No Data"
    from frappe.utils import getdate

    selected_year = getdate(to_date).year
    ytd_from_date = f"{selected_year}-01-01"

    ytd_data = {}

    ytd_invoices = frappe.db.sql("""
        SELECT
            si.custom_division,
            si.base_net_total,
            si.custom_vat_amount,
            si.base_grand_total,
            si.is_return,
            si.posting_date,
            d.code as div_code
        FROM `tabSales Invoice` si
        LEFT JOIN `tabDivision` d
            ON d.name = si.custom_division
        WHERE si.docstatus = 1
        AND si.company = %s
        AND si.posting_date BETWEEN %s AND %s
    """, (company, ytd_from_date, to_date), as_dict=True)

    for row in ytd_invoices:

        month_name = frappe.utils.getdate(
            row.posting_date
        ).strftime("%b").upper()

        if month_name not in ytd_data:
            ytd_data[month_name] = {}

        div_code = row.div_code

        if div_code not in ytd_data[month_name]:
            ytd_data[month_name][div_code] = {
                "net": 0,
                "vat": 0,
                "grand": 0
            }

        sign = -1 if row.is_return else 1

        ytd_data[month_name][div_code]["net"] += (
            sign * abs(float(row.base_net_total or 0))
        )

        ytd_data[month_name][div_code]["vat"] += (
            sign * abs(float(row.custom_vat_amount or 0))
        )

        ytd_data[month_name][div_code]["grand"] += (
            sign * abs(float(row.base_grand_total or 0))
        )
    summary_ws = wb.create_sheet(title="Summary")
    
    summary_ws.column_dimensions["A"].width = 25
    summary_ws.column_dimensions["B"].width = 20
    summary_ws.column_dimensions["C"].width = 20
    summary_ws.column_dimensions["D"].width = 20

    total_sales_net = total_sales_vat = total_sales_grand =total_sales_os_amt =  0.0
    total_cn_net = total_cn_vat = total_cn_grand =total_cn_os_amt = 0.0

    summary_ws.append(["Sales Invoice Summary Breakdown"])
    summary_ws.cell(row=summary_ws.max_row, column=1).font = Font(size=14, bold=True)
    summary_ws.append(["Division", "Sum of Net Total", "Sum of VAT", "Sum of Grand Total"])
    
    for cell in summary_ws[summary_ws.max_row]:
        cell.fill = header_fill
        cell.font = Font(color="ffffff", bold=True)
        cell.border = thin
    total_net = 0
    total_vat = 0
    total_grand = 0

    for div, data in summary_data.items():

        net_total = data["sales_net"] - data["cn_net"]
        vat_total = data["sales_vat"] - data["cn_vat"]
        grand_total = data["sales_grand"] - data["cn_grand"]

        summary_ws.append([
            div,
            net_total,
            vat_total,
            grand_total
        ])

        total_net += net_total
        total_vat += vat_total
        total_grand += grand_total

        for cell in summary_ws[summary_ws.max_row]:
            cell.border = thin
            if cell.column > 1:
                cell.number_format = '#,##0.00'

    summary_ws.append([
        "Total",
        total_net,
        total_vat,
        total_grand
    ])

    for cell in summary_ws[summary_ws.max_row]:
        cell.border = thin
        cell.fill = total_fill
        cell.font = Font(bold=True)

        if cell.column > 1:
            cell.number_format = '#,##0.00'
    summary_ws.append([])
    summary_ws.append([])
    summary_ws.append(["Year to Date Report"])
    title_row = summary_ws.max_row

    summary_ws.cell(title_row, 1).font = Font(size=14, bold=True)

    summary_ws.append([
        "Month",
        "Division",
        "Sum of Net Total",
        "Sum of VAT",
        "Sum of Grand Total"
    ])

    header_row = summary_ws.max_row

    for cell in summary_ws[header_row]:
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.border = thin

    divisions_order = sorted(
        {
            div
            for month_data in ytd_data.values()
            for div in month_data.keys()
        }
    )

    month_order = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12
    }

    for month in sorted(ytd_data.keys(), key=lambda x: month_order.get(x, 99)):

        month_start_row = summary_ws.max_row + 1

        month_net = 0
        month_vat = 0
        month_grand = 0

        for div in divisions_order:

            values = ytd_data.get(month, {}).get(div, {
                "net": 0,
                "vat": 0,
                "grand": 0
            })

            summary_ws.append([
                "",
                div,
                values["net"],
                values["vat"],
                values["grand"]
            ])

            month_net += values["net"]
            month_vat += values["vat"]
            month_grand += values["grand"]

            current_row = summary_ws.max_row

            for col in range(1, 6):
                summary_ws.cell(current_row, col).border = thin

            for col in range(3, 6):
                summary_ws.cell(current_row, col).number_format = '#,##0.00'

        month_end_row = summary_ws.max_row

        summary_ws.merge_cells(
            start_row=month_start_row,
            start_column=1,
            end_row=month_end_row,
            end_column=1
        )

        month_cell = summary_ws.cell(month_start_row, 1)
        month_cell.value = month
        month_cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )
        month_cell.font = Font(bold=True)

        summary_ws.append([
            "",
            "Total",
            month_net,
            month_vat,
            month_grand
        ])

        total_row = summary_ws.max_row

        for col in range(1, 6):
            cell = summary_ws.cell(total_row, col)
            cell.border = thin
            cell.fill = total_fill
            cell.font = Font(bold=True)

        for col in range(3, 6):
            summary_ws.cell(total_row, col).number_format = '#,##0.00'
    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    xlsx_file.seek(0)

    frappe.response["filename"] = "Sales Register.xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"
