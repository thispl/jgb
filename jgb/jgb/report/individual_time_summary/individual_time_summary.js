// Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.query_reports["Individual Time Summary"] = {
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
			reqd: 1,
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

		if (data.bold) {
			return "<b>" + value + "</b>";
		}

		if (column.fieldname === "hours" && value !== "") {
			var h = parseFloat(value);
			if (!isNaN(h))
				return (
					"<span style='color:" +
					(h >= 9 ? "#318AD8" : "#E67E22") +
					";font-weight:600'>" +
					value +
					"</span>"
				);
		}

		if (column.fieldname === "status") {
			if (value == "Present" || value == "Work From Home")
				return "<span style='color:green;font-weight:600'>" + value + "</span>";
			if (value == "Absent")
				return "<span style='color:red;font-weight:600'>" + value + "</span>";
			if (value == "Half Day")
				return "<span style='color:orange;font-weight:600'>" + value + "</span>";
			if (value == "On Leave")
				return "<span style='color:#318AD8;font-weight:600'>" + value + "</span>";
			if (value == "Holiday" || value == "Weekly Off")
				return "<span style='color:#8d99ae'>" + value + "</span>";
			if (value == "Unmarked") return "<span style='color:#e67e22'>" + value + "</span>";
		}
		return value;
	},
};
