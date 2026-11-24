// Asset Prepayment — button on submitted assets to create/open the schedule,
// and an inline schedule view mirroring the depreciation schedule view.

frappe.ui.form.on("Asset", {
	refresh: function (frm) {
		if (frm.doc.docstatus === 1 && frm.doc.custom_is_prepaid) {
			frm.add_custom_button(__("Prepayment Schedule"), function () {
				frappe.call({
					method: "jgb.jgb.asset_prepayment.create_prepayment_schedule",
					args: { asset_name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							frappe.set_route("Form", "Asset Prepayment Schedule", r.message);
						}
					},
				});
			});
		}
		if (frm.doc.custom_is_prepaid) {
			frm.events.render_prepayment_schedule_view(frm);
		}
	},

	render_prepayment_schedule_view: async function (frm) {
		let aps_doc = (
			await frappe.call("jgb.jgb.asset_prepayment.get_asset_prepayment_schedule_doc", {
				asset_name: frm.doc.name,
			})
		).message;

		if (!aps_doc || !(aps_doc.prepayment_schedule || []).length) {
			frm.toggle_display(["custom_prepayment_schedule_view"], 0);
			return;
		}

		let wrapper = $(frm.fields_dict["custom_prepayment_schedule_view"].wrapper).empty();

		let data = aps_doc.prepayment_schedule.map((sch) => [
			sch["idx"],
			frappe.format(sch["schedule_date"], { fieldtype: "Date" }),
			frappe.format(sch["prepayment_amount"], { fieldtype: "Currency" }),
			frappe.format(sch["accumulated_prepayment_amount"], { fieldtype: "Currency" }),
			sch["journal_entry"] || "",
		]);

		let columns = [
			{ name: __("No."), editable: false, resizable: false, format: (value) => value, width: 60 },
			{ name: __("Schedule Date"), editable: false, resizable: false, width: 270 },
			{ name: __("Prepayment Amount"), editable: false, resizable: false, width: 164 },
			{ name: __("Accumulated Prepayment Amount"), editable: false, resizable: false, width: 164 },
			{
				name: __("Journal Entry"),
				editable: false,
				resizable: false,
				format: (value) => `<a href="/app/journal-entry/${value}">${value}</a>`,
				width: 304,
			},
		];

		let datatable = new frappe.DataTable(wrapper.get(0), {
			columns: columns,
			data: data,
			layout: "fluid",
			serialNoColumn: false,
			checkboxColumn: true,
			cellHeight: 35,
		});

		datatable.style.setStyle(`.dt-scrollable`, {
			"font-size": "0.75rem",
			"margin-bottom": "1rem",
			"margin-left": "0.35rem",
			"margin-right": "0.35rem",
		});
		datatable.style.setStyle(`.dt-header`, { "margin-left": "0.35rem", "margin-right": "0.35rem" });
		datatable.style.setStyle(`.dt-cell--header .dt-cell__content`, {
			color: "var(--gray-600)",
			"font-size": "var(--text-sm)",
		});
		datatable.style.setStyle(`.dt-cell`, { color: "var(--text-color)" });
		datatable.style.setStyle(`.dt-cell--col-1`, { "text-align": "center" });
		datatable.style.setStyle(`.dt-cell--col-2`, { "font-weight": 600 });
		datatable.style.setStyle(`.dt-cell--col-3`, { "font-weight": 600 });

		frm.toggle_display(["custom_prepayment_schedule_view"], 1);
	},
});
