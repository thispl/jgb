app_name = "jgb"
app_title = "JGB"
app_publisher = "abdulla.pi@groupteampro.com"
app_description = "JGB"
app_email = "abdulla.pi@groupteampro.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "jgb",
# 		"logo": "/assets/jgb/logo.png",
# 		"title": "JGB",
# 		"route": "/jgb",
# 		"has_permission": "jgb.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = [
	"/assets/jgb/css/brand_theme.css",
	"/assets/jgb/css/sales_dashboard.css",
]
# app_include_js = "/assets/jgb/js/jgb.js"

# include js, css files in header of web template
# web_include_css = "/assets/jgb/css/jgb.css"
# web_include_js = "/assets/jgb/js/jgb.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "jgb/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Advance Sales Invoice": "public/js/advance_sales_invoice.js",
	"Sales Invoice": "public/js/sales_invoice.js",
	"Sales Order": "public/js/sales_order.js",
	"Purchase Invoice": "public/js/purchase_invoice.js",
	"Purchase Order": "public/js/purchase_order.js",
	"Purchase Receipt": "public/js/purchase_receipt.js",
	"Asset": "public/js/asset.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "jgb/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods":[
        "jgb.utils.packing_list",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.return_account_total",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.get_sales_person",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.receivable_report",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.get_accounts_ledger",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.statement_of_account",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.supplier_statement_of_account",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.receipt_report",
        "jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.payable_aging_report",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.return_total_amt_consolidate",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.ageing_report_test",
        "jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.ageing_report_summary",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.return_account_summary_total",
		"jgb.jgb.doctype.accounts_report_dashboard.accounts_report_dashboard.return_total_amt1",
        "jgb.jgb.doctype.party_payment_request.party_payment_request.pay_consolidated_req",
        "jgb.jgb.doctype.accounts_report_dashboard.print_format_aging_sp.ageing_report_summary_sales_person",
        "jgb.jgb.doctype.accounts_report_dashboard.print_format_advance_received.ageing_report_summary_advance_received",
        "jgb.jgb.doctype.accounts_report_dashboard.print_format_receivable_summary_sp.receivable_summary_salesperson",
        "jgb.jgb.doctype.accounts_receivable_dashboard.accounts_receivable_dashboard.ar_dashboard_table",
        "jgb.jgb.doctype.accounts_payable_dashboard.accounts_payable_dashboard.ap_dashboard_table",
        "jgb.jgb.doctype.financial_report_dashboard.financial_report_dashboard.frd_report",
        "jgb.jgb.doctype.financial_report_dashboard.financial_report_dashboard.fmt_money",
        "jgb.jgb.doctype.financial_report_dashboard.financial_report_dashboard.fmt_pct",
        "jgb.jgb.doctype.attendance_report_dashboard.attendance_report_dashboard.ard_report",
        "jgb.jgb.doctype.accounts_report_dashboard.daily_transaction.daily_transaction_report",
        "jgb.jgb.teampro.leave_application.calculate_vacation_pay_print",
        "jgb.jgb.doctype.accounts_report_dashboard.fixed_asset_register_report.get_fixed_asset_register_html"
	] 
}

# Installation
# ------------

# before_install = "jgb.install.before_install"
# after_install = "jgb.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "jgb.uninstall.before_uninstall"
# after_uninstall = "jgb.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "jgb.utils.before_app_install"
# after_app_install = "jgb.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "jgb.utils.before_app_uninstall"
# after_app_uninstall = "jgb.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "jgb.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways
# TEMPORARILY DISABLED — pending client approval (2026-09-01)
# Re-enable by uncommenting the blocks below after approval

# permission_query_conditions = {
# 	"Sales Order": "jgb.permissions.sales_order.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Sales Order": "jgb.permissions.sales_order.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Salary Slip": "jgb.overrides.CustomSalarySlip",
	"Purchase Receipt": "jgb.overrides.CustomPurchaseReceipt",
	"Purchase Invoice": "jgb.overrides.CustomPurchaseInvoice",
    "Additional Salary": "jgb.overrides.CustomAdditionalSalary",
    "Landed Cost Voucher": "jgb.overrides.CustomLandedCostVoucher",
    "Leave Allocation": "jgb.overrides.CustomLeaveAllocation",
    "Sales Order": "jgb.overrides.CustomSalesOrder",
    "Purchase Order": "jgb.overrides.CustomPurchaseOrder"
}

# Repost Accounting Ledger — allow Delivery Note and Stock Entry to be reposted
repost_allowed_doctypes = ["Delivery Note", "Stock Entry"]

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Stock Entry": {
		"validate": "jgb.overrides.set_stock_entry_divisional_accounts",
		"on_submit": "jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.create_division_reclass",
		"on_cancel": "jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.cancel_division_reclass",
	},
	 "Employee Promotion": {
        "on_submit": "hrms.hr.doctype.employee_promotion.employee_promotion.set_final_approval"
    },
	"Stock Reconciliation": {
		"on_submit": "jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.create_division_reclass",
		"on_cancel": "jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.cancel_division_reclass",
	},
	"Payment Entry":{
		"validate":"jgb.jgb.division_cost_center.apply_division_cost_center",
		"before_update_after_submit":"jgb.jgb.division_cost_center.apply_division_cost_center",
		"on_update_after_submit":"jgb.jgb.division_cost_center.sync_gl_cost_center",
        "on_update":"jgb.jgb.doctype.logistics_request.logistics_request.on_payment_entry_submit",
		"on_cancel":["jgb.utils.update_la_status_cancel","jgb.utils.remove_paid_amount_during_cancel","jgb.jgb.doctype.logistics_request.logistics_request.update_lr_for_pi_cancel"],
        "on_submit":['jgb.jgb.teampro.payment_entry.update_leave_salary',"jgb.utils.update_la_status",],
		"before_insert":"jgb.utils.update_paid_amount_in_entry",
        "after_insert":'jgb.utils.update_paid_amount_in_la',
		"on_trash":"jgb.utils.remove_paid_amount_during_deletion",
	},
    "Advance Sales Invoice":{
        "validate":"jgb.jgb.teampro.advance_sales_invoice.fill_address_contact",
        "on_submit":"jgb.jgb.teampro.advance_sales_invoice.validate_advance_sales_invoice",
	},
 
	"Advance Invoice":{
     
        # "after_insert":"jgb.jgb.teampro.advance_invoice.update_advance_amount",
        "on_submit":"jgb.jgb.teampro.advance_invoice.create_new_journal_entry",
        "on_cancel":"jgb.jgb.teampro.advance_invoice.cancel_journal_entry",
     
	},
	"Salary Slip":{
    	'before_insert':'jgb.jgb.teampro.salary_slip.create_expense_salary',
        'validate':'jgb.jgb.teampro.salary_slip.create_pay_now_deduction',
    },
	"Leave Application":{
		'validate':['jgb.utils.update_leave_salary','jgb.jgb.teampro.leave_application.check_leave_validations','jgb.jgb.teampro.leave_application.validate_pending_leave_extension'],
		'on_cancel':'jgb.jgb.teampro.leave_application.cancel_vacation_pay_deductions',
		'on_update_after_submit':['jgb.jgb.teampro.leave_application.apply_pending_leave_extensions','jgb.jgb.teampro.leave_application.update_leave_salary_after_submit'],
	},
    "Payroll Entry":{
		'validate':'jgb.jgb.teampro.payroll_entry.create_additional_salary',
        "on_trash":'jgb.jgb.teampro.payroll_entry.delete_additional_salary',
        "on_cancel":'jgb.jgb.teampro.payroll_entry.delete_additional_salary',
        
		# "before_insert":'jgb.jgb.teampro.payroll_entry.update_party',
	},
	"Leave Allocation":{
		'validate':'jgb.jgb.teampro.leave_allocation.check_allocations',
	},
    "Item":{
        "before_insert":["jgb.jgb.teampro.item.update_item_code_creation", "jgb.jgb.teampro.item.auto_set_is_stock_item"],
		"validate":["jgb.jgb.teampro.item.set_expense_account_from_division_for_item", "jgb.jgb.teampro.item.auto_set_is_stock_item"]
	},
	"Purchase Order":{
		'validate':['jgb.jgb.teampro.purchase_order.update_advance_po','jgb.jgb.teampro.purchase_order.validate_po_mandatory','jgb.jgb.division_cost_center.apply_division_cost_center','jgb.jgb.teampro.purchase_order.set_estimation_margins'],
		'after_insert':'jgb.utils.update_po_status',
		'on_update':['jgb.utils.update_po_status_ref','jgb.jgb.teampro.purchase_order.send_agm_dm_notification_po'],
		'before_cancel':'jgb.utils.restrict_order_cancel_if_linked',
		'on_cancel':'jgb.utils.update_po_status_ref',
        'before_insert': 'jgb.jgb.teampro.purchase_order.set_po_series'
	},
	"Purchase Invoice":{
		"on_submit":["jgb.jgb.teampro.purchase_invoice.check_for_zatca_category","jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.create_division_reclass"],
		"before_validate":"jgb.jgb.teampro.purchase_invoice.preserve_item_tax_template_before_validate",
		"validate":["jgb.jgb.teampro.purchase_invoice.update_zatca_category","jgb.jgb.teampro.purchase_invoice.preserve_item_tax_template", "jgb.jgb.custom.set_expense_account_from_division","jgb.jgb.division_cost_center.apply_division_cost_center"],
		"before_update_after_submit":"jgb.jgb.division_cost_center.apply_division_cost_center",
        "on_update":["jgb.jgb.doctype.logistics_request.logistics_request.purchase_lr_status_update"],
		"on_cancel":["jgb.jgb.doctype.logistics_request.logistics_request.purchase_lr_status_update","jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.cancel_division_reclass"],
        "on_update_after_submit":["jgb.jgb.doctype.logistics_request.logistics_request.purchase_lr_status_update","jgb.jgb.division_cost_center.sync_gl_cost_center"],
	},
	'Purchase Receipt': {
		"on_submit":["jgb.jgb.teampro.purchase_receipt.update_logistic_request","jgb.jgb.teampro.purchase_receipt.update_excess_qty_pr","jgb.jgb.teampro.purchase_receipt.update_pr_in_lr_submit","jgb.utils.update_pr_status_update","jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.create_division_reclass"],
		"after_insert":["jgb.jgb.teampro.purchase_receipt.update_pr_in_lr_draft","jgb.utils.update_pr_status_ref","jgb.jgb.teampro.purchase_receipt.send_notification_to_sales"],
		"on_cancel":["jgb.jgb.teampro.purchase_receipt.update_pr_in_lr_cancel","jgb.utils.update_pr_status_update","jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.cancel_division_reclass"],
		"on_update":["jgb.utils.update_pr_status_update","jgb.jgb.teampro.purchase_receipt.update_pr_currency_validate"],
		"validate":["jgb.jgb.teampro.purchase_receipt.set_expense_account_from_division","jgb.jgb.teampro.purchase_receipt.set_inventory_account_from_division","jgb.jgb.teampro.purchase_receipt.update_pr_currency_validate","jgb.jgb.division_cost_center.apply_division_cost_center"],
		"before_update_after_submit":"jgb.jgb.division_cost_center.apply_division_cost_center",
		"on_update_after_submit":"jgb.jgb.division_cost_center.sync_gl_cost_center",
        # "before_save":"jgb.utils.update_currency"
	},
	
	'Sales Order':{
		"on_submit":"jgb.jgb.teampro.sales_order.create_project_on_so_submit",
		"after_insert":["jgb.utils.update_so_status","jgb.jgb.teampro.sales_order.so_amend_history"],
		"on_update":["jgb.utils.update_status_so", "jgb.jgb.teampro.sales_order.send_agm_dm_notification"],
		"before_cancel":"jgb.utils.restrict_order_cancel_if_linked",
		"on_cancel":"jgb.utils.update_so_status_cancel",
        'before_insert': 'jgb.jgb.teampro.sales_order.set_so_series',
        'validate': ['jgb.jgb.teampro.sales_order.validate_sow_amount',"jgb.jgb.teampro.sales_order.validate_so_mandatory","jgb.jgb.division_cost_center.apply_division_cost_center"],
        "before_update_after_submit":"jgb.jgb.division_cost_center.apply_division_cost_center",
        "on_update_after_submit":["jgb.jgb.teampro.sales_order.capture_so_changes", "jgb.jgb.teampro.sales_order.send_payment_terms_notification"]
	},
	'Lead':{
		"after_insert":["jgb.jgb.teampro.lead.update_lead_name"]
	},
    'Landed Cost Voucher':{
		"validate":["jgb.jgb.teampro.lcv.update_rate_and_total", "jgb.jgb.teampro.lcv.update_total_table"],
		"after_insert":["jgb.jgb.teampro.lcv.update_rate_and_total", "jgb.jgb.teampro.lcv.update_total_table"]
	},
	'Repost Item Valuation':{
		"on_update":["jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.on_repost_item_valuation_update"],
	},
	'Sales Follow UP':{
		"after_insert":"jgb.jgb.teampro.sales_follow_up.update_sfp_status"
	},
	'Opportunity':{
		"after_insert":"jgb.jgb.teampro.opportunity.update_opp_status"
	},
	'Employee':{
		"before_save":"jgb.jgb.teampro.employee.before_save_employee",
		"on_update":["jgb.jgb.teampro.employee.on_update_sales_person","jgb.jgb.teampro.employee.disable_user_employee_status_change"],
        "after_insert":"jgb.jgb.teampro.employee.create_salary_structure_assignment"
	},
	'Employee Promotion':{
		"on_submit":"jgb.jgb.doctype.currency_exchange_upload.currency_exchange_upload.update_internal_work"
	},
	'Quotation':{
		"after_insert":"jgb.utils.update_qn_status",
		"on_update":"jgb.utils.update_status_quotation",
		"validate": ["jgb.jgb.teampro.quotation.validate_items_before_hod_review","jgb.jgb.teampro.quotation.validate_sow_amount","jgb.jgb.teampro.quotation.update_total_est_value","jgb.jgb.teampro.quotation.sync_quote_value"],
        "before_submit":"jgb.jgb.teampro.quotation.validate_qtn_mandatory"
		# "on_submit":"jgb.jgb.custom.update_selling_rate"
		# "on_cancel":"jgb.utils.update_status_quotation"
	},
	'Sales Invoice':{
		"after_insert":"jgb.utils.update_si_status",
		"on_update":"jgb.utils.update_si_status_ref",
		"validate":["jgb.jgb.teampro.sales_invoice.set_expense_account_from_division","jgb.jgb.teampro.sales_invoice.set_income_account_from_division","jgb.jgb.teampro.sales_invoice.set_zatca_exemption_from_category","jgb.jgb.division_cost_center.apply_division_cost_center"],
		"before_update_after_submit":["jgb.jgb.division_cost_center.apply_division_cost_center","jgb.jgb.teampro.sales_invoice.allow_payment_terms_update_after_submit"],
		"on_update_after_submit":"jgb.jgb.division_cost_center.sync_gl_cost_center",
		"on_cancel":["jgb.utils.update_si_status_ref","jgb.jgb.teampro.sales_invoice.reduce_ipc_qty_sold","jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.cancel_division_reclass"],
		"on_submit":["jgb.jgb.teampro.sales_invoice.update_ipc_qty_sold","jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.create_division_reclass"]
        
	},
	'Delivery Note':{
		"after_insert":["jgb.utils.update_dn_status","jgb.jgb.teampro.delivery_note.enqueue_lr_update_dn"],
		"on_submit": ["jgb.jgb.teampro.delivery_note.enqueue_lr_update_dn","jgb.jgb.teampro.delivery_note.send_dn_submission_mail","jgb.jgb.teampro.delivery_note.update_dn_so_qty","jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.create_division_reclass"],
		"on_cancel": ["jgb.jgb.teampro.delivery_note.enqueue_lr_update_dn","jgb.utils.update_dn_status_update","jgb.jgb.teampro.delivery_note.update_dn_so_qty","jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.cancel_division_reclass"],
		"on_update":"jgb.utils.update_dn_status_update",
		"validate":["jgb.jgb.teampro.delivery_note.set_expense_account_from_division","jgb.jgb.division_cost_center.apply_division_cost_center"],
		"before_update_after_submit":"jgb.jgb.division_cost_center.apply_division_cost_center",
		"on_update_after_submit":"jgb.jgb.division_cost_center.sync_gl_cost_center"
	},
	"User":{
        "before_save": "jgb.jgb.teampro.user.update_full_name_hook"
	},
    "Journal Entry":{
        "validate":"jgb.jgb.teampro.journal_entry.update_cost_center",
		"before_update_after_submit":"jgb.jgb.teampro.journal_entry.sync_cost_center_after_submit",
		"after_insert": [
			"jgb.jgb.teampro.journal_entry.auto_submit_depreciation_entry",
			"jgb.jgb.teampro.journal_entry.update_ticket_payment_status"
		],
		"on_submit": [
			"jgb.jgb.teampro.journal_entry.update_ticket_payment_status",
			"jgb.jgb.asset_prepayment.on_prepayment_je_change"
		],
		"on_cancel": [
			"jgb.jgb.teampro.journal_entry.update_ticket_payment_status",
			"jgb.jgb.asset_prepayment.on_prepayment_je_change"
		],
		"on_trash": [
			"jgb.jgb.teampro.journal_entry.update_ticket_payment_status",
			"jgb.jgb.asset_prepayment.on_prepayment_je_change"
		]
	},
	"Asset":{
		'after_insert':'jgb.jgb.asset_prepayment.make_or_update_prepayment_schedule',
		'validate':'jgb.jgb.asset_prepayment.make_or_update_prepayment_schedule',
		'on_submit':'jgb.jgb.asset_prepayment.activate_prepayment_schedules',
		'on_cancel':'jgb.jgb.asset_prepayment.cancel_prepayment_schedules',
		'on_update':'jgb.jgb.asset_prepayment.on_asset_update',
	},
	"Retention Invoice":{
        "on_submit":"jgb.jgb.teampro.retention_invoice.create_new_journal_entry_retention",
        "on_cancel":"jgb.jgb.teampro.retention_invoice.cancel_journal_entry_retention",
	},
	"Customer":{
		"after_insert":"jgb.jgb.teampro.customer.create_new_customer_address",
		"on_update":"jgb.jgb.teampro.customer.create_new_address",
        "before_insert":"jgb.jgb.teampro.customer.set_customer_series"
	},
    "Supplier":{
        "before_insert":"jgb.jgb.teampro.supplier.set_supplier_series"
	},
	"Asset Repair":{
        "validate": ["jgb.jgb.teampro.asset_repair.load_repair_summary", "jgb.jgb.teampro.asset_repair.send_workflow_email"]
        
	},
	'Expense Claim':{
        "before_insert": "jgb.jgb.teampro.expense_claim.expense_claim_before_insert",
		"validate": "jgb.jgb.division_cost_center.apply_division_cost_center",
        # "on_submit":"jgb.jgb.teampro.expense_claim.update_payment_status_submission",
        # "on_cancel":"jgb.jgb.teampro.expense_claim.update_payment_status_cancel",
    #     "on_update_after_submit":"jgb.jgb.teampro.expense_claim.on_update_expense_claim",
	# 	"validate":"jgb.jgb.teampro.expense_claim.on_update_expense_claim"
	}

}

# Scheduled Tasks
# ---------------

scheduler_events = {
# 	"all": [
# 		"jgb.tasks.all"
# 	],
	"daily": [
		"jgb.compliance_alerts.send_compliance_expiry_alerts",
		"jgb.jgb.asset_prepayment.post_prepayment_entries"
	],
# 	"hourly": [
# 		"jgb.tasks.hourly"
# 	],
# 	"weekly": [
# 		"jgb.tasks.weekly"
# 	],
# 	"monthly": [
# 		"jgb.tasks.monthly"
# 	],
"cron": {
        "*/10 * * * *": [
            "jgb.attendance.scheduled_mark_att"
        ],
        "0 1 * * *": [
            "jgb.jgb.teampro.leave_allocation.allocate_sl",
			"jgb.jgb.teampro.leave_allocation.create_update_leave_allocation_new"
        ],
        # 1st of each month, 03:00 — draft payroll-on-cost provision for the month just ended
        "0 3 1 * *": [
            "jgb.jgb.teampro.payroll_provision.scheduled_monthly_provision"
        ]
    }
}

# Testing
# -------

# before_tests = "jgb.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"erpnext.selling.doctype.sales_order.sales_order.make_purchase_order": "jgb.sales_order.make_purchase_order"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Purchase Receipt": "jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.add_purchase_receipt_links",
	"Purchase Invoice": "jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.add_division_reclass_link",
	"Delivery Note": "jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.add_division_reclass_link",
	"Sales Invoice": "jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.add_division_reclass_link",
	"Stock Entry": "jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.add_division_reclass_link",
	"Stock Reconciliation": "jgb.jgb.doctype.division_inventory_reclassification.division_inventory_reclassification.add_division_reclass_link",
	"Asset": "jgb.jgb.asset_prepayment.get_dashboard_data",
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["jgb.utils.before_request"]
# after_request = ["jgb.utils.after_request"]

# Job Events
# ----------
# before_job = ["jgb.utils.before_job"]
# after_job = ["jgb.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"jgb.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

