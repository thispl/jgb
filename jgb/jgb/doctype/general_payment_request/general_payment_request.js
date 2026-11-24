// Copyright (c) 2026, JGB and contributors
// For license information, please see license.txt

frappe.ui.form.on('General Payment Request', {
	setup(frm) {
		frm.set_query('party_type', function() {
			return {
				filters: {
					name: ['in', ['Supplier', 'Employee', 'Customer', 'Shareholder']]
				}
			};
		});
		frm.set_query('cost_center', function() {
			return {
				filters: {
					company: frm.doc.company || frappe.defaults.get_default('company'),
					is_group: 0
				}
			};
		});
	},

	onload(frm) {
		if (frm.is_new()) {
			if (!frm.doc.request_date) {
				frm.set_value('request_date', frappe.datetime.nowdate());
			}
			if (!frm.doc.party_type) {
				frm.set_value('party_type', 'Supplier');
			}
			if (!frm.doc.company) {
				let default_company = frappe.defaults.get_default('company');
				if (default_company) {
					frm.set_value('company', default_company);
				}
			}
			if (!frm.doc.requested_by) {
				frappe.db.get_value('Employee', { user_id: frappe.session.user, status: 'Active' }, ['name', 'custom_division']).then(r => {
					if (r && r.message) {
						if (r.message.name) frm.set_value('requested_by', r.message.name);
						if (r.message.custom_division && !frm.doc.division) frm.set_value('division', r.message.custom_division);
					}
				});
			}
		}
	},

	refresh(frm) {
		if (frm.doc.payment_entry) {
			frm.add_custom_button(__('View Payment Entry'), function() {
				frappe.set_route('Form', 'Payment Entry', frm.doc.payment_entry);
			}, __('Actions'));
		}
	},

	requested_by(frm) {
		if (frm.doc.requested_by && !frm.doc.division) {
			frappe.db.get_value('Employee', frm.doc.requested_by, 'custom_division').then(r => {
				if (r && r.message && r.message.custom_division) {
					frm.set_value('division', r.message.custom_division);
				}
			});
		}
	},

	division(frm) {
		if (frm.doc.division && frm.doc.company) {
			frappe.db.get_value('Division Account Details', { parent: frm.doc.division, company: frm.doc.company }, 'cost_center').then(r => {
				if (r && r.message && r.message.cost_center) {
					frm.set_value('cost_center', r.message.cost_center);
				}
			});
		}
	},

	party_type(frm) {
		frm.set_value('party', '');
		frm.set_value('party_name', '');
	},

	party(frm) {
		if (frm.doc.party_type && frm.doc.party) {
			let name_field = 'name';
			if (frm.doc.party_type === 'Supplier') {
				name_field = 'supplier_name';
			} else if (frm.doc.party_type === 'Employee') {
				name_field = 'employee_name';
			} else if (frm.doc.party_type === 'Customer') {
				name_field = 'customer_name';
			} else if (frm.doc.party_type === 'Shareholder') {
				name_field = 'title';
			}

			frappe.db.get_value(frm.doc.party_type, frm.doc.party, name_field).then(r => {
				if (r && r.message) {
					frm.set_value('party_name', r.message[name_field] || frm.doc.party);
				} else {
					frm.set_value('party_name', frm.doc.party);
				}
			});
		} else {
			frm.set_value('party_name', '');
		}
	},

	validate(frm) {
		if (frm.doc.amount && flt(frm.doc.amount) <= 0) {
			frappe.msgprint(__('Amount must be greater than 0.'));
			frappe.validated = false;
		}
		if (frm.doc.due_date && frm.doc.request_date) {
			if (frappe.datetime.str_to_obj(frm.doc.due_date) < frappe.datetime.str_to_obj(frm.doc.request_date)) {
				frappe.msgprint(__('Due Date cannot be earlier than Request Date.'));
				frappe.validated = false;
			}
		}
	}
});
