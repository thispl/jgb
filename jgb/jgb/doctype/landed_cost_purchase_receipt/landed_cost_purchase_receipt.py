# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LandedCostPurchaseReceipt(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		grand_total: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		posting_date: DF.Date | None
		receipt_document: DF.DynamicLink
		receipt_document_type: DF.Literal["", "Purchase Invoice", "Purchase Receipt"]
		supplier: DF.Link | None
	# end: auto-generated types
	pass
