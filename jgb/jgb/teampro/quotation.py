import frappe
import re
from frappe.utils import flt

@frappe.whitelist()
def get_cost_center_for_division(division=None, company=None):
	keyword = extract_keyword_from_division(division)

	if not keyword or not company:
		return ""

	cost_center = frappe.db.sql("""
		SELECT name FROM `tabCost Center`
		WHERE company = %s
		  AND is_group = 0
		  AND name LIKE %s
		LIMIT 1
	""", (
		company,
		f"%{keyword}%",
	), as_dict=0)

	return cost_center[0][0] if cost_center else ""


def extract_keyword_from_division(division):
	# Custom logic to extract from full name like "HVAC Division - (HVA)"
	match = re.search(r'([A-Za-z\s]+)\s+Division', division)
	if match:
		return match.group(1).strip()
	# fallback
	return division.split('-')[0].strip()



@frappe.whitelist()
def update_quote_value_by_cost(estimation=None, margin=None):
	if estimation is None or margin is None:
		return 0
	value = float(margin)/float(100)
	quote_value = float(estimation) + (float (estimation) * float(value))
	return quote_value



import frappe
import os
import openpyxl
import tempfile
from frappe.utils.csvutils import read_csv_content
from frappe.utils.file_manager import get_file

@frappe.whitelist()
def upload_item_sheet(docname, file_url):
	try:
		file_doc, file_content_or_path = get_file(file_url)
		if os.path.exists(file_content_or_path):
			filepath = file_content_or_path
		else:
			suffix = ".xlsx" if file_url.endswith(".xlsx") else ".csv"
			tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
			if isinstance(file_content_or_path, bytes):
				tmp.write(file_content_or_path)
			else:
				tmp.write(file_content_or_path.encode())
			tmp.close()
			filepath = tmp.name

		ext = os.path.splitext(filepath)[1].lower()

		doc = frappe.get_doc("Quotation", docname)

		if ext == ".xlsx":
			wb = openpyxl.load_workbook(filepath, data_only=True)
			ws = wb.active
			for row in ws.iter_rows(min_row=2, values_only=True):
				if not any(row): 
					continue
				item_code, qty, rate = row
				doc.append("items", {
					"item_code": item_code,
					"qty": qty,
					"rate": rate,
					"custom_cost":rate,
					"custom_total_costcompany_currency":rate*qty*doc.custom_brand_conversion_rate
				})

		elif ext == ".csv":
			with open(filepath, "r", encoding="utf-8-sig") as f:
				rows = read_csv_content(f.read())
			for row in rows[1:]:
				if not any(row):
					continue
				item_code, qty, rate = row
				doc.append("items", {
					"item_code": item_code,
					"qty": qty,
					"rate": rate,
					"custom_cost":rate,
					"custom_total_costcompany_currency":rate*qty*doc.custom_brand_conversion_rate
				})
				# item_code, item_name, qty, uom, discount_per, discount_rate, discount_amount, rate, amount = row
				# doc.append("items", {
				#     "item_code": item_code,
				#     "item_name": item_name,
				#     "qty": qty,
				#     "uom": uom,
				#     "discount_percentage": discount_per,
				#     "discount_amount": discount_amount,
				#     "rate": rate,
				#     "amount": amount
				# })

		else:
			frappe.throw(f"Unsupported file format: {ext}")

		doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {"status": "success", "message": "Items imported successfully."}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Item Sheet Import Failed")
		return {"status": "error", "message": str(e)}




@frappe.whitelist()
def process_uploaded_file(file_url, quotation_name):
	import frappe, os
	from io import BytesIO
	from frappe.utils.file_manager import get_file
	from openpyxl import load_workbook

	file_doc = frappe.get_doc("File", {"file_url": file_url})
	content = None
	file_path = None

	try:
		file_path = frappe.utils.get_site_path(file_doc.file_url.strip("/"))
		if not os.path.exists(file_path):
			raise FileNotFoundError
	except Exception:
		content = file_doc.get_content()

	try:
		if content:
			wb = load_workbook(filename=BytesIO(content), data_only=True)
		else:
			wb = load_workbook(filename=file_path, data_only=True)
		sheet = wb.active
	except Exception as e:
		frappe.throw(f"Unable to read Excel file: {str(e)}")

	rows = list(sheet.iter_rows(values_only=True))
	if not rows:
		frappe.throw("Excel file is empty.")

   

	
	quotation = frappe.get_doc("Quotation", quotation_name)
	if quotation.custom_brand == "Pennbarry":
		data_rows = rows[2:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[9] or 0
			rate = row_vals[10] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:min(8, len(row_vals))] if v]

			if brand:
				item_name_parts.append(str(brand).strip())


			item_name = "-".join(item_name_parts)
			item_description_data=[str(v).strip() for v in row_vals[:min(8, len(row_vals))] if v]
			item_description="-".join(item_description_data)
			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
		frappe.db.commit()
	elif quotation.custom_brand == "Hattersley":
		quotation.price_list = ""

		data_rows = rows[0:]
		for pp in data_rows:
			if not pp[6] or pp[0] == "Qty":
				continue

			# Description should be index 1 to 4 only
			description = "-".join(str(x) for x in pp[1:4] if x)

			# Rate logic
			rate = pp[4] if pp[4] else pp[5]

			quotation.append("items", {
				"item_code": pp[6],
				"item_name": pp[7],
				"qty": pp[0],
				"rate": rate,
				"description": description,
			})
		for row in list(quotation.items):
			if not row.item_code:
				quotation.remove(row)

		quotation.save(ignore_permissions=True)
		frappe.db.commit()

	elif quotation.custom_brand == "Antec Controls":
		data_rows = rows[2:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[4] or 0
			rate = row_vals[5] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:3] if v]
			item_description_data=[str(v).strip() for v in row_vals[:4] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description= "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
		frappe.db.commit()
	elif quotation.custom_brand == "EH Price-VAV/CAV":
		data_rows = rows[1:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[1] or 0
			rate = row_vals[11] or 0


			item_name_parts = [str(v).strip() for v in row_vals[2:11] if v]
			item_description_data = [str(v).strip() for v in row_vals[2:11] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())
			# item_description_data.append("""Variable Air Volume - Pressure Independent Type
			#         Casing : - 20mm Ga Galvanized Steel Sheet (Double skin)
			#         Insulation : - 1" Insulation (48kg/m³, WGF)
			#         Controls : - Neptronic – Bacnet  MS/TP - (EVCB14NIT0S Actuator + TDU00-100 -Thermostat)
			#         Electric Heater : - Neptronic - Modulating Type.
			#         Attenuator : - ATTSP(Where Mentioned)
			#         Accessories : HB - Hanger Bracket, GT - Gauge taps, DSW - Disconnect switch, Transformer """)
			item_name = "-".join(item_name_parts)
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		# quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
	elif quotation.custom_brand == "EH Price-SA":
		data_rows = rows[1:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[8] or 0
			rate = row_vals[9] or 0


			item_name_parts = [str(v).strip() for v in row_vals[1:8] if v]
			item_description_data = [str(v).strip() for v in row_vals[1:8] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
	elif quotation.custom_brand == "EH Price-Dampers":
		data_rows = rows[1:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[7] or 0
			rate = row_vals[8] or 0


			item_name_parts = [str(v).strip() for v in row_vals[1:7] if v]
			item_description_data = [str(v).strip() for v in row_vals[1:7] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			# item_description_data.append("""Motorised Smoke & Fire Damper
			#     Model : FSD-3V-S-231 ( UL Classified) - Class I - (3 Hrs.)
			#     Frame : 16 gauge galvanized steel construction
			#     Blade : 16 gauge triple V grove galvanized steel construction
			#     Fusible Link : UL Listed , Electro-thermal fusible link with 165°F temperature tripping point.
			#     Actuator : Honeywell ,  Spring return Complies with UL873 standard.""")
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.custom_company=quotation.company
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)

	elif quotation.custom_brand == "Vortice":
		data_rows = rows[1:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		quotation.items = [row for row in quotation.items if row.item_code]

		created_items = []  

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[5] or 0
			rate = row_vals[6] or 0


			item_name_parts = [str(v).strip() for v in row_vals[:5] if v]
			item_description_data=[str(v).strip() for v in row_vals[:5] if v]
			if brand:
				item_name_parts.append(str(brand).strip())
				# item_description_data.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description= "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]   
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo
					
				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo
				
			})

		quotation.set("items", [])


		division_settings = {
			"HVAC Division - (HVA)": {
				"warehouse": "HVAC Stores - JGB",
				"income_account": "4001 - Revenue - HVAC - JGB",
				"expense_account": "5011 - COG - HVAC - JGB"
			},
			"MECH": {
				"warehouse": "Main Warehouse - JGB",
				"income_account": "Sales Mechanical - JGB",
				"expense_account": "COGS Mechanical - JGB"
			}
		}

		div = quotation.custom_division_short_code

		warehouse = division_settings.get(div, {}).get("warehouse")
		income_account = division_settings.get(div, {}).get("income_account")
		expense_account = division_settings.get(div, {}).get("expense_account")

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
		frappe.db.commit()

	elif quotation.custom_brand == "MÜPRO":
		data_rows = rows[1:]
		division_code = quotation.custom_division_short_code
		product_short = quotation.custom_product_short_code
		cost_center = quotation.custom_cost_center
		brand = quotation.custom_brand
		quo = quotation.custom_brand_exchange_rate
		company= quotation.company

		created_items = []

		for row in data_rows:
			if not any(row):
				continue

			row_vals = list(row)

			qty = row_vals[5] or 0
			rate = row_vals[6] or 0

			item_name_parts = [str(v).strip() for v in row_vals[:4] if v]
			item_description_data = [str(v).strip() for v in row_vals[:5] if v]
			if brand:
				item_name_parts.append(str(brand).strip())

			item_name = "-".join(item_name_parts)
			item_description = "-".join(item_description_data)

			prefix = f"{division_code}-{product_short}"

			existing_item = frappe.db.get_value(
				"Item",
				{
					"item_name": item_name,
					"item_code": ["like", f"{prefix}%"]
				},
				"name"
			)

			if existing_item:
				created_items.append({
					"item_code": existing_item,
					"item_name": item_name,
					"description": item_description,
					"qty": qty,
					"rate": rate,
					"custom_cost": rate,
					"custom_price_cost":rate*quo,
					"custom_total_cost": rate * qty,
					"custom_total_costcompany_currency": rate * qty * quo

				})
				continue

			last_item = frappe.db.sql("""
				SELECT name FROM `tabItem`
				WHERE item_code LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", (f"{prefix}%",), as_dict=True)

			last_number = 0
			if last_item:
				try:
					last_number = int(last_item[0]["name"].split("-")[-1])
				except:
					pass

			new_code = f"{prefix}-{last_number + 1:06d}"

			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"item_group": quotation.custom_division,
				"custom_quotation_ref": quotation_name,
				"custom_auto_created_item": 1,
				"custom_product": quotation.custom_product,
			})
			item.insert(ignore_permissions=True)
			frappe.db.commit()
			created_items.append({
				"item_code": new_code,
				"item_name": item_name,
				"description": item_description,
				"qty": qty,
				"rate": rate,
				"custom_price_cost":rate*quo,
				"custom_total_cost": rate * qty,
				"custom_total_costcompany_currency": rate * qty * quo

			})

		if not created_items:
			frappe.throw("No data rows found in the uploaded file.")

		quotation.set("items", [])

		for it in created_items:
			quotation.append("items", {
				"item_code": it["item_code"],
				"item_name": it["item_name"],
				"description": it["description"],
				"qty": it["qty"],
				"uom": "Nos",
				"rate": it["rate"] *quo,
				"base_rate": it["rate"] * quo,
				"custom_cost_center": cost_center,
				"custom_cost":it["rate"],
				"custom_price_cost":it["custom_price_cost"],
				"custom_total_cost":it["custom_total_cost"],
				"custom_total_costcompany_currency": it["custom_total_costcompany_currency"],
				"custom_cost_amount":it["custom_total_cost"],
				"custom_cost_amount_sar":it["custom_total_costcompany_currency"]
			})

		quotation.save(ignore_permissions=True)
		frappe.db.commit()

	return "Items created successfully"


@frappe.whitelist()
def margin_tool(item_details, discount=None, per=None,total=None,tax=None):
	import json
	item_details = json.loads(item_details)

	data = ''
	data += """
		<br>
		<style>
			.margin-table {
				width: 100%;
				border-collapse: collapse;
				font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
				font-size: 12px;
				color: #333;
			}

			.margin-table th,
			.margin-table td {
				padding: 6px 8px;
				border: 1px solid #dcdcdc;
			}

			.margin-table thead th {
				background: linear-gradient(135deg, #75506A, #9A6C87);
				color: #fff;
				text-align: center;
				font-size: 13px;
				font-weight: 600;
			}

			.margin-table thead tr.title th {
				font-size: 15px;
				padding: 8px;
			}

			.margin-table tbody tr:nth-child(even) {
				background-color: #f9f9f9;
			}

			.margin-table tbody tr:hover {
				background-color: #f1edf0;
			}

			.text-right {
				text-align: right;
			}

			.text-center {
				text-align: center;
			}

			.summary-row td {
				font-weight: 600;
				background-color: #f4f4f4;
			}

			.net-total td {
				font-size: 13px;
				background-color: #75506A;
				color: #fff;
				font-weight: 700;
			}
			
		</style>

		<table class="margin-table">
			<thead>
				<tr class="title">
					<th colspan="10">ITEM DETAILS</th>
				</tr>
				<tr style="background: #e6e6e6; color: #333;">
					<th width="40" style="background: #e6e6e6; color: #333;">S#</th>
					<th width="250" style="background: #e6e6e6; color: #333;">Item Name</th>
					<th width="300" style="background: #e6e6e6; color: #333;">Description</th>
					<th width="70" style="background: #e6e6e6; color: #333;">Qty</th>
					<th width="70" style="background: #e6e6e6; color: #333;">UOM</th>
					<th width="70" style="background: #e6e6e6; color: #333;">Disc %</th>
					<th width="80" style="background: #e6e6e6; color: #333;">Disc Rate</th>
					<th width="90" style="background: #e6e6e6; color: #333;">Disc Amt</th>
					<th width="80" style="background: #e6e6e6; color: #333;">Unit Rate</th>
					<th width="90" style="background: #e6e6e6; color: #333;">Amount</th>
				</tr>
			</thead>
			<tbody>
		"""

	dis = 0
	amount = 0
	discount = float(discount) if discount else 0.0
	per = float(per) if per else 0.0
	total = float(total) if total else 0.0
	tax = float(tax) if tax else 0.0
	for idx, i in enumerate(item_details, start=1):
		dis += i["discount_amount"]
		amount += i["amount"]

		data += '''
		<tr>
			<td style="text-align:center;">{}</td>
			<td>{}</td>
			<td>{}</td>
			<td style="text-align:right;">{}</td>
			<td>{}</td>
			<td style="text-align:right;">{}</td>
			<td style="text-align:right;">{:.2f}</td>
			<td style="text-align:right;">{:.2f}</td>
			<td style="text-align:right;">{:.2f}</td>
			<td style="text-align:right;">{:.2f}</td>
		</tr>
		'''.format(
			idx,
			i["item_name"],
			i["description"],
			i["qty"],
			i["uom"],
			i["discount_percentage"],
			i["discount_rate"],
			i["discount_amount"],
			i["rate"],
			i["amount"]
		)

	data += """
		<tr class="summary-row">
			<td colspan="7" class="text-right">Total</td>
			<td class="text-right">{:.2f}</td>
			<td></td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="summary-row">
			<td colspan="9" class="text-right">Additional Percentage</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="summary-row">
			<td colspan="9" class="text-right">Additional Discount</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="summary-row">
			<td colspan="9" class="text-right">Tax</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		<tr class="net-total">
			<td colspan="9" class="text-right">Net Total</td>
			<td class="text-right">{:.2f}</td>
		</tr>
		</tbody>
		</table>
		""".format(dis, amount, per, discount, tax, total)
	return data


import frappe
from frappe.utils.file_manager import save_file
from openpyxl import Workbook

@frappe.whitelist()
def get_item_template():

	wb = Workbook()
	ws = wb.active
	ws.title = "Item Template"

	# Add only headings
	ws.append(["Item Code", "Qty", "Rate"])

	# Save temporarily
	file_path = "/tmp/item_template.xlsx"
	wb.save(file_path)

	# Read file
	with open(file_path, "rb") as f:
		file = save_file(
			"Item_Template.xlsx",
			f.read(),
			None,   # dt → no doctype
			None,   # dn → no docname
			folder="Home/Attachments",
			is_private=0
		)

	return file.file_url



import frappe
import openpyxl
from openpyxl import Workbook
from io import BytesIO

@frappe.whitelist()
def get_item_without_code_template(brand=None, product=None):
	brand_doc = frappe.get_doc("Brand", brand)
	if brand_doc.custom_download_template:
		file_doc = frappe.get_doc(
			"File",
			{"file_url": brand_doc.custom_download_template}
		)
		file_content = file_doc.get_content()
		frappe.local.response.filename = file_doc.file_name
		frappe.local.response.filecontent = file_content
		frappe.local.response.type = "download"
		return
	headers = []
	if product:
		product_doc = frappe.get_doc("Product", product)
		for row in product_doc.product_naming:
			if row.title:
				headers.append(row.title)
	headers.extend(["Qty", "Rate"])
	wb = Workbook()
	ws = wb.active
	ws.title = "Template"
	for col_num, header in enumerate(headers, 1):
		ws.cell(row=1, column=col_num).value = header
	output = BytesIO()
	wb.save(output)
	frappe.local.response.filename = "Default_Template.xlsx"
	frappe.local.response.filecontent = output.getvalue()
	frappe.local.response.type = "download"




@frappe.whitelist()
def get_selling_cost_center(item_code, company):
	return frappe.db.get_value(
		"Item Default",
		{"parent": item_code, "company": company},
		"selling_cost_center"
	)





import frappe

@frappe.whitelist()
def validate_items_before_hod_review(doc, method):
	if doc.workflow_state == "HOD Pending":
		if not doc.items:
			frappe.throw("Cannot move to HOD review — No items added in the Quotation.")
		
		for item in doc.items:
			if not item.item_code:
				frappe.throw("Cannot move to HOD review — No Items added in the Quotation.")




import frappe

@frappe.whitelist()
def validate_items_before_hod_review(doc, method):
	if doc.workflow_state == "HOD Pending":
		if not doc.items:
			frappe.throw("Cannot move to HOD review — No items added in the Quotation.")
		
		for item in doc.items:
			if not item.item_code:
				frappe.throw("Cannot move to HOD review — No Items added in the Quotation.")


@frappe.whitelist()
def validate_sow_amount(doc, method):
	if doc.custom_sow_as_item == 1:
		total_sow_amount = sum(item.sow_amount for item in doc.custom_sow if item.sow_amount)
		if doc.base_total != total_sow_amount:
			frappe.throw(f"Total SOW Amount ({total_sow_amount}) does not match the Quotation Item Amount ({doc.base_total}). Please correct the amounts in the items.")


@frappe.whitelist()
def update_total_est_value(doc,method):
	total_value= 0
	total_quotaion=0
	if doc.custom_estimation_details:
		for i in doc.custom_estimation_details:
			if i.value:
				total_value+=i.value
			if i.value_quotation_currency:
				total_quotaion+=i.value_quotation_currency
		doc.custom_total_estimated_value=total_value
		doc.custom_total_estimated_value_quotation_currency=total_quotaion


@frappe.whitelist()
def validate_qtn_mandatory(doc,method):
	if not doc.custom_sales_personuser:
		frappe.throw("Sales Person User must be specified before submit")
	if not doc.custom_support_engineer:
		frappe.throw("Support Engineer must be specified before submit")
	if not doc.payment_terms_template:
		frappe.throw("Payment Terms Template is required before submit")
	if not doc.custom_delivery_terms:
		frappe.throw("Kindly enter the Delivery Terms before submit")


@frappe.whitelist()
def sync_quote_value(doc, method):
	"""Server-side safety net for the estimation table's Quote Value.

	Keeps `custom_quote_value` (Quote Value SAR) in sync with the actual discounted
	sales value on EVERY save: Quote Value = base_total - base_discount_amount
	(i.e. base_net_total). Both margins are recomputed on that discounted basis.

	Without this, the field is only maintained by the client script and can be left
	stale by flows that never trigger the discount-aware recalc (margin-derivation
	path, manual edits, server-side/amend saves) - see ESTIMATION_TABLE.md Section 10.

	Skipped when `custom_derive_quoted_value_based_on_margin_cost` is checked: that
	flow intentionally sets a margin-derived target quote value (the user then pushes
	it into item rates via the Update Quote button, which changes base_total).
	"""
	if doc.custom_derive_quoted_value_based_on_margin_cost:
		return

	quote_value = flt(doc.base_total) - flt(doc.base_discount_amount)
	doc.custom_quote_value = quote_value

	est = flt(doc.custom_total_estimated_value)
	if est:
		doc.custom_estimation_margin = ((quote_value - est) / quote_value * 100) if quote_value else 0
		doc.custom_margin_on_cost = (quote_value - est) / est * 100
	else:
		doc.custom_estimation_margin = 0
		doc.custom_margin_on_cost = 0