# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# Shared helpers for Accounts Report Dashboard print format (PDF/HTML) generation.
# Uses INLINE styles (not CSS classes) for maximum wkhtmltopdf compatibility.

import html as _html


def fmt_currency(val):
	"""Format a number with thousands separator and 2 decimals."""
	try:
		num = float(val)
		return f"{num:,.2f}"
	except (ValueError, TypeError):
		return str(val)


def esc(val):
	"""HTML-escape a value safely."""
	return _html.escape(str(val)) if val is not None else ""


# ---------------------------------------------------------------------------
# Inline style constants (wkhtmltopdf renders inline styles reliably)
# ---------------------------------------------------------------------------
STYLE_TABLE = (
	"width:100%; border-collapse:collapse; font-family:'Calibri',Arial,sans-serif; "
	"font-size:8px; table-layout:fixed;"
)
STYLE_TH = (
	"background:#1F3864; color:#FFFFFF; font-weight:bold; text-align:center; "
	"padding:4px 1px; border:1px solid #1F3864; font-size:8px; "
	"word-wrap:break-word; overflow-wrap:break-word;"
)
STYLE_TD = (
	"padding:2px 1px; border:1px solid #D0D0D0; "
	"word-wrap:break-word; overflow-wrap:break-word;"
)
STYLE_TD_LEFT = STYLE_TD + " text-align:left;"
STYLE_TD_RIGHT = STYLE_TD + " text-align:right; font-variant-numeric:tabular-nums;"
STYLE_TD_CENTER = STYLE_TD + " text-align:center;"

# Row-type styles (applied to <tr>)
STYLE_ROW_ALT = "background:#F7F9FC;"
STYLE_ROW_SALESPERSON = "background:#4472C4;"
STYLE_ROW_SUBTOTAL = "background:#D9E1F2;"
STYLE_ROW_GRAND_TOTAL = "background:#1F3864;"

# Cell styles for special rows
STYLE_TD_SALESPERSON = (
	"background:#4472C4; color:#FFFFFF; font-weight:bold; font-size:10px; "
	"text-align:center; padding:6px; border:1px solid #4472C4;"
)
STYLE_TD_CUSTOMER_SUBTOTAL = (
	"background:#E9EEF7; color:#1F3864; font-weight:bold; font-size:7px; "
	"padding:2px 1px; border:1px solid #B4C6E7;"
)
STYLE_TD_CUSTOMER_SUBTOTAL_LEFT = STYLE_TD_CUSTOMER_SUBTOTAL + " text-align:left;"
STYLE_TD_CUSTOMER_SUBTOTAL_RIGHT = STYLE_TD_CUSTOMER_SUBTOTAL + " text-align:right; font-variant-numeric:tabular-nums;"
STYLE_TD_SUBTOTAL = (
	"background:#D9E1F2; color:#1F3864; font-weight:bold; font-size:8px; "
	"padding:2px 1px; border:1px solid #D0D0D0;"
)
STYLE_TD_SUBTOTAL_LEFT = STYLE_TD_SUBTOTAL + " text-align:left;"
STYLE_TD_SUBTOTAL_RIGHT = STYLE_TD_SUBTOTAL + " text-align:right; font-variant-numeric:tabular-nums;"

STYLE_TD_GRAND_TOTAL = (
	"background:#1F3864; color:#FFFFFF; font-weight:bold; font-size:9px; "
	"padding:2px 1px; border:1px solid #1F3864;"
)
STYLE_TD_GRAND_TOTAL_LEFT = STYLE_TD_GRAND_TOTAL + " text-align:left;"
STYLE_TD_GRAND_TOTAL_RIGHT = STYLE_TD_GRAND_TOTAL + " text-align:right; font-variant-numeric:tabular-nums;"


def build_table_html(headers, widths, data_rows, text_cols, total_cols,
                     salesperson_prefix="SALESPERSON:", subtotal_prefix="Subtotal:",
                     customer_subtotal_prefix="Customer Subtotal:",
                     net_receivables_label="NET RECEIVABLES",
                     grand_total_label="GRAND TOTAL"):
	"""Build a complete HTML table with inline styles for wkhtmltopdf.

	headers:        list of header labels
	widths:         list of CSS width strings (e.g. "7%")
	data_rows:      list of row lists
	text_cols:      number of leading text columns (left-aligned)
	total_cols:     number of leading columns to merge for subtotal/grand-total rows
	"""
	num_cols = len(headers)
	html_output = f"<table style='{STYLE_TABLE}'>"

	# --- Header row ---
	html_output += "<thead><tr>"
	for i, head in enumerate(headers):
		html_output += f"<th style='{STYLE_TH} width:{widths[i]};'>{esc(head)}</th>"
	html_output += "</tr></thead><tbody>"

	# --- Data rows ---
	alt_row = False
	for row in data_rows:
		if not row:
			continue

		row_str = str(row[0]) if len(row) > 0 else ""

		# Sales Person heading row
		if row_str.startswith(salesperson_prefix):
			label = row_str.replace(salesperson_prefix, "").strip()
			html_output += (
				f"<tr>"
				f"<td colspan='{num_cols}' style='{STYLE_TD_SALESPERSON}'>{esc(label)}</td>"
				f"</tr>"
			)
			alt_row = False
			continue

		# Grand Total row
		if row_str == grand_total_label:
			html_output += f"<tr>"
			html_output += f"<td colspan='{total_cols}' style='{STYLE_TD_GRAND_TOTAL_LEFT}'>{esc(row_str)}</td>"
			for cell in row[total_cols:]:
				html_output += f"<td style='{STYLE_TD_GRAND_TOTAL_RIGHT}'>{esc(fmt_currency(cell))}</td>"
			html_output += "</tr>"
			alt_row = False
			continue

		# Customer Subtotal row - lighter blue
		if row_str.startswith(customer_subtotal_prefix):
			html_output += f"<tr>"
			html_output += f"<td colspan='{total_cols}' style='{STYLE_TD_CUSTOMER_SUBTOTAL_LEFT}'>{esc(row_str)}</td>"
			for cell in row[total_cols:]:
				html_output += f"<td style='{STYLE_TD_CUSTOMER_SUBTOTAL_RIGHT}'>{esc(fmt_currency(cell))}</td>"
			html_output += "</tr>"
			alt_row = False
			continue

		# Unapplied payments & credits row - lighter blue (same as customer subtotal)
		if row_str.startswith("Unapplied"):
			html_output += f"<tr>"
			html_output += f"<td colspan='{total_cols}' style='{STYLE_TD_CUSTOMER_SUBTOTAL_LEFT}'>{esc(row_str)}</td>"
			for cell in row[total_cols:]:
				html_output += f"<td style='{STYLE_TD_CUSTOMER_SUBTOTAL_RIGHT}'>{esc(fmt_currency(cell))}</td>"
			html_output += "</tr>"
			alt_row = False
			continue

		# Subtotal / net receivables row - medium blue
		if row_str.startswith(subtotal_prefix) or row_str == net_receivables_label:
			html_output += f"<tr>"
			html_output += f"<td colspan='{total_cols}' style='{STYLE_TD_SUBTOTAL_LEFT}'>{esc(row_str)}</td>"
			for cell in row[total_cols:]:
				html_output += f"<td style='{STYLE_TD_SUBTOTAL_RIGHT}'>{esc(fmt_currency(cell))}</td>"
			html_output += "</tr>"
			alt_row = False
			continue

		# Regular data row
		row_style = f" style='{STYLE_ROW_ALT}'" if alt_row else ""
		html_output += f"<tr{row_style}>"
		for i, cell in enumerate(row):
			if i < text_cols:
				html_output += f"<td style='{STYLE_TD_LEFT}'>{esc(cell)}</td>"
			else:
				html_output += f"<td style='{STYLE_TD_RIGHT}'>{esc(fmt_currency(cell))}</td>"
		html_output += "</tr>"
		alt_row = not alt_row

	html_output += "</tbody></table>"
	return html_output
