// Copyright (c) 2026, JGB and contributors
// For license information, please see license.txt

frappe.ui.form.on('Division Inventory Reclassification', {
	onload: function(frm) {
		frm.trigger('set_queries');
	},
	refresh: function(frm) {
		frm.trigger('set_queries');

		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
					company: frm.doc.company,
					show_cancelled_entries: frm.doc.docstatus === 2,
				};
				frappe.set_route('query-report', 'General Ledger');
			}, __('View'));
		}

		if (frm.doc.reference_doctype && frm.doc.reference_name) {
			frm.add_custom_button(__('Source Document'), function() {
				frappe.set_route('Form', frm.doc.reference_doctype, frm.doc.reference_name);
			}, __('View'));
		}
	},
	set_queries: function(frm) {
		frm.set_query('company', function() {
			return {
				filters: {
					name: 'Joint Global Business Co LLC',
				},
			};
		});
	},
});

frappe.ui.form.on('Division Reclass Item', {
	division: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.division || !frm.doc.company) {
			return;
		}
		frappe.db.get_value(
			'Division Account Details',
			{ parent: row.division, company: frm.doc.company },
			'inventory_account',
			(r) => {
				if (r && r.inventory_account) {
					frappe.model.set_value(cdt, cdn, 'inventory_account', r.inventory_account);
				}
			}
		);
	},
});
