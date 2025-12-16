# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
import frappe
from frappe.model.document import Document
from csv import writer
from inspect import getfile
from unicodedata import name
import frappe
from frappe.utils import cstr, add_days, date_diff, getdate
from frappe import _
from frappe.utils.csvutils import UnicodeWriter, read_csv_content
from frappe.utils.file_manager import get_file, upload
from frappe.model.document import Document
from datetime import datetime,timedelta,date,time
from frappe.utils import cint,today,flt,date_diff,add_days,add_months,date_diff,getdate,formatdate,cint,cstr
from frappe.utils import  formatdate

class ItemTemplate(Document):
	pass

@frappe.whitelist()
def get_template():
    args = frappe.local.form_dict
    w = UnicodeWriter()
    w = add_header(w, args)

    frappe.response['result'] = cstr(w.getvalue())
    frappe.response['type'] = 'csv'
    frappe.response['doctype'] = "Item"

def add_header(w,args):
    w.writerow(["Item Group","Product","Product Type","Model","Size","Description","UOM","Manufacture","Part No"])
    return w

from jgb.jgb.custom import create_item_series
from jgb.jgb.custom import create_item_name

@frappe.whitelist()
def item_creation(filename):
    filepath = get_file(filename)
    pps = read_csv_content(filepath[1])

    for pp in pps:
        if pp[0] != 'Item Group':
            item_code = create_item_series(pp[0], pp[1])

            if not frappe.db.exists("Item", {'item_code': item_code}):
                add = frappe.new_doc('Item')
                add.item_group = pp[0]
                add.custom_product = pp[1]
                add.item_code = item_code
                add.custom_item = item_code
                add.item_name = f"{pp[2]}-{pp[3]}-{pp[4]}"
                add.description = pp[4]
                add.stock_uom = pp[5]
                add.append("custom_product_naming_parameters", {"title": "Product Type", "value": pp[2]})
                add.append("custom_product_naming_parameters", {"title": "Model", "value": pp[3]})
                add.append("custom_product_naming_parameters", {"title": "Capcity (L)", "value": pp[4]})
                add.save(ignore_permissions=True)
                frappe.db.commit()
            else:
                item_name = frappe.db.get_value("Item", {"item_code": item_code}, "name")
                if not item_name:
                    continue  # or frappe.log_error(...)

                add = frappe.get_doc("Item", item_name)
                add.item_group = pp[0]
                add.custom_product = pp[1]
                add.item_code = item_code
                add.custom_item = item_code
                add.item_name = f"{pp[2]}-{pp[3]}-{pp[4]}"
                add.description = pp[4]
                add.stock_uom = pp[5]
                add.set("custom_product_naming_parameters", [])
                add.append("custom_product_naming_parameters", {"title": "Product Type", "value": pp[2]})
                add.append("custom_product_naming_parameters", {"title": "Model", "value": pp[3]})
                add.append("custom_product_naming_parameters", {"title": "Capcity (L)", "value": pp[4]})
                add.save(ignore_permissions=True)
                frappe.db.commit()

            if pp[7]:
            # Common: Add or update Item Manufacturer
                if not frappe.db.exists("Item Manufacturer", {'item_code': item_code, "manufacturer": pp[7]}):
                    manu = frappe.new_doc('Item Manufacturer')
                    manu.item_code = item_code
                    manu.manufacturer = pp[7]
                    manu.manufacturer_part_no = pp[8]
                    manu.save(ignore_permissions=True)
                    frappe.db.commit()
                else:
                    manu_name = frappe.db.get_value("Item Manufacturer", {'item_code': item_code, "manufacturer": pp[7]}, "name")
                    manu = frappe.get_doc('Item Manufacturer', manu_name)
                    manu.item_code = item_code
                    manu.manufacturer = pp[7]
                    manu.manufacturer_part_no = pp[8]
                    manu.save(ignore_permissions=True)
                    frappe.db.commit()

    return "OK"
