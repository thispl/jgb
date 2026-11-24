import frappe
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
from datetime import datetime
from frappe.utils import getdate, add_months

EXPORT_TAX_CATEGORY = "Services outside scope of tax / Not subject to VAT"


@frappe.whitelist()
def download():
    args = frappe.local.form_dict
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    company = args.get("company")

    if not (from_date and to_date and company):
        frappe.throw("Please provide From Date, To Date and Company filters.")

    filename = f"Sales Summary {from_date} to {to_date}"
    xlsx_file = sales_summary(from_date, to_date, company)

    frappe.response["filename"] = filename + ".xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"


def _months_between(from_date, to_date):
    """Return [(year, month, "January 2026"), ...] covering the period."""
    d = getdate(from_date).replace(day=1)
    end = getdate(to_date).replace(day=1)
    months = []
    while d <= end:
        months.append((d.year, d.month, d.strftime("%B %Y")))
        d = add_months(d, 1)
    return months


def _get_sales_accounts(company):
    """Leaf revenue accounts + leaf output-VAT accounts for the company.

    Revenue = leaf children of the group(s) that parent the divisions'
    income accounts (e.g. `4000 - Revenue` -> 4001-4005, 4011, 4012, 4013).
    Falls back to all leaf Income accounts when no Division Account Details
    exist. VAT = leaf Liability accounts with account_type='Tax'
    (2401, 2402, 2403, 2406) — input VAT sits on the Asset root (1105).
    """
    revenue_groups = frappe.db.sql(
        """
        SELECT DISTINCT a.parent_account
        FROM `tabDivision Account Details` dad
        JOIN `tabAccount` a ON a.name = dad.income_account
        WHERE dad.company = %(company)s AND a.company = %(company)s
        """,
        {"company": company},
        pluck=True,
    )
    if revenue_groups:
        revenue_accounts = frappe.db.get_all(
            "Account",
            filters={
                "company": company,
                "is_group": 0,
                "parent_account": ["in", revenue_groups],
            },
            pluck="name",
        )
    else:
        revenue_accounts = frappe.db.get_all(
            "Account",
            filters={"company": company, "is_group": 0, "root_type": "Income"},
            pluck="name",
        )
    vat_accounts = frappe.db.get_all(
        "Account",
        filters={
            "company": company,
            "is_group": 0,
            "root_type": "Liability",
            "account_type": "Tax",
        },
        pluck="name",
    )
    return revenue_accounts, vat_accounts


def _get_division_maps(company):
    """cost_center -> division and income_account -> division maps."""
    rows = frappe.db.get_all(
        "Division Account Details",
        filters={"company": company},
        fields=["parent", "income_account", "cost_center"],
    )
    cc_map, acct_map, order = {}, {}, []
    for r in rows:
        if r.cost_center:
            cc_map[r.cost_center] = r.parent
        if r.income_account:
            acct_map[r.income_account] = r.parent
        if r.parent not in order:
            order.append(r.parent)
    return cc_map, acct_map, sorted(order)


def _get_monthly_gl_data(from_date, to_date, company, revenue_accounts, vat_accounts):
    """Aggregate GL into {(year, month): {division: {local, vat, export}}}.

    Same basis as the Trial Balance: submitted (is_cancelled=0) GL Entries in
    the period, net credit - debit. Period Closing Voucher rows are excluded —
    they zero out income (the Financial Statements report does the same).
    Division comes from the GL row's cost_center first, then its income account.
    VAT is taken only from sales vouchers — Sales Invoices / credit notes and
    Journal Entries marked custom_include_in_sales_register. Internal VAT
    settlement entries (debit Output VAT -> VAT Net Payable) and advance or
    purchase vouchers are ignored, so VAT matches the sales shown.
    """
    accounts = tuple(set(revenue_accounts) | set(vat_accounts))
    if not accounts:
        return {}, []

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(gl.posting_date) AS yr,
            MONTH(gl.posting_date) AS mth,
            gl.account,
            gl.cost_center,
            gl.voucher_type,
            COALESCE(je.custom_include_in_sales_register, 0) AS in_sales_register,
            CASE
                WHEN gl.voucher_type = 'Sales Invoice'
                     AND si.custom_zatca_tax_category = %(export_cat)s
                THEN 1 ELSE 0
            END AS is_export,
            SUM(gl.credit) - SUM(gl.debit) AS net
        FROM `tabGL Entry` gl
        LEFT JOIN `tabSales Invoice` si
            ON si.name = gl.voucher_no AND gl.voucher_type = 'Sales Invoice'
        LEFT JOIN `tabJournal Entry` je
            ON je.name = gl.voucher_no AND gl.voucher_type = 'Journal Entry'
        WHERE gl.company = %(company)s
          AND gl.is_cancelled = 0
          AND gl.voucher_type != 'Period Closing Voucher'
          AND gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND gl.account IN %(accounts)s
        GROUP BY yr, mth, gl.account, gl.cost_center, gl.voucher_type, in_sales_register, is_export
        """,
        {
            "company": company,
            "from_date": from_date,
            "to_date": to_date,
            "accounts": accounts,
            "export_cat": EXPORT_TAX_CATEGORY,
        },
        as_dict=True,
    )

    cc_map, acct_map, division_order = _get_division_maps(company)
    revenue_set = set(revenue_accounts)

    data = {}
    seen_divisions = []
    for row in rows:
        if row.account not in revenue_set and not (
            row.voucher_type == "Sales Invoice"
            or (row.voucher_type == "Journal Entry" and row.in_sales_register)
        ):
            continue
        division = (
            cc_map.get(row.cost_center)
            or acct_map.get(row.account)
            or "Unallocated"
        )
        if division not in seen_divisions:
            seen_divisions.append(division)
        bucket = data.setdefault((row.yr, row.mth), {}).setdefault(
            division, {"local": 0.0, "vat": 0.0, "export": 0.0}
        )
        net = float(row.net or 0)
        if row.account in revenue_set:
            if row.is_export:
                bucket["export"] += net
            else:
                bucket["local"] += net
        else:
            bucket["vat"] += net

    divisions = [d for d in division_order if d in seen_divisions]
    for d in seen_divisions:
        if d not in divisions:
            divisions.append(d)
    return data, divisions


def sales_summary(from_date, to_date, company, sheet_name="Division Sales Summary"):
    NUMBER_FORMAT = '#,##0.00_);(#,##0.00);"-"_);@'

    if getdate(to_date) < getdate(from_date):
        frappe.throw("To Date cannot be earlier than From Date.")

    months = _months_between(from_date, to_date)
    period_label = f"{months[0][2]} – {months[-1][2]}"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.views.sheetView[0].showGridLines = True

    font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    font_meta = Font(name="Calibri", size=10, bold=False)
    font_header = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
    font_sub_header = Font(name="Calibri", size=10, bold=True)
    font_data = Font(name="Calibri", size=10)
    font_total = Font(name="Calibri", size=10, bold=True)

    color_schemes = [
        ["337AB7", "99BDDB", "CCE0ED"],
        ["70AD47", "B7D6A3", "DBEAD1"],
        ["ED7D31", "F6BE98", "FADECB"],
        ["7030A0", "B898D0", "DFCEEC"] ,
        ["BF8F00", "E5CC80", "F2E6C0"]
    ]

    fill_navy_blue = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    fill_dark_gray = PatternFill(start_color="404040", end_color="404040", fill_type="solid")
    fill_light_gray_1 = PatternFill(start_color="A6A6A6", end_color="A6A6A6", fill_type="solid")
    fill_light_gray_2 = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    fill_cream_yellow = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    fill_dark_cement = PatternFill(start_color="BFBFBF", end_color="BFBFBF", fill_type="solid")
    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_zebra_light = PatternFill(start_color="F9FBFD", end_color="F9FBFD", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9')
    )
    thick_bottom_border = Border(
        left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'), bottom=Side(style='medium', color='595959')
    )
    double_bottom_border = Border(
        left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'), bottom=Side(style='double', color='595959')
    )

    ws.append([f"Consolidated Sales Summary - {period_label}"])
    company_currency = frappe.db.get_value("Company", company, "default_currency") or "SAR"
    formatted_date = datetime.now().strftime("%d-%b-%Y")
    ws.append(["Currency:", company_currency, "Last Updated:", formatted_date])

    ws.cell(row=2, column=1).font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=2, column=3).font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=2, column=2).font = font_meta
    ws.cell(row=2, column=4).font = font_meta

    revenue_accounts, vat_accounts = _get_sales_accounts(company)
    month_div_data, divisions = _get_monthly_gl_data(
        from_date, to_date, company, revenue_accounts, vat_accounts
    )

    months_list = [m[2] for m in months]

    ws.cell(row=5, column=1, value="Month").font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws.cell(row=5, column=1).alignment = Alignment(horizontal="center", vertical="center")

    col_idx = 2
    division_col_mappings = {}

    for idx, div_name in enumerate(divisions):
        scheme = color_schemes[idx % len(color_schemes)]
        fill_solid = PatternFill(start_color=scheme[0], end_color=scheme[0], fill_type="solid")
        fill_faded_half = PatternFill(start_color=scheme[1], end_color=scheme[1], fill_type="solid")
        fill_faded_three_quarters = PatternFill(start_color=scheme[2], end_color=scheme[2], fill_type="solid")

        ws.merge_cells(start_row=3, start_column=col_idx, end_row=3, end_column=col_idx+3)
        div_cell = ws.cell(row=3, column=col_idx, value=div_name)
        div_cell.font = font_header
        div_cell.fill = fill_solid
        div_cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.merge_cells(start_row=4, start_column=col_idx, end_row=4, end_column=col_idx+2)
        local_cell = ws.cell(row=4, column=col_idx, value="Local")
        local_cell.font = font_sub_header
        local_cell.fill = fill_faded_half
        local_cell.alignment = Alignment(horizontal="center", vertical="center")

        export_cell = ws.cell(row=4, column=col_idx+3, value="Export")
        export_cell.font = font_sub_header
        export_cell.fill = fill_faded_half
        export_cell.alignment = Alignment(horizontal="center", vertical="center")

        sub_headers = ["Net Sales", "VAT", "Total", "Export (Net)"]
        for i, sub_head in enumerate(sub_headers):
            c = ws.cell(row=5, column=col_idx+i, value=sub_head)
            c.font = font_sub_header
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.fill = fill_faded_three_quarters

        division_col_mappings[div_name] = {"start_col": col_idx}
        col_idx += 4

    total_block_start = col_idx

    ws.merge_cells(start_row=3, start_column=total_block_start, end_row=3, end_column=total_block_start+3)
    t_cell = ws.cell(row=3, column=total_block_start, value="Total")
    t_cell.font = font_header
    t_cell.fill = fill_dark_gray
    t_cell.alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells(start_row=4, start_column=total_block_start, end_row=4, end_column=total_block_start+2)
    tl_cell = ws.cell(row=4, column=total_block_start, value="Local")
    tl_cell.font = font_sub_header
    tl_cell.fill = fill_light_gray_1
    tl_cell.alignment = Alignment(horizontal="center", vertical="center")

    te_cell = ws.cell(row=4, column=total_block_start+3, value="Export")
    te_cell.font = font_sub_header
    te_cell.fill = fill_light_gray_1
    te_cell.alignment = Alignment(horizontal="center", vertical="center")

    total_sub_headers = ["Net Sales", "VAT", "Total", "Export (Net)"]
    for i, sub_head in enumerate(total_sub_headers):
        c = ws.cell(row=5, column=total_block_start+i, value=sub_head)
        c.font = font_sub_header
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.fill = fill_light_gray_2

    col_idx += 4

    net_sales_final_col = col_idx
    vat_final_col = col_idx + 1
    grand_total_final_col = col_idx + 2

    ws.merge_cells(start_row=3, start_column=net_sales_final_col, end_row=4, end_column=net_sales_final_col)
    ns_cell = ws.cell(row=3, column=net_sales_final_col, value="Net Sales\n(Excl. VAT)")
    ns_cell.font = font_header
    ns_cell.fill = fill_navy_blue
    ns_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.merge_cells(start_row=3, start_column=vat_final_col, end_row=4, end_column=vat_final_col)
    v_cell = ws.cell(row=3, column=vat_final_col, value="Total VAT")
    v_cell.font = font_header
    v_cell.fill = fill_navy_blue
    v_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.merge_cells(start_row=3, start_column=grand_total_final_col, end_row=4, end_column=grand_total_final_col)
    gt_cell = ws.cell(row=3, column=grand_total_final_col, value="Grand Total")
    gt_cell.font = font_header
    gt_cell.fill = fill_navy_blue
    gt_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for c_pos_idx in [net_sales_final_col, vat_final_col, grand_total_final_col]:
        filler = ws.cell(row=5, column=c_pos_idx, value="")
        filler.fill = fill_navy_blue

    row_start_data = 6
    month_rows = []
    for m_idx, (yr, mth, month_name) in enumerate(months):
        current_row = row_start_data + m_idx
        ws.cell(row=current_row, column=1, value=month_name).font = font_data

        data_dict = month_div_data.get((yr, mth), {})
        t_net = t_vat = t_exp = 0.0
        div_net_sales = {}

        for div_name, mapping in division_col_mappings.items():
            start_col = mapping["start_col"]
            div_data = data_dict.get(div_name)

            local_net = div_data["local"] if div_data else 0.0
            local_vat = div_data["vat"] if div_data else 0.0
            export_net = div_data["export"] if div_data else 0.0
            metrics = [local_net, local_vat, local_net + local_vat, export_net]

            for i, val in enumerate(metrics):
                cell = ws.cell(row=current_row, column=start_col+i, value=val)
                cell.font = font_data
                cell.number_format = NUMBER_FORMAT

            t_net += local_net
            t_vat += local_vat
            t_exp += export_net
            div_net_sales[div_name] = local_net + export_net

        month_rows.append({
            "div_net_sales": div_net_sales,
            "net_sales": t_net + t_exp,
            "vat": t_vat,
            "grand": t_net + t_vat + t_exp,
        })

        for i, val in enumerate([t_net, t_vat, t_net + t_vat, t_exp]):
            c = ws.cell(row=current_row, column=total_block_start+i, value=val)
            c.number_format = NUMBER_FORMAT
            c.font = font_data

        ns_formula = ws.cell(row=current_row, column=net_sales_final_col, value=t_net + t_exp)
        ns_formula.font = font_data
        ns_formula.number_format = NUMBER_FORMAT

        v_formula = ws.cell(row=current_row, column=vat_final_col, value=t_vat)
        v_formula.font = font_data
        v_formula.number_format = NUMBER_FORMAT

        gt_formula = ws.cell(row=current_row, column=grand_total_final_col, value=t_net + t_vat + t_exp)
        gt_formula.font = font_data
        gt_formula.number_format = NUMBER_FORMAT

    last_data_row = row_start_data + len(months) - 1
    total_row = last_data_row + 1
    cell_total_label = ws.cell(row=total_row, column=1, value="Total")
    cell_total_label.font = Font(name="Calibri", size=10, bold=True, color="000000")
    cell_total_label.fill = fill_dark_cement

    dept_total_row = total_row + 1
    ws.cell(row=dept_total_row, column=1, value="Dept. Total Excl. VAT").font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")

    # period totals per division -> (local_net, vat, export)
    div_totals = {}
    for div_name, mapping in division_col_mappings.items():
        start_col = mapping["start_col"]
        d_net = d_vat = d_exp = 0.0
        for (yr, mth, _label) in months:
            dd = month_div_data.get((yr, mth), {}).get(div_name)
            if dd:
                d_net += dd["local"]
                d_vat += dd["vat"]
                d_exp += dd["export"]
        div_totals[div_name] = (d_net, d_vat, d_exp)

        for i, val in enumerate([d_net, d_vat, d_net + d_vat, d_exp]):
            c_t = ws.cell(row=total_row, column=start_col+i, value=val)
            c_t.font = font_total
            c_t.number_format = NUMBER_FORMAT
            c_t.fill = fill_dark_cement

            c_d = ws.cell(row=dept_total_row, column=start_col+i)
            c_d.font = font_total
            c_d.number_format = NUMBER_FORMAT
            c_d.fill = fill_cream_yellow

        ws.cell(row=dept_total_row, column=start_col+3, value=d_net + d_exp)

    tot_net = sum(v[0] for v in div_totals.values())
    tot_vat = sum(v[1] for v in div_totals.values())
    tot_exp = sum(v[2] for v in div_totals.values())

    for i, val in enumerate([tot_net, tot_vat, tot_net + tot_vat, tot_exp]):
        c_t = ws.cell(row=total_row, column=total_block_start+i, value=val)
        c_t.font = font_total
        c_t.number_format = NUMBER_FORMAT
        c_t.fill = fill_dark_cement

        c_d = ws.cell(row=dept_total_row, column=total_block_start+i)
        c_d.font = font_total
        c_d.number_format = NUMBER_FORMAT
        c_d.fill = fill_cream_yellow

    ws.cell(row=dept_total_row, column=total_block_start+3, value=tot_net + tot_exp)

    grand_net = tot_net + tot_exp
    grand_gt = tot_net + tot_vat + tot_exp

    for c_pos, val in [(net_sales_final_col, grand_net), (vat_final_col, tot_vat), (grand_total_final_col, grand_gt)]:
        c_t = ws.cell(row=total_row, column=c_pos, value=val)
        c_t.font = font_total
        c_t.number_format = NUMBER_FORMAT
        c_t.fill = fill_dark_cement

        c_d = ws.cell(row=dept_total_row, column=c_pos, value=val)
        c_d.font = font_total
        c_d.number_format = NUMBER_FORMAT
        c_d.fill = fill_cream_yellow

    max_end_col = ws.max_column
    for row in ws.iter_rows(min_row=3, max_row=dept_total_row, min_col=1, max_col=max_end_col):
        for cell in row:
            if cell.row == total_row:
                cell.border = thick_bottom_border
            elif cell.row == dept_total_row:
                cell.border = double_bottom_border
            else:
                cell.border = thin_border

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_end_col)
    ws.merge_cells(start_row=3, start_column=1, end_row=4, end_column=1)
    ws.merge_cells(start_row=2, start_column=4, end_row=2, end_column=max_end_col)

    ws.row_dimensions[1].height = 40
    for col in range(1, max_end_col + 1):
        ws.cell(row=1, column=col).fill = fill_navy_blue

    title_cell = ws.cell(row=1, column=1)
    title_cell.font = font_title
    title_cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_num in range(3, dept_total_row + 1):
        cell = ws.cell(row=row_num, column=1)
        if row_num != total_row:
            cell.fill = fill_navy_blue
        if row_num in [3, 4, 5, dept_total_row]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
        elif row_num == total_row:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center")
            cell.font = Font(name="Calibri", color="FFFFFF")

    for r_num in range(row_start_data, last_data_row + 1):
        current_row_fill = fill_zebra_light if r_num % 2 == 0 else fill_white
        for c_num in range(2, max_end_col + 1):
            ws.cell(row=r_num, column=c_num).fill = current_row_fill

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        col_idx_num = col[0].column
        if col_idx_num > 2:
            ws.column_dimensions[col_letter].width = 15
        else:
            max_len = 0
            for cell in col:
                if cell.row > 2 and cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    ws.freeze_panes = "B6"

    # -------------------------------------------------------------------------
    # METHOD CALL: INJECT EXECUTIVE DASHBOARD AS SHEET 2
    # -------------------------------------------------------------------------
    build_executive_dashboard(
        wb=wb,
        period_label=period_label,
        company_currency=company_currency,
        formatted_date=formatted_date,
        division_col_mappings=division_col_mappings,
        color_schemes=color_schemes,
        months_list=months_list,
        month_rows=month_rows,
        div_totals=div_totals,
    )

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Border, Side, Alignment, PatternFill, Font
from openpyxl.utils import get_column_letter

def build_executive_dashboard(wb, period_label, company_currency, formatted_date, division_col_mappings, color_schemes, months_list, month_rows, div_totals):
    """
    Separate helper method that constructs Sheet 2 (Consolidated Summary)
    with extended headers and color-matched visual data bars.
    """
    ws_dash = wb.create_sheet(title="Consolidated Summary")
    ws_dash.views.sheetView[0].showGridLines = True

    # --- Typography & Styles Layout Refinement ---
    font_data = Font(name="Calibri", size=10)
    DASHBOARD_FORMAT = '#,##0;(#,##0);"-";@'

    fill_navy_blue = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    fill_zebra_light = PatternFill(start_color="F9FBFD", end_color="F9FBFD", fill_type="solid")
    fill_cream_yellow = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9')
    )

    dynamic_div_headers = list(division_col_mappings.keys())
    mom_col_idx = 1 + len(dynamic_div_headers) + 4
    n_months = len(months_list)
    first_data_row = 6
    last_data_row = first_data_row + n_months - 1
    dash_total_row = last_data_row + 1

    ws_dash.merge_cells(start_row=1, start_column=1, end_row=1, end_column=mom_col_idx)
    ws_dash.row_dimensions[1].height = 40
    title_dash = ws_dash.cell(row=1, column=1, value=f"Consolidated Sales Summary – {period_label} | Executive Dashboard View")
    title_dash.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    title_dash.alignment = Alignment(horizontal="center", vertical="center")

    ws_dash.merge_cells(start_row=2, start_column=1, end_row=2, end_column=mom_col_idx)
    ws_dash.row_dimensions[2].height = 20
    meta_dash = ws_dash.cell(row=2, column=1, value=f"Currency: {company_currency}   |   Last Updated: {formatted_date}   |   Data Cycle: {period_label}")
    meta_dash.font = Font(name="Calibri", size=10, italic=True, color="FFFFFF")
    meta_dash.alignment = Alignment(horizontal="center", vertical="center")

    for col in range(1, mom_col_idx + 1):
        ws_dash.cell(row=1, column=col).fill = fill_navy_blue
        ws_dash.cell(row=2, column=col).fill = fill_navy_blue


    # -------------------------------------------------------------------------
    # ► SECTION 1: MONTHLY NET SALES BY DIVISION
    # -------------------------------------------------------------------------
    ws_dash.merge_cells(start_row=4, start_column=1, end_row=4, end_column=mom_col_idx)
    ws_dash.row_dimensions[4].height = 24
    sec1_title = ws_dash.cell(row=4, column=1, value="  ► MONTHLY NET SALES BY DIVISION (SAR, Excl. VAT)")
    sec1_title.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    sec1_title.fill = fill_navy_blue
    sec1_title.alignment = Alignment(horizontal="left", vertical="center")

    # UPDATED: Headers now all use Navy Blue background and White text for consistency
    full_dashboard_headers = ["Month"] + dynamic_div_headers + ["Total Net", "VAT", "Grand Total", "MoM %"]
    ws_dash.row_dimensions[5].height = 24
    for idx, text in enumerate(full_dashboard_headers, start=1):
        c = ws_dash.cell(row=5, column=idx, value=text)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = thin_border

        # LOGIC: Apply Navy to structural columns, Division Colors to dynamic ones
        if idx == 1 or idx > len(dynamic_div_headers) + 1:
            # Month, Total Net, VAT, Grand Total, MoM %
            c.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            c.fill = fill_navy_blue
        else:
            # Dynamic Division Headers
            scheme = color_schemes[(idx - 2) % len(color_schemes)]
            c.font = Font(name="Calibri", size=10, bold=True, color=scheme[0])
            c.fill = PatternFill(start_color=scheme[2], end_color=scheme[2], fill_type="solid")


    # Monthly Data Rows with Zebra Striping
    for m_idx, month_name in enumerate(months_list, start=1):
        r = 5 + m_idx
        ws_dash.row_dimensions[r].height = 20
        m_data = month_rows[m_idx - 1]
        # Determine row fill
        row_fill = fill_zebra_light if m_idx % 2 == 0 else fill_white

        # Apply style to all cells in the row
        for col_idx in range(1, mom_col_idx + 1):
            c = ws_dash.cell(row=r, column=col_idx)
            c.fill = row_fill
            c.border = thin_border
            if col_idx == 1:
                c.value = month_name
                c.font = Font(name="Calibri", size=10, bold=True)
                c.alignment = Alignment(horizontal="left", vertical="center")

        # Populate Division Sales (local + export net)
        for d_idx, div_name in enumerate(division_col_mappings):
            col_target = 2 + d_idx
            ws_dash.cell(row=r, column=col_target, value=m_data["div_net_sales"].get(div_name, 0.0)).number_format = DASHBOARD_FORMAT

        # Populate Global Totals
        for g_idx, val in enumerate([m_data["net_sales"], m_data["vat"], m_data["grand"]]):
            col_target = 2 + len(dynamic_div_headers) + g_idx
            ws_dash.cell(row=r, column=col_target, value=val).number_format = DASHBOARD_FORMAT

        # MoM %
        if m_idx > 1:
            prev = month_rows[m_idx - 2]["net_sales"]
            mom = (m_data["net_sales"] - prev) / prev if prev > 0 else 0
            c_mom = ws_dash.cell(row=r, column=mom_col_idx, value=mom)
            c_mom.number_format = '[Color10]+0.0%;[Red]-0.0%;"0.0%"'
            c_mom.font = Font(name="Calibri", size=10, bold=True)

    # TOTAL ROW: Color-matched to divisions and uniform labels
    s1_total_row = dash_total_row
    ws_dash.row_dimensions[s1_total_row].height = 22

    lbl = ws_dash.cell(row=s1_total_row, column=1, value="TOTAL")
    lbl.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    lbl.fill = fill_navy_blue
    lbl.border = thin_border

    col_totals = [sum(m["div_net_sales"].get(d, 0.0) for m in month_rows) for d in division_col_mappings]
    col_totals += [
        sum(m["net_sales"] for m in month_rows),
        sum(m["vat"] for m in month_rows),
        sum(m["grand"] for m in month_rows),
        None,  # MoM %
    ]
    for col_idx in range(2, mom_col_idx + 1):
        c = ws_dash.cell(row=s1_total_row, column=col_idx)
        c.number_format = DASHBOARD_FORMAT
        c.font = Font(name="Calibri", size=10, bold=True)
        c.border = thin_border

        # Apply division color if it's a division column
        if 2 <= col_idx <= len(dynamic_div_headers) + 1:
            scheme = color_schemes[(col_idx - 2) % len(color_schemes)]
            c.fill = PatternFill(start_color=scheme[2], end_color=scheme[2], fill_type="solid")
            c.font = Font(name="Calibri", size=10, bold=True, color=scheme[0])
        else:
            c.fill = fill_zebra_light

        c.value = col_totals[col_idx - 2]

    # -------------------------------------------------------------------------
    # ► SECTION 1B: PREVIOUS MONTH SALES (last month in the period)
    # -------------------------------------------------------------------------
    prev_title_row = dash_total_row + 3
    ws_dash.merge_cells(start_row=prev_title_row, start_column=1, end_row=prev_title_row, end_column=mom_col_idx)
    ws_dash.row_dimensions[prev_title_row].height = 24
    prev_title = ws_dash.cell(row=prev_title_row, column=1, value=f"  ► {months_list[-1].upper()} SALES")
    prev_title.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    prev_title.fill = fill_navy_blue
    prev_title.alignment = Alignment(horizontal="left", vertical="center")

    prev_headers = ["Division", "Net Sales (SAR)", "% Share", "MoM Growth %"]
    ws_dash.row_dimensions[prev_title_row + 1].height = 20
    for idx, text in enumerate(prev_headers, start=1):
        c = ws_dash.cell(row=prev_title_row + 1, column=idx, value=text)
        c.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        c.fill = fill_navy_blue
        c.alignment = Alignment(horizontal="center", vertical="center")

    cur_month = month_rows[-1]
    prev_month = month_rows[-2] if len(month_rows) > 1 else {}
    cur_net = cur_month["net_sales"]
    prev_net = prev_month.get("net_sales", 0.0)
    prev_total_mom = (cur_net - prev_net) / prev_net if prev_net > 0 else 0
    mom_format = '[Color10]+0.0%;[Red]-0.0%;"0.0%"'

    for idx, div_name in enumerate(division_col_mappings):
        r = prev_title_row + 2 + idx
        ws_dash.row_dimensions[r].height = 20
        scheme = color_schemes[idx % len(color_schemes)]

        c_name = ws_dash.cell(row=r, column=1, value=div_name)
        c_name.font = Font(name="Calibri", size=10, bold=True, color=scheme[0])
        c_name.fill = PatternFill(start_color=scheme[2], end_color=scheme[2], fill_type="solid")
        c_name.border = thin_border

        d_net = cur_month["div_net_sales"].get(div_name, 0.0)
        c_net = ws_dash.cell(row=r, column=2, value=d_net)
        c_net.font = font_data
        c_net.number_format = DASHBOARD_FORMAT
        c_net.border = thin_border

        c_share = ws_dash.cell(row=r, column=3, value=(d_net / cur_net) if cur_net else 0)
        c_share.font = font_data
        c_share.number_format = '0.0%'
        c_share.border = thin_border

        d_prev = prev_month.get("div_net_sales", {}).get(div_name, 0.0)
        c_mom = ws_dash.cell(row=r, column=4, value=((d_net - d_prev) / d_prev) if d_prev > 0 else 0)
        c_mom.font = Font(name="Calibri", size=10, bold=True)
        c_mom.number_format = mom_format
        c_mom.border = thin_border

    prev_total_row = prev_title_row + 2 + len(division_col_mappings)
    ws_dash.row_dimensions[prev_total_row].height = 22
    lbl = ws_dash.cell(row=prev_total_row, column=1, value="TOTAL")
    lbl.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    lbl.fill = fill_navy_blue
    lbl.border = thin_border

    for col_idx, (val, fmt) in enumerate([(cur_net, DASHBOARD_FORMAT), (1, '0.0%'), (prev_total_mom, mom_format)], start=2):
        c = ws_dash.cell(row=prev_total_row, column=col_idx, value=val)
        c.font = Font(name="Calibri", size=10, bold=True)
        c.number_format = fmt
        c.fill = fill_zebra_light
        c.border = thin_border

    # -------------------------------------------------------------------------
    # ► SECTION 2: DIVISION SHARE OF NET SALES (Actual Bar Charts)
    # -------------------------------------------------------------------------
    sec2_title_row = prev_total_row + 4
    ws_dash.merge_cells(start_row=sec2_title_row, start_column=1, end_row=sec2_title_row, end_column=mom_col_idx)
    ws_dash.row_dimensions[sec2_title_row].height = 24
    sec2_title = ws_dash.cell(row=sec2_title_row, column=1, value="  ► DIVISION SHARE OF NET SALES")
    sec2_title.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    sec2_title.fill = fill_navy_blue
    sec2_title.alignment = Alignment(horizontal="left", vertical="center")

    headers_s2 = ["Division", "Net Sales (SAR)", "% Share", "Bar (Visual)", ""]

    ws_dash.column_dimensions['D'].width = 22
    ws_dash.column_dimensions['E'].width = 22
    ws_dash.row_dimensions[sec2_title_row+1].height = 20
    for idx, text in enumerate(headers_s2, start=1):
        c = ws_dash.cell(row=sec2_title_row+1, column=idx, value=text)
        c.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        c.fill = fill_navy_blue
        c.alignment = Alignment(horizontal="center", vertical="center")

    grand_net = sum(v[0] + v[2] for v in div_totals.values())

    for idx, div_name in enumerate(division_col_mappings):
        r = sec2_title_row + 2 + idx
        ws_dash.row_dimensions[r].height = 20
        scheme = color_schemes[idx % len(color_schemes)]

        ws_dash.cell(row=r, column=1, value=div_name).fill = PatternFill(start_color=scheme[2], end_color=scheme[2], fill_type="solid")

        d_net = div_totals[div_name][0] + div_totals[div_name][2]
        c_val = ws_dash.cell(row=r, column=2, value=d_net)
        c_val.number_format = DASHBOARD_FORMAT

        share = d_net / grand_net if grand_net else 0
        c_pct = ws_dash.cell(row=r, column=3, value=share)
        c_pct.number_format = '0.0%'

        bars = min(max(round(share * 20), 0), 20)
        c_bar = ws_dash.cell(row=r, column=4, value="[" + "█" * bars + "░" * (20 - bars) + "]")
        c_bar.font = Font(name="Calibri", size=12, color=scheme[1])
        c_bar.alignment = Alignment(horizontal="left", vertical="center")
        c_bar.border = thin_border

    # -------------------------------------------------------------------------
    # ► SECTION 3: LOCAL vs EXPORT BREAKDOWN
    # -------------------------------------------------------------------------
    sec3_title_row = sec2_title_row + 4 + len(division_col_mappings)
    ws_dash.merge_cells(start_row=sec3_title_row, start_column=1, end_row=sec3_title_row, end_column=mom_col_idx)
    ws_dash.row_dimensions[sec3_title_row].height = 24
    sec3_title = ws_dash.cell(row=sec3_title_row, column=1, value="  ► LOCAL vs EXPORT BREAKDOWN (Net Sales)")
    sec3_title.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    sec3_title.fill = fill_navy_blue
    sec3_title.alignment = Alignment(horizontal="left", vertical="center")

    headers_s3 = ["Division", "Local Net", "Export Net", "Total Net", "Export %"]
    ws_dash.row_dimensions[sec3_title_row+1].height = 20
    for idx, text in enumerate(headers_s3, start=1):
        c = ws_dash.cell(row=sec3_title_row+1, column=idx, value=text)
        c.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        c.fill = fill_navy_blue
        c.alignment = Alignment(horizontal="center", vertical="center")

    for idx, div_name in enumerate(division_col_mappings):
        r = sec3_title_row + 2 + idx
        ws_dash.row_dimensions[r].height = 20
        scheme = color_schemes[idx % len(color_schemes)]
        fill_sub_light = PatternFill(start_color=scheme[2], end_color=scheme[2], fill_type="solid")

        c_name = ws_dash.cell(row=r, column=1, value=div_name)
        c_name.font = Font(name="Calibri", size=10, bold=True, color=scheme[0])
        c_name.fill = fill_sub_light
        c_name.border = thin_border

        d_local, _d_vat, d_export = div_totals[div_name]

        c_loc = ws_dash.cell(row=r, column=2, value=d_local)
        c_loc.font = font_data
        c_loc.number_format = DASHBOARD_FORMAT
        c_loc.border = thin_border

        c_exp = ws_dash.cell(row=r, column=3, value=d_export)
        c_exp.font = font_data
        c_exp.number_format = DASHBOARD_FORMAT
        c_exp.border = thin_border

        c_tot = ws_dash.cell(row=r, column=4, value=d_local + d_export)
        c_tot.font = font_data
        c_tot.number_format = DASHBOARD_FORMAT
        c_tot.border = thin_border

        c_pct = ws_dash.cell(row=r, column=5, value=(d_export / (d_local + d_export)) if (d_local + d_export) > 0 else 0)
        c_pct.font = font_data
        c_pct.number_format = '0.0%'
        c_pct.border = thin_border

    ws_dash.column_dimensions['A'].width = 24
    for col_idx in range(2, mom_col_idx + 1):
        ws_dash.column_dimensions[get_column_letter(col_idx)].width = 16
