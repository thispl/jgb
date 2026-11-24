# Copyright (c) 2026, Joint Global Business and Contributors
# See license.txt

import frappe
from frappe.utils import flt, getdate, formatdate, today, cstr
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from io import BytesIO
import html as _html


def esc(val):
    return _html.escape(str(val)) if val is not None else ""


def fmt_currency(val):
    if val is None or val == "" or flt(val) == 0:
        return "-"
    try:
        return f"{flt(val):,.2f}"
    except Exception:
        return str(val)


def get_fixed_asset_register_data(company=None, to_date=None, from_date=None):
    """Fetch and calculate all Fixed Asset Register data until the selected to_date.

    Fixed Asset Register displays all assets acquired on or before to_date
    with accumulated depreciation and disposal tracking as of that date.
    """
    to_dt = getdate(to_date) if to_date else getdate(today())

    conditions = {"docstatus": 1}
    if company:
        conditions["company"] = company
    if to_dt:
        conditions["purchase_date"] = ["<=", to_dt]

    assets = frappe.get_all(
        "Asset",
        filters=conditions,
        fields=[
            "name",
            "asset_name",
            "item_code",
            "asset_category",
            "purchase_date",
            "available_for_use_date",
            "gross_purchase_amount",
            "opening_accumulated_depreciation",
            "status",
            "disposal_date",
            "calculate_depreciation",
            "is_existing_asset",
            "company",
        ],
        order_by="asset_category asc, purchase_date asc, name asc",
    )

    # Pre-fetch Asset Value Adjustments
    adjustments_map = {}
    if assets:
        asset_names = [a.name for a in assets]
        adjustments = frappe.get_all(
            "Asset Value Adjustment",
            filters={"docstatus": 1, "asset": ["in", asset_names]},
            fields=["asset", "date", "current_asset_value", "new_asset_value", "difference_amount"],
            order_by="date desc",
        )
        for adj in adjustments:
            if adj.asset not in adjustments_map:
                adjustments_map[adj.asset] = adj

    # Group assets by Asset Category
    categories_dict = {}
    for a in assets:
        cat = a.asset_category or "Other Assets"
        categories_dict.setdefault(cat, []).append(a)

    categories_data = []
    grand_totals = {
        "cost_beg": 0.0,
        "additions": 0.0,
        "disposals": 0.0,
        "cost_end": 0.0,
        "dep_curr": 0.0,
        "dep_beg": 0.0,
        "dep_disp": 0.0,
        "total_acc_dep": 0.0,
        "nbv": 0.0,
        "adj_cost": 0.0,
        "adj_acc_dep": 0.0,
        "adj_nbv": 0.0,
        "disp_cost": 0.0,
        "disp_acc_dep": 0.0,
        "disp_nbv": 0.0,
    }

    for cat_name, cat_assets in categories_dict.items():
        cat_subtotals = {
            "cost_beg": 0.0,
            "additions": 0.0,
            "disposals": 0.0,
            "cost_end": 0.0,
            "dep_curr": 0.0,
            "dep_beg": 0.0,
            "dep_disp": 0.0,
            "total_acc_dep": 0.0,
            "nbv": 0.0,
            "adj_cost": 0.0,
            "adj_acc_dep": 0.0,
            "adj_nbv": 0.0,
            "disp_cost": 0.0,
            "disp_acc_dep": 0.0,
            "disp_nbv": 0.0,
        }
        rows = []

        for asset in cat_assets:
            desc = asset.asset_name or asset.item_code or asset.name
            p_date_raw = asset.purchase_date or asset.available_for_use_date
            p_date_str = formatdate(p_date_raw, "dd/mm/yyyy") if p_date_raw else ""
            code = asset.item_code or asset.name

            # Rate
            afb = frappe.db.get_value(
                "Asset Finance Book",
                {"parent": asset.name},
                ["rate_of_depreciation", "total_number_of_depreciations", "frequency_of_depreciation"],
                as_dict=True,
            )
            rate = 0.25
            if afb:
                if afb.get("rate_of_depreciation"):
                    rate = flt(afb.rate_of_depreciation) / 100.0
                elif afb.get("total_number_of_depreciations") and afb.get("frequency_of_depreciation"):
                    total_months = flt(afb.total_number_of_depreciations) * flt(afb.frequency_of_depreciation)
                    if total_months > 0:
                        rate = round(12.0 / total_months, 4)

            gpa = flt(asset.gross_purchase_amount or 0.0)
            cost_beg = gpa
            add_yr = 0.0

            # Disposals as of to_dt
            dispos = 0.0
            disp_month = ""
            if asset.status in ["Sold", "Scrapped"] and asset.disposal_date:
                disp_dt = getdate(asset.disposal_date)
                if not to_dt or disp_dt <= to_dt:
                    dispos = gpa
                    disp_month = disp_dt.strftime("%b %Y")

            cost_end = cost_beg + add_yr - dispos

            # Depreciation calculations up to to_dt
            gl_entries = frappe.db.sql(
                """
                SELECT posting_date, debit
                FROM `tabGL Entry`
                WHERE against_voucher = %s AND is_cancelled = 0 AND debit > 0
            """,
                (asset.name,),
                as_dict=True,
            )

            dep_beg = flt(asset.opening_accumulated_depreciation or 0.0)
            dep_curr = 0.0
            for gle in gl_entries:
                entry_dt = getdate(gle.posting_date)
                if not to_dt or entry_dt <= to_dt:
                    dep_curr += flt(gle.debit)

            dep_disp = (dep_beg + dep_curr) if dispos > 0 else 0.0
            total_acc_dep = dep_beg + dep_curr - dep_disp
            nbv = cost_end - total_acc_dep

            # Adjustments
            adj_data = adjustments_map.get(asset.name)
            adj_cost = flt(adj_data.new_asset_value or adj_data.current_asset_value or 0.0) if adj_data else None
            adj_acc_dep = dep_beg if adj_data else None
            adj_nbv = (adj_cost - adj_acc_dep) if adj_cost is not None else None

            disp_cost = dispos if dispos > 0 else None
            disp_acc_dep = dep_disp if dep_disp > 0 else None
            disp_nbv = (dispos - dep_disp) if dispos > 0 else None

            # Subtotal additions
            cat_subtotals["cost_beg"] += cost_beg
            cat_subtotals["additions"] += add_yr
            cat_subtotals["disposals"] += dispos
            cat_subtotals["cost_end"] += cost_end
            cat_subtotals["dep_curr"] += dep_curr
            cat_subtotals["dep_beg"] += dep_beg
            cat_subtotals["dep_disp"] += dep_disp
            cat_subtotals["total_acc_dep"] += total_acc_dep
            cat_subtotals["nbv"] += nbv
            if adj_cost is not None:
                cat_subtotals["adj_cost"] += adj_cost
                cat_subtotals["adj_acc_dep"] += adj_acc_dep
                cat_subtotals["adj_nbv"] += adj_nbv
            if disp_cost is not None:
                cat_subtotals["disp_cost"] += disp_cost
                cat_subtotals["disp_acc_dep"] += disp_acc_dep
                cat_subtotals["disp_nbv"] += disp_nbv

            rows.append(
                {
                    "desc": desc,
                    "purchase_date": p_date_str,
                    "code": code,
                    "cost_beg": cost_beg,
                    "add_yr": add_yr if add_yr > 0 else None,
                    "dispos": dispos if dispos > 0 else None,
                    "cost_end": cost_end,
                    "rate": rate,
                    "dep_curr": dep_curr,
                    "dep_beg": dep_beg,
                    "dep_disp": dep_disp if dep_disp > 0 else None,
                    "total_acc_dep": total_acc_dep,
                    "nbv": nbv,
                    "adj_cost": adj_cost,
                    "adj_acc_dep": adj_acc_dep,
                    "adj_nbv": adj_nbv,
                    "disp_month": disp_month,
                    "disp_cost": disp_cost,
                    "disp_acc_dep": disp_acc_dep,
                    "disp_nbv": disp_nbv,
                }
            )

        for k in grand_totals:
            grand_totals[k] += cat_subtotals[k]

        categories_data.append(
            {
                "category_name": cat_name,
                "rows": rows,
                "subtotals": cat_subtotals,
            }
        )

    company_name = company or "Joint Global Business Co LLC"
    company_name_upper = (frappe.db.get_value("Company", company, "company_name") or company_name).upper()
    if not company_name_upper.endswith("."):
        company_name_upper += "."

    date_str = to_dt.strftime("%B %d, %Y").upper()

    return {
        "company_name": company_name_upper,
        "to_date": to_dt,
        "date_str": date_str,
        "subtitle_text": f"AS OF {date_str}",
        "categories": categories_data,
        "grand_totals": grand_totals,
    }


@frappe.whitelist()
def get_fixed_asset_register_html(doc=None):
    """Generate HTML table for Fixed Asset Register Report print format."""
    if isinstance(doc, str):
        import json
        doc = frappe._dict(json.loads(doc))
    elif not doc:
        doc = frappe.local.form_dict

    company = doc.get("company") if hasattr(doc, "get") else getattr(doc, "company", None)
    to_date = doc.get("to_date") if hasattr(doc, "get") else getattr(doc, "to_date", None)

    data = get_fixed_asset_register_data(company=company, to_date=to_date)
    categories = data["categories"]
    grand_totals = data["grand_totals"]

    html_out = """
<style>
@page {
    size: A4 landscape;
    margin: 0.8cm 0.6cm;
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-family: 'Calibri', Arial, sans-serif;
        font-size: 7px;
        color: #555;
    }
}
.far-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-family: 'Calibri', Arial, sans-serif;
    font-size: 6.5px;
}
.far-table th, .far-table td {
    border: 0.5px solid #A6A6A6;
    padding: 2px 1.5px;
    word-wrap: break-word;
    overflow-wrap: break-word;
    vertical-align: middle;
}
.far-grp-main {
    background: #D9E1F2;
    color: #1F3864;
    font-weight: bold;
    font-size: 7.5px;
    text-align: center;
}
.far-grp-adj {
    background: #FFF2CC;
    color: #7F6000;
    font-weight: bold;
    font-size: 7.5px;
    text-align: center;
}
.far-grp-disp {
    background: #E2EFDA;
    color: #375623;
    font-weight: bold;
    font-size: 7.5px;
    text-align: center;
}
.far-col-hdr {
    background: #F2F2F2;
    font-weight: bold;
    text-align: center;
    font-size: 6.5px;
}
.far-cat-hdr td {
    background: #F9F9F9;
    font-weight: bold;
    font-size: 7.5px;
    color: #1F497D;
    padding: 3px 2px;
}
.far-subtotal td {
    background: #E9EEF7;
    font-weight: bold;
    font-size: 6.5px;
    color: #1F3864;
}
.far-cat-total td {
    background: #F2F2F2;
    font-weight: bold;
    font-size: 6.5px;
    color: #1F497D;
    border-top: 1px solid #1F497D;
    border-bottom: 1px solid #1F497D;
}
.far-grand-total td {
    background: #1F3864;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 7px;
    border-top: 1px solid #000;
    border-bottom: 2px double #000;
}
.far-left { text-align: left; }
.far-center { text-align: center; }
.far-right { text-align: right; font-variant-numeric: tabular-nums; }
</style>

<table class="far-table">
<thead>
<tr>
    <th colspan="13" class="far-grp-main">Core Asset Cost &amp; Depreciation Schedule</th>
    <th colspan="3" class="far-grp-adj">Asset Value Adjustments / Revaluations</th>
    <th colspan="4" class="far-grp-disp">Disposal Tracking &amp; Realized Values</th>
</tr>
<tr>
    <th class="far-col-hdr" style="width: 10%;">Asset Description</th>
    <th class="far-col-hdr" style="width: 5%;">Purchase Date</th>
    <th class="far-col-hdr" style="width: 6.5%;">Asset Code</th>
    <th class="far-col-hdr" style="width: 5.5%;">Cost (Beg)</th>
    <th class="far-col-hdr" style="width: 4.5%;">Additions</th>
    <th class="far-col-hdr" style="width: 4.5%;">Disposals</th>
    <th class="far-col-hdr" style="width: 5.5%;">Cost (Ending)</th>
    <th class="far-col-hdr" style="width: 3.5%;">Dep Rate</th>
    <th class="far-col-hdr" style="width: 5.5%;">Dep (Curr)</th>
    <th class="far-col-hdr" style="width: 5.5%;">Dep (Beg)</th>
    <th class="far-col-hdr" style="width: 4.5%;">Dep on Disp</th>
    <th class="far-col-hdr" style="width: 6%;">Total Acc. Dep.</th>
    <th class="far-col-hdr" style="width: 6%;">Net Book Value</th>
    <th class="far-col-hdr" style="width: 4.5%;">Adj Cost</th>
    <th class="far-col-hdr" style="width: 4.5%;">Adj Acc Dep</th>
    <th class="far-col-hdr" style="width: 4.5%;">Adj NBV</th>
    <th class="far-col-hdr" style="width: 4%;">Disp Mo</th>
    <th class="far-col-hdr" style="width: 4.5%;">Disp Cost</th>
    <th class="far-col-hdr" style="width: 4.5%;">Disp Acc Dep</th>
    <th class="far-col-hdr" style="width: 5%;">Disp NBV</th>
</tr>
</thead>
<tbody>
"""

    for cat in categories:
        cat_name = cat["category_name"]
        cat_rows = cat["rows"]
        st = cat["subtotals"]

        html_out += f"""
<tr class="far-cat-hdr">
    <td colspan="20">{esc(cat_name.upper())}</td>
</tr>
"""
        for r in cat_rows:
            html_out += f"""
<tr>
    <td class="far-left">{esc(r["desc"])}</td>
    <td class="far-center">{esc(r["purchase_date"])}</td>
    <td class="far-center">{esc(r["code"])}</td>
    <td class="far-right">{fmt_currency(r["cost_beg"])}</td>
    <td class="far-right">{fmt_currency(r["add_yr"])}</td>
    <td class="far-right">{fmt_currency(r["dispos"])}</td>
    <td class="far-right">{fmt_currency(r["cost_end"])}</td>
    <td class="far-right">{f"{r['rate']*100:.1f}%"}</td>
    <td class="far-right">{fmt_currency(r["dep_curr"])}</td>
    <td class="far-right">{fmt_currency(r["dep_beg"])}</td>
    <td class="far-right">{fmt_currency(r["dep_disp"])}</td>
    <td class="far-right">{fmt_currency(r["total_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(r["nbv"])}</td>
    <td class="far-right">{fmt_currency(r["adj_cost"])}</td>
    <td class="far-right">{fmt_currency(r["adj_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(r["adj_nbv"])}</td>
    <td class="far-center">{esc(r["disp_month"])}</td>
    <td class="far-right">{fmt_currency(r["disp_cost"])}</td>
    <td class="far-right">{fmt_currency(r["disp_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(r["disp_nbv"])}</td>
</tr>
"""

        # Subtotal row
        html_out += f"""
<tr class="far-subtotal">
    <td colspan="3" class="far-left">Sub-total {esc(cat_name.upper())}</td>
    <td class="far-right">{fmt_currency(st["cost_beg"])}</td>
    <td class="far-right">{fmt_currency(st["additions"])}</td>
    <td class="far-right">{fmt_currency(st["disposals"])}</td>
    <td class="far-right">{fmt_currency(st["cost_end"])}</td>
    <td class="far-right">-</td>
    <td class="far-right">{fmt_currency(st["dep_curr"])}</td>
    <td class="far-right">{fmt_currency(st["dep_beg"])}</td>
    <td class="far-right">{fmt_currency(st["dep_disp"])}</td>
    <td class="far-right">{fmt_currency(st["total_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(st["nbv"])}</td>
    <td class="far-right">{fmt_currency(st["adj_cost"])}</td>
    <td class="far-right">{fmt_currency(st["adj_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(st["adj_nbv"])}</td>
    <td class="far-center">-</td>
    <td class="far-right">{fmt_currency(st["disp_cost"])}</td>
    <td class="far-right">{fmt_currency(st["disp_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(st["disp_nbv"])}</td>
</tr>
<tr class="far-cat-total">
    <td colspan="3" class="far-left">TOTAL - {esc(cat_name.upper())}</td>
    <td class="far-right">{fmt_currency(st["cost_beg"])}</td>
    <td class="far-right">{fmt_currency(st["additions"])}</td>
    <td class="far-right">{fmt_currency(st["disposals"])}</td>
    <td class="far-right">{fmt_currency(st["cost_end"])}</td>
    <td class="far-right">-</td>
    <td class="far-right">{fmt_currency(st["dep_curr"])}</td>
    <td class="far-right">{fmt_currency(st["dep_beg"])}</td>
    <td class="far-right">{fmt_currency(st["dep_disp"])}</td>
    <td class="far-right">{fmt_currency(st["total_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(st["nbv"])}</td>
    <td class="far-right">{fmt_currency(st["adj_cost"])}</td>
    <td class="far-right">{fmt_currency(st["adj_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(st["adj_nbv"])}</td>
    <td class="far-center">-</td>
    <td class="far-right">{fmt_currency(st["disp_cost"])}</td>
    <td class="far-right">{fmt_currency(st["disp_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(st["disp_nbv"])}</td>
</tr>
"""

    # Grand total row
    html_out += f"""
<tr class="far-grand-total">
    <td colspan="3" class="far-left">GRAND TOTAL</td>
    <td class="far-right">{fmt_currency(grand_totals["cost_beg"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["additions"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["disposals"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["cost_end"])}</td>
    <td class="far-right">-</td>
    <td class="far-right">{fmt_currency(grand_totals["dep_curr"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["dep_beg"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["dep_disp"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["total_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["nbv"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["adj_cost"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["adj_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["adj_nbv"])}</td>
    <td class="far-center">-</td>
    <td class="far-right">{fmt_currency(grand_totals["disp_cost"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["disp_acc_dep"])}</td>
    <td class="far-right">{fmt_currency(grand_totals["disp_nbv"])}</td>
</tr>
</tbody>
</table>
"""
    return html_out


@frappe.whitelist()
def download():
    """Download Schedule of Fixed Assets as Excel (.xlsx).

    Shows all assets and calculations until the selected to_date.
    """
    args = frappe.local.form_dict
    to_date = args.get("to_date")
    company = args.get("company")

    data = get_fixed_asset_register_data(company=company, to_date=to_date)
    company_name_upper = data["company_name"]
    subtitle_text = data["subtitle_text"]
    categories = data["categories"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SCHEDULE OF FIXED ASSETS"
    ws.views.sheetView[0].showGridLines = True

    # Styling definitions
    thin_side = Side(style="thin", color="A6A6A6")
    dark_thin_side = Side(style="thin", color="000000")
    double_side = Side(style="double", color="000000")

    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    cat_border = Border(left=thin_side, right=thin_side, top=dark_thin_side, bottom=dark_thin_side)
    grand_total_border = Border(left=thin_side, right=thin_side, top=dark_thin_side, bottom=double_side)

    font_company = Font(name="Calibri", size=15, bold=True)
    font_title = Font(name="Calibri", size=13, bold=True)
    font_subtitle = Font(name="Calibri", size=11, bold=True)
    font_group_header = Font(name="Calibri", size=10, bold=True)
    font_header = Font(name="Calibri", size=10, bold=True, color="000000")
    font_cat = Font(name="Calibri", size=11, bold=True, color="1F497D")
    font_regular = Font(name="Calibri", size=10)
    font_total = Font(name="Calibri", size=10, bold=True)
    font_grand_total = Font(name="Calibri", size=11, bold=True)

    fill_main_group = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    fill_adj_group = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    fill_disp_group = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    fill_table_header = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    fill_cat_header = PatternFill(start_color="F9F9F9", end_color="F9F9F9", fill_type="solid")

    headers = [
        ("A", "Asset Description", 30, "left"),
        ("B", "Purchase Date", 14, "center"),
        ("C", "Asset Code", 16, "center"),
        ("D", "Cost (Beginning)", 18, "right"),
        ("E", "Additions (Period)", 18, "right"),
        ("F", "Disposals (Period)", 18, "right"),
        ("G", "Cost (Ending)", 18, "right"),
        ("H", "Depreciation Rate", 16, "right"),
        ("I", "Depreciation (Current)", 20, "right"),
        ("J", "Depreciation (Beginning)", 22, "right"),
        ("K", "Depreciation on Disposal", 22, "right"),
        ("L", "Total Accumulated Depreciation", 26, "right"),
        ("M", "Net Book Value (Ending)", 22, "right"),
        ("N", "Adjusted Cost", 18, "right"),
        ("O", "Adjusted Acc. Depr.", 20, "right"),
        ("P", "Adjusted Net Book Value", 22, "right"),
        ("Q", "Disposal Month", 16, "center"),
        ("R", "Disposed Asset Cost", 20, "right"),
        ("S", "Disposed Acc. Depr.", 20, "right"),
        ("T", "Disposal Net Book Value", 22, "right"),
    ]
    total_cols = len(headers)

    # 1. Company Name (Row 1)
    ws.append([company_name_upper])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
    cell_c = ws.cell(row=1, column=1)
    cell_c.font = font_company
    cell_c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    # 2. Schedule Title (Row 2)
    ws.append(["SCHEDULE OF FIXED ASSETS"])
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_cols)
    cell_t = ws.cell(row=2, column=1)
    cell_t.font = font_title
    cell_t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 24

    # 3. Subtitle / Period (Row 3)
    ws.append([subtitle_text])
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=total_cols)
    cell_s = ws.cell(row=3, column=1)
    cell_s.font = font_subtitle
    cell_s.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 20

    # 4. Group Category Header (Row 4)
    ws.append([""] * total_cols)

    # Main Schedule Group (Cols A - M)
    ws.merge_cells("A4:M4")
    cell_g1 = ws.cell(row=4, column=1, value="Core Asset Cost & Depreciation Schedule")
    cell_g1.font = font_group_header
    cell_g1.alignment = Alignment(horizontal="center", vertical="center")
    for c in range(1, 14):
        ws.cell(row=4, column=c).fill = fill_main_group
        ws.cell(row=4, column=c).border = thin_border

    # Adjustments Group (Cols N - P)
    ws.merge_cells("N4:P4")
    cell_g2 = ws.cell(row=4, column=14, value="Asset Value Adjustments / Revaluations")
    cell_g2.font = font_group_header
    cell_g2.alignment = Alignment(horizontal="center", vertical="center")
    for c in range(14, 17):
        ws.cell(row=4, column=c).fill = fill_adj_group
        ws.cell(row=4, column=c).border = thin_border

    # Disposal Group (Cols Q - T)
    ws.merge_cells("Q4:T4")
    cell_g3 = ws.cell(row=4, column=17, value="Disposal Tracking & Realized Values")
    cell_g3.font = font_group_header
    cell_g3.alignment = Alignment(horizontal="center", vertical="center")
    for c in range(17, 21):
        ws.cell(row=4, column=c).fill = fill_disp_group
        ws.cell(row=4, column=c).border = thin_border

    ws.row_dimensions[4].height = 22

    # 5. Column Headers (Row 5)
    header_row = 5
    for col_idx, (col_letter, label, width, _) in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=label)
        cell.font = font_header
        cell.fill = fill_table_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        ws.column_dimensions[col_letter].width = width
    ws.row_dimensions[header_row].height = 30

    current_row = 6
    category_total_rows = []
    numeric_cols = ["D", "E", "F", "G", "I", "J", "K", "L", "M", "N", "O", "P", "R", "S", "T"]

    for cat in categories:
        cat_name = cat["category_name"]
        cat_rows = cat["rows"]

        # Category Heading Row
        ws.cell(row=current_row, column=1, value=cat_name.upper()).font = font_cat
        ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[current_row].height = 22
        current_row += 1

        cat_start_row = current_row

        for r in cat_rows:
            ws[f"A{current_row}"] = r["desc"]
            ws[f"B{current_row}"] = r["purchase_date"]
            ws[f"C{current_row}"] = r["code"]
            ws[f"D{current_row}"] = r["cost_beg"]
            ws[f"E{current_row}"] = r["add_yr"]
            ws[f"F{current_row}"] = r["dispos"]
            ws[f"G{current_row}"] = f"=D{current_row}+IFERROR(E{current_row},0)-IFERROR(F{current_row},0)"
            ws[f"H{current_row}"] = r["rate"]
            ws[f"I{current_row}"] = r["dep_curr"]
            ws[f"J{current_row}"] = r["dep_beg"]
            ws[f"K{current_row}"] = r["dep_disp"]
            ws[f"L{current_row}"] = f"=J{current_row}+I{current_row}-IFERROR(K{current_row},0)"
            ws[f"M{current_row}"] = f"=G{current_row}-L{current_row}"

            ws[f"N{current_row}"] = r["adj_cost"]
            ws[f"O{current_row}"] = r["adj_acc_dep"]
            ws[f"P{current_row}"] = f"=IFERROR(N{current_row},0)-IFERROR(O{current_row},0)" if r["adj_cost"] is not None else None

            ws[f"Q{current_row}"] = r["disp_month"]
            ws[f"R{current_row}"] = r["disp_cost"]
            ws[f"S{current_row}"] = r["disp_acc_dep"]
            ws[f"T{current_row}"] = f"=IFERROR(R{current_row},0)-IFERROR(S{current_row},0)" if r["disp_cost"] is not None else None

            for col_idx, (_, _, _, align) in enumerate(headers, start=1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.font = font_regular
                cell.border = thin_border
                cell.alignment = Alignment(horizontal=align, vertical="center")

            ws[f"C{current_row}"].number_format = "@"
            ws[f"H{current_row}"].number_format = "0.00"

            for col_letter in numeric_cols:
                ws[f"{col_letter}{current_row}"].number_format = "#,##0.00"

            ws.row_dimensions[current_row].height = 20
            current_row += 1

        cat_end_row = current_row - 1

        # Category Subtotal Row
        ws.cell(row=current_row, column=1, value=f"Sub-total {cat_name.upper()}").font = font_total
        ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="left", vertical="center")
        for col_letter in numeric_cols:
            ws[f"{col_letter}{current_row}"] = f"=SUM({col_letter}{cat_start_row}:{col_letter}{cat_end_row})"
            ws[f"{col_letter}{current_row}"].font = font_total
            ws[f"{col_letter}{current_row}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"{col_letter}{current_row}"].number_format = "#,##0.00"

        for col_idx in range(1, total_cols + 1):
            ws.cell(row=current_row, column=col_idx).border = thin_border
        ws.row_dimensions[current_row].height = 20
        current_row += 1

        # Category Total Row
        cat_tot_row = current_row
        category_total_rows.append(cat_tot_row)

        ws.cell(row=cat_tot_row, column=1, value=f"TOTAL - {cat_name.upper()}").font = font_cat
        ws.cell(row=cat_tot_row, column=1).alignment = Alignment(horizontal="left", vertical="center")

        for col_letter in numeric_cols:
            ws[f"{col_letter}{cat_tot_row}"] = f"={col_letter}{cat_tot_row-1}"
            ws[f"{col_letter}{cat_tot_row}"].font = font_cat
            ws[f"{col_letter}{cat_tot_row}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"{col_letter}{cat_tot_row}"].number_format = "#,##0.00"

        for col_idx in range(1, total_cols + 1):
            cell = ws.cell(row=cat_tot_row, column=col_idx)
            cell.border = cat_border
            cell.fill = fill_cat_header

        ws.row_dimensions[cat_tot_row].height = 22
        current_row += 1

        # Spacer row between categories
        ws.append([""] * total_cols)
        current_row += 1

    # Grand Total Row
    grand_row = current_row
    ws.cell(row=grand_row, column=1, value="GRAND TOTAL").font = font_grand_total
    ws.cell(row=grand_row, column=1).alignment = Alignment(horizontal="left", vertical="center")

    if category_total_rows:
        for col_letter in numeric_cols:
            formula = "=" + "+".join([f"{col_letter}{r}" for r in category_total_rows])
            ws[f"{col_letter}{grand_row}"] = formula
            ws[f"{col_letter}{grand_row}"].font = font_grand_total
            ws[f"{col_letter}{grand_row}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"{col_letter}{grand_row}"].number_format = "#,##0.00"

    for col_idx in range(1, total_cols + 1):
        cell = ws.cell(row=grand_row, column=col_idx)
        cell.border = grand_total_border
        cell.fill = fill_cat_header

    ws.row_dimensions[grand_row].height = 24

    file_data = BytesIO()
    wb.save(file_data)
    file_data.seek(0)

    frappe.local.response.filename = "Schedule of Fixed Assets.xlsx"
    frappe.local.response.filecontent = file_data.getvalue()
    frappe.local.response.type = "download"
