import frappe
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from io import BytesIO
from openpyxl.styles import Border, Side
from openpyxl.utils import get_column_letter
@frappe.whitelist()
def download():
    filename = "Daily Transaction Report"
    xlsx_file = make_xlsx()
    frappe.response["filename"] = filename + ".xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"

def get_bank_accounts(company):
    return frappe.db.get_all(
        "Account",
        filters=[
            ["parent_account", "like", "%Bank%"],
            ["parent_account", "not like", "%Charges%"],
            ["is_group", "=", 0],
            ["company", "=", company],
        ],
        pluck="name"
    )

def get_bank(account):
    account = account or ""
    if "- SNB" in account:
        return "SNB"
    elif "- SAB -" in account:
        return "SAB"
    elif "- BSF -" in account:
        return "BSF"
    else:
        return "SAB (USD)"

def get_bank_summary(from_date, company):
    accounts = get_bank_accounts(company)
    rows = []
    if not accounts:
        return rows

    opening_map = {
        d.account: d.opening or 0
        for d in frappe.db.sql(
            """
            SELECT account, SUM(debit_in_transaction_currency - credit_in_transaction_currency) opening
            FROM `tabGL Entry`
            WHERE posting_date < %(from_date)s
              AND company = %(company)s
              AND account IN %(accounts)s
              AND is_cancelled = 0
            GROUP BY account
            """,
            {"from_date": from_date, "company": company, "accounts": tuple(accounts)},
            as_dict=True
        )
    }

    day_map = {
        d.account: d
        for d in frappe.db.sql(
            """
            SELECT account, SUM(debit_in_transaction_currency) debit, SUM(credit_in_transaction_currency) credit
            FROM `tabGL Entry`
            WHERE posting_date = %(from_date)s
              AND company = %(company)s
              AND account IN %(accounts)s
              AND is_cancelled = 0
            GROUP BY account
            """,
            {"from_date": from_date, "company": company, "accounts": tuple(accounts)},
            as_dict=True
        )
    }

    for acc in accounts:
        opening = opening_map.get(acc, 0)
        debit = day_map.get(acc, {}).get("debit", 0)
        credit = day_map.get(acc, {}).get("credit", 0)
        rows.append({
            "account": acc,
            "source": get_bank(acc),
            "opening": opening,
            "debit": debit,
            "credit": credit,
            "closing": opening + debit - credit,
        })
    return rows

def get_received_data(args):
    from_date = args.get("from_date")
    company = args.get("company")

    accounts = get_bank_accounts(company)

    if not accounts:
        return []

    entry = frappe.db.sql(
        """
        SELECT
            pe.posting_date,
            pe.paid_to,
            pe.paid_amount,
            COALESCE(per.reference_doctype,pe.party_type) AS reference_doctype,
            COALESCE(per.reference_name,pe.party) AS party_name

        FROM `tabPayment Entry` pe
        INNER JOIN `tabPayment Entry Reference` per
            ON per.parent = pe.name

        WHERE pe.posting_date = %(from_date)s
          AND pe.company = %(company)s
          AND pe.payment_type = 'Receive'
          AND pe.docstatus = 1
          AND pe.paid_to IN %(accounts)s

        ORDER BY pe.party
        """,
        {
            "from_date": from_date,
            "company": company,
            "accounts": tuple(accounts),
        },
        as_dict=True
    )
    journal_entries = frappe.db.sql(
        """
        SELECT
            je.posting_date,
            jea.account AS paid_from,
            jea.debit_in_account_currency AS paid_amount,
            COALESCE(
                jea.party_type,
                (
                    SELECT party_type
                    FROM `tabJournal Entry Account`
                    WHERE parent = je.name
                    AND party_type IS NOT NULL
                )
            ) AS reference_doctype,
             COALESCE(
                jea.party,
                (
                    SELECT party
                    FROM `tabJournal Entry Account`
                    WHERE parent = je.name
                    AND party IS NOT NULL
                    LIMIT 1
                )
            ) AS party_name,
            je.user_remark AS remark
        FROM `tabJournal Entry` je
        INNER JOIN `tabJournal Entry Account` jea
            ON jea.parent = je.name
        WHERE je.posting_date = %(from_date)s
        AND je.company = %(company)s
        AND je.docstatus = 1
        AND jea.account IN %(accounts)s
        AND jea.debit_in_account_currency > 0
        """,
        {
            "from_date": from_date,
            "company": company,
            "accounts": tuple(accounts),
        },
        as_dict=True
    )


    return entry + journal_entries

def get_pay_data(args):
    from_date = args.get("from_date")
    company = args.get("company")

    accounts = get_bank_accounts(company)
    # frappe.log_error('DATA1',accounts)
    if not accounts:
        return []

    entry = frappe.db.sql(
        """
        SELECT
            pe.posting_date,
            pe.paid_from,
            pe.paid_amount,
            COALESCE(per.reference_doctype, pe.party_type) AS reference_doctype,
            COALESCE(per.reference_name,pe.party) AS party_name

        FROM `tabPayment Entry` pe
        LEFT JOIN `tabPayment Entry Reference` per
            ON per.parent = pe.name

        WHERE pe.posting_date = %(from_date)s
        AND pe.company = %(company)s
        AND pe.payment_type = 'Pay'
        AND pe.docstatus = 1
        AND pe.paid_from IN %(accounts)s

        ORDER BY pe.party
        """,
        {
            "from_date": from_date,
            "company": company,
            "accounts": tuple(accounts),
        },
        as_dict=True
    )

    journal_entries = frappe.db.sql(
        """
        SELECT
            je.posting_date,
            jea.account AS paid_from,
            jea.credit_in_account_currency AS paid_amount,
            COALESCE(
                jea.party_type,
                (
                    SELECT party_type
                    FROM `tabJournal Entry Account`
                    WHERE parent = je.name
                    AND party_type IS NOT NULL
                    LIMIT 1
                )
            ) AS reference_doctype,
            COALESCE(
                jea.party,
                (
                    SELECT party
                    FROM `tabJournal Entry Account`
                    WHERE parent = je.name
                    AND party IS NOT NULL
                    LIMIT 1
                )
            ) AS party_name,
            je.user_remark AS remark
        FROM `tabJournal Entry` je
        INNER JOIN `tabJournal Entry Account` jea
            ON jea.parent = je.name
        WHERE je.posting_date = %(from_date)s
        AND je.company = %(company)s
        AND je.docstatus = 1
        AND jea.account IN %(accounts)s
        AND jea.credit_in_account_currency > 0
        """,
        {
            "from_date": from_date,
            "company": company,
            "accounts": tuple(accounts),
        },
        as_dict=True
    )


    return entry + journal_entries
        

def make_xlsx(sheet_name="Daily Transaction Report"):
    SAR_FORMAT = '_("SAR"* #,##0.00_);_("SAR"* (#,##0.00);_("SAR"* "-"??_);_(@_)'

    args = frappe.local.form_dict
    from_date = args.get("from_date")
    company = args.get("company")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name

    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")
    yellow = PatternFill("solid", fgColor="FFC000")
    blue = PatternFill("solid", fgColor="9DC3E6")
    thin = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    ws.merge_cells("A1:E1")
    ws["A1"] = "Daily Transaction Report"
    ws["A1"].font = Font(bold=True, size=16)
    ws["A1"].alignment = center
    
    report_date = frappe.utils.getdate(from_date).strftime("%d.%m.%Y : %A")
    ws.merge_cells("A2:E2")
    ws["A2"] = report_date
    ws["A2"].font = bold
    ws["A2"].alignment = center

    row = 3
    # RECEIVE PART (SECTION 1 IN CODE)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
    ws[f"A{row}"] = "Receipt"
    ws[f"A{row}"].font = bold
    ws[f"A{row}"].fill = blue
    ws[f"A{row}"].alignment = center
    row += 1

    headers = ["Source", "Party", "Party Name", "", "Value"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=col, value=h)
        c.font = bold
        c.fill = yellow
        c.border = thin
        c.alignment = center

    ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=4)
    row += 1

    total_receipt = 0
    for r in get_received_data(args):
        ws.append([
            get_bank(r.get("paid_to") or r.get("paid_from")),
            r.reference_doctype,
            r.party_name,
            "",
            r.paid_amount
        ])
        total_receipt += r.paid_amount or 0

        current_row = ws.max_row
        ws.merge_cells(start_row=current_row, start_column=3, end_row=current_row, end_column=4)
        ws.cell(row=current_row, column=5).number_format = SAR_FORMAT

    ws.append(["Total Receipt", "", "", "", total_receipt])
    # ws.append(["Total Receipt", "", "", "", total_receipt])
    ws.cell(row=ws.max_row, column=5).number_format = SAR_FORMAT

    row = ws.max_row + 1

    # PAY PART (SECTION 2 IN CODE)

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
    ws[f"A{row}"] = "Payments"
    ws[f"A{row}"].font = bold
    ws[f"A{row}"].fill = blue
    ws[f"A{row}"].alignment = center
    row += 1

    for col, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=col, value=h)
        c.font = bold
        c.fill = yellow
        c.border = thin
        c.alignment = center

    ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=4)
    row += 1

    total_payment = 0
    for p in get_pay_data(args):
        ws.append([
            get_bank(p.paid_from),
            p.reference_doctype,
            p.party_name,
            "",
            p.paid_amount
        ])
        total_payment += p.paid_amount or 0

        current_row = ws.max_row
        ws.merge_cells(start_row=current_row, start_column=3, end_row=current_row, end_column=4)
        ws.cell(row=current_row, column=5).number_format = SAR_FORMAT


    ws.append(["Total Expense", "", "", "", total_payment])
    ws.cell(row=ws.max_row, column=5).number_format = SAR_FORMAT

    row = ws.max_row + 1

    # BANK BALANCE PART (SECTION 3 IN CODE)

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
    ws[f"A{row}"] = "Bank Balance Summary"
    ws[f"A{row}"].font = bold
    ws[f"A{row}"].fill = blue
    ws[f"A{row}"].alignment = center
    row += 1

    headers = ["Source", "Opening", "Dr.", "Cr.", "Closing"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=col, value=h)
        c.font = bold
        c.fill = yellow
        c.border = thin
        c.alignment = center
    row += 1

    bank_rows = get_bank_summary(from_date, company)

    tot_op = tot_dr = tot_cr = tot_cl = 0

    for r_data in bank_rows:
        ws.append([
            r_data["source"],
            r_data["opening"],
            r_data["debit"],
            r_data["credit"],
            r_data["closing"]
        ])

        r = ws.max_row
        for col in range(2, 6):
            ws.cell(row=r, column=col).number_format = SAR_FORMAT

        tot_op += r_data["opening"]
        tot_dr += r_data["debit"]
        tot_cr += r_data["credit"]
        tot_cl += r_data["closing"]

    # ws.append(["Total", tot_op, tot_dr, tot_cr, tot_cl])
    
    ws.append(["Total", tot_op, tot_dr, tot_cr, tot_cl])

    r = ws.max_row
    for col in range(2, 6):
        ws.cell(row=r, column=col).number_format = SAR_FORMAT


    max_row = ws.max_row
    max_col = ws.max_column

    for row in range(1, max_row + 1):
        ws.row_dimensions[row].height = 22

        for col in range(1, max_col + 1):
            ws.column_dimensions[get_column_letter(col)].width = 20
            c = ws.cell(row=row, column=col)
            c.border = thin
            c.font = Font(name="Calibri", size=11)
    total_fill = PatternFill("solid", fgColor="D9D9D9")
    for row in range(1, ws.max_row + 1):
        cell_value = ws.cell(row=row, column=1).value 

        if cell_value in ["Total Receipt",'Total Expense']:
            ws.merge_cells(
                start_row=row,
                start_column=1,
                end_row=row,
                end_column=4
            )
            merged_cell = ws.cell(row=row, column=1)
            merged_cell.alignment = Alignment(horizontal="center", vertical="center")
            merged_cell.fill = total_fill

            ws.cell(row=row, column=5).fill = total_fill
    last_row = ws.max_row

    if ws.cell(row=last_row, column=1).value == "Total":
        for col in range(1, ws.max_column + 1):
            ws.cell(row=last_row, column=col).fill = total_fill
            ws.cell(row=last_row, column=col).font = Font(bold=True)
    title_font = Font(
        bold=True,
        size=14,
        color="154186" 
    )

    for row in range(1, ws.max_row + 1):
        cell = ws.cell(row=row, column=1)
        if cell.value == "Daily Transaction Report":
            cell.font = title_font
    bold_font = Font(bold=True)

    keywords = {
        "Receipt",
        "Payments",
        "Bank Balance Summary",
        "Total Receipt",
        "Total Expense",
    }

    for row in range(1, ws.max_row + 1):
        cell_value = ws.cell(row=row, column=1).value

        if isinstance(cell_value, str) and cell_value.strip() in keywords:
            for col in range(1, ws.max_column + 1):
                ws.cell(row=row, column=col).font = bold_font
    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    xlsx_file.seek(0)
    return xlsx_file

def daily_transaction_report(doc):
    from_date = doc.get("transaction_date") or doc.get("from_date")
    company = doc.get("company")
    args = {"from_date": from_date, "company": company}

    receipts = get_received_data(args)
    payments = get_pay_data(args)
    bank_rows = get_bank_summary(from_date, company)

    def fmt(v):
        return frappe.utils.fmt_money(v, currency="SAR")

    html = """
    <style>
        .dtr-table { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
        .dtr-table th, .dtr-table td { border: 1px solid #000; padding: 4px 8px; font-size: 12px; }
        .dtr-table th { background: #FFC000; text-align: center; font-weight: bold; }
        .dtr-section td { background: #9DC3E6; text-align: center; font-weight: bold; }
        .dtr-total td { background: #D9D9D9; font-weight: bold; }
        .dtr-num { text-align: right; }
    </style>
    """

    def section(title, rows, total_label):
        total = 0
        out = '<table class="dtr-table">'
        out += f'<tr class="dtr-section"><td colspan="5">{title}</td></tr>'
        out += '<tr><th>Source</th><th>Party</th><th colspan="2">Party Name</th><th>Value</th></tr>'
        for r in rows:
            amt = r.paid_amount or 0
            total += amt
            bank_account = r.get("paid_to") or r.get("paid_from")
            out += (
                f'<tr><td>{get_bank(bank_account)}</td>'
                f'<td>{r.reference_doctype or ""}</td>'
                f'<td colspan="2">{r.party_name or ""}</td>'
                f'<td class="dtr-num">{fmt(amt)}</td></tr>'
            )
        out += f'<tr class="dtr-total"><td colspan="4" style="text-align:center;">{total_label}</td><td class="dtr-num">{fmt(total)}</td></tr>'
        out += '</table>'
        return out

    html += section("Receipt", receipts, "Total Receipt")
    html += section("Payments", payments, "Total Expense")

    html += '<table class="dtr-table">'
    html += '<tr class="dtr-section"><td colspan="5">Bank Balance Summary</td></tr>'
    html += '<tr><th>Source</th><th>Opening</th><th>Dr.</th><th>Cr.</th><th>Closing</th></tr>'
    tot_op = tot_dr = tot_cr = tot_cl = 0
    for r in bank_rows:
        html += (
            f'<tr><td>{r["source"]}</td>'
            f'<td class="dtr-num">{fmt(r["opening"])}</td>'
            f'<td class="dtr-num">{fmt(r["debit"])}</td>'
            f'<td class="dtr-num">{fmt(r["credit"])}</td>'
            f'<td class="dtr-num">{fmt(r["closing"])}</td></tr>'
        )
        tot_op += r["opening"]
        tot_dr += r["debit"]
        tot_cr += r["credit"]
        tot_cl += r["closing"]
    html += (
        f'<tr class="dtr-total"><td>Total</td>'
        f'<td class="dtr-num">{fmt(tot_op)}</td>'
        f'<td class="dtr-num">{fmt(tot_dr)}</td>'
        f'<td class="dtr-num">{fmt(tot_cr)}</td>'
        f'<td class="dtr-num">{fmt(tot_cl)}</td></tr>'
    )
    html += '</table>'
    return html
