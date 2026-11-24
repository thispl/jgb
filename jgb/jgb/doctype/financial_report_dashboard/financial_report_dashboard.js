// Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Financial Report Dashboard", {
	refresh(frm) {
		if (!frm.doc.report_type) {
			frm.set_value("report_type", "Summary");
		}
		if (!frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_user_default("Company"));
		}
		if (!frm.doc.from_date) {
			frm.set_value("from_date", frappe.datetime.get_today().slice(0, 4) + "-01-01");
		}
		if (!frm.doc.to_date) {
			frm.set_value("to_date", frappe.datetime.get_today());
		}
	},

	view_report(frm) {
		let filters = financial_report_filters(frm);
		let report_name = filters.report_name;
		delete filters.report_name;
		frappe.set_route("query-report", report_name, filters).then(() => {
			frappe.query_report && frappe.query_report.refresh();
		});
	},

	download(frm) {
		if (!frm.doc.company) {
			frappe.throw(__("Kindly choose the company."));
		}
		let url = frappe.urllib.get_full_url(
			"/api/method/jgb.jgb.doctype.financial_report_dashboard.financial_report_dashboard.download?" +
				"report=" +
				encodeURIComponent(frm.doc.report) +
				"&company=" +
				encodeURIComponent(frm.doc.company) +
				"&from_date=" +
				encodeURIComponent(frm.doc.from_date || "") +
				"&to_date=" +
				encodeURIComponent(frm.doc.to_date || "") +
				"&project=" +
				encodeURIComponent(frm.doc.project || "") +
				"&sales_order=" +
				encodeURIComponent(frm.doc.sales_order || "") +
				"&customer=" +
				encodeURIComponent(frm.doc.customer || "") +
				"&division=" +
				encodeURIComponent(frm.doc.division || "") +
				"&report_type=" +
				encodeURIComponent(frm.doc.report_type || "Summary") +
				"&show_account_details=" +
				(frm.doc.show_account_details ? 1 : 0)
		);
		window.open(url);
	},

	print(frm) {
		if (!frm.doc.company) {
			frappe.throw(__("Kindly choose the company."));
		}
		let print_formats = {
			"Income Statement": "Income Statement Dashboard",
			"Balance Sheet": "Balance Sheet Dashboard",
			"Cash Flow": "Cash Flow Dashboard",
			"Project Profitability": "Project Profitability Dashboard",
			"Inventory Schedule": "Inventory Schedule Dashboard",
		};
		const open_pdf = () =>
			window.open(
				frappe.urllib.get_full_url(
					"/api/method/frappe.utils.print_format.download_pdf?" +
						"doctype=" +
						encodeURIComponent("Financial Report Dashboard") +
						"&name=" +
						encodeURIComponent(frm.doc.name) +
						"&trigger_print=1" +
						"&format=" +
						encodeURIComponent(print_formats[frm.doc.report]) +
						"&no_letterhead=0"
				)
			);
		// print format renders from the saved doc — persist unsaved filter changes first
		if (frm.is_dirty()) {
			frm.save().then(open_pdf);
		} else {
			open_pdf();
		}
	},
});

function financial_report_filters(frm) {
	let filters = {
		company: frm.doc.company,
		from_date: frm.doc.from_date,
		to_date: frm.doc.to_date,
	};

	if (frm.doc.report === "Project Profitability") {
		filters.report_name = "JGB Project Profitability";
		filters.project = frm.doc.project;
		filters.sales_order = frm.doc.sales_order;
		filters.customer = frm.doc.customer;
		filters.division = frm.doc.division;
	} else if (frm.doc.report === "Inventory Schedule") {
		filters.report_name = "Inventory Schedule";
		filters.report_type = frm.doc.report_type || "Summary";
		filters.division = frm.doc.division;
	} else {
		// Income Statement / Balance Sheet / Cash Flow -> "Financial Statements" report
		filters.report_name = "Financial Statements";
		filters.statement = frm.doc.report;
		filters.report_type =
			frm.doc.report === "Cash Flow" ? "Summary" : frm.doc.report_type || "Summary";
		filters.include_details = frm.doc.show_account_details ? 1 : 0;
	}
	return filters;
}
