// Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Time Summary"] = {
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
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => {
				var company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company,
					},
				};
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		// date columns only (fieldname is an ISO date)
		if (!/^\d{4}-\d{2}-\d{2}$/.test(column.fieldname)) return value;

		if (/^\d{2}:\d{2}/.test(value)) {
			// check-in time cells: blue if >= 9h worked, orange if not
			var m = value.match(/(\d{2}):(\d{2}) - (\d{2}):(\d{2})/);
			var hrs = m ? (+m[3] * 60 + +m[4] - +m[1] * 60 - +m[2]) / 60 : 0;
			return (
				"<span style='color:" +
				(hrs >= 9 ? "#318AD8" : "#E67E22") +
				";font-weight:600'>" +
				value +
				"</span>"
			);
		}
		if (value == "P" || value == "WFH")
			return "<span style='color:green;font-weight:600'>" + value + "</span>";
		if (value == "A") return "<span style='color:red;font-weight:600'>" + value + "</span>";
		if (value == "HD")
			return "<span style='color:orange;font-weight:600'>" + value + "</span>";
		if (value == "L")
			return "<span style='color:#318AD8;font-weight:600'>" + value + "</span>";
		if (value == "H" || value == "WO")
			return "<span style='color:#8d99ae'>" + value + "</span>";
		return value;
	},
};
