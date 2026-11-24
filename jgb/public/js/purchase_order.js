frappe.ui.form.on("Purchase Order", {
	refresh(frm) {
		const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
		if (!grid) return;

		// keep the right-aligned container, hide only the stock upload button inside it
		grid.wrapper.find(".grid-upload").addClass("hidden");

		const allowed = !frm.is_new() && frm.doc.docstatus === 0;
		const bulk_actions = grid.wrapper.find(".grid-bulk-actions");
		grid
			.add_custom_button(__("Download"), () => jgb_po_download_items(frm))
			.html('<i class="fa fa-download"></i>')
			.attr("title", __("Download items template"))
			.appendTo(bulk_actions)
			.toggleClass("hidden", !allowed);
		grid
			.add_custom_button(__("Upload"), () => jgb_po_upload_items(frm))
			.html('<i class="fa fa-arrow-circle-up" style="color: green;"></i>')
			.attr("title", __("Upload items from Excel/CSV"))
			.appendTo(bulk_actions)
			.toggleClass("hidden", !allowed);
	},
});

function jgb_po_download_items(frm) {
	frappe.tools.downloadify(
		[[__("Item Code"), __("Quantity"), __("Rate")]],
		null,
		frm.docname + "-items-template"
	);
}

function jgb_po_upload_items(frm) {
	if (frm.is_dirty()) {
		// upload_item_sheet_po reloads + saves the doc server-side; flush pending edits first
		frm.save(null, (r) => !r.exc && jgb_po_upload_items(frm));
		return;
	}
	new frappe.ui.FileUploader({
		allow_multiple: false,
		restrictions: { allowed_file_types: [".xlsx", ".csv"] },
		on_success(file_doc) {
			frm.call({
				method: "jgb.jgb.teampro.purchase_order.upload_item_sheet_po",
				args: { docname: frm.docname, file_url: file_doc.file_url },
				freeze: true,
				freeze_message: __("Importing items..."),
				callback(r) {
					if (r.message && r.message.status === "success") {
						frappe.show_alert({
							message: __(r.message.message),
							indicator: "green",
						});
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __("Item Import Failed"),
							message: (r.message && r.message.message) || "",
							indicator: "red",
						});
					}
				},
			});
		},
	});
}
