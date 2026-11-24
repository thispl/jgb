import json

import frappe


def write_auth(path="/home/ubuntu/erp-video/.auth.json"):
	key = frappe.db.get_value("User", "Administrator", "api_key")
	secret = frappe.utils.password.get_decrypted_password("User", "Administrator", "api_secret")
	with open(path, "w") as f:
		json.dump({"key": key, "secret": secret}, f)
	print("written", bool(key), bool(secret))
