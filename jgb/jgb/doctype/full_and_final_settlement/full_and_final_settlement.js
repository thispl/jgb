// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Full and Final Settlement", {
    refresh(frm){
        if(!frm.doc.__islocal){
            frm.add_custom_button(__("Print"), function () {
    			var f_name = frm.doc.name;
    			var print_format = "Full and Final Settlement";
    			window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
    				+ "doctype=" + encodeURIComponent("Full and Final Settlement")
    				+ "&name=" + encodeURIComponent(f_name)
    				+ "&trigger_print=1"
    				+ "&format=" + print_format
    				+ "&no_letterhead=0"
    		    ));
            });
        }
    },
	employee(frm) {
        frm.trigger('update_working_days')
	},
    // last_day_of_work(frm){
    //     frm.trigger('update_working_days')
    // },
    update_working_days(frm){
        if (frm.doc.date_of_joining && frm.doc.last_day_of_work && frm.doc.employee){
            frappe.call({
            method:'jgb.jgb.doctype.full_and_final_settlement.full_and_final_settlement.get_working_days',
            args:{
                employee : frm.doc.employee,
                last: frm.doc.last_day_of_work,
                doj:frm.doc.date_of_joining
            },
            callback:function(r){
                    frm.set_value('total_working_days',r.message.working_days)
                    frm.set_value('total_worked',r.message.working_days)
                    frm.set_value('employment_duration',r.message.employment_period_years)
            }
        })
        }
        
    },
    pay_start_date(frm){
        if (frm.doc.pay_start_date){
            frm.trigger('update_p_a')
        }
    },
    pay_end_date(frm){
        if (frm.doc.pay_end_date){
            frm.trigger('update_p_a')
        }
    },
    update_p_a(frm){
        if (frm.doc.pay_start_date && frm.doc.pay_end_date){
            frappe.call({
            method:'jgb.jgb.doctype.full_and_final_settlement.full_and_final_settlement.get_pre_abs',
            args:{
                employee : frm.doc.employee,
                start: frm.doc.pay_start_date,
                end:frm.doc.pay_end_date
            },
            callback:function(r){
                    frm.set_value('noof_days_worked',r.message.pre)
                    frm.set_value('absent_days',r.message.abs)
                    frm.set_value('total_ot',r.message.ot)
            }
        })
        }
        
    },
    last_day_of_work(frm) {
    if (frm.doc.last_day_of_work) {
        frappe.call({
            method: "jgb.jgb.doctype.full_and_final_settlement.full_and_final_settlement.get_annual_vacation_balance",
            args: {
                employee: frm.doc.employee,
                last_day_of_work: frm.doc.last_day_of_work
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value("annual_leave_balance", r.message);

                    let basic = frm.doc.basic_salary || 0;
                    let hra = frm.doc.hra || 0;

                    let amount = 0;
                    if (frm.doc.annual_leave_balance) {
                        let now = moment();
                        let daysInMonth = now.daysInMonth(); 


                        amount = ((basic/daysInMonth) + (hra/daysInMonth)) * frm.doc.annual_leave_balance;
                    }

                    frm.set_value("leave_balance_amount", amount);
                    
                }else{
                    frm.set_value("annual_leave_balance", "");
                    frm.set_value("leave_balance_amount", "");
                }
            }
        });
    }
    else {
        frm.set_value("annual_leave_balance", "");
        frm.set_value("leave_balance_amount", "");
    }
}
 
});


    
