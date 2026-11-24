// Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.query_reports["JGB Project Profitability"] = {
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
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today().slice(0, 4) + "-01-01",
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
			get_query: function () {
				var company = frappe.query_report.get_filter_value("company");
				return company ? { filters: { company: company } } : {};
			},
		},
		{
			fieldname: "sales_order",
			label: __("Sales Order"),
			fieldtype: "Link",
			options: "Sales Order",
			get_query: function () {
				var company = frappe.query_report.get_filter_value("company");
				return company ? { filters: { company: company, docstatus: 1 } } : {};
			},
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "division",
			label: __("Division"),
			fieldtype: "Link",
			options: "Division",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		if (column.fieldname === "est_vs_actual" && data.est_vs_actual != null) {
			var color = flt(data.est_vs_actual) >= 0 ? "green" : "red";
			value = `<span style="color:${color};font-weight:bold">${value}</span>`;
		}
		if (column.fieldname === "net_profit" || column.fieldname === "profit_pct") {
			if (flt(data.net_profit) < 0) {
				value = `<span style="color:red">${value}</span>`;
			}
		}
		if (data.is_total) {
			value = `<b>${value}</b>`;
		}
		return value;
	},
};
