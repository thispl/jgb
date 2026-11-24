# Copyright (c) 2026, JGB and contributors

import frappe
from frappe.model.document import Document
from jgb.jgb.page.accounts_payable_.accounts_payable_aging import (
    _text_col_count,
    download_excel as page_download_excel,
    get_report_data
)


class AccountsPayableDashboard(Document):
    pass


@frappe.whitelist(allow_guest=False)
def download_excel():
    """Generate and download Excel from query parameters."""
    args = _args_from_request()
    if not args.get("company"):
        frappe.throw("Kindly choose the company.")
    page_download_excel(**args)


@frappe.whitelist(allow_guest=False)
def download_pdf():
    """Generate and download PDF from query parameters."""
    args = _args_from_request()
    if not args.get("company"):
        frappe.throw("Kindly choose the company.")
    _build_pdf(args)


@frappe.whitelist(allow_guest=False)
def print_report():
    """Return printable HTML from query parameters."""
    args = _args_from_request()
    if not args.get("company"):
        frappe.throw("Kindly choose the company.")
    return _build_html(args)


@frappe.whitelist(allow_guest=False)
def sync_ap_print_formats():
    """Create or update AP print formats from the app JSON files without running migrate."""
    import os
    import json as _json

    formats = [
        "ap_supplier_wise_aging",
        "ap_division_wise_aging",
    ]

    base = frappe.get_app_path("jgb", "jgb", "print_format")

    synced_names = []
    for fmt in formats:
        json_path = os.path.join(base, fmt, f"{fmt}.json")
        if not os.path.exists(json_path):
            frappe.msgprint(f"Print format JSON not found: {json_path}")
            continue

        with open(json_path, "r") as f:
            data = _json.load(f)

        # Remove keys that Frappe sets automatically
        for k in ["doctype", "creation", "modified", "modified_by", "owner", "docstatus", "idx"]:
            data.pop(k, None)

        name = data.get("name")
        if not name:
            continue

        if frappe.db.exists("Print Format", name):
            pf = frappe.get_doc("Print Format", name)
            for k, v in data.items():
                if k not in ("name", "doctype"):
                    pf.set(k, v)
            pf.save(ignore_permissions=True)
        else:
            pf = frappe.new_doc("Print Format")
            pf.name = name
            for k, v in data.items():
                if k not in ("name", "doctype"):
                    pf.set(k, v)
            pf.insert(ignore_permissions=True, ignore_mandatory=True)

        synced_names.append(name)

    return {"status": "ok", "synced": synced_names}


def _args_from_request():
    """Map the DocType fields to the existing aging report backend."""
    form = frappe.form_dict

    grouping = form.get("primary_grouping") or "Supplier Wise"
    view_type = form.get("report_view_type") or "Summary"
    aging_method = form.get("aging_method__basis") or "Due Date"

    entity = ""
    if grouping == "Division Wise":
        entity = form.get("division") or ""
    else:
        # Supplier / Vendor / Customer-style groupings all use the supplier field
        entity = form.get("supplier") or form.get("vendor") or ""

    return {
        "company": form.get("company"),
        "view_type": view_type,
        "grouping": grouping,
        "entities": [entity] if entity else [],
        "as_of_date": form.get("as_of_date") or frappe.utils.today(),
        "aging_method": aging_method,
        "show_unapplied": int(form.get("show_unapplied_payments_and_credits_as_separate_line") or 0),
        "purchase_type": form.get("purchase_type") or "",
        "currency": form.get("currency") or "",
    }


def _build_pdf(args):
    """Build PDF and send as binary response."""
    html = _build_html(args)
    from frappe.utils.pdf import get_pdf
    pdf = get_pdf(html)
    frappe.response["filename"] = "Accounts Payable Dashboard.pdf"
    frappe.response["filecontent"] = pdf
    frappe.response["type"] = "binary"


def _ap_widths(headers):
    """Return print-friendly column widths for the aging report."""
    if len(headers) == 13:
        return ["7%", "10%", "11%", "7%", "7%", "7%", "7%", "7%", "4%", "7%", "7%", "7%", "7%"]
    if len(headers) == 10:
        return ["18%", "10%", "10%", "10%", "10%", "6%", "9%", "9%", "9%", "9%"]
    return ["8%"] * len(headers)


@frappe.whitelist()
def ap_dashboard_table(doc, grouping=None):
    """Jinja helper for print formats. Builds the aging table from the dashboard doc."""
    import json
    if isinstance(doc, str):
        doc = frappe._dict(json.loads(doc))
    if not doc.get("company"):
        frappe.throw("Kindly choose company")

    from jgb.jgb.doctype.accounts_report_dashboard.print_format_helpers import build_table_html

    g = grouping or doc.get("primary_grouping") or "Supplier Wise"
    entity = ""
    if g == "Division Wise":
        entity = doc.get("division") or ""
    else:
        # Supplier / Vendor / Customer-style groupings all use the supplier field
        entity = doc.get("supplier") or ""

    args = {
        "company": doc.get("company"),
        "view_type": doc.get("report_view_type") or "Summary",
        "grouping": g,
        "entities": [entity] if entity else [],
        "as_of_date": doc.get("as_of_date") or frappe.utils.today(),
        "aging_method": doc.get("aging_method__basis") or "Due Date",
        "show_unapplied": int(doc.get("show_unapplied_payments_and_credits_as_separate_line") or 0),
        "purchase_type": doc.get("purchase_type") or "",
        "currency": doc.get("currency") or "",
    }

    result = get_report_data(**args)
    columns = result["columns"]
    rows = result["rows"]
    headers = [c["label"] for c in columns]

    ap_widths = _ap_widths(headers)
    text_cols = _text_col_count(columns)

    return build_table_html(
        headers=headers,
        widths=ap_widths,
        data_rows=rows,
        text_cols=text_cols,
        total_cols=text_cols,
        salesperson_prefix="GROUP:",
        subtotal_prefix="Subtotal:",
        customer_subtotal_prefix="Supplier Subtotal:"
    )


@frappe.whitelist(allow_guest=False)
def download_ap_dashboard_pdf():
    """Generate PDF from the saved dashboard using the selected print format."""
    from frappe.utils.print_utils import get_print
    from frappe.utils.pdf import get_pdf

    doctype = "Accounts Payable Dashboard"
    name = "Accounts Payable Dashboard"
    doc = frappe.get_doc(doctype, name)

    if not doc.company:
        frappe.throw("Kindly choose the company.")

    fmt_map = {
        "Supplier Wise": "AP Supplier Wise Aging",
        "Division Wise": "AP Division Wise Aging",
    }
    print_format = fmt_map.get(doc.primary_grouping, "AP Supplier Wise Aging")

    html = get_print(
        doctype,
        name,
        print_format,
        doc=doc,
        as_pdf=False,
        no_letterhead=1,
    )

    pdf = get_pdf(html, {"orientation": "Landscape"})
    frappe.response["filename"] = f"{doc.company} - {print_format}.pdf"
    frappe.response["filecontent"] = pdf
    frappe.response["type"] = "binary"


def _build_html(args):
    """Build a printable HTML report."""
    from jgb.jgb.doctype.accounts_report_dashboard.print_format_helpers import build_table_html

    result = get_report_data(**args)
    columns = result["columns"]
    rows = result["rows"]
    headers = [c["label"] for c in columns]

    title_html = """
    <div style="text-align:center; margin-bottom:10px;">
        <h3 style="margin:0; color:#1F3864;">{company}</h3>
        <h4 style="margin:4px 0; color:#1F3864;">Accounts Payable Dashboard</h4>
        <div style="font-size:12px; color:#404040;">
            As-of Date: {as_of} &nbsp;|&nbsp; Report Date: {report_date} &nbsp;|&nbsp; Currency: {currency}
        </div>
    </div>
    """.format(
        company=frappe.utils.escape_html(result.get("company", "")),
        as_of=frappe.utils.escape_html(result.get("as_of_date", "")),
        report_date=frappe.utils.escape_html(result.get("report_date", "")),
        currency=frappe.utils.escape_html(result.get("currency", "")),
    )

    text_cols = _text_col_count(columns)
    table = build_table_html(
        headers=headers,
        widths=_ap_widths(headers),
        data_rows=rows,
        text_cols=text_cols,
        total_cols=text_cols,
        salesperson_prefix="GROUP:",
        subtotal_prefix="Subtotal:",
        customer_subtotal_prefix="Supplier Subtotal:"
    )

    return """
    <html>
    <head><title>Accounts Payable Dashboard</title></head>
    <body style="font-family:Calibri,Arial,sans-serif; font-size:10px;">
        {title}
        {table}
    </body>
    </html>
    """.format(title=title_html, table=table)
