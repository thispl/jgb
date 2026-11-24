import frappe
from frappe.utils import add_months, add_years, flt, fmt_money, get_last_day, getdate, nowdate
from frappe import _


@frappe.whitelist()
def get_profitability_html(sales_invoice):
	data = _get_profitability_data(sales_invoice)
	company_currency = data.company_currency
	doc_currency = data.doc_currency
	rows = data.rows
	totals = data.totals

	html = """
	<div style="margin-bottom: 10px; font-size: 12px; color: #666;">
		<strong>Column Calculations:</strong>
		<ul style="margin: 5px 0; padding-left: 20px;">
			<li><strong>SO Qty:</strong> Quantity from linked Sales Order Item</li>
			<li><strong>Inv Qty:</strong> Invoiced quantity from Sales Invoice</li>
			<li><strong>DN Qty:</strong> Delivered quantity from linked Delivery Note</li>
			<li><strong>Cost:</strong> Valuation rate from Bin → Item → Purchase Invoice (Product Bundles and BOM items: sum of child item costs)</li>
			<li><strong>Rate:</strong> Selling rate from Sales Invoice</li>
			<li><strong>Total:</strong> (Base Rate - Cost) × Invoiced Qty</li>
			<li><strong>Profit %:</strong> ((Base Rate - Cost) / Cost) × 100</li>
		</ul>
	</div>
	<table class="table table-bordered" style="width:100%">
		<thead>
			<tr style="background-color:#f3f4f6;">
				<th style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
				<th class="text-right" style="background-color:#f3f4f6;">{}</th>
			</tr>
		</thead>
		<tbody>
	""".format(
		_("Item"),
		_("SO Qty"),
		_("Inv.Qty"),
		_("DN Qty"),
		_("Cost"),
		_("Rate"),
		_("Total"),
		_("Profit %"),
	)
	for row in rows:
		profit_color = "#dc3545" if row["profit_pct"] < 0 else "#28a745" if row["profit_pct"] > 0 else "inherit"
		html += """
		<tr>
			<td>{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right" style="color:{}">{}</td>
		</tr>
		""".format(
			frappe.utils.escape_html(row["item"]),
			frappe.format(row["so_qty"], {"fieldtype": "Float"}),
			frappe.format(row["inv_qty"], {"fieldtype": "Float"}),
			frappe.format(row["dn_qty"], {"fieldtype": "Float"}),
			fmt_money(row["cost"], currency=company_currency),
			fmt_money(row["rate"], currency=doc_currency),
			fmt_money(row["total"], currency=company_currency),
			profit_color,
			frappe.format(row["profit_pct"], {"fieldtype": "Float"}) + " %",
		)

	overall_color = "#dc3545" if totals.profit_pct < 0 else "#28a745" if totals.profit_pct > 0 else "inherit"
	html += """
		<tr style="background-color:#f3f4f6; font-weight: bold;">
			<td>{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right">{}</td>
			<td class="text-right" style="color:{}">{}</td>
		</tr>
	""".format(
		_("<b>Total</b>"),
		frappe.format(totals.so_qty, {"fieldtype": "Float"}),
		frappe.format(totals.inv_qty, {"fieldtype": "Float"}),
		frappe.format(totals.dn_qty, {"fieldtype": "Float"}),
		fmt_money(totals.cost, currency=company_currency),
		fmt_money(totals.rate, currency=doc_currency),
		fmt_money(totals.profit, currency=company_currency),
		overall_color,
		frappe.format(totals.profit_pct, {"fieldtype": "Float"}) + " %",
	)
	html += "</tbody></table>"
	return html


def _fallback_item_cost(item_code, warehouse=None):
	bin_filters = {"item_code": item_code}
	if warehouse:
		bin_filters["warehouse"] = warehouse
	bins = frappe.get_all("Bin", filters=bin_filters, fields=["valuation_rate"])
	cost = flt(sum(flt(b.valuation_rate) for b in bins) / len(bins)) if bins else 0.0
	if not cost:
		cost = flt(frappe.db.get_value("Item", item_code, "valuation_rate"))
	if not cost:
		cost = flt(frappe.db.get_value("Item", item_code, "last_purchase_rate"))
	if not cost:
		pi_rate = frappe.db.sql(
			"""
			SELECT pii.base_rate
			FROM `tabPurchase Invoice Item` pii
			INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
			WHERE pii.item_code = %s AND pi.docstatus = 1
			ORDER BY pi.posting_date DESC, pii.creation DESC
			LIMIT 1
			""",
			item_code,
		)
		if pi_rate:
			cost = flt(pi_rate[0][0])
	return cost


@frappe.whitelist()
def _get_profitability_data(sales_invoice):
	doc = frappe.get_doc("Sales Invoice", sales_invoice)
	company_currency = frappe.get_cached_value("Company", doc.company, "default_currency")
	rows = []
	totals = frappe._dict(
		so_qty=0.0,
		inv_qty=0.0,
		dn_qty=0.0,
		cost=0.0,
		rate=0.0,
		profit=0.0,
		profit_pct=0.0,
	)
	for item in doc.items:
		ordered_qty = 0.0
		if item.sales_order and item.so_detail:
			ordered_qty = frappe.db.get_value("Sales Order Item", item.so_detail, "qty") or 0.0

		delivered_qty = 0.0
		if item.dn_detail:
			dn = frappe.db.get_value("Delivery Note Item", item.dn_detail, "qty")
			delivered_qty = flt(dn)
		elif item.sales_order:
			filters = {"against_sales_order": item.sales_order, "docstatus": 1}
			if item.so_detail:
				filters["so_detail"] = item.so_detail
			dn_items = frappe.get_all(
				"Delivery Note Item",
				filters=filters,
				fields=["qty"],
				order_by="creation",
			)
			delivered_qty = sum(flt(d.qty) for d in dn_items)

		# Cost: product bundles sum child costs via the fallback chain;
		# BOM items use the BOM's raw_material_cost per unit; else the chain.
		cost = 0.0
		if frappe.db.exists("Product Bundle", item.item_code):
			for bundle_item in frappe.get_all(
				"Product Bundle Item",
				filters={"parent": item.item_code},
				fields=["item_code", "qty"],
			):
				cost += _fallback_item_cost(bundle_item.item_code, item.warehouse) * flt(bundle_item.qty)
		else:
			bom = frappe.db.get_value(
				"BOM",
				{"item": item.item_code, "is_active": 1, "is_default": 1, "docstatus": 1},
				["name", "quantity"],
				as_dict=True,
			)
			if bom:
				for bom_item in frappe.get_all(
					"BOM Item",
					filters={"parent": bom.name},
					fields=["item_code", "qty"],
				):
					cost += _fallback_item_cost(bom_item.item_code, item.warehouse) * flt(bom_item.qty)
				if bom.quantity:
					cost = flt(cost / bom.quantity)
			if not cost:
				cost = _fallback_item_cost(item.item_code, item.warehouse)

		so_qty = flt(ordered_qty)
		inv_qty = flt(item.qty)
		dn_qty = flt(delivered_qty)
		rate = flt(item.rate)
		base_rate = flt(item.base_rate)
		total = (base_rate - cost) * inv_qty if cost > 0 else 0.0
		profit_pct = 0.0
		if cost > 0:
			profit_pct = ((base_rate - cost) / cost) * 100

		rows.append(
			{
				"item": f"{item.item_code}: {item.item_name or ''}",
				"so_qty": so_qty,
				"inv_qty": inv_qty,
				"dn_qty": dn_qty,
				"cost": cost,
				"rate": rate,
				"total": total,
				"profit_pct": profit_pct,
			}
		)

		totals.so_qty += so_qty
		totals.inv_qty += inv_qty
		totals.dn_qty += dn_qty
		totals.cost += cost * inv_qty
		totals.rate += rate * inv_qty
		totals.profit += total

	if totals.cost > 0:
		totals.profit_pct = (totals.profit / totals.cost) * 100

	return frappe._dict(
		doc=doc,
		company_currency=company_currency,
		doc_currency=doc.currency,
		rows=rows,
		totals=totals,
	)


@frappe.whitelist()
def download_profitability_excel(sales_invoice):
	from frappe.utils.xlsxutils import build_xlsx_response

	data = _get_profitability_data(sales_invoice)
	xlsx_rows = [
		[
			"Item",
			"SO Qty",
			"Inv.Qty",
			"DN Qty",
			"Cost",
			"Rate",
			"Total",
			"Profit %",
		]
	]
	for row in data.rows:
		xlsx_rows.append(
			[
				row["item"],
				row["so_qty"],
				row["inv_qty"],
				row["dn_qty"],
				row["cost"],
				row["rate"],
				row["total"],
				row["profit_pct"],
			]
		)
	xlsx_rows.append(
		[
			"Total",
			data.totals.so_qty,
			data.totals.inv_qty,
			data.totals.dn_qty,
			data.totals.cost,
			data.totals.rate,
			data.totals.profit,
			data.totals.profit_pct,
		]
	)

	build_xlsx_response(xlsx_rows, f"Profitability_{sales_invoice}.xlsx")


DASHBOARD_ROLES = {"System Manager", "Sales Manager", "Sales User"}


@frappe.whitelist()
def get_sales_dashboard_data(from_date=None, to_date=None, company=None, customer=None,
		region=None, sales_person=None, item_group=None):
	# endpoint-level gate: whitelisted methods do not inherit Page roles
	if not set(frappe.get_roles()) & DASHBOARD_ROLES:
		frappe.throw(_("Not permitted to view Sales Dashboard"), frappe.PermissionError)

	# users linked to a Sales Person always see only their own records;
	# pure managers (no Sales Person link) and System Managers see everything
	user_roles = set(frappe.get_roles())
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	linked_sp = frappe.db.get_value("Sales Person", {"employee": employee}, "name") if employee else None
	if linked_sp:
		sales_person = linked_sp
	elif not (user_roles & {"System Manager", "Sales Manager"}):
		frappe.throw(_("No Sales Person is linked to your user. Please contact your administrator."),
			frappe.PermissionError)

	from_date = getdate(from_date) if from_date else getdate(nowdate()).replace(month=1, day=1)
	to_date = getdate(to_date) if to_date else getdate(nowdate())
	prev_from, prev_to = add_years(from_date, -1), add_years(to_date, -1)

	def base_filters(doctype, date_field, start=None, end=None):
		f = {"docstatus": 1, date_field: ["between", [start or from_date, end or to_date]]}
		if company and doctype != "Opportunity":
			f["company"] = company
		if customer and doctype != "Opportunity":
			f["customer"] = customer
		if region and doctype in ("Quotation", "Sales Order", "Sales Invoice"):
			f["custom_region"] = region
		return f

	sp_cache = {}

	def sales_person_names(doctype):
		if not sales_person:
			return None
		if doctype not in sp_cache:
			# sales person is recorded in any of: Sales Team child table,
			# custom_sales_person (Link) or custom_sales_personuser (name) —
			# attribute via the union of all sources
			parents = set(frappe.get_all("Sales Team",
				filters={"sales_person": sales_person, "parenttype": doctype, "docstatus": 1},
				pluck="parent"))
			for field in ("custom_sales_person", "custom_sales_personuser"):
				if frappe.db.has_column(doctype, field):
					parents.update(frappe.get_all(doctype,
						filters={field: sales_person, "docstatus": 1}, pluck="name"))
			sp_cache[doctype] = list(parents)
		return sp_cache[doctype]

	def count(doctype, extra=None, date_field="transaction_date", start=None, end=None):
		f = base_filters(doctype, date_field, start, end)
		if doctype == "Opportunity":
			f.pop("company", None)
			f.pop("customer", None)
			f.pop("custom_region", None)
			f["status"] = ["!=", "Closed"]
		sp = sales_person_names(doctype)
		if sp is not None:
			f["name"] = ["in", sp]
		if extra:
			f.update(extra)
		# get_list applies user permissions (roles + user permissions)
		rows = frappe.get_list(doctype, filters=f, fields=["count(name) as cnt"], as_list=True)
		return rows[0][0] if rows else 0

	def sum_field(doctype, field, extra=None, date_field="transaction_date", start=None, end=None):
		f = base_filters(doctype, date_field, start, end)
		sp = sales_person_names(doctype)
		if sp is not None:
			f["name"] = ["in", sp]
		if extra:
			f.update(extra)
		rows = frappe.get_list(doctype, filters=f,
			fields=["sum({0}) as total".format(field)], as_list=True)
		return flt(rows[0][0]) if rows else 0.0

	enquiries = count("Opportunity")
	quotations = count("Quotation")
	# a quotation counts as converted when it was ordered (fully or partially)
	converted = count("Quotation", {"status": ["in", ["Converted", "Ordered", "Partially Ordered", "Closed"]]})
	orders = count("Sales Order")
	invoices = count("Sales Invoice", {"is_return": 0}, date_field="posting_date")

	delivered = count("Sales Order", {"status": ["in", ["Delivered", "Completed"]]})
	partially_delivered = count("Sales Order", {"status": "Partially Delivered"})
	pending = count("Sales Order", {"status": ["in", ["To Deliver and Bill", "To Deliver", "To Bill"]]})

	revenue = sum_field("Sales Invoice", "base_grand_total", None, "posting_date")

	# previous period for % change
	p_enquiries = count("Opportunity", start=prev_from, end=prev_to)
	p_quotations = count("Quotation", start=prev_from, end=prev_to)
	p_orders = count("Sales Order", start=prev_from, end=prev_to)
	p_invoices = count("Sales Invoice", {"is_return": 0}, "posting_date", prev_from, prev_to)
	p_revenue = sum_field("Sales Invoice", "base_grand_total", None, "posting_date", prev_from, prev_to)

	def pct(cur, prev):
		if not prev:
			return None
		return flt((cur - prev) / prev * 100, 1)

	# monthly values
	monthly = {"labels": [], "quotation": [], "order": [], "invoice": []}
	for m in range(12):
		month_start = add_months(from_date.replace(day=1), m)
		month_end = get_last_day(month_start)
		monthly["labels"].append(month_start.strftime("%b"))
		monthly["quotation"].append(sum_field("Quotation", "base_grand_total", None, "transaction_date", month_start, month_end))
		monthly["order"].append(sum_field("Sales Order", "base_grand_total", None, "transaction_date", month_start, month_end))
		monthly["invoice"].append(sum_field("Sales Invoice", "base_grand_total", None, "posting_date", month_start, month_end))

	# quotation status (map ERPNext statuses to dashboard buckets)
	quo_status = {"Converted": [0, 0.0], "Open": [0, 0.0], "Lost": [0, 0.0]}
	status_map = {"Ordered": "Converted", "Partially Ordered": "Converted",
		"Closed": "Converted", "Expired": "Open", "Draft": "Open"}
	quo_filters = base_filters("Quotation", "transaction_date")
	sp = sales_person_names("Quotation")
	if sp is not None:
		quo_filters["name"] = ["in", sp]
	for st, cnt, val in frappe.get_list(
		"Quotation",
		filters=quo_filters,
		fields=["status", "count(name) as cnt", "sum(base_grand_total) as total"],
		group_by="status", as_list=True,
	):
		bucket = status_map.get(st, st if st in quo_status else "Open")
		quo_status[bucket][0] += cnt
		quo_status[bucket][1] += flt(val)

	# invoice-scoped aggregations
	inv_filters = base_filters("Sales Invoice", "posting_date")
	sp = sales_person_names("Sales Invoice")
	if sp is not None:
		inv_filters["name"] = ["in", sp]
	inv_names = frappe.get_list("Sales Invoice", filters=inv_filters, pluck="name")
	item_filters = {"docstatus": 1, "parenttype": "Sales Invoice", "parent": ["in", inv_names]}
	if item_group:
		item_filters["item_group"] = item_group

	top_customers = frappe.get_list(
		"Sales Invoice", filters=inv_filters,
		fields=["customer", "customer_name", "sum(base_grand_total) as value", "count(name) as orders"],
		group_by="customer", order_by="value desc", limit_page_length=5)

	top_products = frappe.get_all(
		"Sales Invoice Item",
		fields=["item_name", "sum(base_amount) as value", "sum(qty) as qty"],
		filters=item_filters,
		group_by="item_name", order_by="value desc", limit_page_length=5)

	category = frappe.get_all(
		"Sales Invoice Item",
		fields=["item_group", "sum(base_amount) as value"],
		filters=item_filters,
		group_by="item_group", order_by="value desc")

	region = frappe.get_list(
		"Sales Invoice", filters=inv_filters,
		fields=["custom_region", "sum(base_grand_total) as value"],
		group_by="custom_region", order_by="value desc", limit_page_length=10)

	if item_group:
		revenue = flt(frappe.get_list("Sales Invoice Item", filters=item_filters,
			fields=["sum(base_amount) as total"], as_list=True)[0][0])

	currency = company and frappe.db.get_value("Company", company, "default_currency") \
		or frappe.db.get_single_value("Global Defaults", "default_currency") or "SAR"

	return {
		"from_date": str(from_date), "to_date": str(to_date), "currency": currency,
		"kpi": {
			"enquiries": enquiries, "quotations": quotations, "converted": converted,
			"orders": orders, "delivered": delivered, "invoices": invoices,
			"revenue": revenue,
			"enquiries_pct": pct(enquiries, p_enquiries),
			"quotations_pct": pct(quotations, p_quotations),
			"orders_pct": pct(orders, p_orders),
			"invoices_pct": pct(invoices, p_invoices),
			"revenue_pct": pct(revenue, p_revenue),
			"conversion_rate": flt(converted / quotations * 100, 1) if quotations else 0,
			"fulfillment_rate": flt(delivered / orders * 100, 1) if orders else 0,
		},
		"funnel": [
			["Enquiries", enquiries], ["Quotations", quotations], ["Converted", converted],
			["Orders", orders], ["Delivered", delivered], ["Invoiced", invoices],
		],
		"monthly": monthly,
		"quotation_status": quo_status,
		"fulfillment": {"Delivered": delivered, "Partially Delivered": partially_delivered,
			"Pending": pending, "Total": orders},
		"top_customers": top_customers,
		"top_products": top_products,
		"category": category,
		"region": region,
	}
