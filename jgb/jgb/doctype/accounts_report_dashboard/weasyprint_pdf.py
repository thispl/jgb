# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# WeasyPrint-based PDF generation for Accounts Report Dashboard print formats.
# WeasyPrint handles CSS (table-layout, percentage widths, flexbox) much better
# than wkhtmltopdf, so all columns render correctly without zoom hacks.

import frappe
from frappe import _
from frappe.utils import format_date


@frappe.whitelist()
def download_pdf_weasyprint():
	"""Generate a PDF using WeasyPrint for the Accounts Report Dashboard.

	Expected params (via frappe.local.form_dict or query string):
		name:           Accounts Report Dashboard document name
		print_format:   Print Format name (e.g. "Accounts Aging Summary Sales Person")
	"""
	from weasyprint import HTML, CSS

	name = frappe.local.form_dict.get("name")
	print_format_name = frappe.local.form_dict.get("print_format")

	if not name:
		frappe.throw(_("Document name is required"))
	if not print_format_name:
		frappe.throw(_("Print Format name is required"))

	doc = frappe.get_doc("Accounts Report Dashboard", name)
	doc.check_permission("print")

	# Get the Print Format record
	pf = frappe.get_doc("Print Format", print_format_name)
	if pf.doc_type != "Accounts Report Dashboard":
		frappe.throw(_("Print Format is not for Accounts Report Dashboard"))

	# Build the HTML by rendering the print format's Jinja template
	# The print format html uses Jinja, so we render it with the doc context
	context = {
		"doc": doc,
		"frappe": frappe,
		"format_date": format_date,
	}

	# Get the print format HTML template
	template_html = pf.html or ""

	# Render the Jinja template
	rendered_html = frappe.render_template(template_html, context)

	# Wrap in a full HTML document with @page CSS for A4 landscape
	full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
	size: A4 landscape;
	margin: 1.5cm 1cm;
}}
body {{
	font-family: 'Calibri', Arial, sans-serif;
	font-size: 10px;
	color: #000;
}}
h4 {{
	text-align: center;
	margin: 4px 0;
}}
img {{
	max-height: 60px;
}}
</style>
</head>
<body>
{rendered_html}
</body>
</html>"""

	# Generate PDF with WeasyPrint
	base_url = frappe.utils.get_url()
	html_obj = HTML(string=full_html, base_url=base_url)
	pdf_bytes = html_obj.write_pdf()

	# Set response
	filename = f"{print_format_name.replace(' ', '-')}.pdf" if print_format_name else f"{name.replace(' ', '-')}.pdf"
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = pdf_bytes
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def generate_pdf(doc_name, print_format_name):
	"""Generate a PDF using WeasyPrint and return the bytes.

	This is a helper function that can be called from other Python code.
	"""
	from weasyprint import HTML

	doc = frappe.get_doc("Accounts Report Dashboard", doc_name)
	pf = frappe.get_doc("Print Format", print_format_name)

	context = {
		"doc": doc,
		"frappe": frappe,
		"format_date": format_date,
	}

	template_html = pf.html or ""
	rendered_html = frappe.render_template(template_html, context)

	full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
	size: A4 landscape;
	margin: 1.5cm 1cm;
}}
body {{
	font-family: 'Calibri', Arial, sans-serif;
	font-size: 10px;
	color: #000;
}}
h4 {{
	text-align: center;
	margin: 4px 0;
}}
img {{
	max-height: 60px;
}}
</style>
</head>
<body>
{rendered_html}
</body>
</html>"""

	base_url = frappe.utils.get_url()
	html_obj = HTML(string=full_html, base_url=base_url)
	return html_obj.write_pdf()
