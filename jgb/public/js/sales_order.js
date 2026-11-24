frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
		if (grid) {
			const allowed = !frm.is_new() && frm.doc.docstatus === 0;
			grid
				.add_custom_button(__("Upload Items"), () => jgb_so_upload_items(frm))
				.html('<i class="fa fa-upload" style="color: var(--blue-600);"></i>')
				.attr("title", __("Upload items (Item Code, Qty, Currency, Cost, Rate)"))
				.appendTo(grid.wrapper.find(".grid-bulk-actions"))
				.toggleClass("hidden", !allowed);
		}
		if (
			frm.doc.docstatus === 1 &&
			!frm.doc.is_internal_customer &&
			frm.doc.status !== "Closed" &&
			frappe.model.can_create("Purchase Order")
		) {
			frm.add_custom_button(
				__("Raw Material Purchase Order"),
				() => jgb_make_bom_po_dialog(frm),
				__("Create")
			);
		}
	},
});

function jgb_make_bom_po_dialog(frm) {
	frm.call({
		method: "erpnext.selling.doctype.sales_order.sales_order.get_work_order_items",
		args: {
			sales_order: frm.docname,
			for_raw_material_request: 1,
		},
		callback: function (r) {
			if (!r.message || !r.message.length) {
				frappe.msgprint({
					message: __("No Items with Bill of Materials."),
					indicator: "orange",
				});
				return;
			}
			jgb_bom_po_dialog(frm, r.message);
		},
	});
}

function jgb_bom_po_dialog(frm, items) {
	var fields = [
		{
			fieldtype: "Link",
			fieldname: "supplier",
			options: "Supplier",
			label: __("Supplier"),
			reqd: 1,
		},
		{
			fieldtype: "Date",
			fieldname: "schedule_date",
			label: __("Required By"),
			default: frm.doc.delivery_date,
		},
		{
			fieldtype: "Link",
			fieldname: "target_warehouse",
			options: "Warehouse",
			label: __("Target Warehouse"),
			reqd: 1,
			default: frm.doc.set_warehouse,
		},
		{ fieldtype: "Column Break" },
		{ fieldtype: "Check", fieldname: "include_exploded_items", label: __("Include Exploded Items") },
		{
			fieldtype: "Check",
			fieldname: "ignore_existing_ordered_qty",
			label: __("Ignore Existing Ordered Qty"),
		},
		{ fieldtype: "Section Break" },
		{
			fieldtype: "Table",
			fieldname: "items",
			description: __("Select BOM, Qty and For Warehouse"),
			fields: [
				{
					fieldtype: "Read Only",
					fieldname: "item_code",
					label: __("Item Code"),
					in_list_view: 1,
				},
				{
					fieldtype: "Link",
					fieldname: "warehouse",
					options: "Warehouse",
					label: __("For Warehouse"),
					in_list_view: 1,
				},
				{
					fieldtype: "Link",
					fieldname: "bom",
					options: "BOM",
					label: __("BOM"),
					in_list_view: 1,
					get_query: function (doc) {
						return { filters: { item: doc.item_code } };
					},
				},
				{
					fieldtype: "Float",
					fieldname: "required_qty",
					reqd: 1,
					label: __("Qty"),
					in_list_view: 1,
				},
			],
			data: items,
			get_data: function () {
				return items;
			},
		},
	];

	var d = new frappe.ui.Dialog({
		title: __("Purchase Raw Materials for BOM Items"),
		fields: fields,
		primary_action: function () {
			var data = d.get_values();
			frm.call({
				method: "jgb.sales_order.make_bom_purchase_order",
				args: {
					items: data,
					company: frm.doc.company,
					sales_order: frm.docname,
					supplier: data.supplier,
					schedule_date: data.schedule_date,
					target_warehouse: data.target_warehouse,
					project: frm.doc.project,
				},
				freeze: true,
				callback: function (r) {
					if (r.message) {
						frappe.set_route("Form", "Purchase Order", r.message);
					}
					d.hide();
					frm.reload_doc();
				},
			});
		},
		primary_action_label: __("Create"),
	});
	d.show();
}

function jgb_so_upload_items(frm) {
	if (frm.is_dirty()) {
		// upload_item_sheet_so reloads + saves the doc server-side; flush pending edits first
		frm.save(null, (r) => !r.exc && jgb_so_upload_items(frm));
		return;
	}
	new frappe.ui.FileUploader({
		allow_multiple: false,
		restrictions: { allowed_file_types: [".xlsx", ".csv"] },
		on_success(file_doc) {
			frm.call({
				method: "jgb.jgb.teampro.sales_order.upload_item_sheet_so",
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
