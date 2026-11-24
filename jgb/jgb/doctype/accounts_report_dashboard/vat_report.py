import frappe
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from io import BytesIO
from openpyxl.styles import Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from jgb.jgb.doctype.accounts_report_dashboard.domestic_sales_zero_vat_gl import domestic_sales_zero_vat_gl
from jgb.jgb.doctype.accounts_report_dashboard.domestic_sales_gl import domestic_sales_gl
from jgb.jgb.doctype.accounts_report_dashboard.export_sales_gl import export_sales_gl
from jgb.jgb.doctype.accounts_report_dashboard.domestic_purchase_vat import domestic_purchase_vat
from jgb.jgb.doctype.accounts_report_dashboard.ref_supp_pur import ref_supp_pur
from jgb.jgb.doctype.accounts_report_dashboard.zero_rate_domestic_purchase import zero_rate_domestic_purchase
from jgb.jgb.doctype.accounts_report_dashboard.import_purchase_gl import import_purchase_gl
from jgb.jgb.doctype.accounts_report_dashboard.vat_summary import vat_summary
@frappe.whitelist()
def download_all():
    wb = openpyxl.Workbook()

    wb.remove(wb.active)
    arg1, arg2 = domestic_sales_gl(wb)
    arg3 = domestic_sales_zero_vat_gl(wb)
    arg4 = export_sales_gl(wb)
    arg5, arg6 = domestic_purchase_vat(wb)
    arg7, arg8 = ref_supp_pur(wb)
    arg9 = zero_rate_domestic_purchase(wb)
    arg10 = import_purchase_gl(wb)
    vat_summary(wb,arg1, arg2,arg3,arg4,arg5, arg6,arg7, arg8,arg9,arg10)

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    xlsx_file.seek(0)

    frappe.response["filename"] = "VAT_Reports.xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"] = "binary"
