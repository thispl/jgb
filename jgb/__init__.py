__version__ = "0.0.1"


# ---------------------------------------------------------------------------
# Monkey-patch Repost Item Valuation to trigger division reclass refresh
# ---------------------------------------------------------------------------
# The repost() function in ERPNext uses db_set() to update the status to
# "Completed", which bypasses the normal save cycle and does NOT trigger
# the on_update doc_event hook.  To catch SLE reposting in real time we
# wrap the original repost() function and call our reclass refresh logic
# right after it completes successfully.

def _patch_repost_item_valuation():
	try:
		import erpnext.stock.doctype.repost_item_valuation.repost_item_valuation as riv_mod

		if getattr(riv_mod, "_jgb_reclass_patched", False):
			return  # already patched

		_original_repost = riv_mod.repost

		def _wrapped_repost(doc):
			# Call the original repost function
			_original_repost(doc)

			# After successful repost, refresh division reclass entries
			try:
				if doc.company != "Joint Global Business Co LLC":
					return
				if doc.status != "Completed":
					return
				from jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification import (
					_recreate_reclass_for_repost,
				)
				_recreate_reclass_for_repost(doc)
			except Exception:
				import frappe
				frappe.log_error(
					title="[Division Reclass] Failed to refresh after repost",
					message=frappe.get_traceback(),
				)

		riv_mod.repost = _wrapped_repost
		riv_mod._jgb_reclass_patched = True
	except Exception:
		# Don't crash the app if the patch fails — just log it
		try:
			import frappe
			frappe.log_error(
				title="[Division Reclass] Failed to patch repost_item_valuation",
				message=frappe.get_traceback(),
			)
		except Exception:
			pass


# Apply the patch when this module is imported
_patch_repost_item_valuation()


# ---------------------------------------------------------------------------
# Monkey-patch Item-wise Sales History to tolerate missing item/customer rows
# ---------------------------------------------------------------------------
# SOJGBKSA3076 (and possibly others) has submitted Sales Order Item rows with
# item_code = NULL ("Installation" text-only lines).  Upstream get_data() calls
# item_details.get(record.item_code).get("item_name"), which raises
# AttributeError when the lookup returns None.  Wrap get_item_details() and
# get_customer_details() so missing lookups yield an empty _dict instead of
# crashing.  This also guards against dangling item/customer references.

def _patch_item_wise_sales_history():
	try:
		import frappe
		import erpnext.selling.report.item_wise_sales_history.item_wise_sales_history as iwsh

		if getattr(iwsh, "_jgb_safe_lookup_patched", False):
			return  # already patched

		class _SafeLookupDict(dict):
			def get(self, key, default=None):
				return super().get(key) or frappe._dict()

		_original_get_item_details = iwsh.get_item_details
		_original_get_customer_details = iwsh.get_customer_details

		def _get_item_details_safe():
			return _SafeLookupDict(_original_get_item_details())

		def _get_customer_details_safe():
			return _SafeLookupDict(_original_get_customer_details())

		iwsh.get_item_details = _get_item_details_safe
		iwsh.get_customer_details = _get_customer_details_safe
		iwsh._jgb_safe_lookup_patched = True
	except Exception:
		# Don't crash the app if the patch fails — just log it
		try:
			import frappe
			frappe.log_error(
				title="[JGB] Failed to patch item_wise_sales_history",
				message=frappe.get_traceback(),
			)
		except Exception:
			pass


# Apply the patch when this module is imported
_patch_item_wise_sales_history()
