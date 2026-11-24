import json
import frappe
from bs4 import BeautifulSoup
@frappe.whitelist()
def create_item_name(parameter, description=None):
	import json
	if isinstance(parameter, str):
		parameter = json.loads(parameter)
	item_name = "-".join(i["value"] for i in parameter if i.get("value"))
	if not item_name and description:
		description = BeautifulSoup(description, "html.parser").get_text(strip=True)
		item_name = description
	item_name = item_name[:140]
	return item_name


@frappe.whitelist()
def set_asset_naming(asset_category):
	item_group_short_code = "AST"
	product_short_code =frappe.db.get_value("Asset Category",asset_category,"custom_short_code")
	if not product_short_code:
		frappe.throw("Short code is missing in Asset category")
	prefix = f"{item_group_short_code}-{product_short_code}-"

	existing_items = frappe.db.get_all("Item", filters={
		"item_code": ["like", f"{prefix}%"]
	}, fields=["item_code"])

	max_num = 0
	pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$") 
	for item in existing_items:
		item_code = item["item_code"]
		match = pattern.match(item_code)
		if match:
			num_part = int(match.group(1))
			if num_part > max_num:
				max_num = num_part

	next_num = max_num + 1
	next_code = f"{prefix}{str(next_num).zfill(6)}" 

	return next_code


import re
import frappe

@frappe.whitelist()
def create_item_series(item_group, product):
	item_group_short_code = frappe.db.get_value("Item Group", {"name": item_group}, "custom_short_code")
	product_short_code = frappe.db.get_value("Product", {"name": product}, "short_code")

	if not item_group_short_code or not product_short_code:
		frappe.throw("Missing short code for Item Group or Product.")

	prefix = f"{item_group_short_code}-{product_short_code}-"

	existing_items = frappe.db.get_all("Item", filters={
		"item_code": ["like", f"{prefix}%"]
	}, fields=["item_code"])

	max_num = 0
	pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$") 
	for item in existing_items:
		item_code = item["item_code"]
		match = pattern.match(item_code)
		if match:
			num_part = int(match.group(1))
			if num_part > max_num:
				max_num = num_part

	next_num = max_num + 1
	next_code = f"{prefix}{str(next_num).zfill(6)}" 

	return next_code



@frappe.whitelist()
def set_parameters(type):
	product = frappe.get_doc("Product",type)
	return product.product_naming



def update_item_code_creation(doc,method):
	# Asset items use their own series (set_asset_naming: AST-<cat>-NNNNNN).
	if doc.is_fixed_asset or doc.item_group == "Fixed Assets Register (FAR)" or doc.get("variant_of"):
		return

	# Enforce the GROUP-PRODUCT-NNNNNN code on every insert path, not just
	# imports - link-field quick-create and the API otherwise save whatever
	# free text was typed (e.g. a supplier part number) as the item code.
	if not doc.item_group or not doc.custom_product:
		frappe.throw(
			"Item Group and Product are required to generate the Item Code "
			"(GROUP-PRODUCT-NNNNNN). Create the item from the Item form instead."
		)

	next_code = create_item_series(doc.item_group, doc.custom_product)
	doc.name = doc.item_code = doc.custom_item = next_code
	if doc.custom_product_naming_parameters:
		doc.item_name = "-".join(
			row.value for row in doc.custom_product_naming_parameters
			if row.value
		)



from frappe.utils import cint
def auto_set_is_stock_item(doc, method=None):
	"""Auto-set is_stock_item based on Item Group's custom_is_stock_group flag.

	Runs on before_insert and validate. Ensures items in non-stock groups
	(e.g. Non Stock Items, Fixed Assets) don't have Maintain Stock enabled,
	and items in stock groups do.
	"""
	if not doc.item_group:
		return

	if doc.is_fixed_asset or doc.custom_item_type == "Bundle":
		doc.is_stock_item = 0
		return

	is_stock_group = frappe.db.get_value("Item Group", doc.item_group, "custom_is_stock_group")
	if is_stock_group is not None:
		doc.is_stock_item = 1 if cint(is_stock_group) else 0




def set_expense_account_from_division_for_item(doc, method=None):
	"""
	Set accounts in Item Defaults based on division and item type
	- Stock items (is_stock_item = 1): Use SRBNB from Division Account Details
	- Non-stock items (is_stock_item = 0): Use COG from Division Account Details
	- Also sets income_account from Division Account Details
	"""
	if not doc.item_group:
		return
	
	# Get division from item group
	division = frappe.db.get_value("Item Group", doc.item_group, "custom_group_name")
	if not division:
		return
	
	# Get company (use first company if multiple)
	company = doc.get("custom_company") or "Joint Global Business Co LLC"
	
	# Get division account details
	div_details = frappe.db.get_value("Division Account Details", 
		{"parent": division, "company": company}, 
		["snrb_account", "expense_account", "income_account"], as_dict=True)
	
	if not div_details:
		return
	
	# Find or create Item Default for the company
	item_default = frappe.db.get_value("Item Default", 
		{"parent": doc.name, "company": company}, "name")
	
	updates = {}
	
	# Set expense_account based on item type
	if doc.is_stock_item:
		# Stock items use SRBNB
		if div_details.snrb_account:
			updates["expense_account"] = div_details.snrb_account
	else:
		# Non-stock items use COG
		if div_details.expense_account:
			updates["expense_account"] = div_details.expense_account
	
	# Set income_account
	if div_details.income_account:
		updates["income_account"] = div_details.income_account
	
	if item_default:
		# Update existing Item Default
		if updates:
			frappe.db.set_value("Item Default", item_default, updates)
	else:
		# Create new Item Default
		item_default_doc = frappe.new_doc("Item Default")
		item_default_doc.parent = doc.name
		item_default_doc.parenttype = "Item"
		item_default_doc.parentfield = "item_defaults"
		item_default_doc.company = company
		
		# Set accounts
		for key, value in updates.items():
			setattr(item_default_doc, key, value)
		
		# Set other defaults if available
		buying_cc = doc.get("buying_cost_center")
		if buying_cc:
			item_default_doc.buying_cost_center = buying_cc
		selling_cc = doc.get("selling_cost_center")
		if selling_cc:
			item_default_doc.selling_cost_center = selling_cc
		
		item_default_doc.insert()

