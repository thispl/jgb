import frappe
from frappe.utils import flt, getdate, nowdate


@frappe.whitelist()
def get_data(company=None, item_group=None, warehouse=None, to_date=None):
	# stock balance as on date, computed from Stock Ledger Entry (same basis as
	# ERPNext Stock Balance report): qty = sum(actual_qty), value = latest SLE stock_value
	to_date = getdate(to_date) if to_date else getdate(frappe.utils.nowdate())

	conditions = ["sle.is_cancelled = 0", "sle.posting_date <= %(to_date)s", "i.disabled = 0"]
	values = {"to_date": to_date}
	if warehouse:
		conditions.append("sle.warehouse = %(warehouse)s")
		values["warehouse"] = warehouse
	if company:
		conditions.append("w.company = %(company)s")
		values["company"] = company
	if item_group:
		conditions.append("i.item_group = %(item_group)s")
		values["item_group"] = item_group

	rows = frappe.db.sql("""
		select t.item_code, t.item_name, t.item_group, t.stock_uom, t.warehouse, t.qty, t.value
		from (
			select sle.item_code, i.item_name, i.item_group, i.stock_uom, sle.warehouse,
				sle.stock_value as value,
				sum(sle.actual_qty) over w as qty,
				row_number() over w2 as rn
			from `tabStock Ledger Entry` sle
			join `tabItem` i on i.name = sle.item_code
			join `tabWarehouse` w on w.name = sle.warehouse
			where {cond}
			window w as (partition by sle.item_code, sle.warehouse),
				w2 as (partition by sle.item_code, sle.warehouse
					order by sle.posting_datetime desc, sle.creation desc)
		) t
		where t.rn = 1 and (t.qty != 0 or t.value != 0)
	""".format(cond=" and ".join(conditions)), values=values, as_dict=1)

	if not rows:
		return {"empty": True, "as_on": str(to_date)}

	category = {}
	warehouses = {}
	items = {}
	negative = 0
	for r in rows:
		if flt(r.qty) < 0:
			negative += 1
		grp = category.setdefault(r.item_group or "Not Set", {"qty": 0.0, "value": 0.0, "items": set()})
		grp["qty"] += flt(r.qty)
		grp["value"] += flt(r.value)
		grp.setdefault("_items", set()).add(r.item_code)
		wh = warehouses.setdefault(r.warehouse, {"qty": 0.0, "value": 0.0})
		wh["qty"] += flt(r.qty)
		wh["value"] += flt(r.value)
		it = items.setdefault(r.item_code, {
			"item_name": r.item_name or r.item_code, "item_group": r.item_group,
			"stock_uom": r.stock_uom, "qty": 0.0, "value": 0.0, "warehouses": 0})
		it["qty"] += flt(r.qty)
		it["value"] += flt(r.value)
		it["warehouses"] += 1

	grp_list = [{"item_group": k, "qty": v["qty"], "value": v["value"], "items": len(v["_items"])}
		for k, v in category.items()]
	grp_list.sort(key=lambda d: -d["value"])
	wh_list = sorted(warehouses.items(), key=lambda kv: -kv[1]["value"])
	wh_list = [{"warehouse": k, "qty": v["qty"], "value": v["value"]} for k, v in wh_list[:10]]
	item_list = sorted(items.values(), key=lambda d: -d["value"])[:10]

	total_value = flt(sum(v["value"] for v in category.values()))
	total_qty = flt(sum(v["qty"] for v in category.values()))
	out_of_stock = len({r.item_code for r in rows if flt(r.qty) <= 0})

	currency = frappe.db.get_value("Company", company, "default_currency") if company \
		else frappe.db.get_single_value("Global Defaults", "default_currency") or "SAR"

	return {
		"currency": currency, "as_on": str(to_date),
		"kpi": {
			"total_items": len(items),
			"stock_value": total_value,
			"total_qty": total_qty,
			"item_groups": len(category),
			"warehouses": len(warehouses),
			"out_of_stock": out_of_stock,
			"negative": negative,
		},
		"category": grp_list,
		"warehouses": wh_list[:10],
		"top_items": item_list,
	}
