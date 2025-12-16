// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Leave Salary', {
    refresh(frm){
        if(!frm.doc.__islocal){
            frm.add_custom_button(__("Print"), function () {
    			var f_name = frm.doc.name;
    			var print_format = "Leave Salary";
    			window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
    				+ "doctype=" + encodeURIComponent("Leave Salary")
    				+ "&name=" + encodeURIComponent(f_name)
    				+ "&trigger_print=1"
    				+ "&format=" + print_format
    				+ "&no_letterhead=0"
    		    ));
            });
        }
    },
    from_date(frm){
        if (frm.doc.basic && frm.doc.salary_payable_days && frm.doc.from_date) {
            let date = frappe.datetime.str_to_obj(frm.doc.from_date);
            let year = date.getFullYear();
            let month = date.getMonth(); 
            let total_days_in_month = new Date(year, month + 1, 0).getDate();
            let earned = (frm.doc.basic / total_days_in_month) * frm.doc.salary_payable_days;
            frm.set_value('earned_basic', earned);
        }
        if(frm.doc.hra && frm.doc.salary_payable_days && frm.doc.from_date){
            let date = frappe.datetime.str_to_obj(frm.doc.from_date);
            let year = date.getFullYear();
            let month = date.getMonth(); 
            let total_days_in_month = new Date(year, month + 1, 0).getDate();
		    frm.set_value('earned_hra',frm.doc.hra/total_days_in_month*frm.doc.salary_payable_days);
		}
	    frm.trigger('calculate_salary_payable_days');
	},
	to_date(frm){
	    frm.trigger('calculate_salary_payable_days');
	},
	basic(frm) {
        if (frm.doc.basic && frm.doc.salary_payable_days && frm.doc.from_date) {
            let date = frappe.datetime.str_to_obj(frm.doc.from_date);
            let year = date.getFullYear();
            let month = date.getMonth(); 
            let total_days_in_month = new Date(year, month + 1, 0).getDate();
            let earned = (frm.doc.basic / total_days_in_month) * frm.doc.salary_payable_days;
            frm.set_value('earned_basic', earned);
        }

		frm.trigger('calculate_gross_salary');
		frm.trigger('calculate_net_pay');
	},
	hra(frm) {
		if(frm.doc.hra && frm.doc.salary_payable_days && frm.doc.from_date){
            let date = frappe.datetime.str_to_obj(frm.doc.from_date);
            let year = date.getFullYear();
            let month = date.getMonth(); 
            let total_days_in_month = new Date(year, month + 1, 0).getDate();
		    frm.set_value('earned_hra',frm.doc.hra/total_days_in_month*frm.doc.salary_payable_days);
		}
		frm.trigger('calculate_gross_salary');
		frm.trigger('calculate_net_pay');
	},
	earned_basic(frm){
	    frm.trigger('calculate_gross_salary');
	    frm.trigger('calculate_net_pay');
	},
	earned_hra(frm){
	    frm.trigger('calculate_gross_salary');
	    frm.trigger('calculate_net_pay');
	},
	ticket_allowance(frm){
	    frm.trigger('calculate_gross_salary');
	    frm.trigger('calculate_net_pay');
	},
	other_allowance(frm){
	    frm.trigger('calculate_gross_salary');
	    frm.trigger('calculate_net_pay');
	},
	visa(frm){
	    frm.trigger('calculate_deduction');
	    frm.trigger('calculate_net_pay');
	},
	air_ticket_expense(frm){
	    frm.trigger('calculate_deduction');
	    frm.trigger('calculate_net_pay');
	},
	course_deduction(frm){
	    frm.trigger('calculate_deduction');
	    frm.trigger('calculate_net_pay');
	},
	other_deduction(frm){
	    frm.trigger('calculate_deduction');
	    frm.trigger('calculate_net_pay');
	},
	calculate_gross_salary(frm){
	    var gross =(frm.doc.earned_basic || 0) + (frm.doc.earned_hra || 0)+ (frm.doc.ticket_allowance || 0) + (frm.doc.other_allowance || 0);
        frm.set_value('gross',gross);
	},
	calculate_deduction(frm){
	    var deduction = (frm.doc.visa || 0) + (frm.doc.air_ticket_expense || 0) + (frm.doc.course_deduction || 0) + (frm.doc.other_deduction || 0);
	    frm.set_value('total_deduction',deduction);
	},
	calculate_net_pay(frm){
	    var net_pay = (frm.doc.gross || 0) - (frm.doc.total_deduction || 0)
	    frm.set_value('net_pay',net_pay);
	},
	calculate_salary_payable_days(frm) {
        if (frm.doc.from_date && frm.doc.to_date) {
            var salary_payable_days = frappe.datetime.get_diff(frm.doc.to_date, frm.doc.from_date) + 1;
            frm.set_value('salary_payable_days', salary_payable_days);
        }
    }

});
