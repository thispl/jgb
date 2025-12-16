// Copyright (c) 2025, contact@half-ware.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Rejoining Form", {
    start_date(frm){
        if(frm.doc.start_date && frm.doc.end_date){
            var end_date = frappe.datetime.obj_to_str(frm.doc.end_date);
            var start_date = frappe.datetime.obj_to_str(frm.doc.start_date);
            var datediff = frappe.datetime.get_day_diff(end_date,start_date);
            frm.set_value("total_leave_in_days",datediff+1);
        }
    },
    end_date(frm){
        if(frm.doc.start_date && frm.doc.end_date){
            var end_date = frappe.datetime.obj_to_str(frm.doc.end_date);
            var start_date = frappe.datetime.obj_to_str(frm.doc.start_date);
            var datediff = frappe.datetime.get_day_diff(end_date,start_date);
            frm.set_value("total_leave_in_days",datediff+1);
        }
    },

    
	    
});
