# Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

from jgb.api import _get_profitability_data


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.currency = frappe.get_cached_value("Company", filters.company, "default_currency")

	invoices = get_invoices(filters)
	show_items = cint(filters.get("show_item_detail"))

	# ponytail: _get_profitability_data does a get_doc + per-item lookups per invoice,
	# so long ranges get slow. If a yearly run ever times out, batch the
	# SO/DN/Bin/PI lookups across all invoices instead of per invoice.
	totals = frappe._dict(
		grand_total=0, so_qty=0, inv_qty=0, dn_qty=0, cost=0, selling=0, rate_amt=0, profit=0
	)
	data = []
	for name in invoices:
		d = _get_profitability_data(name)
		doc, t = d.doc, d.totals

		if show_items:
			for row in d.rows:
				data.append(
					{
						"sales_invoice": doc.name,
						"posting_date": doc.posting_date,
						"customer": doc.customer,
						"item": row["item"],
						"so_qty": row["so_qty"],
						"inv_qty": row["inv_qty"],
						"dn_qty": row["dn_qty"],
						"cost": row["cost"],
						"rate": row["rate"],
						"profit": row["total"],
						"profit_pct": row["profit_pct"],
						"currency": filters.currency,
					}
				)
		else:
			data.append(
				{
					"sales_invoice": doc.name,
					"posting_date": doc.posting_date,
					"customer": doc.customer,
					"customer_name": doc.customer_name,
					"project": doc.project,
					"grand_total": flt(doc.base_grand_total),
					"so_qty": t.so_qty,
					"inv_qty": t.inv_qty,
					"dn_qty": t.dn_qty,
					"cost": t.cost,
					"selling_amount": flt(doc.base_net_total),
					"profit": t.profit,
					"profit_pct": t.profit_pct,
					"currency": filters.currency,
				}
			)

		totals.grand_total += flt(doc.base_grand_total)
		totals.so_qty += flt(t.so_qty)
		totals.inv_qty += flt(t.inv_qty)
		totals.dn_qty += flt(t.dn_qty)
		totals.cost += flt(t.cost)
		totals.selling += flt(doc.base_net_total)
		totals.rate_amt += flt(t.rate)
		totals.profit += flt(t.profit)

	if data:
		precision = cint(frappe.db.get_default("currency_precision")) or 3
		profit_pct = flt((totals.profit / totals.cost) * 100.0, precision) if totals.cost else 0
		data.append(
			{
				"sales_invoice": _("Total"),
				"grand_total": totals.grand_total,
				"so_qty": totals.so_qty,
				"inv_qty": totals.inv_qty,
				"dn_qty": totals.dn_qty,
				"cost": totals.cost,
				"rate": totals.rate_amt if show_items else None,
				"selling_amount": None if show_items else totals.selling,
				"profit": totals.profit,
				"profit_pct": profit_pct,
				"currency": filters.currency,
			}
		)

	return get_columns(show_items), data


def get_invoices(filters):
	conditions = ""
	if filters.get("from_date"):
		conditions += " and posting_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " and posting_date <= %(to_date)s"
	if filters.get("sales_invoice"):
		conditions += " and name = %(sales_invoice)s"
	if filters.get("customer"):
		conditions += " and customer = %(customer)s"
	if filters.get("project"):
		conditions += " and project = %(project)s"

	return frappe.db.sql_list(
		"""
		select name from `tabSales Invoice`
		where docstatus = 1 and is_opening != 'Yes' and company = %(company)s
		{conditions}
		order by posting_date, name
		""".format(conditions=conditions),
		filters,
	)


def get_columns(show_items):
	columns = [
		{
			"label": _("Sales Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 180,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120,
		},
	]

	if show_items:
		columns.append(
			{
				"label": _("Item"),
				"fieldname": "item",
				"fieldtype": "Data",
				"width": 280,
			}
		)
	else:
		columns += [
			{
				"label": _("Customer Name"),
				"fieldname": "customer_name",
				"fieldtype": "Data",
				"width": 180,
			},
			{
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 140,
			},
			{
				"label": _("Total Value"),
				"fieldname": "grand_total",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
		]

	columns += [
		{"label": _("SO Qty"), "fieldname": "so_qty", "fieldtype": "Float", "width": 80},
		{"label": _("Inv Qty"), "fieldname": "inv_qty", "fieldtype": "Float", "width": 80},
		{"label": _("DN Qty"), "fieldname": "dn_qty", "fieldtype": "Float", "width": 80},
	]

	if show_items:
		columns += [
			{
				"label": _("Cost"),
				"fieldname": "cost",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 110,
			},
			{
				"label": _("Rate"),
				"fieldname": "rate",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 110,
			},
		]
	else:
		columns += [
			{
				"label": _("Cost"),
				"fieldname": "cost",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Selling Amount"),
				"fieldname": "selling_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
		]

	columns += [
		{
			"label": _("Profit"),
			"fieldname": "profit",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Profit %"),
			"fieldname": "profit_pct",
			"fieldtype": "Percent",
			"width": 100,
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]

	return columns
