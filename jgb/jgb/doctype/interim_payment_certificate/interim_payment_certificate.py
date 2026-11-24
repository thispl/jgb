# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils.csvutils import read_csv_content
from frappe.utils import get_first_day, get_last_day, format_datetime, get_url_to_form
from frappe.utils import cint
from frappe.utils.data import date_diff, now_datetime, nowdate, today, add_days
import datetime
from frappe.utils import money_in_words
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate
from frappe import throw, msgprint
from frappe.model.naming import make_autoname
from frappe import throw, _
from datetime import date, timedelta
import frappe
from frappe.utils import add_months, nowdate, getdate
from frappe.utils import flt, fmt_money
import json
from erpnext.setup.utils import get_exchange_rate
import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry



class InterimPaymentCertificate(Document):
    def on_submit(self):

        # -----------------------------------------
        # 1️⃣ COLLECT IPC QTY PER SOURCE ROW
        # -----------------------------------------
        so_qty_map = {}
        dn_qty_map = {}

        for i in self.items:
            if i.delivery_note and i.dn_row:
                key = i.dn_row
                dn_qty_map[key] = dn_qty_map.get(key, 0) + i.qty

            elif i.so and i.so_row:
                key = i.so_row
                so_qty_map[key] = so_qty_map.get(key, 0) + i.qty

        # -----------------------------------------
        # 2️⃣ UPDATE DELIVERY NOTE ITEMS
        # -----------------------------------------
        for dn_row, ipc_qty in dn_qty_map.items():

            current_ipc_qty = frappe.db.get_value(
                "Delivery Note Item",
                dn_row,
                "custom_ipc_qty"
            ) or 0

            frappe.db.set_value(
                "Delivery Note Item",
                dn_row,
                "custom_ipc_qty",
                current_ipc_qty + ipc_qty
            )

        # -----------------------------------------
        # 3️⃣ UPDATE SALES ORDER ITEMS
        # -----------------------------------------
        for so_row, ipc_qty in so_qty_map.items():

            current_ipc_qty = frappe.db.get_value(
                "Sales Order Item",
                so_row,
                "custom_ipc_qty"
            ) or 0

            frappe.db.set_value(
                "Sales Order Item",
                so_row,
                "custom_ipc_qty",
                current_ipc_qty + ipc_qty
            )

                    
        
    def before_submit(self):
        if not self.amended_from:
            ipc_count = frappe.db.count(
                "Interim Payment Certificate",
                filters={
                    "sales_order": self.sales_order,
                    "docstatus": 1
                }
            )

            # Next IPC number
            self.ipc = ipc_count + 1

        

    def on_cancel(self):

        # -----------------------------------------
        # 1️⃣ COLLECT IPC QTY PER SOURCE ROW
        # -----------------------------------------
        so_qty_map = {}
        dn_qty_map = {}

        for i in self.items:
            if i.delivery_note and i.dn_row:
                dn_qty_map[i.dn_row] = dn_qty_map.get(i.dn_row, 0) + i.qty

            elif i.so and i.so_row:
                so_qty_map[i.so_row] = so_qty_map.get(i.so_row, 0) + i.qty

        # -----------------------------------------
        # 2️⃣ REVERT DELIVERY NOTE ITEM IPC QTY
        # -----------------------------------------
        for dn_row, ipc_qty in dn_qty_map.items():

            current_ipc_qty = frappe.db.get_value(
                "Delivery Note Item",
                dn_row,
                "custom_ipc_qty"
            ) or 0

            new_qty = current_ipc_qty - ipc_qty
            if new_qty < 0:
                new_qty = 0

            frappe.db.set_value(
                "Delivery Note Item",
                dn_row,
                "custom_ipc_qty",
                new_qty
            )

        # -----------------------------------------
        # 3️⃣ REVERT SALES ORDER ITEM IPC QTY
        # -----------------------------------------
        for so_row, ipc_qty in so_qty_map.items():

            current_ipc_qty = frappe.db.get_value(
                "Sales Order Item",
                so_row,
                "custom_ipc_qty"
            ) or 0

            new_qty = current_ipc_qty - ipc_qty
            if new_qty < 0:
                new_qty = 0

            frappe.db.set_value(
                "Sales Order Item",
                so_row,
                "custom_ipc_qty",
                new_qty
            )

                    
@frappe.whitelist()
def update_ipc_values(source_name, target_doc=None, args=None):

    def postprocess(source, target):
        target.custom = source.customer
        target.customer_name = source.customer_name
        target.delivery_note = source.name
        target.project = source.project
        target.date_issued = source.posting_date
        target.lpo_no = source.po_no

        so = None
        if source.items and source.items[0].against_sales_order:
            so = frappe.db.get_value(
                "Sales Order",
                source.items[0].against_sales_order,
                ["transaction_date", "grand_total", "custom_title_of_project"],
                as_dict=True
            )

        if so:
            target.sales_order = source.items[0].against_sales_order
            target.so_date = so.transaction_date
            target.so_value = so.grand_total
            target.project_name = so.custom_title_of_project

        for s_item, t_item in zip(source.items, target.items):
            ipc_qty = s_item.custom_ipc_qty or 0
            t_item.qty = max(0, s_item.qty - ipc_qty)
            t_item.amount = t_item.qty * t_item.rate

    doc = get_mapped_doc(
        "Delivery Note",
        source_name,
        {
            "Delivery Note": {
                "doctype": "Interim Payment Certificate"
            },
            "Delivery Note Item": {
                "doctype": "IPC Item",
                "field_map": {
                    "name": "dn_row",
                    "parent": "delivery_note",
                    "rate": "rate"
                }
            }
        },
        target_doc,
        postprocess
    )

    return doc


@frappe.whitelist()
def make_ipc_values(source_name, target_doc=None, ignore_permissions=False):

    def postprocess(source, target):
        # Header mapping
        target.custom = source.customer
        target.customer_name = source.customer_name
        target.sales_order = source.name
        target.project = source.project
        target.date_issued = source.transaction_date
        target.lpo_no = source.po_no
        target.so_date = source.transaction_date
        target.so_value = source.grand_total
        target.project_name = source.custom_title_of_project

        # Item level balance qty calculation
        for s_item, t_item in zip(source.items, target.items):
            ipc_qty = s_item.custom_ipc_qty or 0
            balance_qty = max(0, s_item.qty - ipc_qty)

            t_item.qty = balance_qty
            t_item.rate = s_item.rate
            t_item.amount = balance_qty * s_item.rate

    doc = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {
                "doctype": "Interim Payment Certificate"
            },
            "Sales Order Item": {
                "doctype": "IPC Item",
                "field_map": {
                    "name": "so_row",
                    "parent": "sales_order",
                    "rate": "rate"
                }
            }
        },
        target_doc,
        postprocess,
        ignore_permissions=ignore_permissions
    )

    return doc

@frappe.whitelist()
def update_ipc_qty_sold(doc,method):
    qty_ipc = 0
    if doc.custom_interim_payment_certificate:
        dn = frappe.get_doc("Interim Payment Certificate", doc.custom_interim_payment_certificate)
        for d in dn.items:
            for i in doc.items:
                if d.item_code == i.item_code and d.name == i.custom_ipc_details:
                    qty_ipc += i.qty
                    qty = qty_ipc + d.inv_qty 
                frappe.db.set_value("IPC Item", d.name, "inv_qty", qty)

@frappe.whitelist()
def reduce_ipc_qty_sold(doc,method):
    qty_ipc = 0
    if doc.custom_interim_payment_certificate:
        dn = frappe.get_doc("Interim Payment Certificate", doc.custom_interim_payment_certificate)
        for d in dn.items:
            for i in doc.items:
                if d.item_code == i.item_code and d.name == i.custom_ipc_details:
                    qty_ipc += i.qty
                    qty = qty_ipc - d.inv_qty
                frappe.db.set_value("IPC Item", d.name, "inv_qty", qty)
                
                
@frappe.whitelist()
def update_status():
    frappe.db.set_value("Interim Payment Certificate","IPC-000055","docstatus","1")

