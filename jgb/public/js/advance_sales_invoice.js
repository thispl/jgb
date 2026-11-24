frappe.ui.form.on("Advance Sales Invoice", {
	refresh(frm) {

		frm.add_custom_button(
			__("Create Payment Entry"),
			function () {

				frappe.call({
					method: "jgb.jgb.custom.make_payment_entry_from_advance_sales_invoice",
					args: {
						advance_invoice: frm.doc.name
					},
					callback: function (r) {
						if (r.message) {
							if (r.message.is_existing && r.message.payment_entry) {
								frappe.set_route("Form", "Payment Entry", r.message.payment_entry);
							} else if (r.message.doc) {
								let doc = r.message.doc;
								frappe.model.sync(doc);
								frappe.set_route("Form", doc.doctype, doc.name);
							} else {
								frappe.msgprint({
									title: __("Payment Entry Not Found"),
									message: __("Could not find or prepare a Payment Entry for this Advance Sales Invoice."),
									indicator: "orange",
								});
							}
						}
					}
				});

			},
			__("Create")
		);

	}
});