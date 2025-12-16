// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Accounts Report Dashboard", {
    refresh(frm){
		if(frm.doc.report =="Ledger Summary Report"){
			frm.set_query("account",function () {
				return{
					filters:{
					"company":frm.doc.company
					}
				}
			})
		}
	},
	customer(frm){
		if (frm.doc.report=='Consolidated Customer and Supplier Ledger Summary'){
			if(frm.doc.customer){
				if(frm.doc.supplier){
					frm.set_value('supplier','')
				}
			}
		}
	},
	supplier(frm){
		if (frm.doc.report=='Consolidated Customer and Supplier Ledger Summary'){
			if(frm.doc.supplier){
				if(frm.doc.customer){
					frm.set_value('customer','')
				}
			}
		}
	},
	download: function (frm) {
		if (frm.doc.report == 'Group Summary Report') {
			var path = "jgb.jgb.doctype.accounts_report_dashboard.group_summary_report.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&account=%(account)s&company=%(company)s'
		}
        else if (frm.doc.report == 'Customer Ledger Report') {
			var path = "jgb.jgb.doctype.accounts_report_dashboard.customer_ledger_report.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&company=%(company)s&customer=%(customer)s'
		}
        else if (frm.doc.report == 'Ledger Summary Report') {
			var path = "jgb.jgb.doctype.accounts_report_dashboard.ledger_summary.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&company=%(company)s&account=%(account)s'
		}
        else if (frm.doc.report == 'Sales Person Wise Income Report') {
			var path = "jgb.jgb.doctype.accounts_report_dashboard.sales_person_report.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&sales_person_user=%(sales_person_user)s&company=%(company)s'
		}
		else if (frm.doc.report == 'Accounts Receivable Report') {
			var path = "jgb.jgb.doctype.accounts_report_dashboard.receivable_report.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&project=%(project)s&so_no=%(so_no)s'
		}
		else if (frm.doc.report == 'Statement of Account') {
			if (!frm.doc.company){
				frappe.msgprint('Kindly choose the company.')
			}
			frappe.msgprint()
			var path = "jgb.jgb.doctype.accounts_report_dashboard.statement_of_account.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&company=%(company)s&customer=%(customer)s'
		} 
		else if (frm.doc.report == 'Accounts Ledger Summary') {
			if (!frm.doc.company){
				frappe.msgprint('Kindly choose the company.')
			}
			var path = "jgb.jgb.doctype.accounts_report_dashboard.accounts_ledger.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&company=%(company)s&customer=%(customer)s'
		}
		else if (frm.doc.report == 'Receipt Report') {
			if (!frm.doc.company){
				frappe.msgprint('Kindly choose the company.')
			}
			var path = "jgb.jgb.doctype.accounts_report_dashboard.receipt_report.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&company=%(company)s'
		}
		else if (frm.doc.report == 'Accounts Receivable Aging Report') {
			if (!frm.doc.company){
				frappe.msgprint('Kindly choose the company.')
			}
			else if (frm.doc.customer && frm.doc.company){
				var path = "jgb.jgb.doctype.accounts_report_dashboard.accounts_aging.download"
			    var args = 'customer=%(customer)s&company=%(company)s'
			}
			else if (!frm.doc.customer){
				frappe.msgprint('Kindly choose the customer.')
			}
			
		}
		else if (frm.doc.report == 'Consolidated Ledger Report') {
			if (!frm.doc.company){
				frappe.msgprint('Kindly choose the company.')
			}
			var path = "jgb.jgb.doctype.accounts_report_dashboard.consolidated_ledger_report.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&company=%(company)s&account=%(account)s'
		}
		else if (frm.doc.report == 'Group Account Summary Report') {
			if (!frm.doc.company){
				frappe.msgprint('Kindly choose the company.')
			}
			var path = "jgb.jgb.doctype.accounts_report_dashboard.group_account_summary.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&company=%(company)s&account=%(account)s'
		}
		else if (frm.doc.report == 'Supplier Statement of Account') {
			if (!frm.doc.company){
				frappe.msgprint('Kindly choose the company.')
			}
			// frappe.set_route('query-report', 'Consolidated Customer and Supplier Ledger Summary', {
			// 	party_type: 'Customer',
			// 	from_date: frm.doc.from_date,
			// 	to_date: frm.doc.to_date
			// });

			var path = "jgb.jgb.doctype.accounts_report_dashboard.supplier_statement_of_account.download"
			var args = 'from_date=%(from_date)s&to_date=%(to_date)s&company=%(company)s&supplier=%(supplier)s'
		}
		else if (frm.doc.report=='Consolidated Customer and Supplier Ledger Summary'){
			if(frm.doc.customer){
				frappe.set_route('query-report', 'Consolidated Customer and Supplier Ledger Summary', {
					party_type: 'Customer',
					from_date: frm.doc.from_date,
					to_date: frm.doc.to_date,
					customer:frm.doc.customer
				}).then(() => {
					frappe.query_report.refresh();
				});
			}
			else if(frm.doc.supplier){
				frappe.set_route('query-report', 'Consolidated Customer and Supplier Ledger Summary', {
					party_type: 'Supplier',
					from_date: frm.doc.from_date,
					to_date: frm.doc.to_date,
					supplier: frm.doc.supplier
				}).then(() => {
					frappe.query_report.refresh();
				});
			}
		}
        if (path) {
			window.location.href = repl(frappe.request.url +
				'?cmd=%(cmd)s&%(args)s', {
				cmd: path,
				args: args,
				from_date : frm.doc.from_date,
				to_date : frm.doc.to_date,	
				company : frm.doc.company,
				account:frm.doc.account,
                customer:frm.doc.customer,
				sales_person_user:frm.doc.sales_person,
				so_no:frm.doc.sales_order,
				project:frm.doc.project,
				supplier:frm.doc.supplier
				

			});
		}
	
    },
	print:function(frm){
		if(frm.doc.report=="Group Summary Report"){
			var f_name = frm.doc.name
				var print_format = "Group Summary Report Dashboard";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Customer Ledger Report"){
			var f_name = frm.doc.name
				var print_format = "Customer Ledger Report Dashboard";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Ledger Summary Report"){
			var f_name = frm.doc.name
				var print_format = "Ledger Summary Report Dashboard";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Sales Person Wise Income Report"){
			var f_name = frm.doc.name
				var print_format = "Sales Person Wise Income Report Dashboard";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Accounts Receivable Report"){
			var f_name = frm.doc.name
				var print_format = "Accounts Receivable Report Dashboard";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Accounts Ledger Summary"){
			var f_name = frm.doc.name
				var print_format = "Accounts Ledger Summary Report Dashboard";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Statement of Account"){
			var f_name = frm.doc.name
				var print_format = "Statement of Accounts Report";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Supplier Statement of Account"){
			var f_name = frm.doc.name
				var print_format = "Supplier Statement of Account";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Receipt Report"){
			var f_name = frm.doc.name
				var print_format = "Receipt Report Dashboard";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Consolidated Ledger Report"){
			var f_name = frm.doc.name
				var print_format = "Consolidated Ledger Report";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Accounts Receivable Aging Report"){
			var f_name = frm.doc.name
				var print_format = "Accounts Receivabale";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}
		else if(frm.doc.report=="Group Account Summary Report"){
			var f_name = frm.doc.name
				var print_format = "Group Account Summary Report";
				window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
					+ "doctype=" + encodeURIComponent("Accounts Report Dashboard")
					+ "&name=" + encodeURIComponent(f_name)
					+ "&trigger_print=1"
					+ "&format=" + print_format
					+ "&no_letterhead=0"
				));
		}

	}
});

