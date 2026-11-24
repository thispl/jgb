frappe.ui.form.on("Sales Invoice", {
	refresh: function (frm) {
		frm.add_custom_button(
			__("Profitability"),
			function () {
				frappe.call({
					method: "jgb.api.get_profitability_html",
					args: {
						sales_invoice: frm.doc.name,
					},
					callback: function (r) {
						if (!r.exc && r.message) {
							const dialog = new frappe.ui.Dialog({
								title: __("Profitability"),
								size: "extra-large",
								secondary_action_label: __("Download Excel"),
								secondary_action: function () {
									open_url_post(frappe.request.url, {
										cmd: "jgb.api.download_profitability_excel",
										sales_invoice: frm.doc.name,
									});
								},
								fields: [
									{
										fieldtype: "HTML",
										fieldname: "profitability_html",
									},
								],
							});
							dialog.get_field("profitability_html").$wrapper.html(r.message);
							dialog.show();
						}
					},
				});
			},
			__("View")
		);
	},
});
