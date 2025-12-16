# Copyright (c) 2025, TEAMPRO and contributors
# For license information, please see license.txt

import frappe
from frappe import throw, _, scrub
from frappe.model.document import Document
from erpnext.setup.utils import get_exchange_rate
from frappe.utils import get_url_to_form, today, add_days, nowdate, flt, getdate
from frappe.core.api.file import zip_files
import json
from frappe.model.mapper import get_mapped_doc
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

class LogisticsRequest(Document):   
    def after_insert(self):
        if self.inventory_destination == "Warehouse Bonded" and not self.warehouse:
                warehouse = frappe.db.get_value("Warehouse", {
                    "company": self.company,
                    "is_group": 0,
                    "warehouse_name": ["like", "%Stores%"]
                }, "name")

                if warehouse:
                    frappe.db.set_value("Logistics Request",self.name,"warehouse",warehouse)
        if self.cargo_type=='Sea':
            title_list=["SAL Charges","Customs","Saber Charges","Customs Clearance FF Charges","BL Exchange","Port Charges - SGB / DP World","Customs Clearance","Freight & Forwarding Charges","Mawani Charges","Delivery Order Charges"]
        elif self.cargo_type=='Air':
            title_list=["SAL Charges","Customs","Saber Charges","Customs Clearance FF Charges","BL Exchange","Port Charges - SGB / DP World","Customs Clearance","Freight & Forwarding Charges","Mawani Charges","Delivery Order Charges"]
        # if self.cargo_type=='Sea':
        #     title_list=["Port / Handling Charges","Delivery Order","Mawani Charges"]
        # elif self.cargo_type=='Air':
        #     title_list=["SAL Charges","Customs","Saber Charges","Customs Clearance","Freight & Forwarding Charges"]
        else:
            # title_list=[]
            title_list=["SAL Charges","Customs","Saber Charges","Customs Clearance FF Charges","BL Exchange","Port Charges - SGB / DP World","Customs Clearance","Freight & Forwarding Charges","Mawani Charges","Delivery Order Charges"]
        if title_list:
            for t in title_list:
                self.append('support_documents', {
                    'document_type': t
                })
    def on_update(self):
        if not self.lr_costing_payment_po:
            return

        for row in self.lr_costing_payment_po:
            if row.purchase_invoice and frappe.db.exists("Purchase Invoice", row.purchase_invoice):
                pi_status = frappe.db.get_value("Purchase Invoice", row.purchase_invoice, "status")
                row.status = pi_status

    def before_insert(self):
        if self.cargo_type=='Sea':
            title_list=["SAL Charges","Customs","Saber Charges","Customs Clearance FF Charges","BL Exchange","Port Charges - SGB / DP World","Customs Clearance","Freight & Forwarding Charges","Mawani Charges","Delivery Order Charges"]
        elif self.cargo_type=='Air':
            title_list=["SAL Charges","Customs","Saber Charges","Customs Clearance FF Charges","BL Exchange","Port Charges - SGB / DP World","Customs Clearance","Freight & Forwarding Charges","Mawani Charges","Delivery Order Charges"]
        # if self.cargo_type=='Sea':
        #     title_list=["Customs","Port / Handling Charges","Delivery Order","Mawani Charges"]
        # elif self.cargo_type=='Air':
        #     title_list=["SAL Charges","Customs","Saber Charges","Customs Clearance","Freight & Forwarding Charges"]
        else:
            title_list=["SAL Charges","Customs","Saber Charges","Customs Clearance FF Charges","BL Exchange","Port Charges - SGB / DP World","Customs Clearance","Freight & Forwarding Charges","Mawani Charges","Delivery Order Charges"]

            # title_list=[]
        if title_list:
            for t in title_list:
                self.append('table_wdql', {
                    'title': t
                })
            for t in title_list:
                self.append('support_documents', {
                    'document_type': t
                })
    def validate(self):
        if self.lr_costing_payment_po:
            for i in self.lr_costing_payment_po:
                if i.purchase_invoice:
                    if frappe.db.exists("Purchase Invoice",i.purchase_invoice):
                        pi=frappe.get_doc("Purchase Invoice",i.purchase_invoice)
                        i.status=pi.status
        if not self.bills:
            if self.bills_copy:
                for i in self.bills_copy:
                    self.append('bills', {
                    'party_name': i.party_name,
                    'bills':i.bills,
                    'amount':i.amount,
                    'advance':i.advance,
                    'outstanding':i.outstanding
                })
        if self.ffw_quotation_vehicle and not self.carried_by:
            for i in self.ffw_quotation_vehicle:
                self.carried_by=i.driver
        self.update_delivery_note_statuses()
        if self.has_value_changed("workflow_state") and self.workflow_state=="Dispatched" and self.logistic_type!= "Local Delivery":
            if not self.etd:
                frappe.throw("Kindly enter ETD  before moving to the next status")
            if not self.eta:
                frappe.throw("Kindly enter ETA  before moving to the next status")
            if not self.master_bl_number__awb:
                frappe.throw("Kindly enter Master BL Number / AWB  before moving to the next status")
        if self.has_value_changed("workflow_state") and self.workflow_state=="Out for Delivery" and self.logistic_type== "Local Delivery":
            if not self.etd:
                frappe.throw("Kindly enter ETD  before moving to the next status")
            if not self.eta:
                frappe.throw("Kindly enter ETA  before moving to the next status")
        if self.workflow_state=="Scheduled":
            self.custom_details=1
        if self.workflow_state=="Dispatched":
            self.custom_schedule=1
        if self.workflow_state=="Out for Delivery" and self.logistic_type == "Local Delivery":
            self.custom_schedule=1
        if self.workflow_state=="Payment":
            self.custom_dispatched=1
        if self.workflow_state=="Out for Delivery" and  self.logistic_type != "Local Delivery":
            self.custom_payment=1
        if self.workflow_state=="Arrived":
            self.custom_arrived=1
        total=0
        tot_box=0
        tot_pallet=0
        tot_box_kg=0
        tot_pallet_kg=0
        tot_cbm=0
        if self.product_description:
            for i in self.product_description:
                if i.net_weight:
                    total+=i.net_weight
                if i.no_of_boxes:
                    tot_box+=i.no_of_boxes
                if i.no_of_pallets:
                    tot_pallet+=i.no_of_pallets
                if i.total_pallet_weight_kg:
                    tot_pallet_kg+=i.total_pallet_weight_kg
                if i.total_box_weight_kg:
                    tot_box_kg+=i.total_box_weight_kg
                if i.cbm:
                    tot_cbm+=i.cbm
                
        self.net_wt=total
        self.box=tot_box
        self.pallet=tot_pallet
        if self.cargo_type=="Sea":
            self.cbm=tot_cbm
        self.gross_wt=tot_box_kg+tot_pallet_kg+self.net_wt
        if self.has_value_changed("workflow_state") and self.workflow_state == "Arrived":
            self.bills=[]
            if self.recommended_ffw:
                self.append("bills",{
                    "party_name":self.recommended_ffw,
                    "amount":self.quoted_amount_sar
                })
            
        if self.has_value_changed("workflow_state") and self.workflow_state == "Closed" and self.logistic_type=='Import':
            if not self.lr_status_details:
                frappe.throw("Kindly create PR before moved to closed.")
            if self.lr_status_details:
                for i in self.lr_status_details:
                    if not i.voucher_type=="Purchase Receipt":
                        frappe.throw("Kindly create PR before moved to closed.")
        if self.has_value_changed("workflow_state") and self.workflow_state == "Out for Delivery" and self.custom_payment_by!="Customer":
            if self.po_so!="Purchase Order":
                for row in self.custom_lr_cost_payment:
                    if not row.attach_payment:
                        frappe.throw("Kindly attach the payment document in all rows before proceeding to 'Out for Delivery'.")
            if self.po_so=="Purchase Order":
                for row in self.lr_costing_payment_po:
                    if not row.attach_payment:
                        frappe.throw("Kindly attach the payment document in all rows before proceeding to 'Out for Delivery'.")
            self.table_gqxd=[]
            if self.ffw_quotation_vehicle:
                for i in self.ffw_quotation_vehicle:
                    self.append("table_gqxd",{
                        "vehicle_number":i.vehicle_number,
                        "driver":i.driver,
                        "driver_contact_number":i.driver_contact_number
                    })
        if self.has_value_changed("workflow_state") and self.workflow_state == "Closed" and self.custom_payment_by!="Customer":
            if self.bills:
                attachments = []
                rows_data = []

                for row in self.bills:
                    if row.bills:
                        attachments.append(row.bills)
                        rows_data.append({
                            "title": row.party_name,
                            "cost": row.amount,
                            "advance": row.advance,
                            "outstanding": row.outstanding,
                            "url": frappe.utils.get_url(row.bills)
                        })

                if attachments:
                    send_accounts_mail_ebill(
                        parent_name=self.name,
                        rows=rows_data
                    )
        if self.workflow_state == "Dispatched" :
            self.set('custom_lr_cost_payment', []) 
            for dis in self.support_documents:
                self.append('custom_lr_cost_payment', {
                    'title': dis.document_type,
                    'cost': dis.cost,
                    # 'attach_challan': dis.attach_challan,
                    'currency': dis.currency,
                    'cost_in_sar': dis.cost_in_sar,
                    "read_only":1

                })
            self.set('lr_costing_payment_po', []) 
            for dis in self.support_documents:
                self.append('lr_costing_payment_po', {
                    'title': dis.document_type,
                    'cost': dis.cost,
                    # 'attach_challan': dis.attach_challan,
                    'currency': dis.currency,
                    'cost_in_sar': dis.cost_in_sar,
                    "read_only":1

                })
        if self.product_description:
            for i in self.product_description:
                if not i.voucher_type and not i.voucher_no:
                    if self.po_so and self.order_no:
                        i.voucher_type = self.po_so
                        i.voucher_no = self.order_no
                        i.requester_name=self.requester_name
                if i.voucher_type in ["Sales Order", "Sales Invoice", "Delivery Note"] and i.voucher_no and not i.customer:
                    try:
                        customer = frappe.db.get_value(i.voucher_type, i.voucher_no, "customer")
                        if customer:
                            i.customer = customer
                    except Exception as e:
                        frappe.log_error(f"Error setting customer from {i.voucher_type} {i.voucher_no}: {e}")
                elif i.voucher_type=="Purchase Order" and not i.supplier and i.voucher_no:
                    supplier = frappe.db.get_value(i.voucher_type, i.voucher_no, "supplier")
                    if supplier:
                        i.supplier = supplier
    # @frappe.whitelist()
    # def update_delivery_note_statuses(self):
    #     status_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}

    #     for row in self.product_description:
    #         delivery_notes = []

    #         if row.voucher_type == "Sales Order":
    #             # Fetch DNs linked to SO
    #             dn_items = frappe.get_all("Delivery Note Item",
    #                 filters={"against_sales_order": row.voucher_no},
    #                 fields=["parent"])
    #             delivery_notes.extend([dn["parent"] for dn in dn_items])

    #         elif row.voucher_type == "Sales Invoice":
    #             # Fetch DNs linked to SI
    #             dn_items = frappe.get_all("Delivery Note Item",
    #                 filters={"against_sales_invoice": row.voucher_no},
    #                 fields=["parent"])
    #             delivery_notes.extend([dn["parent"] for dn in dn_items])

    #         # Loop through found DNs and update lr_status_details
    #         for dn_name in delivery_notes:
    #             dn_doc = frappe.get_doc("Delivery Note", dn_name)
    #             dn_status = status_map.get(dn_doc.docstatus, "Unknown")

    #             # Check if DN is already added
    #             existing = next(
    #                 (d for d in self.lr_status_details
    #                     if d.voucher_type == "Delivery Note" and d.voucher_name == dn_doc.name),
    #                 None
    #             )

    #             if existing:
    #                 existing.status = dn_status
    #             else:
    #                 self.append("lr_status_details", {
    #                     "voucher_type": "Delivery Note",
    #                     "voucher_name": dn_doc.name,
    #                     "status": dn_status
    #                 })
    @frappe.whitelist()
    def update_delivery_note_statuses(self):
        status_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}

        for row in self.product_description:
            delivery_notes = []

            if row.voucher_type == "Sales Order":
                # Fetch DNs linked to SO
                dn_items = frappe.get_all("Delivery Note Item",
                    filters={"against_sales_order": row.voucher_no},
                    fields=["parent"])
                delivery_notes.extend([dn["parent"] for dn in dn_items])

            elif row.voucher_type == "Sales Invoice":
                # Fetch DNs linked to SI
                dn_items = frappe.get_all("Delivery Note Item",
                    filters={"against_sales_invoice": row.voucher_no},
                    fields=["parent"])
                delivery_notes.extend([dn["parent"] for dn in dn_items])

            for dn_name in delivery_notes:
                dn_doc = frappe.get_doc("Delivery Note", dn_name)
                dn_status = status_map.get(dn_doc.docstatus, "Unknown")

                # Find existing DN status in lr_status_details
                existing = next(
                    (d for d in self.lr_status_details
                        if d.voucher_type == "Delivery Note" and d.voucher_name == dn_doc.name),
                    None
                )

                if dn_doc.docstatus == 2:  # Cancelled - remove if exists
                    if existing:
                        self.lr_status_details.remove(existing)
                else:
                    if existing:
                        existing.status = dn_status
                    else:
                        self.append("lr_status_details", {
                            "voucher_type": "Delivery Note",
                            "voucher_name": dn_doc.name,
                            "status": dn_status
                        })


    @frappe.whitelist()
    def compare_po_items(self):
        if self.po_so == 'Purchase Order':
            multiple_pos_list = [po.strip() for po in self.multiple_pos.split(',')] if self.multiple_pos else []
            net_weight = 0
            gross_weight = 0
            for item in self.product_description:
                if multiple_pos_list:
                    actual_qty = frappe.db.get_value('Purchase Order Item',{'parent':('in',multiple_pos_list),'item_code':item.item_code,'material_request':item.material_request},'qty')
                    utilized_qty = frappe.db.sql("""select `tabPurchase Order Item`.qty as qty from `tabLogistics Request`
                    left join `tabPurchase Order Item` on `tabLogistics Request`.name = `tabPurchase Order Item`.parent where `tabPurchase Order Item`.item_code = '%s' and `tabLogistics Request`.name != '%s' and `tabPurchase Order Item`.parent = '%s' and `tabLogistics Request`.docstatus != 2 """%(item.item_code,self.name,item.parent),as_dict=True)
                else:
                    actual_qty = frappe.db.get_value('Purchase Order Item',{'parent':self.order_no,'item_code':item.item_code,'material_request':item.material_request},'qty')
                    utilized_qty = frappe.db.sql("""select `tabPurchase Order Item`.qty as qty from `tabLogistics Request`
                    left join `tabPurchase Order Item` on `tabLogistics Request`.name = `tabPurchase Order Item`.parent where `tabPurchase Order Item`.item_code = '%s' and `tabLogistics Request`.name != '%s' and `tabLogistics Request`.order_no = '%s' and `tabLogistics Request`.docstatus != 2 """%(item.item_code,self.name,self.order_no),as_dict=True)
                
                if not utilized_qty:
                    utilized_qty = 0
                else:
                    utilized_qty = utilized_qty[0].qty
                remaining_qty = int(actual_qty) - utilized_qty
                if item.qty > remaining_qty:
                    msg = """<table class='table table-bordered'><tr><th>Purchase Order Qty</th><td>%s</td></tr>
                    <tr><th>Logistics Request Already raised for</th><td>%s</td></tr>
                    <tr><th>Remaining Qty</th><td>%s</td></tr>
                    </table><p><b>Requesting Qty should not go beyond Remaining Qty</b><p>"""%(actual_qty,utilized_qty,remaining_qty)
                    return msg
            

    

@frappe.whitelist()
def get_supporting_docs(selected_docs):
    selected_docs = json.loads(selected_docs)
    file_list = []
    for s in selected_docs:
        file_name = frappe.get_value("File", {"file_url": s['attach']},"name")
        file_list.append(file_name)
    return file_list

@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None, args=None):
    pos=[]
    if args is None:
        args = {}
    if isinstance(args, str):
        args = json.loads(args)

    def postprocess(source, target_doc):
        
        if frappe.flags.args and frappe.flags.args.default_supplier:
            # items only for given default supplier
            supplier_items = []
            for d in target_doc.items:
                default_supplier = get_item_defaults(d.item_code, target_doc.company).get("default_supplier")
                if frappe.flags.args.default_supplier == default_supplier:
                    supplier_items.append(d)
            target_doc.items = supplier_items
        
        target_doc.logistic_type='Import'
        target_doc.po_so='Purchase Order'
        if target_doc.multiple_pos:
            # If there are already values, append a separator (comma, for example)
            target_doc.multiple_pos += ", " + source.name
        else:
            # If no values, just set it to the first PO name
            target_doc.multiple_pos = source.name

    def select_item(d):
        filtered_items = args.get("filtered_children", [])
        child_filter = d.name in filtered_items if filtered_items else True

        return d.ordered_qty < d.stock_qty and child_filter
    # current_date = datetime.strptime(nowdate(), "%Y-%m-%d").date()
    doclist = get_mapped_doc(
        "Purchase Order",
        source_name,
        {
            "Purchase Order": {
                "doctype": "Purchase Order",
                "validation": {"docstatus": ["=", 1]},
            },
            "Purchase Order Item": {
                "doctype": "Purchase Order Item",
                "field_map": [
                    ["name", "purchase_order_item"],
                    ["parent", "purchase_order"],
                    ["uom", "stock_uom"],
                    ["uom", "uom"],
                    ["sales_order", "sales_order"],
                    ["sales_order_item", "sales_order_item"],
                    ["wip_composite_asset", "wip_composite_asset"],
                    ["material_request", "material_request"],
                    ["material_request_item", "material_request_item"],
                    ['schedule_date','schedule_date']
                ],
                "postprocess": update_item,
                "condition": select_item,
            },
        },
        target_doc,
        postprocess,
    )

    return doclist

def update_item(obj, target, source_parent):
    target.conversion_factor = obj.conversion_factor
    target.qty = flt(flt(obj.stock_qty) - flt(obj.ordered_qty)) / target.conversion_factor
    target.stock_qty = target.qty * target.conversion_factor
    if getdate(target.schedule_date) < getdate(nowdate()):
        target.schedule_date = getdate(nowdate())

@frappe.whitelist()
def set_property():
    make_property_setter('Sales Order Item', 'custom_schedule_button', "in_list_view", 0, "Check")
    # make_property_setter('Purchase Order Item', 'schedule', "in_list_view", 0, "Check")
    # make_property_setter('Purchase Order Item', 'schedule', "columns", 0, "Int")

@frappe.whitelist()
def set_property_so():
    make_property_setter('Sales Order Item', 'custom_schedule_button', "in_list_view", 1, "Check")

@frappe.whitelist()
def get_filtered_ports(doctype, txt, searchfield, start, page_len, filters):
    cargo_type = filters.get('cargo_type', '')
    data = frappe.db.sql("""
        SELECT name FROM `tabPORT`
        WHERE cargo_type LIKE %s
        AND name LIKE %s
        LIMIT %s OFFSET %s
    """, (
        f"%{cargo_type}%",
        f"%{txt}%",
        page_len,
        start
    ))
    return data

@frappe.whitelist()
def get_box_pallet_summary(sales_invoice):
    if frappe.db.exists("Sales Invoice", sales_invoice):
        doc = frappe.get_doc("Sales Invoice", sales_invoice)
        html = """
                <style>
                    th, td {
                        border: 1px solid black;
                        padding-left: 8px;
                        text-align: left;
                        font-size: 12px
                    } 
                </style>
                <p>Summary of Box and Pallet</p>
                <table style="width: 200%; border-collapse: collapse;">
                    <tr>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 20%;">Box Name</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 15%;">Total No. of Boxes</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 15%;">Weight Per Unit (in Kg)</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 15%;">Total Weight (in Kg)</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 10%;">Total Length</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 15%;">Total Breadth</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 10%;">Total Height</td>
                    </tr>
            """
        data = frappe.db.sql("""
            SELECT custom_box as box_name, custom_no_of_boxes as total_no, SUM(custom_weight_per_unit_b) as weight_per_unit, SUM(custom_total_weight_of_boxes) as total_weight,
            SUM(custom_box_length) as blength,  
            SUM(custom_box_height) as bheight,            
            SUM(custom_box_breadth) as bbreadth
            FROM `tabSales Invoice Item`
            WHERE parent = %s
            GROUP BY custom_box
        """, (sales_invoice,), as_dict=True)
        for row in data:
            if row.box_name and row.total_no and row.weight_per_unit and row.total_weight:
                # html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(row.box_name, row.total_no, row.weight_per_unit, row.total_weight)
                # html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(row.box_name, row.total_no, row.weight_per_unit, row.total_weight)
                # html += "<tr><th>Box Name</th><th>Total No. of Boxes</th><th>Weight Per Unit (in Kg)</th><th>Total Weight (in Kg)</th></tr>"
                html += f"""
                            <tr>
                                <td>{row.box_name}</td>
                                <td>{row.total_no}</td>
                                <td>{row.weight_per_unit}</td>
                                <td>{row.total_weight}</td>
                                <td>{row.blength}</td>
                                <td>{row.bbreadth}</td>
                                <td>{row.bheight}</td>
                                
                            </tr>
                        """
        html += "</table>"
        html += """
                <table style="width: 200%; margin-top: 10px; border-collapse: collapse;">
                    <tr>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 20%;">Pallete Name</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 15%;">Total No. of Pallets</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 15%;">Weight Per Unit (in Kg)</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 15%;">Total Weight (in Kg)</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 10%;">Total Length</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 15%;">Total Breadth</td>
                        <td style="background-color: #f68b1f; color: white; font-weigt: 500; width: 10%;">Total Height</td>
                    </tr>
            """
        data = frappe.db.sql("""
            SELECT custom_pallet as pallet_name, custom_no_of_pallets as total_no, SUM(custom_weight_per_unit_p) as weight_per_unit, SUM(custom_total_weight_of_pallets) as total_weight,
            SUM(custom_pallet_length) as plength,
            SUM(custom_pallet_breadth) as pbreadth,
            SUM(custom_pallet_height) as pheight
            FROM `tabSales Invoice Item`
            WHERE parent = %s
            GROUP BY custom_pallet
        """, (sales_invoice,), as_dict=True)
        for row in data:
            if row.pallet_name and row.total_no and row.weight_per_unit and row.total_weight:
                # html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(row.pallet_name, row.total_no, row.weight_per_unit, row.total_weight)
                # html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(row.pallet_name, row.total_no, row.weight_per_unit, row.total_weight)
                # html += "<tr><th>Box Name</th><th>Total No. of Boxes</th><th>Weight Per Unit (in Kg)</th><th>Total Weight (in Kg)</th></tr>"
                html += f"""
                            <tr>
                                <td>{row.pallet_name}</td>
                                <td>{row.total_no}</td>
                                <td>{row.weight_per_unit}</td>
                                <td>{row.total_weight}</td>
                                <td>{row.plength}</td>
                                <td>{row.pbreadth}</td>
                                <td>{row.pheight}</td>
                            </tr>
                        """
        html += "</table>"
        return html

@frappe.whitelist()
def get_box_summary(sales_invoice):
    if frappe.db.exists("Sales Invoice", sales_invoice):
        doc = frappe.get_doc("Sales Invoice", sales_invoice)
        data = frappe.db.sql("""
            SELECT custom_box as box_name, custom_no_of_boxes as total_no,
                   SUM(custom_weight_per_unit_b) as weight_per_unit,
                   SUM(custom_total_weight_of_boxes) as total_weight,
                   SUM(custom_box_length) as blength,
                   SUM(custom_box_height) as bheight,
                   SUM(custom_box_breadth) as bbreadth
            FROM `tabSales Invoice Item`
            WHERE parent = %s
            GROUP BY custom_box
        """, (sales_invoice,), as_dict=True)
        
        data_set = []
        for row in data:
            if row.box_name and row.total_no and row.weight_per_unit and row.total_weight:
                data_set.append({
                    "box": row.box_name,
                    "total_no_of_box": row.total_no,
                    "weight_per_unit": row.weight_per_unit,
                    "total_weight": row.total_weight,
                    "total_length": row.blength,
                    "total_breadth": row.bbreadth,
                    "total_height": row.bheight
                })
        data2 = frappe.db.sql("""
            SELECT custom_pallet as pallet_name, custom_no_of_pallets as total_no, SUM(custom_weight_per_unit_p) as weight_per_unit, SUM(custom_total_weight_of_pallets) as total_weight,
            SUM(custom_pallet_length) as plength,
            SUM(custom_pallet_breadth) as pbreadth,
            SUM(custom_pallet_height) as pheight
            FROM `tabSales Invoice Item`
            WHERE parent = %s
            GROUP BY custom_pallet
        """, (sales_invoice,), as_dict=True)
        data_set2=[]
        for pal in data2:
            if pal.pallet_name and pal.total_no and pal.weight_per_unit and pal.total_weight:
                data_set2.append({
                    "box": pal.pallet_name,
                    "total_no_of_box": pal.total_no,
                    "weight_per_unit": pal.weight_per_unit,
                    "total_weight": pal.total_weight,
                    "total_length": pal.plength,
                    "total_breadth": pal.pbreadth,
                    "total_height": pal.pheight
                })
                 
        return data_set, data_set2


@frappe.whitelist()
def update_status(name):
    self = frappe.get_doc("Logistics Request", name)
    if self.status == "Variation - Pending for Finance":
        if self.date_of_shipment and self.shipping_line and self.jgb_incoterms and (self.customer_incoterms or self.supplier_incoterms) and self.transit_time and self.etd and self.eta:
            if self.cargo_type == "Sea":
                pol = "self.pol_seaport and self.pol_city_seaport and self.pol_country_seaport"
                pod = "self.pod_seaport and self.pod_city_seaport and self.pod_country_seaport"
            elif self.cargo_type == "Air":
                pol = "self.pol_airport and self.pol_city_airport and self.pol_country_airport"
                pod = "self.pod_airport and self.pod_city_airport and self.pod_country_airport"
            else:
                pol = True
                pod = True
            if pol and pod:
                self.status = "Scheduled"
                if self.po_so == "Sales Invoice":
                    frappe.db.set_value("Sales Invoice", self.order_no, "custom_lr_status", "Pending Export")

        attachment_count = 0
        row_count = 0
        for row in self.support_documents:
            row_count += 1
            if row.attach:
                attachment_count += 1
        if row_count !=0 and row_count == attachment_count:
            self.status = "Dispatched"
            if self.po_so == "Sales Invoice":
                frappe.db.set_value("Sales Invoice", self.order_no, "custom_lr_status", "Ready to Ship")

        if self.boe_number and self.clearance_status and self.appointed_cha_name and self.boe_date and self.payment_challan_attachment and self.payment_date:
            self.status = "In Transit"
            if self.po_so == "Sales Invoice":
                frappe.db.set_value("Sales Invoice", self.order_no, "custom_lr_status", "Shipped")
            
        if self.attachment and self.date_of_delivery and self.receive_by_name:
            self.status = "Delivered"
    
        if self.closing_remarks:
            self.status = "Closed"
        self.save(ignore_permissions=True)

@frappe.whitelist()
def get_suplier(name):
    doc = frappe.get_doc("Logistics Request", name)
    sup_list=[]
    for d in doc.ffw_quotation:
        sup_list.append(d.ffw_name)
    return sup_list

@frappe.whitelist()
def validate_ffw_quotation(self):
    if len(self.ffw_quotation) > 0:
        total = 0
        for row in self.product_description:
            total += row.amount
        self.grand_total = total
        for row in self.product_description_so:
            total += row.amount
        self.grand_total = total
        quoted=False
        if self.recommended_ffw:
            for i in self.ffw_quotation:
                if i.ffw_name==self.recommended_ffw:
                    quoted=True
        if quoted==False:
            frappe.throw("Recommended FFW not present in FFW Quotation table")
        if self.quoted_currency=='SAR':
            if self.quoted_amount!=self.total_shipment_cost:
                frappe.throw("Total Shipment Cost must be equal to the quoted amount")
        else:
            if self.quoted_value_in_company_currency!=self.total_shipment_cost:
                frappe.throw("Total Shipment Cost must be equal to the quoted amount")

@frappe.whitelist()
def return_conversion(currency,price_list_currency):
    conv_rate = get_exchange_rate(currency, price_list_currency)
    return conv_rate

@frappe.whitelist()
def send_accounts_mail(parent_name, row_title, cost, attach_challan):
    doc = frappe.get_doc("Logistics Request", parent_name)

    # Get all Accounts Users (or filter as needed)
    accounts_users = frappe.get_all("Has Role", 
    filters={"role": "Accounts User"}, 
    fields=["parent"]
)
    to_emails = []
    for u in accounts_users:
        user = frappe.get_value("User", u.parent, "email")
        if user and user not in ["admin@example.com"] and user != "HOD": 
            to_emails.append(user)
    # to_emails = [u.name for u in accounts_users if u.name != "Administrator"]
    frappe.log_error(title="Accounts Users",message=to_emails)
    if not to_emails:
        frappe.throw("No Accounts Users found to send email.")

    subject = f"[Action Required] Challan Attached - {doc.name}"

    message = f"""
<p>Dear Accounts Team,</p>

<p>A challan has been attached in the <strong>Logistics Request</strong> document. Please process the payment and upload the payment attachment.</p>

<table style="border-collapse: collapse;border: 1px solid black; width: 100%; font-size: 14px;">
    <tr>
        <td style="border: 1px solid black;font-weight: bold;text-align:center">Document</td>
        
        <td style="border: 1px solid black;font-weight: bold;text-align:center">Title</td>
        <td style="border: 1px solid black;font-weight: bold;text-align:center">Cost</td>
        <td style="border: 1px solid black;font-weight: bold;text-align:center">Attached Challan</td>
    </tr>
    <tr>
    <td style="border: 1px solid black;text-align:left">{doc.name}</td>
    <td style="border: 1px solid black;text-align:left">{row_title}</td>
    <td style="border: 1px solid black;text-align:right">{cost}</td>
    <td style="border: 1px solid black;text-align:center">{"<a href='" + frappe.utils.get_url(attach_challan) + "' target='_blank'>View Challan</a>" if attach_challan else "Not Available"}</td>

    </tr>
</table>

<p>Once the payment is attached, the document status will move to <strong>Out to Delivery</strong>.</p>

<p>Thank you,<br>{frappe.session.user}</p>
"""


    frappe.sendmail(
        recipients=to_emails,
        # recipients="divya.p@groupteampro.com",
        subject=subject,
        message=message
    )


@frappe.whitelist()
def send_accounts_mail_ebill(parent_name, rows):
    doc = frappe.get_doc("Logistics Request", parent_name)
    accounts_users = frappe.get_all("Has Role", 
    filters={"role": "Accounts User"}, 
    fields=["parent"]
)
    to_emails = []
    for u in accounts_users:
        user = frappe.get_value("User", u.parent, "email")
        if user and user not in ["admin@example.com"] and user != "HOD": 
            to_emails.append(user)
    # to_emails = [u.name for u in accounts_users if u.name != "Administrator"]
    # if not to_emails:
    #     frappe.throw("No Accounts Users found to send email.")


    subject = f"[Action Required] Logistics Request Closed - {doc.name}"

    message = f"""
    <p>Dear Accounts Team,</p>
    <p><strong>Logistics Request</strong> document <b>{doc.name}</b> has been closed. Please find the bill attachments.</p>

    <table style="border-collapse: collapse; border: 1px solid black; width: 100%; font-size: 14px;">
        <tr>
            <th style="border: 1px solid black; text-align:center">Title</th>
            <th style="border: 1px solid black; text-align:center">Cost</th>
            <th style="border: 1px solid black; text-align:center">Advance</th>
            <th style="border: 1px solid black; text-align:center">Outstanding</th>
            <th style="border: 1px solid black; text-align:center">Bill Link</th>
        </tr>
    """

    for row in rows:
        message += f"""
        <tr>
            <td style="border: 1px solid black;">{row['title']}</td>
            <td style="border: 1px solid black; text-align:right;">{row['cost']}</td>
            <td style="border: 1px solid black; text-align:right;">{row['advance']}</td>
            <td style="border: 1px solid black; text-align:right;">{row['outstanding']}</td>
            <td style="border: 1px solid black; text-align:center;">
                <a href="{row['url']}" target="_blank">View Bill</a>
            </td>
        </tr>
        """

    message += f"""
    </table>
    <p>Thank you,<br>{frappe.session.user}</p>
    """

    frappe.sendmail(
        # recipients=to_emails,
        recipients="divya.p@groupteampro.com",  # replace with accounts list in live
        subject=subject,
        message=message
    )



@frappe.whitelist()
def payment_attach_validate(name):
    doc = frappe.get_doc("Logistics Request", name)
    doc.workflow_state = "Payment"
    doc.save(ignore_permissions=True)
    frappe.db.commit()


@frappe.whitelist()
def purchase_receipt_validate(name):
    frappe.db.sql("""update `tabLogistics Request` set workflow_state='Arrived' where name=%s """,name)

@frappe.whitelist()
def send_lr_team_mail(parent_name, row_title, cost, attach_payment):
    doc = frappe.get_doc("Logistics Request", parent_name)
    accounts_users = frappe.get_all("Has Role", 
    filters={"role": "Logistics User"}, 
    fields=["parent"]
)
    to_emails = []
    for u in accounts_users:
        user = frappe.get_value("User", u.parent, "email")
        if user and user not in ["admin@example.com"] and user != "HOD": 
            to_emails.append(user)
    subject = f"[Action Required] Payment Attached - {doc.name}"

    message = f"""
<p>Dear Team,</p>

<p>A payment has been attached in the <strong>Logistics Request</strong> document.</p>

<table style="border-collapse: collapse;border: 1px solid black; width: 100%; font-size: 14px;">
    <tr>
        <td style="border: 1px solid black;font-weight: bold;text-align:center">Document</td>
        
        <td style="border: 1px solid black;font-weight: bold;text-align:center">Title</td>
        <td style="border: 1px solid black;font-weight: bold;text-align:center">Cost</td>
        <td style="border: 1px solid black;font-weight: bold;text-align:center">Attached Payment</td>
    </tr>
    <tr>
    <td style="border: 1px solid black;text-align:left">{doc.name}</td>
    <td style="border: 1px solid black;text-align:left">{row_title}</td>
    <td style="border: 1px solid black;text-align:right">{cost}</td>
    <td style="border: 1px solid black;text-align:center">{"<a href='" + frappe.utils.get_url(attach_payment) + "' target='_blank'>View Payment</a>" if attach_payment else "Not Available"}</td>

    </tr>
</table>


<p>Thank you,<br>{frappe.session.user}</p>
"""


    frappe.sendmail(
        recipients=to_emails,
        # recipients="divya.p@groupteampro.com",
        subject=subject,
        message=message
    )


import frappe
from frappe.utils import getdate, nowdate, add_days, formatdate

@frappe.whitelist()
def send_lr_eta_team_mail():
    today = getdate(nowdate())
    next_week = add_days(today, 7)
    lr_list = frappe.db.get_all(
        "Logistics Request",
        filters={
            "workflow_state": ["!=", "Closed"],
            "eta": ["between", [today, next_week]]
        },
        fields=["name", "eta", "company", "logistic_type"]
    )

    if not lr_list:
        return "No pending Logistics Requests with upcoming ETA."
    logistics_users = frappe.get_all(
        "Has Role", 
        filters={"role": "Logistics User"}, 
        fields=["parent as name"]
    )
    to_emails = [u.name for u in logistics_users if u.name != "Administrator"]

    if not to_emails:
        frappe.throw("No Logistics Users found to send email.")
    subject = "Upcoming Logistics Requests (ETA within 7 days)"
    message = """
    <p>Dear Team,</p>
    <p>The following <b>Logistics Requests</b> have an ETA within the next 7 days and are still open. Kindly review and take necessary action:</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f0f0f0;">
            <th>Name</th>
            <th>ETA</th>
            <th>Company</th>
            <th>Logistics Type</th>
        </tr>
    """

    for lr in lr_list:
        link = frappe.utils.get_url_to_form("Logistics Request", lr.name)
        message += f"""
        <tr>
            <td><a href="{link}">{lr.name}</a></td>
            <td>{formatdate(lr.eta)}</td>
            <td>{lr.company}</td>
            <td>{lr.logistic_type}</td>
        </tr>
        """

    message += """
    </table>
    <p>Regards,<br>ERP System</p>
    """

    # Send email
    frappe.sendmail(
        recipients=to_emails,
        # recipients=["divya.p@groupteampro.com","jenisha.p@groupteampro.com"],
        subject=subject,
        message=message
    )

from erpnext.setup.utils import get_exchange_rate
@frappe.whitelist()
def create_pi_for_lr(parent_name=None,row_title=None,cost=None,supplier=None,currency=None,cost_sar=None):
    doc = frappe.get_doc("Logistics Request", parent_name)
    if not supplier:
        frappe.throw("Kindly select supplier before create Purchase Invoice")
    if not cost:
        frappe.throw("Cost is mandatory")
    default_currency = frappe.db.get_value("Company", "Joint Global Business Co LLC", "default_currency")

    if currency == default_currency or not currency:
        conversion = 1
        amount_value = cost
    else:
        conversion = get_exchange_rate(currency, default_currency)
        amount_value = float(conversion) * float(cost)

    pi = frappe.new_doc("Purchase Invoice")
    pi.custom_logistics_request = parent_name
    pi.supplier = supplier
    pi.company = "Joint Global Business Co LLC"
    pi.custom_division = "Common"
    pi.posting_date = nowdate()
    pi.currency = currency or default_currency
    pi.conversion_rate = conversion
    pi.custom_zoho_pi_number = f"{row_title}-{parent_name}"

    if row_title=="SAL Charges":
        pi.append("items",{
            "item_code":"NST-OTH-000007",
            "item_name":"SAL Charges",
            "qty":1,
            "uom":"NOS",
            "rate":cost,
            "amount":amount_value,
        })
    if row_title=="Customs":
        pi.append("items",{
            "item_code":"NST-OTH-000008",
            "item_name":"Customs Charges",
            "qty":1,
            "uom":"NOS",
            "rate":cost,
            "amount":amount_value,
        })
    if row_title=="Customs Clearance":
        pi.append("items",{
            "item_code":"NST-OTH-000009",
            "item_name":"Customs Clearance",
            "qty":1,
            "uom":"NOS",
            "rate":cost,
            "amount":amount_value,
        })
    if row_title=="Saber Charges":
        pi.append("items",{
            "item_code":"NST-OTH-000010",
            "item_name":"Saber Charges",
            "qty":1,
            "uom":"NOS",
            "rate":cost,
            "amount":amount_value,
        })
    if row_title=="Freight & Forwarding Charges":
        pi.append("items",{
            "item_code":"NST-OTH-000011",
            "item_name":"Freight & Forwarding Charges",
            "qty":1,
            "uom":"NOS",
            "rate":cost,
            "amount":amount_value,
        })
    pi.save()
    return pi.name

# @frappe.whitelist()
# def purchase_lr_status_update(doc, method):
#     if doc.custom_logistics_request and frappe.db.exists("Logistics Request", doc.custom_logistics_request):
#         lr = frappe.get_doc("Logistics Request", doc.custom_logistics_request)
#         updated = False
#         for row in lr.lr_costing_payment_po:
#             if row.purchase_invoice == doc.name:
#                 if doc.status == "Cancelled":
#                     row.purchase_invoice = ""
#                     row.status = ""
#                 else:
#                     row.status = doc.status
#                 updated = True
#         if updated:
#             lr.save(ignore_permissions=True)
#             lr.reload()

@frappe.whitelist()
def purchase_lr_status_update(doc, method=None):
    if not doc.custom_logistics_request:
        return

    if not frappe.db.exists("Logistics Request", doc.custom_logistics_request):
        return

    lr = frappe.get_doc("Logistics Request", doc.custom_logistics_request)
    updated = False
    for row in lr.lr_costing_payment_po:
        if row.purchase_invoice == doc.name:
            if doc.status == "Cancelled":
                row.purchase_invoice = ""
                row.status = ""
            else:
                row.status = doc.status
            updated = True
    if updated:
        lr.save(ignore_permissions=True)
        lr.reload()
    

@frappe.whitelist()
def get_pi_from_lr(logistics_request):
    if not logistics_request:
        return []
    pi_list = frappe.db.get_all(
        "Purchase Invoice",
        filters={"custom_logistics_request": logistics_request},
        fields=["name", "supplier", "grand_total"]
    )
    if not pi_list:
        return []

    for pi in pi_list:
        items = frappe.db.get_all(
            "Purchase Invoice Item",
            filters={"parent": pi["name"]},
            fields=["item_name", "expense_account", "amount", "net_amount"]
        )
        pi["items"] = items

    return pi_list

@frappe.whitelist()
def on_payment_entry_submit(doc, method=None):
    if not doc.references:
        return
    for ref in doc.references:
        if not ref.reference_name:
            continue
        pi = frappe.get_doc("Purchase Invoice", ref.reference_name)
        if not pi.custom_logistics_request:
            continue
        if ref.idx==1:
            update_lr_for_paid_pi(pi, payment_entry=doc)


def update_lr_for_paid_pi(pi, payment_entry=None):
    if not frappe.db.exists("Logistics Request", pi.custom_logistics_request):
        return

    lr = frappe.get_doc("Logistics Request", pi.custom_logistics_request)

    updated = False
    po_list = []
    lr_status = pi.status
    for row in lr.lr_costing_payment_po:
        if row.purchase_invoice == pi.name:
            row.is_paid=1
            updated = True

    item_title = ", ".join(
        sorted(set(i.item_name for i in pi.items if i.item_name))
    ) or "Logistics Charges"

    if lr.product_description:
        for i in lr.product_description:
            if i.voucher_no:
                po_list.append(i.voucher_no)

    if updated:
        lr.save(ignore_permissions=True)

    if po_list and updated:
        po_nos = ", ".join(sorted(set(po_list)))

        subject = (
            f"{lr.name} - {item_title} "
            f"paid for against - {po_nos}"
        )

        message = f"""
        <p>Dear Team,</p>
        <p>
            Payment Entry <b>{payment_entry.name if payment_entry else ''}</b>
            has been <b>Paid</b> for
            Purchase Invoice <b>{pi.name}</b>.
        </p>
        <p>
            <b>Logistics Request:</b> {lr.name}<br>
            <b>Purchase Orders:</b> {po_nos}<br>
        </p>
        <p>Regards,<br>ERP System</p>
        """

        frappe.sendmail(
            recipients=["divya.p@groupteampro.com"],
            # recipients=["ajmal@jgbksa.com"],
            subject=subject,
            message=message
        )

def update_lr_for_pi_cancel(doc,method):
    if not doc.references:
        return
    for ref in doc.references:
        if not ref.reference_name:
            continue
        pi = frappe.get_doc("Purchase Invoice", ref.reference_name)
        if not pi.custom_logistics_request:
            continue
        if ref.idx==1:
            if not frappe.db.exists("Logistics Request", pi.custom_logistics_request):
                return

            lr = frappe.get_doc("Logistics Request", pi.custom_logistics_request)

            updated = False
            for row in lr.lr_costing_payment_po:
                if row.purchase_invoice == pi.name:
                    row.is_paid=0
                    updated = True

            if updated:
                lr.save(ignore_permissions=True)