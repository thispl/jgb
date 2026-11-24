frappe.ui.form.on("Purchase Receipt", {
	refresh(frm) {
		if (
			frm.doc.docstatus === 1 &&
			frm.doc.status !== "Closed" &&
			frappe.model.can_create("Stock Entry")
		) {
			frm.add_custom_button(
				__("Manufacture Stock Entry"),
				() => jgb_auto_manufacture(frm),
				__("Create")
			);
		}
	},
});

function jgb_auto_manufacture(frm) {
	frm.call({
		method: "jgb.jgb.teampro.purchase_receipt.auto_manufacture_stock_entries",
		args: { purchase_receipt: frm.docname },
		freeze: true,
		callback: function (r) {
			var names = r.message || [];
			if (!names.length) {
				jgb_manufacture_dialog(frm);
				return;
			}
			frappe.msgprint({
				title: __("Manufacture Stock Entries Created"),
				message:
					__("Draft Stock Entries created — review and submit each:") +
					"<br>" +
					names
						.map(
							(n) =>
								`<a href="${frappe.utils.get_form_link("Stock Entry", n)}">${n}</a>`
						)
						.join("<br>"),
				indicator: "green",
			});
			if (names.length === 1) {
				frappe.set_route("Form", "Stock Entry", names[0]);
			}
		},
	});
}

function jgb_manufacture_dialog(frm) {
	var d = new frappe.ui.Dialog({
		title: __("Manufacture Stock Entry"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "fg_item",
				options: "Item",
				label: __("Finished Good Item"),
				reqd: 1,
				onchange: function () {
					var item = d.get_value("fg_item");
					d.set_value("bom_no", "");
					if (item) {
						frappe.db
							.get_value("Item", item, "default_bom")
							.then((r) => r.message && r.message.default_bom && d.set_value("bom_no", r.message.default_bom));
					}
				},
			},
			{
				fieldtype: "Link",
				fieldname: "bom_no",
				options: "BOM",
				label: __("BOM"),
				reqd: 1,
				get_query: function () {
					return { filters: { item: d.get_value("fg_item") || "", is_active: 1 } };
				},
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Float",
				fieldname: "fg_qty",
				label: __("Manufacturing Qty"),
				reqd: 1,
				default: 1,
			},
			{
				fieldtype: "Link",
				fieldname: "target_warehouse",
				options: "Warehouse",
				label: __("FG Target Warehouse"),
				reqd: 1,
				default: frm.doc.set_warehouse,
			},
		],
		primary_action: function () {
			var data = d.get_values();
			frm.call({
				method: "jgb.jgb.teampro.purchase_receipt.make_manufacture_stock_entry",
				args: {
					purchase_receipt: frm.docname,
					bom_no: data.bom_no,
					fg_qty: data.fg_qty,
					target_warehouse: data.target_warehouse,
				},
				freeze: true,
				callback: function (r) {
					if (r.message) {
						frappe.model.sync(r.message);
						frappe.set_route("Form", "Stock Entry", r.message.name);
					}
					d.hide();
				},
			});
		},
		primary_action_label: __("Create"),
	});
	d.show();
}
