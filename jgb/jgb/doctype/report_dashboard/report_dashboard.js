// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Report Dashboard", {
	download: function(frm){
        if(frm.doc.report == 'Salary Register Report') {
            var path = "jgb.jgb.doctype.report_dashboard.report_dashboard.download_dynamic_salary_report";
            var args = $.param({
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date,
                company: frm.doc.company
                
            });
            window.location.href = frappe.request.url + 
                                    '?cmd=' + encodeURIComponent(path) + '&' + args;
        }

        if(frm.doc.report == 'WPS Report') {
            var path = "jgb.jgb.doctype.report_dashboard.report_dashboard.download_dynamic_wps_report";
            var args = $.param({
                from_date: frm.doc.from_date,
                to_date: frm.doc.to_date,
                company: frm.doc.company
                
            });
            window.location.href = frappe.request.url + 
                                    '?cmd=' + encodeURIComponent(path) + '&' + args;
        }
    },
    to_date: function(frm) {
        if(frm.doc.from_date && frm.doc.to_date) {
            if(frm.doc.to_date < frm.doc.from_date) {
                frappe.msgprint("To Date cannot be earlier than From Date.");
                frm.set_value("to_date", ""); 
            }
        }
    },
});
