# Copyright (c) 2026, JGB and contributors
# Accounts Receivable Aging Report - Page backend
# Supports the filter matrix defined in the Excel model:
#   1. Report View Type (Summary / Detailed)
#   2. Primary Grouping (Customer / Salesperson / Division / Region)
#   3. Entity Selection Filter (All / Multi-Select)
#   4. As-of Date (Cut-off)
#   5. Aging Method / Basis (Due Date / Invoice Date)
#   6. Unapplied Payments & Credits (Show as Separate Line)
#   7. Output / Export Format (Excel / PDF)

import frappe
import json
from frappe.utils import date_diff, getdate, today, flt, format_date
from datetime import datetime
from six import BytesIO

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

from jgb.jgb.doctype.accounts_report_dashboard.report_styles import (
    header_fill, header_font, title_font, company_font, date_font,
    subtotal_font, subtotal_fill, cust_subtotal_font, cust_subtotal_fill,
    grand_total_font, grand_total_fill, salesperson_font, salesperson_fill,
    data_font, alt_row_fill, border_thin, align_center, align_right, align_left,
    currency_format, apply_title_rows, apply_header_row, setup_page,
)

AGING_BUCKETS = [
    ("0-30", 0, 30),
    ("31-60", 31, 60),
    ("61-90", 61, 90),
    ("Above 90", 91, 99999),
]

GROUP_LABELS = {
    "Customer Wise": "customer",
    "Salesperson Wise": "salesperson",
    "Division Wise": "division",
    "Region Wise": "region",
}


@frappe.whitelist()
def debug_invoices(company=None, as_of_date=None):
    """Debug helper to inspect raw invoice data."""
    if not company:
        company = "JGB International Limited Company"
    as_of = getdate(as_of_date) if as_of_date else getdate(today())
    rows = frappe.db.sql("""
        SELECT name, posting_date, due_date, customer, base_grand_total, is_return
        FROM `tabSales Invoice`
        WHERE company=%s AND docstatus=1 AND posting_date <= %s
        ORDER BY posting_date
        LIMIT 10
    """, (company, as_of), as_dict=True)
    companies = frappe.db.sql("""
        SELECT company, COUNT(*) as cnt FROM `tabSales Invoice`
        WHERE docstatus=1 GROUP BY company
    """, as_dict=True)
    return {"count": len(rows), "as_of": str(as_of), "sample": rows, "by_company": companies}


@frappe.whitelist()
def get_entity_options(company=None, grouping="Customer Wise", search=""):
    """Return available entity values for the Multi-Select filter based on grouping."""
    if not company:
        return []
    group_key = GROUP_LABELS.get(grouping, "customer")
    search = (search or "").strip()

    if group_key == "customer":
        rows = frappe.db.sql("""
            SELECT DISTINCT customer FROM `tabSales Invoice`
            WHERE company=%s AND docstatus=1
        """, company)
        vals = [r[0] for r in rows if r[0]]
        names = {}
        if vals:
            for c in frappe.db.get_all("Customer", filters={"name": ["in", vals]},
                                       fields=["name", "customer_name"]):
                names[c["name"]] = c["customer_name"]
        result = [{"value": v, "label": "{0} : {1}".format(v, names.get(v, v))}
                  for v in sorted(vals)]
    elif group_key == "salesperson":
        rows = frappe.db.sql("""
            SELECT DISTINCT custom_sales_personuser FROM `tabSales Invoice`
            WHERE company=%s AND docstatus=1 AND custom_sales_personuser IS NOT NULL
        """, company)
        result = [{"value": r[0], "label": r[0]} for r in rows if r[0]]
        result = sorted(result, key=lambda x: x["value"])
    elif group_key == "division":
        rows = frappe.db.sql("""
            SELECT DISTINCT custom_division FROM `tabSales Invoice`
            WHERE company=%s AND docstatus=1 AND custom_division IS NOT NULL
        """, company)
        result = [{"value": r[0], "label": r[0]} for r in rows if r[0]]
        result = sorted(result, key=lambda x: x["value"])
    elif group_key == "region":
        rows = frappe.db.sql("""
            SELECT DISTINCT sp.custom_territory
            FROM `tabSales Invoice` si
            LEFT JOIN `tabSales Person` sp ON sp.name = si.custom_sales_personuser
            WHERE si.company=%s AND si.docstatus=1 AND sp.custom_territory IS NOT NULL
        """, company)
        result = [{"value": r[0], "label": r[0]} for r in rows if r[0]]
        result = sorted(result, key=lambda x: x["value"])
    else:
        result = []

    if search:
        s = search.lower()
        result = [v for v in result if s in (v.get("label", "") + " " + v.get("value", "")).lower()]
    return result


@frappe.whitelist()
def get_report_data(
    company=None,
    view_type="Summary",
    grouping="Customer Wise",
    entities=None,
    as_of_date=None,
    aging_method="Due Date",
    show_unapplied=0,
    include_asi=0,
):
    """Return report rows + columns for the page table (JSON)."""
    if not company:
        frappe.throw("Kindly choose the company.")

    as_of = getdate(as_of_date) if as_of_date else getdate(today())
    entity_list = _parse_entities(entities)
    group_key = GROUP_LABELS.get(grouping, "customer")

    invoices = _get_open_invoices(company, as_of, group_key, entity_list, include_asi)
    rows = _build_rows(invoices, group_key, view_type, aging_method, as_of,
                       show_unapplied, company, entity_list)

    columns = _get_columns(view_type, group_key)

    currency = frappe.db.get_value("Company", company, "default_currency") or "SAR"

    return {
        "columns": columns,
        "rows": rows,
        "company": company,
        "currency": currency,
        "as_of_date": format_date(as_of),
        "report_date": datetime.now().strftime("%d-%m-%Y"),
    }


@frappe.whitelist()
def download_excel(
    company=None,
    view_type="Summary",
    grouping="Customer Wise",
    entities=None,
    as_of_date=None,
    aging_method="Due Date",
    show_unapplied=0,
    include_asi=0,
):
    """Build and send the Excel (.xlsx) export."""
    if not company:
        frappe.throw("Kindly choose the company.")

    result = get_report_data(
        company=company, view_type=view_type, grouping=grouping,
        entities=entities, as_of_date=as_of_date, aging_method=aging_method,
        show_unapplied=show_unapplied, include_asi=include_asi,
    )

    wb = openpyxl.Workbook()
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])
    ws = wb.create_sheet("AR Aging Report", 0)

    columns = result["columns"]
    rows = result["rows"]
    num_cols = len(columns)

    # Title rows
    ws.append([result["company"]])
    ws.append(["Accounts Receivable Aging Report"])
    ws.append(["Report Date: " + result["report_date"]])
    ws.append(["As-of Date: " + result["as_of_date"] + "   |   Currency: " + result["currency"]])

    # Header row (row 5)
    header_labels = [c["label"] for c in columns]
    ws.append(header_labels)

    # Data rows
    for row in rows:
        ws.append([_cell_for_excel(c, columns) for c in row])

    # Column widths
    widths = _column_widths(columns)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Styling
    apply_title_rows(ws, num_cols, "Accounts Receivable Aging Report",
                     company=result["company"], report_date=result["report_date"])
    # Row 4 (as-of / currency) styling
    for cell in ws[4]:
        cell.font = date_font
        cell.alignment = align_center
    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=num_cols)
    ws.row_dimensions[4].height = 20

    header_row_idx = 5
    apply_header_row(ws, header_row_idx, num_cols)

    data_start = 6
    data_end = data_start + len(rows) - 1
    text_cols = _text_col_count(columns)
    alt = False
    for row in ws.iter_rows(min_row=data_start, max_row=data_end, min_col=1, max_col=num_cols):
        label = str(row[0].value or "")
        is_group = label.startswith("GROUP:")
        is_cust_sub = label.startswith("Customer Subtotal:")
        is_subtotal = label.startswith("Subtotal:")
        is_unapplied = label.startswith("Unapplied")
        is_net = label.startswith("NET RECEIVABLES")
        is_grand = label == "GRAND TOTAL"

        for i, cell in enumerate(row):
            cell.border = border_thin
            if is_group:
                cell.font = salesperson_font
                cell.fill = salesperson_fill
                cell.alignment = align_center
            elif is_grand or is_net:
                cell.font = grand_total_font
                cell.fill = grand_total_fill
                cell.alignment = align_left if i < text_cols else align_right
                if i >= text_cols:
                    cell.number_format = currency_format
            elif is_subtotal:
                cell.font = subtotal_font
                cell.fill = subtotal_fill
                cell.alignment = align_left if i < text_cols else align_right
                if i >= text_cols:
                    cell.number_format = currency_format
            elif is_cust_sub or is_unapplied:
                cell.font = cust_subtotal_font
                cell.fill = cust_subtotal_fill
                cell.alignment = align_left if i < text_cols else align_right
                if i >= text_cols:
                    cell.number_format = currency_format
            else:
                cell.font = data_font
                cell.alignment = align_left if i < text_cols else align_right
                if i >= text_cols:
                    cell.number_format = currency_format
                if alt:
                    cell.fill = alt_row_fill

        if is_group:
            ws.merge_cells(start_row=row[0].row, start_column=1,
                           end_row=row[0].row, end_column=num_cols)
            alt = False
        elif is_subtotal or is_cust_sub or is_grand or is_net or is_unapplied:
            ws.merge_cells(start_row=row[0].row, start_column=1,
                           end_row=row[0].row, end_column=text_cols)
            alt = False
        else:
            alt = not alt

    setup_page(ws, orientation="landscape")

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    frappe.response["filename"] = "Accounts Receivable Aging Report.xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_entities(entities):
    if not entities:
        return []
    if isinstance(entities, (list, tuple)):
        return [e for e in entities if e]
    if isinstance(entities, str):
        try:
            parsed = json.loads(entities)
            if isinstance(parsed, list):
                return [e for e in parsed if e]
        except (ValueError, TypeError):
            pass
        return [e.strip() for e in entities.split(",") if e.strip()]
    return []


def _get_columns(view_type, group_key):
    """Return column definitions for the report table."""
    # Summary view always uses a single text column followed by the amount columns.
    if view_type == "Summary":
        cols = [
            {"label": "Customer", "fieldname": "customer", "type": "text"},
            {"label": "Invoiced Amount", "fieldname": "invoiced", "type": "currency"},
            {"label": "Paid Amount", "fieldname": "paid", "type": "currency"},
            {"label": "Credit Note", "fieldname": "credit_note", "type": "currency"},
            {"label": "Outstanding Amount", "fieldname": "outstanding", "type": "currency"},
            {"label": "Age (Days)", "fieldname": "age", "type": "int"},
        ]
        for label, *_ in AGING_BUCKETS:
            cols.append({"label": label, "fieldname": label.lower().replace(" ", "_"),
                         "type": "currency"})
        return cols

    cols = [
        {"label": "Posting Date", "fieldname": "posting_date", "type": "text"},
        {"label": "Voucher No", "fieldname": "voucher_no", "type": "text"},
        {"label": "Customer", "fieldname": "customer", "type": "text"},
        {"label": "Sales Engineer", "fieldname": "sales_person", "type": "text"},
    ]
    cols += [
        {"label": "Invoiced Amount", "fieldname": "invoiced", "type": "currency"},
        {"label": "Paid Amount", "fieldname": "paid", "type": "currency"},
        {"label": "Credit Note", "fieldname": "credit_note", "type": "currency"},
        {"label": "Outstanding Amount", "fieldname": "outstanding", "type": "currency"},
        {"label": "Age (Days)", "fieldname": "age", "type": "int"},
    ]
    for label, *_ in AGING_BUCKETS:
        cols.append({"label": label, "fieldname": label.lower().replace(" ", "_"),
                     "type": "currency"})
    return cols


def _text_col_count(columns):
    """Number of leading text columns (left-aligned)."""
    count = 0
    for c in columns:
        if c["type"] in ("text", "int"):
            count += 1
        else:
            break
    return count


def _column_widths(columns):
    widths = []
    for c in columns:
        label = c["label"]
        if "Posting" in label:
            widths.append(13)
        elif "Voucher" in label:
            widths.append(18)
        elif "Customer" in label:
            widths.append(35)
        elif "Sales" in label:
            widths.append(20)
        elif "Age" in label:
            widths.append(10)
        else:
            widths.append(14)
    return widths


def _cell_for_excel(value, columns):
    """Ensure numeric values are floats for Excel."""
    if value is None or value == "":
        return ""
    if isinstance(value, (int, float)):
        return value
    # try to convert numeric strings
    try:
        f = float(value)
        return f
    except (ValueError, TypeError):
        return value


def _get_open_invoices(company, as_of, group_key, entity_list, include_asi=0):
    """Fetch all open (non-zero outstanding) Sales Invoices
    posted on or before the as-of date, enriched with grouping attributes.
    Return invoices / credit notes are handled through the parent invoice
    (linked via return_against/custom_return_reason) or the unapplied section.
    When include_asi is set, open Advance Sales Invoice documents are appended
    as invoice-like rows (each ASI books a receivable on 1101 at submit)."""
    si_rows = frappe.db.sql("""
        SELECT si.name, si.posting_date, si.due_date, si.customer,
               si.custom_sales_personuser AS sales_person,
               si.custom_division AS division,
               si.po_no, si.base_grand_total, si.outstanding_amount,
               si.is_return, si.return_against, si.custom_return_reason
        FROM `tabSales Invoice` si
        WHERE si.company = %s
          AND si.docstatus = 1
          AND si.is_return = 0
          AND si.posting_date <= %s
        ORDER BY si.posting_date
    """, (company, as_of), as_dict=True)

    # Pre-fetch customer names and territories
    customers = list({r["customer"] for r in si_rows if r.get("customer")})
    cust_names = {}
    cust_territory = {}
    if customers:
        for c in frappe.db.get_all("Customer",
                                   filters={"name": ["in", customers]},
                                   fields=["name", "customer_name", "territory"]):
            cust_names[c["name"]] = c["customer_name"]
            cust_territory[c["name"]] = c.get("territory") or ""

    # Pre-fetch sales person territories
    sps = list({r["sales_person"] for r in si_rows if r.get("sales_person")})
    sp_territory = {}
    if sps:
        for s in frappe.db.get_all("Sales Person",
                                   filters={"name": ["in", sps]},
                                   fields=["name", "custom_territory"]):
            sp_territory[s["name"]] = s.get("custom_territory") or ""

    enriched = []
    for r in si_rows:
        cust = r["customer"]
        r["customer_name"] = cust_names.get(cust, cust)
        # Determine region: prefer sales person territory, fall back to customer territory
        region = sp_territory.get(r.get("sales_person")) or cust_territory.get(cust) or ""
        r["region"] = region
        r["group_value"] = _group_value(r, group_key)
        enriched.append(r)

    if int(include_asi):
        enriched.extend(_get_open_asi_rows(company, as_of, group_key))

    # Filter by entity selection
    if entity_list:
        enriched = [r for r in enriched if r["group_value"] in entity_list]

    # Calculate outstanding for each invoice
    for r in enriched:
        if r.get("is_asi"):
            continue
        r["outstanding"] = _calc_outstanding(r, company, as_of)
        r["paid_amount"] = _calc_paid(r, company, as_of)
        r["credit_note_amt"] = _calc_credit_note(r, company, as_of)

    # Keep only open items. When ERPNext has already closed the invoice
    # (outstanding_amount = 0 — fully paid/returned/reconciled) and no linked
    # credit note still holds unconsumed credit, a negative or sub-riyal
    # recomputed remainder is model noise: rounding crumbs, or credit that
    # was actually consumed against other invoices (e.g. via a JV).
    enriched = [
        r for r in enriched
        if abs(r["outstanding"]) > 0.01
        and (r.get("is_asi") or not _is_settled_cluster(r, company, as_of))
    ]
    return enriched


def _get_open_asi_rows(company, as_of, group_key):
    """Open Advance Sales Invoice documents as invoice-like rows.

    On submit an ASI posts Dr 1101 (AR) gross / Cr 2202 advance / Cr 2401 VAT,
    so each ASI is a real receivable this report cannot otherwise see. When the
    ASI is allocated on a submitted Sales Invoice, the ASI VAT reversal JV
    credits 1101 by the allocated amount (non-historical ASIs only), so:

        open AR = net receivable GL on the ASI voucher - allocated amount

    Historical imports (custom_is_historical_import) posted no 1101 GL and
    their reversal JV never credits 1101, so the GL net is the truth for them.
    Return ASIs (is_return) credit 1101; ones linked via return_against fold
    into the parent's credit-note column, unlinked ones stand alone.
    """
    asis = frappe.db.sql("""
        SELECT name, posting_date, due_date, party, party_name, sales_order,
               grand_total, is_return, return_against, custom_is_historical_import
        FROM `tabAdvance Sales Invoice`
        WHERE company = %s AND docstatus = 1
          AND party_type = 'Customer' AND payment_type = 'Receive'
          AND posting_date <= %s
        ORDER BY posting_date, name
    """, (company, as_of), as_dict=True)
    if not asis:
        return []

    names = [a["name"] for a in asis]

    # Net receivable booked by each ASI voucher on 1101-style accounts
    ar_net = {r["voucher_no"]: flt(r["amt"]) for r in frappe.db.sql("""
        SELECT gle.voucher_no, SUM(gle.debit - gle.credit) AS amt
        FROM `tabGL Entry` gle
        JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.company = %(company)s AND gle.voucher_type = 'Advance Sales Invoice'
          AND gle.voucher_no IN %(names)s AND gle.posting_date <= %(as_of)s
          AND gle.is_cancelled = 0 AND acc.account_type = 'Receivable'
          AND acc.root_type = 'Asset'
        GROUP BY gle.voucher_no
    """, {"company": company, "names": names, "as_of": as_of}, as_dict=True)}

    # Amount of each ASI consumed by submitted Sales Invoices on/before as_of —
    # equals the reversal JV's 1101 credit for non-historical ASIs
    allocated = {r["asi_name"]: flt(r["amt"]) for r in frappe.db.sql("""
        SELECT at.reference_name AS asi_name,
               SUM(COALESCE(at.custom_allocated_amount, at.advance_amount)) AS amt
        FROM `tabadvance sales invoice table` at
        JOIN `tabSales Invoice` si ON si.name = at.parent
        WHERE at.parenttype = 'Sales Invoice' AND si.docstatus = 1
          AND at.reference_name IN %(names)s AND si.posting_date <= %(as_of)s
        GROUP BY at.reference_name
    """, {"names": names, "as_of": as_of}, as_dict=True)}

    # Grouping attributes resolved through the linked Sales Order
    so_names = list({a["sales_order"] for a in asis if a.get("sales_order")})
    so_map = {}
    if so_names:
        for so in frappe.db.get_all(
            "Sales Order", filters={"name": ["in", so_names]},
            fields=["name", "custom_sales_personuser", "custom_sales_person",
                    "custom_division"],
        ):
            so_map[so["name"]] = so

    parties = list({a["party"] for a in asis if a.get("party")})
    cust_names = {}
    cust_territory = {}
    if parties:
        for c in frappe.db.get_all(
            "Customer", filters={"name": ["in", parties]},
            fields=["name", "customer_name", "territory"],
        ):
            cust_names[c["name"]] = c["customer_name"]
            cust_territory[c["name"]] = c.get("territory") or ""

    sps = list({(so_map.get(a.get("sales_order")) or {}).get("custom_sales_personuser")
                for a in asis})
    sps = [s for s in sps if s]
    sp_territory = {}
    if sps:
        for s in frappe.db.get_all(
            "Sales Person", filters={"name": ["in", sps]},
            fields=["name", "custom_territory"],
        ):
            sp_territory[s["name"]] = s.get("custom_territory") or ""

    # Linked return ASIs fold into their parent's credit-note column
    returns_by_parent = {}
    for a in asis:
        if int(a.get("is_return") or 0) and a.get("return_against") in ar_net:
            returns_by_parent[a["return_against"]] = (
                returns_by_parent.get(a["return_against"], 0.0)
                + flt(ar_net[a["name"]])
            )

    rows = []
    for a in asis:
        ar_amt = flt(ar_net.get(a["name"]))
        if abs(ar_amt) <= 0.01:
            continue  # no receivable posted (e.g. historical imports)

        so = so_map.get(a.get("sales_order") or "") or {}
        sp_link = so.get("custom_sales_personuser") or ""
        is_return = int(a.get("is_return") or 0)
        is_historical = int(a.get("custom_is_historical_import") or 0)
        folded = is_return and a.get("return_against") in ar_net

        paid = 0.0
        credit = 0.0
        if not is_return:
            # reversal JV credits 1101 only for non-historical ASIs
            paid = 0.0 if is_historical else flt(allocated.get(a["name"]))
            credit = flt(returns_by_parent.get(a["name"]))  # negative
        elif folded:
            continue  # folded into the parent row above

        outstanding = ar_amt - paid + credit
        row = {
            "name": a["name"],
            "posting_date": a["posting_date"],
            "due_date": a.get("due_date") or a["posting_date"],
            "customer": a["party"],
            "customer_name": a.get("party_name") or cust_names.get(a["party"], a["party"]),
            "sales_person": sp_link or so.get("custom_sales_person") or "",
            "division": so.get("custom_division") or "",
            "region": sp_territory.get(sp_link) or cust_territory.get(a["party"]) or "",
            "po_no": a.get("sales_order") or "",
            "base_grand_total": ar_amt,
            "outstanding_amount": outstanding,
            "is_return": is_return,
            "is_asi": 1,
            "paid_amount": paid,
            "credit_note_amt": credit,
            "outstanding": outstanding,
        }
        row["group_value"] = _group_value(row, group_key)
        rows.append(row)

    return rows


def _is_settled_cluster(row, company, as_of):
    """True when the invoice and its linked credit notes are all settled."""
    if flt(row["outstanding_amount"]) != 0:
        return False
    if row["outstanding"] >= 1:
        return False
    return not _has_open_linked_credit_note(row, company, as_of)


def _has_open_linked_credit_note(row, company, as_of):
    """True if a credit note linked to this invoice still has unconsumed
    credit as of the as-of date (evaluated the same way standalone credit
    notes are handled in _get_unapplied)."""
    cns = frappe.db.sql("""
        SELECT name, base_grand_total, is_return
        FROM `tabSales Invoice`
        WHERE company = %s AND docstatus = 1 AND is_return = 1
          AND posting_date <= %s
          AND (
              return_against = %s
              OR (custom_return_reason = %s AND (return_against IS NULL OR return_against = ''))
          )
    """, (company, as_of, row["name"], row["name"]), as_dict=True)
    for cn in cns:
        open_credit = (cn["base_grand_total"] or 0) - _calc_paid(cn, company, as_of)
        if open_credit < -0.01:
            return True
    return False


def _group_value(row, group_key):
    if group_key == "customer":
        return row.get("customer") or ""
    if group_key == "salesperson":
        return row.get("sales_person") or "Unassigned"
    if group_key == "division":
        return row.get("division") or "Unassigned"
    if group_key == "region":
        return row.get("region") or "Unassigned"
    return row.get("customer") or ""


def _calc_outstanding(row, company, as_of):
    base = row["base_grand_total"] or 0
    if row.get("is_return"):
        # If the return is linked to a parent invoice, its credit is already
        # applied to that invoice; do not show it as a separate open item.
        if row.get("return_against"):
            return 0
        if row.get("custom_return_reason"):
            parent_is_return = frappe.db.get_value("Sales Invoice",
                                                    row["custom_return_reason"],
                                                    "is_return")
            if parent_is_return is not None and not parent_is_return:
                return 0
        paid = _calc_paid(row, company, as_of)
        # credit note: outstanding is negative base minus payments allocated to it
        return base - paid
    paid = _calc_paid(row, company, as_of)
    cn = _calc_credit_note(row, company, as_of)
    if paid and cn:
        return base - paid + cn
    if paid:
        return base - paid
    if cn:
        return base + cn
    return base


def _calc_paid(row, company, as_of):
    """Sum of payments allocated to this invoice on or before as_of_date."""
    inv = row["name"]
    pe = frappe.db.sql("""
        SELECT SUM(per.allocated_amount * COALESCE(per.exchange_rate, 1)) AS amt
        FROM `tabPayment Entry Reference` per
        LEFT JOIN `tabPayment Entry` pe ON per.parent = pe.name
        WHERE pe.company = %s AND per.reference_name = %s AND pe.docstatus = 1
          AND pe.posting_date <= %s
    """, (company, inv, as_of))[0][0] or 0

    je = frappe.db.sql("""
        SELECT SUM(jva.credit - jva.debit) AS amt
        FROM `tabJournal Entry Account` jva
        LEFT JOIN `tabJournal Entry` jv ON jva.parent = jv.name
        WHERE jv.docstatus = 1
          AND jva.reference_type = 'Sales Invoice'
          AND jva.reference_name = %s
          AND jv.posting_date <= %s
          AND NOT EXISTS (
              SELECT 1 FROM `tabJournal Entry Account` jva2
              LEFT JOIN `tabSales Invoice` si ON jva2.reference_name = si.name
              WHERE jva2.parent = jv.name
                AND jva2.reference_type = 'Sales Invoice'
                AND si.is_return = 1
                AND si.return_against = %s
          )
    """, (inv, as_of, inv))[0][0] or 0

    return flt(pe + je)


def _calc_credit_note(row, company, as_of):
    """Sum of credit notes linked to this invoice (non-return invoices only)."""
    if row.get("is_return"):
        return 0
    inv = row["name"]
    res = frappe.db.sql("""
        SELECT SUM(base_grand_total) AS total
        FROM `tabSales Invoice`
        WHERE company = %s AND docstatus = 1 AND is_return = 1
          AND posting_date <= %s
          AND (
              return_against = %s
              OR (custom_return_reason = %s AND (return_against IS NULL OR return_against = ''))
          )
    """, (company, as_of, inv, inv))[0][0]
    return flt(res) if res else 0


def _calc_age(row, aging_method, as_of):
    ref_date = row.get("due_date") if aging_method == "Due Date" else row.get("posting_date")
    if not ref_date:
        ref_date = row.get("posting_date")
    if not ref_date:
        return 0
    return date_diff(as_of, ref_date)


def _bucket_amount(outstanding, age):
    for label, lo, hi in AGING_BUCKETS:
        if lo <= age <= hi:
            return outstanding
    return 0


def _build_rows(invoices, group_key, view_type, aging_method, as_of,
                show_unapplied, company, entity_list=None):
    """Build the final row list with group headers, detail/subtotal rows, grand total."""
    rows = []
    # Sort by group then posting date
    invoices = sorted(invoices, key=lambda x: (x.get("group_value") or "", x.get("posting_date")))

    grand = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
             "buckets": [0] * len(AGING_BUCKETS)}

    # Pre-load unapplied advances/credits and split by customer.
    # In Summary view these are netted into the single row per group.
    unapplied = _get_unapplied(company, as_of, entity_list, group_key) if show_unapplied else []
    unapplied_by_customer = _unapplied_by_customer(unapplied) if unapplied else {}

    # Group invoices
    groups = {}
    group_order = []
    for inv in invoices:
        gv = inv.get("group_value") or ""
        if gv not in groups:
            groups[gv] = []
            group_order.append(gv)
        groups[gv].append(inv)

    # For Customer Wise view, also include customers that only have
    # unapplied advances/credits and no open invoices.
    if group_key == "customer" and show_unapplied:
        for cust in unapplied_by_customer:
            if cust not in groups:
                groups[cust] = []
                group_order.append(cust)

    if view_type == "Summary":
        # Summary view: one text column + amount columns.
        for gv in group_order:
            items = groups[gv]
            group_label = _group_label(gv, group_key)

            if group_key != "customer":
                rows.append(_summary_group_header_row(group_label))

            g = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
                 "buckets": [0] * len(AGING_BUCKETS)}

            # Advance Sales Invoices stay out of the summary row and are
            # emitted as separate lines under each customer.
            inv_items = [i for i in items if not i.get("is_asi")]
            asi_items = [i for i in items if i.get("is_asi")]

            if group_key == "customer":
                net = _calc_group_summary(gv, inv_items, unapplied_by_customer, group_key,
                                          aging_method, as_of)
                if net:
                    rows.append(_summary_row(gv, group_key, net))
                    _accumulate(g, net)
                elif asi_items:
                    # Customer with only ASIs still needs a name row
                    rows.append(_summary_row(gv, group_key, {
                        "invoiced": 0, "paid": 0, "credit_note": 0,
                        "outstanding": 0, "buckets": [0] * len(AGING_BUCKETS)}))
                _emit_asi_lines(rows, g, asi_items, aging_method, as_of)
            else:
                # Group per customer inside salesperson/division/region.
                by_cust = {}
                cust_order = []
                for inv in items:
                    c = inv.get("customer") or ""
                    if c not in by_cust:
                        by_cust[c] = []
                        cust_order.append(c)
                    by_cust[c].append(inv)

                for c in cust_order:
                    citems = [i for i in by_cust[c] if not i.get("is_asi")]
                    cust_asis = [i for i in by_cust[c] if i.get("is_asi")]
                    net = _calc_group_summary(c, citems, unapplied_by_customer, "customer",
                                              aging_method, as_of)
                    if net:
                        rows.append(_summary_row(c, "customer", net))
                        _accumulate(g, net)
                    elif cust_asis:
                        rows.append(_summary_row(c, "customer", {
                            "invoiced": 0, "paid": 0, "credit_note": 0,
                            "outstanding": 0, "buckets": [0] * len(AGING_BUCKETS)}))
                    _emit_asi_lines(rows, g, cust_asis, aging_method, as_of)

            if group_key != "customer":
                rows.append(_summary_subtotal_row("Subtotal: " + group_label, g))

            for k in grand:
                if k == "buckets":
                    for i in range(len(AGING_BUCKETS)):
                        grand["buckets"][i] += g["buckets"][i]
                else:
                    grand[k] += g[k]
    else:
        for gv in group_order:
            items = groups[gv]
            group_label = _group_label(gv, group_key)
            rows.append(_group_header_row(group_label))

            g = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
                 "buckets": [0] * len(AGING_BUCKETS)}

            # If grouping by customer, show customer subtotals; else detail rows
            if group_key == "customer":
                # sub-group by customer within the group (group == customer here)
                _emit_customer_detail(rows, items, g, aging_method, as_of, view_type,
                                      unapplied_by_customer, customer=gv)
            else:
                # Within non-customer groups, sub-group by customer for subtotals
                _emit_grouped_detail(rows, items, g, aging_method, as_of, view_type,
                                     unapplied_by_customer)

            # Group subtotal
            rows.append(_subtotal_row("Subtotal: " + group_label, g))

            for k in grand:
                if k == "buckets":
                    for i in range(len(AGING_BUCKETS)):
                        grand["buckets"][i] += g["buckets"][i]
                else:
                    grand[k] += g[k]

        # In Detailed view, keep the separate Unapplied Payments & Credits section.
        if show_unapplied and view_type == "Detailed" and unapplied:
            rows.append(_unapplied_header_row())
            u = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
                 "buckets": [0] * len(AGING_BUCKETS)}
            for item in unapplied:
                rows.append(_unapplied_detail_row(item))
                u["outstanding"] += item["amount"]
                # unapplied credits go to above 90 bucket by convention
                if item["amount"] < 0:
                    u["buckets"][3] += item["amount"]
                else:
                    u["buckets"][0] += item["amount"]
            rows.append(_subtotal_row("Subtotal: Unapplied Payments & Credits", u))
            for i in range(len(AGING_BUCKETS)):
                grand["buckets"][i] += u["buckets"][i]
            grand["outstanding"] += u["outstanding"]
            rows.append(_net_receivables_row(grand))

    # Grand total
    rows.append(_summary_grand_total_row(grand, view_type))
    return rows


def _emit_customer_detail(rows, items, g, aging_method, as_of, view_type,
                          unapplied_by_customer, customer=None):
    """Emit detail + customer subtotal rows (group_key == customer)."""
    cust = customer or (items[0].get("customer") if items else "")
    cg = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
          "buckets": [0] * len(AGING_BUCKETS)}
    current = cust if cust else None
    # Invoice lines first, Advance Sales Invoice lines after them
    ordered = ([i for i in items if not i.get("is_asi")]
               + [i for i in items if i.get("is_asi")])
    for inv in ordered:
        if current is not None and inv.get("customer") != current:
            _emit_customer_unapplied_and_net(rows, g, cg, current,
                                             unapplied_by_customer, view_type)
            cg = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
                  "buckets": [0] * len(AGING_BUCKETS)}
        current = inv.get("customer")
        age = _calc_age(inv, aging_method, as_of)
        buckets = [_bucket_amount(inv["outstanding"], age) if lo <= age <= hi else 0
                   for label, lo, hi in AGING_BUCKETS]
        if view_type == "Detailed":
            rows.append(_detail_row(inv, age, buckets))
        _accumulate_single(cg, inv, age, buckets)
    if current is not None:
        _emit_customer_unapplied_and_net(rows, g, cg, current,
                                         unapplied_by_customer, view_type)
    else:
        _accumulate(g, cg)


def _emit_grouped_detail(rows, items, g, aging_method, as_of, view_type,
                         unapplied_by_customer):
    """Emit detail rows + customer subtotals within a non-customer group."""
    by_cust = {}
    order = []
    for inv in items:
        c = inv.get("customer") or ""
        if c not in by_cust:
            by_cust[c] = []
            order.append(c)
        by_cust[c].append(inv)

    for c in order:
        citems = ([i for i in by_cust[c] if not i.get("is_asi")]
                  + [i for i in by_cust[c] if i.get("is_asi")])
        cg = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
              "buckets": [0] * len(AGING_BUCKETS)}
        for inv in citems:
            age = _calc_age(inv, aging_method, as_of)
            buckets = [_bucket_amount(inv["outstanding"], age) if lo <= age <= hi else 0
                       for label, lo, hi in AGING_BUCKETS]
            if view_type == "Detailed":
                rows.append(_detail_row(inv, age, buckets))
            _accumulate_single(cg, inv, age, buckets)
        _emit_customer_unapplied_and_net(rows, g, cg, c,
                                         unapplied_by_customer, view_type)


def _emit_customer_unapplied_and_net(rows, g, cg, customer,
                                     unapplied_by_customer, view_type):
    """Emit customer subtotal and, in Summary view, unapplied advances/credit
    notes and net receivables immediately under the customer section."""
    ua = unapplied_by_customer.get(customer)
    has_invoices = bool(cg["invoiced"] or cg["paid"] or cg["credit_note"]
                        or abs(cg["outstanding"]) > 0.01)
    has_unapplied = bool(ua and (abs(ua.get("advances", 0)) > 0.01
                                  or abs(ua.get("credits", 0)) > 0.01))

    if not has_invoices and not has_unapplied:
        return

    # Emit the customer subtotal row (gross invoice outstanding).
    rows.append(_customer_subtotal_row(customer, cg))

    if ua and view_type == "Summary":
        advances = flt(ua.get("advances", 0), 2)
        credits = flt(ua.get("credits", 0), 2)

        # Emit unapplied advances row (positive amount in 0-30 bucket)
        if abs(advances) > 0.01:
            rows.append(_unapplied_advances_row(advances))
        # Emit unapplied credit notes row (negative amount in Above 90 bucket)
        if abs(credits) > 0.01:
            rows.append(_unapplied_credits_row(credits))

        # Compute net receivables and adjust buckets
        # advances are positive and reduce receivables;
        # credits are negative and also reduce receivables.
        net_outstanding = cg["outstanding"] - advances + credits
        net_buckets = cg["buckets"][:]
        if advances:
            net_buckets[0] -= advances
        if credits:
            net_buckets[3] += credits  # credits is negative

        # Replace cg outstanding/buckets with net so group totals are net
        cg["outstanding"] = net_outstanding
        cg["buckets"] = net_buckets

        # Only emit net row if there is a non-zero net or any unapplied activity
        if abs(net_outstanding) > 0.01 or abs(advances) > 0.01 or abs(credits) > 0.01:
            rows.append(_net_receivables_customer_row(net_outstanding, net_buckets))

    _accumulate(g, cg)


def _accumulate(acc, src):
    for k in ("invoiced", "paid", "credit_note", "outstanding"):
        acc[k] += src[k]
    for i in range(len(AGING_BUCKETS)):
        acc["buckets"][i] += src["buckets"][i]


def _accumulate_single(acc, inv, age, buckets):
    acc["invoiced"] += inv["base_grand_total"] or 0
    acc["paid"] += inv["paid_amount"]
    acc["credit_note"] += inv["credit_note_amt"]
    acc["outstanding"] += inv["outstanding"]
    for i in range(len(buckets)):
        acc["buckets"][i] += buckets[i]


def _group_label(gv, group_key):
    if group_key == "customer":
        name = frappe.db.get_value("Customer", gv, "customer_name") or gv
        return "{0} : {1}".format(gv, name)
    if group_key == "salesperson":
        return gv or "Unassigned"
    if group_key == "division":
        return gv or "Unassigned"
    if group_key == "region":
        return gv or "Unassigned"
    return gv


def _detail_row(inv, age, buckets):
    return [
        inv.get("posting_date").strftime("%d-%m-%Y") if hasattr(inv.get("posting_date"), "strftime") else inv.get("posting_date"),
        inv.get("name", ""),
        "{0} : {1}".format(inv.get("customer", ""), inv.get("customer_name", "")),
        inv.get("sales_person") or "",
        flt(inv["base_grand_total"], 2),
        flt(inv["paid_amount"], 2),
        flt(inv["credit_note_amt"], 2),
        flt(inv["outstanding"], 2),
        age,
    ] + [flt(b, 2) for b in buckets]


def _customer_subtotal_row(customer, cg):
    name = frappe.db.get_value("Customer", customer, "customer_name") or customer
    return [
        "Customer Subtotal: {0} - {1}".format(customer, name),
        "", "", "",
        flt(cg["invoiced"], 2), flt(cg["paid"], 2), flt(cg["credit_note"], 2),
        flt(cg["outstanding"], 2), "",
    ] + [flt(b, 2) for b in cg["buckets"]]


def _group_header_row(label):
    return ["GROUP: " + label] + [""] * 12


def _subtotal_row(label, g):
    return [
        label, "", "", "",
        flt(g["invoiced"], 2), flt(g["paid"], 2), flt(g["credit_note"], 2),
        flt(g["outstanding"], 2), "",
    ] + [flt(b, 2) for b in g["buckets"]]


def _grand_total_row(g):
    return [
        "GRAND TOTAL", "", "", "",
        flt(g["invoiced"], 2), flt(g["paid"], 2), flt(g["credit_note"], 2),
        flt(g["outstanding"], 2), "",
    ] + [flt(b, 2) for b in g["buckets"]]


def _net_receivables_row(g):
    return [
        "NET RECEIVABLES", "", "", "",
        flt(g["invoiced"], 2), flt(g["paid"], 2), flt(g["credit_note"], 2),
        flt(g["outstanding"], 2), "",
    ] + [flt(b, 2) for b in g["buckets"]]


def _unapplied_header_row():
    return ["GROUP: Unapplied Payments & Credits"] + [""] * 12


def _unapplied_detail_row(item):
    return [
        item.get("date", ""),
        item.get("voucher", ""),
        item.get("party", ""),
        "",
        0, 0, flt(item["amount"], 2) if item["amount"] < 0 else 0,
        flt(item["amount"], 2),
        "",
    ] + [flt(item["amount"], 2) if item["amount"] >= 0 else 0, 0, 0,
         flt(item["amount"], 2) if item["amount"] < 0 else 0]


def _unapplied_summary_row(s):
    """Single line per customer showing total of unapplied payments/credits.
    Kept for Detailed view compatibility."""
    amt = flt(s["amount"], 2)
    return [
        "Unapplied: " + s["party"], "", "", "",
        0, 0,
        amt if amt < 0 else 0,
        amt,
        "",
        amt if amt >= 0 else 0,
        0, 0,
        amt if amt < 0 else 0,
    ]


def _unapplied_advances_row(amount):
    """Row showing unapplied customer advances (positive, in 0-30 bucket)."""
    amt = flt(amount, 2)
    buckets = [0] * len(AGING_BUCKETS)
    buckets[0] = amt
    return [
        "Unapplied advances", "", "", "",
        0, 0, 0,
        amt,
        "",
    ] + [flt(b, 2) for b in buckets]


def _unapplied_credits_row(amount):
    """Row showing unapplied credit notes (negative, in Above 90 bucket)."""
    amt = flt(amount, 2)
    buckets = [0] * len(AGING_BUCKETS)
    buckets[3] = amt
    return [
        "Unapplied credit notes", "", "", "",
        0, 0, 0,
        amt,
        "",
    ] + [flt(b, 2) for b in buckets]


def _net_receivables_customer_row(outstanding, buckets):
    """Net receivables row shown below a customer's unapplied rows."""
    return [
        "NET RECEIVABLES", "", "", "",
        0, 0, 0,
        flt(outstanding, 2),
        "",
    ] + [flt(b, 2) for b in buckets]


def _get_unapplied(company, as_of, entity_list=None, group_key="customer"):
    """Fetch unapplied customer payments (advances) and standalone credit notes
    with no invoice linkage, posted on or before as_of_date, optionally filtered
    by the same entity selection used for invoices."""
    items = []
    allowed = set(entity_list or [])
    filter_by_customer = group_key == "customer" and allowed

    # Build customer filter SQL for Payment Entry and Credit Notes
    def _in_clause(values):
        return " AND pe.party IN ({0})".format(", ".join(["%s"] * len(values))) if values else ""

    def _in_clause_cn(values):
        return " AND customer IN ({0})".format(", ".join(["%s"] * len(values))) if values else ""

    pe_sql = """
        SELECT pe.name, pe.posting_date, pe.party, pe.paid_amount,
               pe.unallocated_amount
        FROM `tabPayment Entry` pe
        WHERE pe.company = %s AND pe.docstatus = 1
          AND pe.payment_type = 'Receive'
          AND pe.party_type = 'Customer'
          AND pe.posting_date <= %s
          AND pe.unallocated_amount > 0.01
    """
    pe_params = [company, as_of]
    if filter_by_customer:
        pe_sql += _in_clause(list(allowed))
        pe_params.extend(list(allowed))

    pe_rows = frappe.db.sql(pe_sql, tuple(pe_params), as_dict=True)

    for pe in pe_rows:
        cust_name = (frappe.db.get_value("Customer", pe["party"], "customer_name") or pe["party"] or "").strip()
        party = (pe["party"] or "").strip()
        items.append({
            "date": pe["posting_date"].strftime("%d-%m-%Y") if hasattr(pe["posting_date"], "strftime") else pe["posting_date"],
            "voucher": pe["name"],
            "customer": party,
            "party": "{0} : {1}".format(party, cust_name),
            "amount": flt(pe["unallocated_amount"], 2),
        })

    # Standalone credit notes not already counted as invoice-linked
    cn_sql = """
        SELECT name, posting_date, customer, base_grand_total
        FROM `tabSales Invoice`
        WHERE company = %s AND docstatus = 1 AND is_return = 1
          AND posting_date <= %s
          AND (return_against IS NULL OR return_against = '')
          AND (custom_return_reason IS NULL OR custom_return_reason = ''
               OR custom_return_reason NOT IN (
                   SELECT name FROM `tabSales Invoice`
                   WHERE company = %s AND docstatus = 1 AND is_return = 0
               ))
    """
    cn_params = [company, as_of, company]
    if filter_by_customer:
        cn_sql += _in_clause_cn(list(allowed))
        cn_params.extend(list(allowed))

    cn_rows = frappe.db.sql(cn_sql, tuple(cn_params), as_dict=True)

    for cn in cn_rows:
        # Subtract any payments allocated to this credit note
        paid = _calc_paid(cn, company, as_of)
        outstanding = (cn["base_grand_total"] or 0) - paid
        if abs(outstanding) > 0.01:
            cust = (cn["customer"] or "").strip()
            cust_name = (frappe.db.get_value("Customer", cust, "customer_name") or cust).strip()
            items.append({
                "date": cn["posting_date"].strftime("%d-%m-%Y") if hasattr(cn["posting_date"], "strftime") else cn["posting_date"],
                "voucher": cn["name"],
                "customer": cust,
                "party": "{0} : {1}".format(cust, cust_name),
                "amount": flt(outstanding, 2),  # negative (credit)
            })

    return items


def _unapplied_by_customer(unapplied):
    """Return a dict of customer code -> {party, advances, credits}."""
    by_cust = {}
    for item in unapplied:
        cust = (item.get("customer") or "").strip()
        if not cust:
            continue
        if cust not in by_cust:
            by_cust[cust] = {
                "party": item.get("party") or cust,
                "advances": 0.0,
                "credits": 0.0,
            }
        amt = flt(item["amount"], 2)
        if amt > 0:
            by_cust[cust]["advances"] += amt
        elif amt < 0:
            by_cust[cust]["credits"] += amt
    return by_cust


def _calc_group_summary(gv, items, unapplied_by_customer, group_key, aging_method, as_of):
    """Return net aggregated values for a single summary row."""
    cg = {
        "invoiced": 0.0,
        "paid": 0.0,
        "credit_note": 0.0,
        "outstanding": 0.0,
        "buckets": [0.0] * len(AGING_BUCKETS),
    }

    for inv in items:
        age = _calc_age(inv, aging_method, as_of)
        buckets = [_bucket_amount(inv["outstanding"], age) if lo <= age <= hi else 0
                   for label, lo, hi in AGING_BUCKETS]
        _accumulate_single(cg, inv, age, buckets)

    # Apply unapplied advances/credits into the same row.
    ua = None
    if group_key == "customer":
        ua = unapplied_by_customer.get(gv)
    else:
        customers = {inv.get("customer") for inv in items if inv.get("customer")}
        ua = {"advances": 0.0, "credits": 0.0}
        for c in customers:
            cust_ua = unapplied_by_customer.get(c)
            if cust_ua:
                ua["advances"] += cust_ua["advances"]
                ua["credits"] += cust_ua["credits"]
        if abs(ua["advances"]) < 0.01 and abs(ua["credits"]) < 0.01:
            ua = None

    if ua:
        advances = flt(ua.get("advances", 0), 2)
        credits = flt(ua.get("credits", 0), 2)
        if abs(advances) > 0.01 or abs(credits) > 0.01:
            cg["paid"] += advances
            cg["credit_note"] += credits
            cg["outstanding"] = cg["outstanding"] - advances + credits
            cg["buckets"][0] -= advances
            cg["buckets"][3] += credits

    has_data = (
        abs(cg["invoiced"]) > 0.01
        or abs(cg["paid"]) > 0.01
        or abs(cg["credit_note"]) > 0.01
        or abs(cg["outstanding"]) > 0.01
    )
    return cg if has_data else None


def _emit_asi_lines(rows, g, asi_items, aging_method, as_of):
    """Emit a single aggregated "Advance Sales Invoice" line for the customer
    (Summary view) and accumulate it into the group totals."""
    if not asi_items:
        return
    tot = {"invoiced": 0.0, "paid": 0.0, "credit_note": 0.0, "outstanding": 0.0,
           "buckets": [0.0] * len(AGING_BUCKETS)}
    for asi in asi_items:
        age = _calc_age(asi, aging_method, as_of)
        buckets = [flt(asi["outstanding"], 2) if lo <= age <= hi else 0
                   for label, lo, hi in AGING_BUCKETS]
        tot["invoiced"] += asi["base_grand_total"]
        tot["paid"] += asi["paid_amount"]
        tot["credit_note"] += asi["credit_note_amt"]
        tot["outstanding"] += asi["outstanding"]
        for i in range(len(AGING_BUCKETS)):
            tot["buckets"][i] += buckets[i]
    rows.append([
        "Advance Sales Invoice",
        flt(tot["invoiced"], 2),
        flt(tot["paid"], 2),
        flt(tot["credit_note"], 2),
        flt(tot["outstanding"], 2),
        "",
    ] + [flt(b, 2) for b in tot["buckets"]])
    _accumulate(g, tot)


def _summary_row(gv, group_key, net):
    """Return a single summary row for the group."""
    if group_key == "customer":
        name = frappe.db.get_value("Customer", gv, "customer_name") or gv
        label = "{0} - {1}".format(gv, name)
    else:
        label = _group_label(gv, group_key)
    return [
        label,
        flt(net["invoiced"], 2),
        flt(net["paid"], 2),
        flt(net["credit_note"], 2),
        flt(net["outstanding"], 2),
        "",
    ] + [flt(b, 2) for b in net["buckets"]]


def _summary_grand_total_row(g, view_type):
    """Return a grand total row sized for the current view type."""
    if view_type == "Summary":
        return [
            "GRAND TOTAL",
            flt(g["invoiced"], 2),
            flt(g["paid"], 2),
            flt(g["credit_note"], 2),
            flt(g["outstanding"], 2),
            "",
        ] + [flt(b, 2) for b in g["buckets"]]
    return _grand_total_row(g)


def _summary_group_header_row(label):
    """Return a 10-column group header row for summary views."""
    return ["GROUP: " + label] + [""] * 9


def _summary_subtotal_row(label, g):
    """Return a 10-column subtotal row for summary views."""
    return [
        label,
        flt(g["invoiced"], 2),
        flt(g["paid"], 2),
        flt(g["credit_note"], 2),
        flt(g["outstanding"], 2),
        "",
    ] + [flt(b, 2) for b in g["buckets"]]
