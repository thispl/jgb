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
# app_include_css = "/assets/jgb/css/jgb.css"
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
# doctype_js = {"doctype" : "public/js/doctype.js"}
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
		"jgb.jgb.custom.return_account_total",
		"jgb.jgb.custom.get_sales_person",
		"jgb.jgb.custom.receivable_report",
		"jgb.jgb.custom.get_accounts_ledger",
		"jgb.jgb.custom.statement_of_account",
		"jgb.jgb.custom.supplier_statement_of_account",
		"jgb.jgb.custom.receipt_report",
		"jgb.jgb.custom.return_total_amt_consolidate",
		"jgb.jgb.custom.ageing_report_test",
		"jgb.jgb.custom.return_account_summary_total",
		"jgb.jgb.custom.return_total_amt1"
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

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Salary Slip": "jgb.overrides.CustomSalarySlip"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	# "Delivery Note": {
	# 	"on_submit": "jgb.jgb.custom.update_logistics_status_from_dn",
	# 	"validate": "jgb.jgb.custom.update_logistics_status_from_dn",
	# 	"on_cancel": "jgb.jgb.custom.update_logistics_status_from_dn",
	# },
	"Payment Entry":{
        "on_update":"jgb.jgb.doctype.logistics_request.logistics_request.on_payment_entry_submit",
		"on_cancel":"jgb.jgb.doctype.logistics_request.logistics_request.update_lr_for_pi_cancel",
        "on_submit":'jgb.jgb.custom.update_leave_salary',
	},
 
	"Advance Invoice":{
     
        # "after_insert":"jgb.jgb.custom.update_advance_amount",
        "on_submit":"jgb.jgb.custom.create_new_journal_entry",
        "on_cancel":"jgb.jgb.custom.cancel_journal_entry",
     
     },
	"Leave Application":{
		'validate':'jgb.jgb.custom.check_leave_validations',
	},
    "Payroll Entry":{
		'validate':'jgb.jgb.custom.create_additional_salary',
        "on_trash":'jgb.jgb.custom.delete_additional_salary',
        
		# "before_insert":'jgb.jgb.custom.update_party',
	},
	"Leave Allocation":{
		'validate':'jgb.jgb.custom.check_allocations',
	},
	"Landed Cost Voucher":{
		'validate':'jgb.jgb.custom.update_pi_items',
	},
	"Purchase Order":{
		'validate':'jgb.jgb.custom.update_advance_po',
		'after_insert':'jgb.utils.update_po_status',
		'on_update':'jgb.utils.update_po_status_ref',
		'on_cancel':'jgb.utils.update_po_status_ref',
        'before_insert': 'jgb.jgb.custom.set_po_series'
	},
	"Purchase Invoice":{
        "on_update":["jgb.jgb.doctype.logistics_request.logistics_request.purchase_lr_status_update"],
		"on_cancel":["jgb.jgb.doctype.logistics_request.logistics_request.purchase_lr_status_update"],
        "on_update_after_submit":["jgb.jgb.doctype.logistics_request.logistics_request.purchase_lr_status_update"],
	},
	'Purchase Receipt': {
		"on_submit":["jgb.jgb.custom.update_logistic_request","jgb.jgb.custom.update_excess_qty_pr","jgb.jgb.custom.update_pr_in_lr_submit","jgb.utils.update_pr_status_update"],
		"after_insert":["jgb.jgb.custom.update_pr_in_lr_draft","jgb.utils.update_pr_status_ref","jgb.jgb.custom.send_notification_to_sales"],
		"on_cancel":["jgb.jgb.custom.update_pr_in_lr_cancel","jgb.utils.update_pr_status_update"],
		"on_update":["jgb.utils.update_pr_status_update","jgb.jgb.custom.update_pr_currency"],
		"validate":["jgb.jgb.custom.set_expense_account_from_division","jgb.jgb.custom.set_inventory_account_from_division"],
        # "before_save":"jgb.utils.update_currency"
	},
	
	'Sales Order':{
		"on_submit":"jgb.jgb.custom.create_project_on_so_submit",
		"after_insert":"jgb.utils.update_so_status",
		"on_update":"jgb.utils.update_status_so",
		"on_cancel":"jgb.utils.update_so_status_cancel",
        'before_insert': 'jgb.jgb.custom.set_so_series',
        'validate': ['jgb.jgb.custom.validate_sow_amount']
	},
	'Lead':{
		"after_insert":["jgb.jgb.custom.update_lead_name"]
	},
	'Sales Follow UP':{
		"after_insert":"jgb.jgb.custom.update_sfp_status"
	},
	'Opportunity':{
		"after_insert":"jgb.jgb.custom.update_opp_status"
	},
	'Employee':{
		"before_save":"jgb.jgb.custom.before_save_employee",
		"on_update":"jgb.jgb.custom.on_update_sales_person"
	},
	'Employee Promotion':{
		"on_submit":"jgb.jgb.doctype.currency_exchange_upload.currency_exchange_upload.update_internal_work"
	},
	'Quotation':{
		"after_insert":"jgb.utils.update_qn_status",
		"on_update":"jgb.utils.update_status_quotation",
		"validate": ["jgb.jgb.custom.validate_items_before_hod_review","jgb.jgb.custom.validate_sow_amount"],
		# "on_submit":"jgb.jgb.custom.update_selling_rate"
		# "on_cancel":"jgb.utils.update_status_quotation"
	},
	'Sales Invoice':{
		"after_insert":"jgb.utils.update_si_status",
		"on_update":"jgb.utils.update_si_status_ref",
		"on_cancel":"jgb.utils.update_si_status_ref"
	},
	'Delivery Note':{
		"after_insert":["jgb.utils.update_dn_status","jgb.jgb.custom.update_logistics_status_from_dn"],
		"on_submit": ["jgb.jgb.custom.update_logistics_status_from_dn","jgb.jgb.custom.send_mail_for_dn"],
		"on_cancel": ["jgb.jgb.custom.update_logistics_status_from_dn","jgb.utils.update_dn_status_update"],
		"on_update":"jgb.utils.update_dn_status_update",
		"validate":["jgb.jgb.custom.set_expense_account_from_division",]
	},
	"User":{
        "before_save": "jgb.jgb.custom.update_full_name_hook"
	},
	"Retention Invoice":{
        "on_submit":"jgb.jgb.custom.create_new_journal_entry_retention",
        "on_cancel":"jgb.jgb.custom.cancel_journal_entry_retention",
	},
	"Customer":{
		"after_insert":"jgb.jgb.custom.create_new_address",
	}
	# 'Expense Claim':{
	# 	"validate":"jgb.jgb.custom.restrict_expense_claim"
	# }

}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"jgb.tasks.all"
# 	],
# 	"daily": [
# 		"jgb.tasks.daily"
# 	],
# 	"hourly": [
# 		"jgb.tasks.hourly"
# 	],
# 	"weekly": [
# 		"jgb.tasks.weekly"
# 	],
# 	"monthly": [
# 		"jgb.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "jgb.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "jgb.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "jgb.task.get_dashboard_data"
# }

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

