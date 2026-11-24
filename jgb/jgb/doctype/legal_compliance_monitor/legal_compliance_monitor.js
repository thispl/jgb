// Copyright (c) 2026, JGB and contributors
// For license information, please see license.txt

frappe.ui.form.on('Legal Compliance Monitor', {
	refresh(frm) {
		frm.trigger('calculate_dates_and_status');
	},
	validate(frm) {
		frm.trigger('calculate_dates_and_status');
	},
	expiry_date(frm) {
		frm.trigger('calculate_dates_and_status');
	},
	last_renewal_date(frm) {
		frm.trigger('calculate_dates_and_status');
	},
	renewability(frm) {
		frm.trigger('calculate_dates_and_status');
	},
	calculate_dates_and_status(frm) {
		if (frm.doc.renewability === 'Permanent / Lifetime') {
			frm.set_value('status', 'Permanent');
			frm.set_value('days_left', null);
			frm.set_value('frequency_days', null);
			return;
		}
		if (frm.doc.renewability === 'Non-Renewable') {
			frm.set_value('status', 'Not Renewable');
			frm.set_value('days_left', null);
			frm.set_value('frequency_days', null);
			return;
		}
		if (frm.doc.expiry_date) {
			// Calculate Days Left until Expiry
			let diff = frappe.datetime.get_diff(frm.doc.expiry_date, frappe.datetime.nowdate());
			frm.set_value('days_left', diff);

			// Calculate Frequency if last renewal date is set
			if (frm.doc.last_renewal_date) {
				let freq = frappe.datetime.get_diff(frm.doc.expiry_date, frm.doc.last_renewal_date);
				frm.set_value('frequency_days', freq);
			}

			// Set Renewal Status based on remaining days
			if (diff < 0) {
				frm.set_value('status', 'Expired');
			} else if (diff <= 30) {
				frm.set_value('status', 'Expiring Soon');
			} else {
				frm.set_value('status', 'Valid');
			}
		}
	}
});
