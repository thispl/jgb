# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt



def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data




def get_columns(filters):
    columns = []
    columns += [
        _("Date") + ":Date/:120",
        _("Invoice No") + ":Data/:200",
        _("Purchase Invoice") + ":Link/Purchase Invoice:200",
        _("Supplier Name") + ":Data/:150",
        _("Currency") + ":Data/:70",
        _("Invoice Value") + ":Currency/:150",
        _("Invoice QAR Value") + ":Currency/:150",
        _("Overhead Cost") + ":Currency/:150",
        _("Total Purchase") + ":Currency/:150",
    ]
    return columns
    



def get_data(filters):
    data = []
    value = frappe.get_all("Has Role",{"role":"Purchase Manager"},["parent"])
    for role in value:
        purchase_invoice = frappe.db.get_all("Purchase Invoice",{'company':filters.company,"posting_date":('between',(filters.from_date,filters.to_date)),"owner":role["parent"],"status":('not in',("Cancelled","Draft"))},['*'])
        for i in purchase_invoice:
           
                gt = frappe.get_doc("Purchase Invoice",i.name)
                for j in gt.items[:1]:
                    

                    lc = frappe.db.sql("""select total_taxes_and_charges,sum(`tabLanded Cost Item`.applicable_charges) as pd from `tabLanded Cost Voucher`
                    left join `tabLanded Cost Item` on `tabLanded Cost Voucher`.name = `tabLanded Cost Item`.parent
                    where `tabLanded Cost Item`.receipt_document = '%s' and  `tabLanded Cost Voucher`.docstatus =1 """%(j.purchase_receipt),as_dict=True)
                    if lc:
                        for l in lc:
                            if l.pd:
                                p = l.pd
                            else:
                                p = 0
                    else:
                        p = 0
                    value = lc[0].total_taxes_and_charges if lc and lc[0].total_taxes_and_charges is not None else 0
                    tot = round((i.base_net_total+(value)),2)
                    row = [i.posting_date, i.bill_no, i.name, i.supplier, i.currency, round(i.net_total, 2), round(i.base_net_total, 2), round(value, 2), round(tot, 2)]
                    data.append(row)
    return data
    
    