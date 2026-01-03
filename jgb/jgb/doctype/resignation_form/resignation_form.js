// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Resignation Form", {
	refresh(frm) {
        if (frm.doc.workflow_state =="Approved"){
	        frm.add_custom_button(__('F & F Statement'), function() {
                frappe.db.get_value('Full and Final Settlement',{'employee': frm.doc.employee },'name')
                .then(r => {
                if(r.message && Object.entries(r.message).length === 0){
                    frappe.route_options = { 'employee':frm.doc.employee,'employee_name': frm.doc.employee_name}
                    frappe.set_route('Form','Full and Final Settlement','new-full-and-final-settlement-1')
                    
                }
                else{
                frappe.set_route('Form','Full and Final Settlement',r.message.name)
                }
            
                })
                
            });
		   }

        if (frm.doc.workflow_state === "Draft") {
            frm.add_custom_button(__('Apply No Due'), function () {
                frappe.db.get_value('No due',{ employee: frm.doc.employee },'name'
                ).then(r => {
                    if (r.message && r.message.name) {
                        frappe.set_route('Form', 'No due', r.message.name);
                    } 
                    else {
                        frappe.route_options = {
                            employee: frm.doc.employee,
                            employee_name: frm.doc.employee_name
                        };
                        frappe.set_route('Form', 'No due', 'new-no-due-1');
                    }
                });
            });
        }

	},
});
