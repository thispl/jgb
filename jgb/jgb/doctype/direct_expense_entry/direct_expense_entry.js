// Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Direct Expense Entry', {
	onload: function(frm) {
		// Apply dynamic filters based on selected Company
		frm.trigger('set_queries');
		frm.trigger('toggle_tax_fields');
		if (frm.is_new() && frm.doc.leave_application) {
			setTimeout(() => {
				if (frm.doc.expenses.length === 0) {
					frappe.db.get_value('Account', {
						'account_number': '5151',
						'company': frm.doc.company
					}, 'name', (r) => {
						if (r && r.name) {
							let child = frm.add_child('expenses');
							child.expense_account = r.name;

							frm.refresh_field('expenses');
						}
					});
				}
			}, 1000);
		}
	},
	refresh: function(frm) {
		frm.trigger('set_queries');
		frm.trigger('toggle_tax_fields');
		calculate_total(frm);

		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
					company: frm.doc.company,
					categorize_by: "",
					show_cancelled_entries: frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "General Ledger");
			}, "fa fa-table");
		}
	},
	company: function(frm) {
		// Clear selected accounts to avoid cross-company database anomalies
		frm.set_value('bank_cash_account', '');
		frm.clear_table('expenses');
		frm.refresh_field('expenses');
		frm.set_value('include_tax', 0);
		frm.set_value('tax_account', '');
		frm.set_value('tax_amount', 0);
		frm.trigger('toggle_tax_fields');
		frm.trigger('set_queries');
	},
	include_tax: function(frm) {
		frm.trigger('toggle_tax_fields');
		calculate_total(frm);
	},
	tax_amount: function(frm) {
		calculate_total(frm);
	},
	set_queries: function(frm) {
		if (!frm.doc.company) return;

		frm.set_query('bank_cash_account', function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
					account_type: ['in', ['Bank', 'Cash']]
				}
			};
		});

		frm.set_query('expense_account', 'expenses', function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
					root_type: 'Expense'
				}
			};
		});

		frm.set_query('cost_center', 'expenses', function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			};
		});

		frm.set_query('tax_account', function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
					disabled: 0,
					account_type: 'Tax'
				}
			};
		});
	},
	toggle_tax_fields: function(frm) {
		if (frm.doc.include_tax) {
			frm.toggle_display('tax_account', true);
			frm.toggle_display('tax_amount', true);
			frm.toggle_reqd('tax_account', true);
		} else {
			frm.toggle_display('tax_account', false);
			frm.toggle_display('tax_amount', false);
			frm.toggle_reqd('tax_account', false);
			frm.set_value('tax_amount', 0);
		}
	}
});

frappe.ui.form.on('Direct Expense Entry Account', {
	amount: function(frm, cdt, cdn) {
		calculate_total(frm);
	},
	expenses_remove: function(frm, cdt, cdn) {
		calculate_total(frm);
	},
	expenses_add: function(frm, cdt, cdn) {
		// Proactively set the default cost center from the Company
		if (frm.doc.company) {
			frappe.db.get_value('Company', frm.doc.company, 'cost_center', (r) => {
				if (r && r.cost_center) {
					frappe.model.set_value(cdt, cdn, 'cost_center', r.cost_center);
				}
			});
		}
	}
});

function calculate_total(frm) {
	let total = 0.0;
	if (frm.doc.expenses) {
		frm.doc.expenses.forEach(row => {
			total += flt(row.amount);
		});
	}
	if (frm.doc.include_tax) {
		total += flt(frm.doc.tax_amount) || 0;
	}
	frm.set_value('total_amount', total);
}
