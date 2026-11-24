# Copyright (c) 2026, JGB and contributors

import frappe
from frappe.model.document import Document
from jgb.jgb.page.accounts_receivable_.accounts_receivable_aging import (
    _text_col_count,
    download_excel as page_download_excel,
    get_report_data
)


class AccountsReceivableAgingReport(Document):
    pass


@frappe.whitelist(allow_guest=False)
def download_report():
    """Download Excel/PDF report from query params or saved DocType values."""
    args = _args_from_request()

    if not args.get("company"):
        frappe.throw("Kindly choose the company.")

    if args.get("export_format") == "PDF":
        _build_pdf(args)
    else:
        page_download_excel(**args)


@frappe.whitelist(allow_guest=False)
def print_report():
    """Return printable HTML report from query params or saved DocType values."""
    args = _args_from_request()

    if not args.get("company"):
        frappe.throw("Kindly choose the company.")

    return _build_html(args)


def _args_from_request():
    """Read filter values from GET/POST query parameters, fallback to saved DocType."""
    form = frappe.form_dict

    # If parameters are passed in URL, use them; otherwise read the saved single DocType
    if form.get("company"):
        return {
            "company": form.get("company"),
            "view_type": form.get("view_type") or "Summary",
            "grouping": form.get("grouping") or "Customer Wise",
            "entities": _parse_entities(form.get("entities")),
            "as_of_date": form.get("as_of_date") or frappe.utils.today(),
            "aging_method": form.get("aging_method") or "Due Date",
            "show_unapplied": int(form.get("show_unapplied") or 0),
            "export_format": form.get("export_format") or "Excel",
        }

    doc = frappe.get_doc("Accounts Receivable Aging Report")
    return _args_from_doc(doc)


def _args_from_doc(doc):
    entities = []
    if doc.grouping == "Customer Wise" and doc.customer:
        entities = [doc.customer]
    elif doc.grouping == "Salesperson Wise" and doc.sales_person:
        entities = [doc.sales_person]
    elif doc.grouping == "Division Wise" and doc.division:
        entities = [doc.division]
    elif doc.grouping == "Region Wise" and doc.region:
        entities = [doc.region]

    return {
        "company": doc.company,
        "view_type": doc.view_type,
        "grouping": doc.grouping,
        "entities": entities,
        "as_of_date": doc.as_of_date,
        "aging_method": doc.aging_method,
        "show_unapplied": doc.show_unapplied,
        "export_format": doc.export_format,
    }


def _parse_entities(entities):
    import json
    if not entities:
        return []
    try:
        parsed = json.loads(entities)
        if isinstance(parsed, list):
            return parsed
    except (ValueError, TypeError):
        pass
    return [e.strip() for e in str(entities).split(",") if e.strip()]


def _build_pdf(args):
    """Build PDF and send as binary response."""
    html = _build_html(args)
    from frappe.utils.pdf import get_pdf
    pdf = get_pdf(html)
    frappe.response["filename"] = "Accounts Receivable Aging Report.pdf"
    frappe.response["filecontent"] = pdf
    frappe.response["type"] = "binary"


def _build_html(args):
    """Build a printable HTML report."""
    from jgb.jgb.doctype.accounts_report_dashboard.print_format_helpers import build_table_html

    result = get_report_data(**args)
    columns = result["columns"]
    rows = result["rows"]
    headers = [c["label"] for c in columns]
    text_cols = _text_col_count(columns)
    total_cols = text_cols

    title_html = """
    <div style="text-align:center; margin-bottom:10px;">
        <h3 style="margin:0; color:#1F3864;">{company}</h3>
        <h4 style="margin:4px 0; color:#1F3864;">Accounts Receivable Aging Report</h4>
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

    table = build_table_html(
        headers=headers,
        widths=["8%"] * len(headers),
        data_rows=rows,
        text_cols=text_cols,
        total_cols=total_cols,
        salesperson_prefix="GROUP:",
        subtotal_prefix="Subtotal:"
    )

    return """
    <html>
    <head><title>Accounts Receivable Aging Report</title></head>
    <body style="font-family:Calibri,Arial,sans-serif; font-size:10px;">
        {title}
        {table}
    </body>
    </html>
    """.format(title=title_html, table=table)
