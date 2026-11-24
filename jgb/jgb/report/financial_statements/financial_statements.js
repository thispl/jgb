// Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.query_reports["Financial Statements"] = {
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
			fieldname: "statement",
			label: __("Statement"),
			fieldtype: "Select",
			options: "Income Statement\nBalance Sheet\nCash Flow",
			default: "Income Statement",
			reqd: 1,
		},
		{
			fieldname: "report_type",
			label: __("Report Type"),
			fieldtype: "Select",
			options: "Summary\nSummary without Comparison\nDivisionwise",
			default: "Summary",
			reqd: 1,
			description: __(
				"Summary without Comparison shows a single period column; Divisionwise shows one column per Cost Center plus a Total column"
			),
			depends_on: "eval:doc.statement !== 'Cash Flow'",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today().slice(0, 4) + "-01-01",
			reqd: 1,
			description: __("First column covers this range; the second column shows the previous month / year of the same span"),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "compare_with",
			label: __("Compare With"),
			fieldtype: "Select",
			options: "Auto\nSame Period Last Year\nPrevious Period\nNone",
			default: "Auto",
			description: __(
				"Auto: year-over-year for multi-month ranges, previous month for a single month"
			),
			depends_on: "eval:doc.report_type === 'Summary'",
		},
		{
			fieldname: "include_details",
			label: __("Show Account Details"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
