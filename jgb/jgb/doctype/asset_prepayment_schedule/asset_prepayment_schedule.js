// Copyright (c) 2026, JGB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Prepayment Schedule", {
	make_prepayment_entry: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!row.journal_entry) {
			frappe.call({
				method: "jgb.jgb.doctype.asset_prepayment_schedule.asset_prepayment_schedule.make_prepayment_entry",
				args: {
					asset_prepayment_schedule_name: frm.doc.name,
					date: row.schedule_date,
				},
				debounce: 1000,
				callback: function (r) {
					frappe.model.sync(r.message);
					frm.refresh();
				},
			});
		}
	},
});
