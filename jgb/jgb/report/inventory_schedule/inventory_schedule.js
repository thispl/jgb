// Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.query_reports["Inventory Schedule"] = {
	tree: true,

	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "report_type",
			label: __("Report Type"),
			fieldtype: "Select",
			options: "Summary\nDivisionwise",
			default: "Summary",
			reqd: 1,
			description: __(
				"Summary: one line per division. Divisionwise: items listed under each division"
			),
		},
		{
			fieldname: "to_date",
			label: __("As of Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			description: __("Stock balance as of this date"),
		},
		{
			fieldname: "division",
			label: __("Division"),
			fieldtype: "Link",
			options: "Division",
		},
	],
};
