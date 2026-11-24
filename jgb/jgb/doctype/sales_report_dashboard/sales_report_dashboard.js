// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Report Dashboard", {
    download: function (frm) {
        if (frm.doc.report == 'Sales Summary') {
            if (!frm.doc.company || !frm.doc.from_date || !frm.doc.to_date) {
                frappe.throw(__('To generate the <b>Sales Summary</b>, <b>Company</b>, <b>From Date</b> and <b>To Date</b> are mandatory.'));
            }
            var path = "jgb.jgb.doctype.sales_report_dashboard.sales_summary.download";
            var args = $.param({
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date,
                company: frm.doc.company

            });
            window.location.href = frappe.request.url +
                '?cmd=' + encodeURIComponent(path) + '&' + args;
        }
        if (frm.doc.report == 'Sales Register Report') {
            var path = "jgb.jgb.doctype.sales_report_dashboard.sales_report_dashboard.sales_register_download_summary";
            var args = $.param({
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date,
                company: frm.doc.company

            });
            window.location.href = frappe.request.url +
                '?cmd=' + encodeURIComponent(path) + '&' + args;
        }
    },
    to_date: function (frm) {
        if (frm.doc.from_date && frm.doc.to_date) {
            if (frm.doc.to_date < frm.doc.from_date) {
                frappe.msgprint("To Date cannot be earlier than From Date.");
                frm.set_value("to_date", "");
            }
        }
    },
});
