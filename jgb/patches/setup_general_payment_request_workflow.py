# Copyright (c) 2026, JGB and contributors
# For license information, please see license.txt

import frappe
from jgb.jgb.doctype.general_payment_request.general_payment_request import (
	setup_general_payment_request_workflow,
)


def execute():
	setup_general_payment_request_workflow()
