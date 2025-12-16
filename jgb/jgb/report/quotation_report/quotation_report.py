# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        _("Quotation") + ":Link/Quotation:200",
        _("Date") + ":Date:110",
        _("Customer") + ":Data:300",
        _("Sales Person") + ":Data:200",
        _("Total Amount") + ":Currency:150",
        _("Discount Amount") + ":Currency:150",
        _("Net Amount") + ":Currency:150",
        _("Status") + ":Data:130",
        _("Phone No") + ":Data:100",
    ]

def get_data(filters):
    data = []
    conditions = "transaction_date BETWEEN %(from_date)s AND %(to_date)s AND company = %(company)s"
    params = {
        "from_date": filters.from_date,
        "to_date": filters.to_date,
        "company": filters.company
    }

    if filters.order_type:
        conditions += " AND order_type = %(order_type)s"
        params["order_type"] = filters.order_type

    if filters.customer:
        conditions += " AND party_name = %(customer)s"
        params["customer"] = filters.customer

    if filters.sales_person:
        conditions += " AND custom_sales_personuser = %(sales_person)s"
        params["sales_person"] = filters.sales_person

    if filters.docstatus:
        conditions += " AND status = %(docstatus)s"
        params["docstatus"] = filters.docstatus

    # Handle amount condition safely
    if filters.amount_condition:
        if filters.amount_condition == ">":
            conditions += " AND net_total > %(amount_from)s"
            params["amount_from"] = filters.amount_from or 0
        elif filters.amount_condition == "<":
            conditions += " AND net_total < %(amount_from)s"
            params["amount_from"] = float(filters.amount_from or 0)

        elif filters.amount_condition == "=":
            conditions += " AND net_total = %(amount_from)s"
            params["amount_from"] = filters.amount_from or 0
        elif filters.amount_condition == "between":
            if filters.amount_from is not None:
                conditions += " AND net_total >= %(amount_from)s"
                params["amount_from"] = filters.amount_from
            if filters.amount_to is not None:
                conditions += " AND net_total <= %(amount_to)s"
                params["amount_to"] = filters.amount_to
    query = f"""
        SELECT *
        FROM `tabQuotation`
        WHERE {conditions}
        ORDER BY transaction_date
    """
    quotation = frappe.db.sql(query, params, as_dict=True)

    for i in quotation:
        if i.status != "Cancelled":
            row = [
                i.name,
                i.transaction_date,
                i.party_name,
                i.custom_sales_personuser,
                round(i.total or 0, 2),
                round(i.discount_amount or 0, 2),
                round(i.net_total or 0, 2),
                i.status,
                i.contact_mobile or "",
            ]
            data.append(row)
    return data
