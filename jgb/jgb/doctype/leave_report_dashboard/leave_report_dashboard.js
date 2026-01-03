// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Leave Report Dashboard", {
    refresh(frm) {
        frm.disable_save();
    },
    employee(frm) {
        frm.trigger('load_leave_details');
    },
    year(frm) {
        frm.trigger('load_leave_details');
    },

    load_leave_details(frm) {
        if (!frm.doc.employee || !frm.doc.year) {
            frm.fields_dict.leave_html.$wrapper.html('');
            return;
        }

        frappe.call({
            method: 'jgb.jgb.doctype.leave_report_dashboard.leave_report_dashboard.get_leave_details',
            args: {
                employee: frm.doc.employee,
                year: frm.doc.year
            },
            callback: function(r) {
                frm.fields_dict.leave_html.$wrapper.html(r.message || '');
            }
        });
    }
});
