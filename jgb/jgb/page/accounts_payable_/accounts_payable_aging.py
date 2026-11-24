# Copyright (c) 2026, JGB and contributors
# Accounts Payable Aging Report - Page backend
# Mirrors the Accounts Receivable aging backend but for payables.

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
from jgb.jgb.doctype.accounts_report_dashboard.print_format_helpers import (
    fmt_currency, esc,
)

AGING_BUCKETS = [
    ("0-30", 0, 30),
    ("31-60", 31, 60),
    ("61-90", 61, 90),
    ("Above 90", 91, 99999),
]

GROUP_LABELS = {
    "Supplier Wise": "supplier",
    "Division Wise": "division",
}


def get_exchange_rate(from_currency, to_currency):
    """Get exchange rate between any two currencies.
    Tries: direct rate -> reverse rate -> cross rate via SAR -> cross rate via USD."""
    if from_currency == to_currency:
        return 1.0

    def _get_direct_rate(frm, to):
        r = frappe.db.sql("""
            SELECT exchange_rate FROM `tabCurrency Exchange`
            WHERE from_currency = %s AND to_currency = %s
            ORDER BY date DESC LIMIT 1
        """, (frm, to))
        return flt(r[0][0]) if r and r[0][0] else None

    # 1. Direct rate: from -> to
    rate = _get_direct_rate(from_currency, to_currency)
    if rate:
        return rate

    # 2. Reverse rate: to -> from, then invert
    rate = _get_direct_rate(to_currency, from_currency)
    if rate:
        return 1.0 / rate

    # 3. Cross rate via SAR: from -> SAR, then SAR -> to
    if from_currency != "SAR" and to_currency != "SAR":
        rate_from_sar = _get_direct_rate(from_currency, "SAR")
        rate_to_sar = _get_direct_rate(to_currency, "SAR")
        if rate_from_sar and rate_to_sar:
            return rate_from_sar / rate_to_sar

    # 4. Cross rate via USD: from -> USD, then USD -> to
    if from_currency != "USD" and to_currency != "USD":
        rate_from_usd = _get_direct_rate(from_currency, "USD") or (_get_direct_rate("USD", from_currency) and 1.0 / _get_direct_rate("USD", from_currency))
        rate_to_usd = _get_direct_rate(to_currency, "USD") or (_get_direct_rate("USD", to_currency) and 1.0 / _get_direct_rate("USD", to_currency))
        if rate_from_usd and rate_to_usd:
            return rate_from_usd / rate_to_usd

    frappe.msgprint(f"No exchange rate found for {from_currency} -> {to_currency}. Using 1.0")
    return 1.0


@frappe.whitelist()
def debug_invoices(company=None, as_of_date=None):
    """Debug helper to inspect raw invoice data."""
    if not company:
        company = "JGB International Limited Company"
    as_of = getdate(as_of_date) if as_of_date else getdate(today())
    rows = frappe.db.sql("""
        SELECT name, posting_date, due_date, supplier, base_grand_total, is_return
        FROM `tabPurchase Invoice`
        WHERE company=%s AND docstatus=1 AND posting_date <= %s
        ORDER BY posting_date
        LIMIT 10
    """, (company, as_of), as_dict=True)
    companies = frappe.db.sql("""
        SELECT company, COUNT(*) as cnt FROM `tabPurchase Invoice`
        WHERE docstatus=1 GROUP BY company
    """, as_dict=True)
    return {"count": len(rows), "as_of": str(as_of), "sample": rows, "by_company": companies}


@frappe.whitelist()
def get_entity_options(company=None, grouping="Supplier Wise", search=""):
    """Return available entity values for the Multi-Select filter based on grouping."""
    if not company:
        return []
    group_key = GROUP_LABELS.get(grouping, "supplier")
    search = (search or "").strip()

    if group_key == "supplier":
        rows = frappe.db.sql("""
            SELECT DISTINCT supplier FROM `tabPurchase Invoice`
            WHERE company=%s AND docstatus=1
        """, company)
        vals = [r[0] for r in rows if r[0]]
        names = {}
        if vals:
            for s in frappe.db.get_all("Supplier", filters={"name": ["in", vals]},
                                       fields=["name", "supplier_name"]):
                names[s["name"]] = s["supplier_name"]
        result = [{"value": v, "label": "{0} - {1}".format(v, names.get(v, v))}
                  for v in sorted(vals)]
    elif group_key == "division":
        rows = frappe.db.sql("""
            SELECT DISTINCT custom_division FROM `tabPurchase Invoice`
            WHERE company=%s AND docstatus=1 AND custom_division IS NOT NULL
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
    grouping="Supplier Wise",
    entities=None,
    as_of_date=None,
    aging_method="Due Date",
    show_unapplied=0,
    purchase_type=None,
    currency=None,
):
    """Return report rows + columns for the page table (JSON)."""
    if not company:
        frappe.throw("Kindly choose the company.")

    as_of = getdate(as_of_date) if as_of_date else getdate(today())
    entity_list = _parse_entities(entities)
    group_key = GROUP_LABELS.get(grouping, "supplier")

    invoices = _get_open_invoices(company, as_of, group_key, entity_list, purchase_type)
    rows = _build_rows(invoices, group_key, view_type, aging_method, as_of,
                       show_unapplied, company, entity_list, purchase_type)

    columns = _get_columns(view_type, group_key)

    base_currency = frappe.db.get_value("Company", company, "default_currency") or "SAR"
    target_currency = currency or base_currency
    if target_currency and target_currency != base_currency:
        exchange_rate = get_exchange_rate(base_currency, target_currency)
        if exchange_rate and exchange_rate != 1.0:
            _convert_amounts(rows, columns, exchange_rate)

    return {
        "columns": columns,
        "rows": rows,
        "company": company,
        "currency": target_currency,
        "as_of_date": format_date(as_of),
        "report_date": datetime.now().strftime("%d-%m-%Y"),
    }


@frappe.whitelist()
def download_excel(
    company=None,
    view_type="Summary",
    grouping="Supplier Wise",
    entities=None,
    as_of_date=None,
    aging_method="Due Date",
    show_unapplied=0,
    purchase_type=None,
    currency=None,
):
    """Build and send the Excel (.xlsx) export."""
    if not company:
        frappe.throw("Kindly choose the company.")

    result = get_report_data(
        company=company, view_type=view_type, grouping=grouping,
        entities=entities, as_of_date=as_of_date, aging_method=aging_method,
        show_unapplied=show_unapplied, purchase_type=purchase_type,
        currency=currency,
    )

    wb = openpyxl.Workbook()
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])
    ws = wb.create_sheet("AP Aging Report", 0)

    columns = result["columns"]
    rows = result["rows"]
    num_cols = len(columns)

    # Title rows
    ws.append([result["company"]])
    ws.append(["Accounts Payable Aging Report"])
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
    apply_title_rows(ws, num_cols, "Accounts Payable Aging Report",
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
        is_cust_sub = label.startswith("Supplier Subtotal:")
        is_subtotal = label.startswith("Subtotal:")
        is_unapplied = label.startswith("Unapplied")
        is_net = label.startswith("NET PAYABLES")
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
    frappe.response["filename"] = "Accounts Payable Aging Report.xlsx"
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
            {"label": "Supplier", "fieldname": "supplier", "type": "text"},
            {"label": "Invoiced Amount", "fieldname": "invoiced", "type": "currency"},
            {"label": "Paid Amount", "fieldname": "paid", "type": "currency"},
            {"label": "Debit Note", "fieldname": "credit_note", "type": "currency"},
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
        {"label": "Supplier", "fieldname": "supplier", "type": "text"},
        {"label": "Division", "fieldname": "division", "type": "text"},
    ]
    cols += [
        {"label": "Invoiced Amount", "fieldname": "invoiced", "type": "currency"},
        {"label": "Paid Amount", "fieldname": "paid", "type": "currency"},
        {"label": "Debit Note", "fieldname": "credit_note", "type": "currency"},
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
        elif "Supplier" in label:
            widths.append(35)
        elif "Division" in label:
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


def _convert_amounts(rows, columns, exchange_rate):
    """Convert currency columns in-place by the given exchange rate."""
    if not exchange_rate or exchange_rate == 1.0:
        return
    currency_indices = [i for i, c in enumerate(columns) if c.get("type") == "currency"]
    for row in rows:
        for i in currency_indices:
            val = row[i]
            if isinstance(val, (int, float)):
                row[i] = round(val * exchange_rate, 2)


def _get_open_invoices(company, as_of, group_key, entity_list, purchase_type=None):
    """Fetch all open (non-zero outstanding) Purchase Invoices
    posted on or before the as-of date, enriched with grouping attributes.
    Return invoices / debit notes are handled through the parent invoice
    (linked via return_against) or the unapplied section.
    Optionally filtered by purchase_type (Local/Import) via the linked Purchase Order."""
    pi_rows = frappe.db.sql("""
        SELECT pi.name, pi.posting_date, pi.due_date, pi.supplier,
               pi.custom_division AS division,
               pi.bill_no, pi.base_grand_total, pi.is_return,
               pi.return_against
        FROM `tabPurchase Invoice` pi
        WHERE pi.company = %s
          AND pi.docstatus = 1
          AND pi.is_return = 0
          AND pi.posting_date <= %s
          {purchase_type_filter}
        ORDER BY pi.posting_date
    """.format(
        purchase_type_filter=_purchase_type_filter(purchase_type)
    ), _purchase_type_params(company, as_of, purchase_type), as_dict=True)

    # Pre-fetch supplier names
    suppliers = list({r["supplier"] for r in pi_rows if r.get("supplier")})
    supp_names = {}
    if suppliers:
        for s in frappe.db.get_all("Supplier",
                                   filters={"name": ["in", suppliers]},
                                   fields=["name", "supplier_name"]):
            supp_names[s["name"]] = s["supplier_name"]

    enriched = []
    for r in pi_rows:
        supp = r["supplier"]
        r["supplier_name"] = supp_names.get(supp, supp)
        r["group_value"] = _group_value(r, group_key)
        enriched.append(r)

    # Filter by entity selection
    if entity_list:
        enriched = [r for r in enriched if r["group_value"] in entity_list]

    # Calculate outstanding for each invoice
    for r in enriched:
        r["outstanding"] = _calc_outstanding(r, company, as_of)
        r["paid_amount"] = _calc_paid(r, company, as_of)
        r["credit_note_amt"] = _calc_credit_note(r, company, as_of)

    # Keep only open items
    enriched = [r for r in enriched if abs(r["outstanding"]) > 0.01]
    return enriched


def _group_value(row, group_key):
    if group_key == "supplier":
        return row.get("supplier") or ""
    if group_key == "division":
        return row.get("division") or "Unassigned"
    return row.get("supplier") or ""


def _purchase_type_filter(purchase_type):
    """Return SQL EXISTS clause to filter invoices by PO's custom_purchase_type."""
    if not purchase_type:
        return ""
    return (
        " AND EXISTS ("
        "  SELECT 1 FROM `tabPurchase Invoice Item` pii"
        "  INNER JOIN `tabPurchase Order` po ON pii.purchase_order = po.name"
        "  WHERE pii.parent = pi.name AND po.custom_purchase_type = %s"
        " )"
    )


def _purchase_type_params(company, as_of, purchase_type):
    """Build parameter list for _get_open_invoices query."""
    params = [company, as_of]
    if purchase_type:
        params.append(purchase_type)
    return tuple(params)


def _purchase_type_filter_debit_note(purchase_type):
    """Return SQL EXISTS clause for standalone debit notes (no alias prefix)."""
    if not purchase_type:
        return ""
    return (
        " AND EXISTS ("
        "  SELECT 1 FROM `tabPurchase Invoice Item` pii"
        "  INNER JOIN `tabPurchase Order` po ON pii.purchase_order = po.name"
        "  WHERE pii.parent = `tabPurchase Invoice`.name"
        "    AND po.custom_purchase_type = %s"
        " )"
    )


def _calc_outstanding(row, company, as_of):
    base = row["base_grand_total"] or 0
    if row.get("is_return"):
        # If the return is linked to a parent invoice, its debit is already
        # applied to that invoice; do not show it as a separate open item.
        if row.get("return_against"):
            return 0
        paid = _calc_paid(row, company, as_of)
        # debit note: outstanding is negative base minus payments allocated to it
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

    # For payables, supplier liability is reduced by a debit entry,
    # so allocated amount is debit - credit.
    je = frappe.db.sql("""
        SELECT SUM(jva.debit - jva.credit) AS amt
        FROM `tabJournal Entry Account` jva
        LEFT JOIN `tabJournal Entry` jv ON jva.parent = jv.name
        WHERE jv.docstatus = 1
          AND jva.reference_type = 'Purchase Invoice'
          AND jva.reference_name = %s
          AND jv.posting_date <= %s
          AND NOT EXISTS (
              SELECT 1 FROM `tabJournal Entry Account` jva2
              LEFT JOIN `tabPurchase Invoice` pi ON jva2.reference_name = pi.name
              WHERE jva2.parent = jv.name
                AND jva2.reference_type = 'Purchase Invoice'
                AND pi.is_return = 1
                AND pi.return_against = %s
          )
    """, (inv, as_of, inv))[0][0] or 0

    return flt(pe + je)


def _calc_credit_note(row, company, as_of):
    """Sum of debit notes linked to this invoice (non-return invoices only)."""
    if row.get("is_return"):
        return 0
    inv = row["name"]
    res = frappe.db.sql("""
        SELECT SUM(base_grand_total) AS total
        FROM `tabPurchase Invoice`
        WHERE company = %s AND docstatus = 1 AND is_return = 1
          AND posting_date <= %s
          AND return_against = %s
    """, (company, as_of, inv))[0][0]
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
                show_unapplied, company, entity_list=None, purchase_type=None):
    """Build the final row list with group headers, detail/subtotal rows, grand total."""
    rows = []
    # Sort by group then posting date
    invoices = sorted(invoices, key=lambda x: (x.get("group_value") or "", x.get("posting_date")))

    grand = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
             "buckets": [0] * len(AGING_BUCKETS)}

    # Pre-load unapplied advances/debit notes and split by supplier.
    # Summary view nets them only when show_unapplied is set.
    # Detailed view uses them either inline (when not show_unapplied) or as a separate section.
    unapplied = _get_unapplied(company, as_of, entity_list, group_key, purchase_type)
    unapplied_by_supplier = _unapplied_by_supplier(unapplied) if unapplied else {}

    # In Summary view, only include unapplied when the checkbox is enabled.
    summary_unapplied = unapplied_by_supplier if show_unapplied else {}

    # Group invoices
    groups = {}
    group_order = []
    for inv in invoices:
        gv = inv.get("group_value") or ""
        if gv not in groups:
            groups[gv] = []
            group_order.append(gv)
        groups[gv].append(inv)

    # For Supplier Wise view, also include suppliers that only have
    # unapplied advances/credits and no open invoices.
    if group_key == "supplier" and show_unapplied:
        for supp in unapplied_by_supplier:
            if supp not in groups:
                groups[supp] = []
                group_order.append(supp)

    if view_type == "Summary":
        # Summary view: one text column + amount columns.
        for gv in group_order:
            items = groups[gv]
            group_label = _group_label(gv, group_key)

            if group_key != "supplier":
                rows.append(_summary_group_header_row(group_label))

            g = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
                 "buckets": [0] * len(AGING_BUCKETS)}

            if group_key == "supplier":
                net = _calc_group_summary(gv, items, summary_unapplied, group_key,
                                          aging_method, as_of)
                if net:
                    rows.append(_summary_row(gv, group_key, net))
                    _accumulate(g, net)
            else:
                # Group per supplier inside division.
                by_supp = {}
                supp_order = []
                for inv in items:
                    s = inv.get("supplier") or ""
                    if s not in by_supp:
                        by_supp[s] = []
                        supp_order.append(s)
                    by_supp[s].append(inv)

                for s in supp_order:
                    sitems = by_supp[s]
                    net = _calc_group_summary(s, sitems, summary_unapplied, "supplier",
                                              aging_method, as_of)
                    if not net:
                        continue
                    rows.append(_summary_row(s, "supplier", net))
                    _accumulate(g, net)

            if group_key != "supplier":
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

            # If grouping by supplier, show supplier subtotals; else detail rows
            if group_key == "supplier":
                _emit_supplier_detail(rows, items, g, aging_method, as_of, view_type,
                                      unapplied_by_supplier, show_unapplied, supplier=gv)
            else:
                # Within division, sub-group by supplier for subtotals
                _emit_grouped_detail(rows, items, g, aging_method, as_of, view_type,
                                     unapplied_by_supplier, show_unapplied)

            # Group subtotal (only for non-supplier groupings; for supplier wise
            # the supplier subtotal already acts as the group subtotal).
            if group_key != "supplier":
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
            rows.append(_net_payables_row(grand))

    # Grand total
    rows.append(_summary_grand_total_row(grand, view_type))
    return rows


def _emit_supplier_detail(rows, items, g, aging_method, as_of, view_type,
                          unapplied_by_supplier, show_unapplied, supplier=None):
    """Emit detail + supplier subtotal rows (group_key == supplier)."""
    supp = supplier or (items[0].get("supplier") if items else "")
    cg = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
          "buckets": [0] * len(AGING_BUCKETS)}
    current = supp if supp else None
    for inv in items:
        if current is not None and inv.get("supplier") != current:
            _emit_supplier_unapplied_and_net(rows, g, cg, current,
                                             unapplied_by_supplier, view_type,
                                             show_unapplied)
            cg = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
                  "buckets": [0] * len(AGING_BUCKETS)}
        current = inv.get("supplier")
        age = _calc_age(inv, aging_method, as_of)
        buckets = [_bucket_amount(inv["outstanding"], age) if lo <= age <= hi else 0
                   for label, lo, hi in AGING_BUCKETS]
        if view_type == "Detailed":
            rows.append(_detail_row(inv, age, buckets))
        _accumulate_single(cg, inv, age, buckets)
    if current is not None:
        _emit_supplier_unapplied_and_net(rows, g, cg, current,
                                         unapplied_by_supplier, view_type,
                                         show_unapplied)
    else:
        _accumulate(g, cg)


def _emit_grouped_detail(rows, items, g, aging_method, as_of, view_type,
                         unapplied_by_supplier, show_unapplied):
    """Emit detail rows + supplier subtotals within a division group."""
    by_supp = {}
    order = []
    for inv in items:
        s = inv.get("supplier") or ""
        if s not in by_supp:
            by_supp[s] = []
            order.append(s)
        by_supp[s].append(inv)

    for s in order:
        sitems = by_supp[s]
        cg = {"invoiced": 0, "paid": 0, "credit_note": 0, "outstanding": 0,
              "buckets": [0] * len(AGING_BUCKETS)}
        for inv in sitems:
            age = _calc_age(inv, aging_method, as_of)
            buckets = [_bucket_amount(inv["outstanding"], age) if lo <= age <= hi else 0
                       for label, lo, hi in AGING_BUCKETS]
            if view_type == "Detailed":
                rows.append(_detail_row(inv, age, buckets))
            _accumulate_single(cg, inv, age, buckets)
        _emit_supplier_unapplied_and_net(rows, g, cg, s,
                                         unapplied_by_supplier, view_type,
                                         show_unapplied)


def _emit_supplier_unapplied_and_net(rows, g, cg, supplier,
                                     unapplied_by_supplier, view_type,
                                     show_unapplied):
    """Emit supplier subtotal and, in Detailed view when show_unapplied is off,
    the unapplied detail rows inline under the supplier."""
    ua = unapplied_by_supplier.get(supplier)
    has_invoices = bool(cg["invoiced"] or cg["paid"] or cg["credit_note"]
                        or abs(cg["outstanding"]) > 0.01)
    has_unapplied = bool(ua and (abs(ua.get("advances", 0)) > 0.01
                                  or abs(ua.get("credits", 0)) > 0.01))

    if not has_invoices and not has_unapplied:
        return

    # When unapplied is not shown as a separate section, emit individual
    # unapplied items as detail rows and include them in the supplier subtotal.
    if view_type == "Detailed" and not show_unapplied and ua:
        for item in ua.get("items", []):
            rows.append(_unapplied_detail_row(item))
            _apply_unapplied_to_cg(cg, item["amount"])

    # Emit the supplier subtotal row.
    rows.append(_supplier_subtotal_row(supplier, cg))
    _accumulate(g, cg)


def _apply_unapplied_to_cg(cg, amount):
    """Net an unapplied amount into the supplier/customer accumulator."""
    amount = flt(amount, 2)
    if abs(amount) < 0.01:
        return
    if amount > 0:
        # Supplier advance: reduces payable, shown in 0-30 bucket
        cg["paid"] += amount
        cg["outstanding"] -= amount
        cg["buckets"][0] -= amount
    else:
        # Debit note: reduces payable, shown in Above 90 bucket
        cg["credit_note"] += amount
        cg["outstanding"] += amount
        cg["buckets"][3] += amount


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
    if group_key == "supplier":
        name = frappe.db.get_value("Supplier", gv, "supplier_name") or gv
        return "{0} - {1}".format(gv, name)
    if group_key == "division":
        return gv or "Unassigned"
    return gv


def _detail_row(inv, age, buckets):
    return [
        inv.get("posting_date").strftime("%d-%m-%Y") if hasattr(inv.get("posting_date"), "strftime") else inv.get("posting_date"),
        inv.get("name", ""),
        "{0} - {1}".format(inv.get("supplier", ""), inv.get("supplier_name", "")),
        inv.get("division") or "",
        flt(inv["base_grand_total"], 2),
        flt(inv["paid_amount"], 2),
        flt(inv["credit_note_amt"], 2),
        flt(inv["outstanding"], 2),
        age,
    ] + [flt(b, 2) for b in buckets]


def _supplier_subtotal_row(supplier, cg):
    name = frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier
    return [
        "Supplier Subtotal: {0} - {1}".format(supplier, name),
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


def _net_payables_row(g):
    return [
        "NET PAYABLES", "", "", "",
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
    """Single line per supplier showing total of unapplied payments/credits.
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
    """Row showing unapplied supplier advances (positive, in 0-30 bucket)."""
    amt = flt(amount, 2)
    buckets = [0] * len(AGING_BUCKETS)
    buckets[0] = amt
    return [
        "Unapplied advances", "", "", "",
        0, 0, 0,
        amt,
        "",
    ] + [flt(b, 2) for b in buckets]


def _unapplied_debit_notes_row(amount):
    """Row showing unapplied debit notes (negative, in Above 90 bucket)."""
    amt = flt(amount, 2)
    buckets = [0] * len(AGING_BUCKETS)
    buckets[3] = amt
    return [
        "Unapplied debit notes", "", "", "",
        0, 0, 0,
        amt,
        "",
    ] + [flt(b, 2) for b in buckets]


def _net_payables_supplier_row(outstanding, buckets):
    """Net payables row shown below a supplier's unapplied rows."""
    return [
        "NET PAYABLES", "", "", "",
        0, 0, 0,
        flt(outstanding, 2),
        "",
    ] + [flt(b, 2) for b in buckets]


def _get_unapplied(company, as_of, entity_list=None, group_key="supplier", purchase_type=None):
    """Fetch unapplied supplier payments (advances) and standalone debit notes
    with no invoice linkage, posted on or before as_of_date, optionally filtered
    by the same entity selection used for invoices."""
    items = []
    allowed = set(entity_list or [])
    filter_by_supplier = group_key == "supplier" and allowed

    # Build supplier filter SQL for Payment Entry and Debit Notes
    def _in_clause(values):
        return " AND pe.party IN ({0})".format(", ".join(["%s"] * len(values))) if values else ""

    def _in_clause_cn(values):
        return " AND supplier IN ({0})".format(", ".join(["%s"] * len(values))) if values else ""

    pe_sql = """
        SELECT pe.name, pe.posting_date, pe.party, pe.paid_amount,
               pe.unallocated_amount
        FROM `tabPayment Entry` pe
        WHERE pe.company = %s AND pe.docstatus = 1
          AND pe.payment_type = 'Pay'
          AND pe.party_type = 'Supplier'
          AND pe.posting_date <= %s
          AND pe.unallocated_amount > 0.01
    """
    pe_params = [company, as_of]
    if filter_by_supplier:
        pe_sql += _in_clause(list(allowed))
        pe_params.extend(list(allowed))

    pe_rows = frappe.db.sql(pe_sql, tuple(pe_params), as_dict=True)

    for pe in pe_rows:
        supp_name = (frappe.db.get_value("Supplier", pe["party"], "supplier_name") or pe["party"] or "").strip()
        party = (pe["party"] or "").strip()
        items.append({
            "date": pe["posting_date"].strftime("%d-%m-%Y") if hasattr(pe["posting_date"], "strftime") else pe["posting_date"],
            "voucher": pe["name"],
            "supplier": party,
            "party": "{0} - {1}".format(party, supp_name),
            "amount": flt(pe["unallocated_amount"], 2),
        })

    # Standalone debit notes not already counted as invoice-linked
    cn_sql = """
        SELECT name, posting_date, supplier, base_grand_total
        FROM `tabPurchase Invoice`
        WHERE company = %s AND docstatus = 1 AND is_return = 1
          AND posting_date <= %s
          AND (return_against IS NULL OR return_against = '')
        {pt_filter}
    """.format(
        pt_filter=_purchase_type_filter_debit_note(purchase_type)
    )
    cn_params = [company, as_of]
    if purchase_type:
        cn_params.append(purchase_type)
    if filter_by_supplier:
        cn_sql += _in_clause_cn(list(allowed))
        cn_params.extend(list(allowed))

    cn_rows = frappe.db.sql(cn_sql, tuple(cn_params), as_dict=True)

    for cn in cn_rows:
        # Subtract any payments allocated to this debit note
        paid = _calc_paid(cn, company, as_of)
        outstanding = (cn["base_grand_total"] or 0) - paid
        if abs(outstanding) > 0.01:
            supp = (cn["supplier"] or "").strip()
            supp_name = (frappe.db.get_value("Supplier", supp, "supplier_name") or supp).strip()
            items.append({
                "date": cn["posting_date"].strftime("%d-%m-%Y") if hasattr(cn["posting_date"], "strftime") else cn["posting_date"],
                "voucher": cn["name"],
                "supplier": supp,
                "party": "{0} - {1}".format(supp, supp_name),
                "amount": flt(outstanding, 2),  # negative (debit note)
            })

    return items


def _unapplied_by_supplier(unapplied):
    """Return a dict of supplier code -> {party, advances, credits, items}."""
    by_supp = {}
    for item in unapplied:
        supp = (item.get("supplier") or "").strip()
        if not supp:
            continue
        if supp not in by_supp:
            by_supp[supp] = {
                "party": item.get("party") or supp,
                "advances": 0.0,
                "credits": 0.0,
                "items": [],
            }
        by_supp[supp]["items"].append(item)
        amt = flt(item["amount"], 2)
        if amt > 0:
            by_supp[supp]["advances"] += amt
        elif amt < 0:
            by_supp[supp]["credits"] += amt
    return by_supp


def _calc_group_summary(gv, items, unapplied_by_supplier, group_key, aging_method, as_of):
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
    if group_key == "supplier":
        ua = unapplied_by_supplier.get(gv)
    else:
        suppliers = {inv.get("supplier") for inv in items if inv.get("supplier")}
        ua = {"advances": 0.0, "credits": 0.0}
        for s in suppliers:
            supp_ua = unapplied_by_supplier.get(s)
            if supp_ua:
                ua["advances"] += supp_ua["advances"]
                ua["credits"] += supp_ua["credits"]
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


def _summary_row(gv, group_key, net):
    """Return a single summary row for the group."""
    if group_key == "supplier":
        name = frappe.db.get_value("Supplier", gv, "supplier_name") or gv
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
