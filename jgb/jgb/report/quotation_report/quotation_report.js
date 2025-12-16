frappe.query_reports["Quotation Report"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.year_start(),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.year_end(),
			"reqd": 1
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname":"sales_person",
			"label": __("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person"
		},
		{
			"fieldname":"docstatus",
			"label":__("Document Status"),
			"fieldtype":"Select",
			"options":["","Draft","Open","Replied","Partially Ordered","Ordered","Lost","Expired"],
			"width": "100px"
		},
		{
			"fieldname":"order_type",
			"label": __("Order Type"),
			"fieldtype": "Select",
			"options": ["", "Sales", "Project"]
		},
		{
			"fieldname": "amount_condition",
			"label": __("Amount Condition"),
			"fieldtype": "Select",
			"options": [">", "<", "=", "between"],
			"default": ">"
		},
		{
			"fieldname": "amount_from",
			"label": __("Amount From"),
			"fieldtype": "Currency"
		},
		{
			"fieldname": "amount_to",
			"label": __("Amount To"),
			"fieldtype": "Currency",
			"depends_on": "eval: doc.amount_condition == 'between'"
		}
	]
};
