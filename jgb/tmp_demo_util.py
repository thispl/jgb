import frappe


def recalc_bins(items=None, warehouse=None):
	"""Recompute Bin.actual_qty/projected_qty from the stock ledger for the given items."""
	from erpnext.stock.doctype.bin.bin import Bin

	filters = {}
	if items:
		filters["item_code"] = ["in", frappe.parse_json(items) if isinstance(items, str) else items]
	if warehouse:
		filters["warehouse"] = warehouse
	names = frappe.get_all("Bin", filters=filters, pluck="name")
	out = []
	for n in names:
		b = frappe.get_doc("Bin", n)
		before = (b.actual_qty, b.projected_qty)
		b.recalculate_qty()
		out.append((n, before, (b.actual_qty, b.projected_qty)))
	frappe.db.commit()
	return out


def show_bins(items=None, warehouse=None):
	filters = {}
	if items:
		filters["item_code"] = ["in", frappe.parse_json(items) if isinstance(items, str) else items]
	if warehouse:
		filters["warehouse"] = warehouse
	return frappe.get_all("Bin", filters=filters, fields=["item_code", "warehouse", "actual_qty", "ordered_qty", "indented_qty", "projected_qty"])


def set_item_default_warehouse(items, warehouse):
	"""Collapse duplicate Item Default rows to one per company and point it at `warehouse`."""
	items = frappe.parse_json(items) if isinstance(items, str) else items
	for code in items:
		rows = frappe.get_all("Item Default", filters={"parent": code}, order_by="idx", pluck="name")
		if not rows:
			continue
		frappe.db.set_value("Item Default", rows[0], "default_warehouse", warehouse)
		for extra in rows[1:]:
			frappe.delete_doc("Item Default", extra, force=True)
	frappe.db.commit()
	return frappe.get_all(
		"Item Default", filters={"parent": ["in", items]}, fields=["parent", "default_warehouse"]
	)

