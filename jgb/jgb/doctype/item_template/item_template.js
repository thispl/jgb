// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item Template", {
	get_template: function (frm) {
		window.location.href = repl(frappe.request.url +
			'?cmd=%(cmd)s&company=%(company)s&payroll_date=%(payroll_date)s&salary_component=%(salary_component)s', {
			cmd: "jgb.jgb.doctype.item_template.item_template.get_template",
			company: frm.doc.company,
			payroll_date: frm.doc.payroll_date,
			// salary_component:frm.doc.salary_component
		});
	},
	process_of_item_creation(frm){
		// console.log("Hii")
		frappe.call({
			method: "jgb.jgb.doctype.item_template.item_template.item_creation",
			args: {
				filename: frm.doc.upload,
			},
			freeze: true,
			freeze_message: 'Creating Item Document....',
			callback: function (r) {
				if (r.message == "OK") {
					frappe.msgprint("Items are Created Successfully,Kindly check after sometime")
				}
			}
		});
	}
});
