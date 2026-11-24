// Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Report Dashboard", {
	refresh(frm) {
		if (!frm.doc.report) {
			frm.set_value("report", "Monthly Time Summary");
		}
		if (!frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_user_default("Company"));
		}
		if (!frm.doc.from_date) {
			frm.set_value("from_date", frappe.datetime.month_start());
		}
		if (!frm.doc.to_date) {
			frm.set_value("to_date", frappe.datetime.get_today());
		}
	},

	view_report(frm) {
		if (frm.doc.report === "Individual Time Summary" && !frm.doc.employee) {
			frappe.throw(__("Please select an employee for the Individual Time Summary."));
		}
		let filters = attendance_report_filters(frm);
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
		if (frm.doc.report === "Individual Time Summary" && !frm.doc.employee) {
			frappe.throw(__("Please select an employee for the Individual Time Summary."));
		}
		let url = frappe.urllib.get_full_url(
			"/api/method/jgb.jgb.doctype.attendance_report_dashboard.attendance_report_dashboard.download?" +
				"report=" +
				encodeURIComponent(frm.doc.report) +
				"&company=" +
				encodeURIComponent(frm.doc.company) +
				"&from_date=" +
				encodeURIComponent(frm.doc.from_date || "") +
				"&to_date=" +
				encodeURIComponent(frm.doc.to_date || "") +
				"&employee=" +
				encodeURIComponent(frm.doc.employee || "")
		);
		window.open(url);
	},

	print(frm) {
		if (!frm.doc.company) {
			frappe.throw(__("Kindly choose the company."));
		}
		if (frm.doc.report === "Individual Time Summary" && !frm.doc.employee) {
			frappe.throw(__("Please select an employee for the Individual Time Summary."));
		}
		let print_formats = {
			"Monthly Time Summary": "Monthly Time Summary Dashboard",
			"Individual Time Summary": "Individual Time Summary Dashboard",
		};
		const open_pdf = () =>
			window.open(
				frappe.urllib.get_full_url(
					"/api/method/frappe.utils.print_format.download_pdf?" +
						"doctype=" +
						encodeURIComponent("Attendance Report Dashboard") +
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

function attendance_report_filters(frm) {
	let filters = {
		company: frm.doc.company,
		from_date: frm.doc.from_date,
		to_date: frm.doc.to_date,
		employee: frm.doc.employee,
	};
	filters.report_name = frm.doc.report || "Monthly Time Summary";
	return filters;
}
