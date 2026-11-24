import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("S.No"), "fieldname": "sno", "fieldtype": "Int", "width": 70},
		{
			"label": _("Asset"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Asset",
			"width": 150,
		},
		{"label": _("Asset Name"), "fieldname": "asset_name", "fieldtype": "Data", "width": 230},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 230},
		{
			"label": _("Asset Category"),
			"fieldname": "asset_category",
			"fieldtype": "Link",
			"options": "Asset Category",
			"width": 160,
		},
		{
			"label": _("Location"),
			"fieldname": "location",
			"fieldtype": "Link",
			"options": "Location",
			"width": 140,
		},
		{
			"label": _("Custodian"),
			"fieldname": "custodian",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150,
		},
	]


def get_data(filters):
	conditions = ""
	values = {}

	if filters.get("asset_name"):
		conditions += " AND name = %(asset_name)s"
		values["asset_name"] = filters["asset_name"]

	if filters.get("item_code"):
		conditions += " AND item_code = %(item_code)s"
		values["item_code"] = filters["item_code"]

	if filters.get("item_name"):
		conditions += " AND item_name LIKE %(item_name)s"
		values["item_name"] = f"%{filters['item_name']}%"

	if filters.get("custodian"):
		conditions += " AND custodian = %(custodian)s"
		values["custodian"] = filters["custodian"]

	data = frappe.db.sql(
		f"""
		SELECT
			name, asset_name, item_code, item_name,
			asset_category, location, custodian
		FROM `tabAsset`
		WHERE 1 = 1 {conditions}
		ORDER BY name
		""",
		values,
		as_dict=1,
	)

	for idx, row in enumerate(data, start=1):
		row["sno"] = idx

	return data
