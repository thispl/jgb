import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, nowdate, strip_html

from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
)
from erpnext.selling.doctype.sales_order.sales_order import (
	make_purchase_order as erpnext_make_purchase_order,
)


def set_item_order_as_per_source(source, target):
	"""Keep the mapped item table in the Sales Order's line order.

	ERPNext maps the Items table before the Packed Items table, so product
	bundle components are appended at the bottom of the target document instead
	of under the bundle line they belong to.
	"""
	item_rank = {row.name: row.idx for row in source.items}
	packed_rank = {
		row.name: (item_rank.get(row.parent_detail_docname, 0), row.idx)
		for row in source.packed_items
	}

	def rank(row):
		if row.sales_order_item:
			return (item_rank[row.sales_order_item], 0)
		return packed_rank[row.sales_order_packed_item]

	if not all(
		row.sales_order_item in item_rank
		if row.sales_order_item
		else row.sales_order_packed_item in packed_rank
		for row in target.items
	):
		return

	target.items.sort(key=rank)
	for idx, row in enumerate(target.items, 1):
		row.idx = idx


@frappe.whitelist()
def make_purchase_order(source_name, selected_items=None, target_doc=None):
	"""Sales Order -> Purchase Order with the SO line order preserved."""
	doc = erpnext_make_purchase_order(source_name, selected_items, target_doc)
	if doc:
		set_item_order_as_per_source(frappe.get_doc("Sales Order", source_name), doc)
	return doc


@frappe.whitelist()
def make_bom_purchase_order(
	items, company, sales_order, supplier, schedule_date=None, project=None, target_warehouse=None
):
	"""Create a Purchase Order for the raw materials of a Sales Order.

	Items dict mirrors the standard "Request for Raw Materials" payload:
	each row has item_code, bom, required_qty and warehouse. BOM items are
	exploded via get_items_for_material_requests which nets off the
	projected stock (actual + ordered - reserved) across company
	warehouses unless ignore_existing_ordered_qty is enabled.
	"""
	if not frappe.has_permission("Purchase Order", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if isinstance(items, str):
		items = json.loads(items)
	items = frappe._dict(items)

	for item in items.get("items"):
		item["include_exploded_items"] = items.get("include_exploded_items")
		item["ignore_existing_ordered_qty"] = items.get("ignore_existing_ordered_qty")
		item["include_raw_materials_from_sales_order"] = items.get("include_raw_materials_from_sales_order")

	items.update({"company": company, "sales_order": sales_order})

	raw_materials = get_items_for_material_requests(items)
	if not raw_materials:
		frappe.msgprint(
			_("Purchase Order not created, as quantity for Raw Materials is already available."),
			title=_("Note"),
		)
		return

	po = frappe.new_doc("Purchase Order")
	po.update(
		dict(
			doctype="Purchase Order",
			supplier=supplier,
			company=company,
			project=project,
			transaction_date=nowdate(),
			set_warehouse=target_warehouse,
		)
	)

	po_meta = frappe.get_meta("Purchase Order")
	so_meta = frappe.get_meta("Sales Order")
	for fieldname in ("custom_division", "custom_division_short_code"):
		if po_meta.has_field(fieldname) and so_meta.has_field(fieldname):
			value = frappe.db.get_value("Sales Order", sales_order, fieldname)
			if value:
				po.set(fieldname, value)

	for item in raw_materials:
		item_doc = frappe.get_cached_doc("Item", item.get("item_code"))
		warehouse = item.get("warehouse")
		if not warehouse or frappe.get_cached_value("Warehouse", warehouse, "disabled"):
			warehouse = target_warehouse
		row = po.append(
			"items",
			{
				"item_code": item.get("item_code"),
				"qty": item.get("quantity"),
				"uom": item.get("uom"),
				"schedule_date": schedule_date
				or add_days(nowdate(), cint(item_doc.lead_time_days)),
				"warehouse": warehouse,
				"sales_order": sales_order,
			},
		)
		if not (strip_html(item.get("description") or "") and strip_html(item_doc.description)):
			row.description = item_doc.item_name or item.get("item_code")

	po.run_method("set_missing_values")
	for row in po.items:
		if not row.warehouse or (
			target_warehouse and frappe.get_cached_value("Warehouse", row.warehouse, "disabled")
		):
			row.warehouse = target_warehouse
	po.insert()
	return po.name
