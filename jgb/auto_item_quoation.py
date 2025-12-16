# import frappe
# from frappe.utils.csvutils import read_csv_content
# from frappe.utils import get_first_day, get_last_day, format_datetime, get_url_to_form
# from frappe.utils import cint
# from frappe.utils.data import date_diff, now_datetime, nowdate, today, add_days
# import datetime
# from frappe import _
# from frappe import _
# from frappe.model.document import Document
# from frappe.utils import getdate, nowdate
# from frappe import throw, msgprint
# from datetime import datetime
# import erpnext
# from frappe.utils import date_diff, add_months, today, add_days, nowdate,formatdate,flt
# from frappe.utils.csvutils import read_csv_content
# from frappe.utils.file_manager import get_file
# import json
# from frappe.model.document import Document
# from frappe.model.rename_doc import rename_doc
# from frappe.model.naming import make_autoname
# from erpnext.setup.utils import get_exchange_rate


# @frappe.whitelist()
# def make_item_sheet():
#     args = frappe.local.form_dict
#     filename = args.name
#     xlsx_file = build_xlsx_response(filename)
#     return xlsx_file


# def build_xlsx_response(filename):
#     xlsx_file = make_xlsx(filename)
#     frappe.response['filename'] = filename + '.xlsx'
#     frappe.response['filecontent'] = xlsx_file.getvalue()
#     frappe.response['type'] = 'binary'
#     frappe.response['content_type'] = (
#         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )


# def make_xlsx(name, sheet_name="Item Details", wb=None, column_widths=None):
#     import openpyxl
#     from io import BytesIO

#     if wb is None:
#         wb = openpyxl.Workbook()
#         ws = wb.active
#         ws.title = sheet_name
#     else:
#         ws = wb.create_sheet(sheet_name, 0)

#     ws.append([
#         "Tag", "Flow", "Ext.sp", "Drive", "KW",
#         "Fan RPM", "Volt", "Model", "Unit Size"
#     ])
#     column_widths = [15, 10, 10, 10, 10, 12, 10, 15, 12]
#     for i, width in enumerate(column_widths, start=1):
#         col_letter = openpyxl.utils.get_column_letter(i)
#         ws.column_dimensions[col_letter].width = width

#     xlsx_file = BytesIO()
#     wb.save(xlsx_file)
#     xlsx_file.seek(0)

#     return xlsx_file