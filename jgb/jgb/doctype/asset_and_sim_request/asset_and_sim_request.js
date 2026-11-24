// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset And SIM Request", {
	refresh(frm) {
		
        if(frm.doc.docstatus==1){
            frm.add_custom_button('Create Item', function() {
                open_selection_dialog(frm);
            }, __('Action'));
            frm.add_custom_button(__("Print"), function () {
    			var f_name = frm.doc.name;
    			var print_format = "Asset Request";
    			window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
    				+ "doctype=" + encodeURIComponent("Asset And SIM Request")
    				+ "&name=" + encodeURIComponent(f_name)
    				+ "&trigger_print=1"
    				+ "&format=" + print_format
    				+ "&no_letterhead=0"
    		    ));
            }, __('Action'));
            frm.add_custom_button(__('Custodian Form'), function () {
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Custodian',
                        filters: {
                            from_request: frm.doc.name,
                        },
                        fields: ['name'],
                        limit: 1
                    },
                    callback: function (res) {
                        if (res.message && res.message.length > 0) {
                            frappe.set_route('Form', 'Custodian', res.message[0].name);
                        } else 
                        {
                           
                            frappe.model.with_doctype('Custodian', function () {
                                let cus = frappe.model.get_new_doc('Custodian');
                                cus.from_request =frm.doc.name;
                                cus.employee =frm.doc.employee;
                                cus.employee_name = frm.doc.employee_name;
                                cus.designation = frm.doc.designation;
                                cus.company = frm.doc.company;
                                (frm.doc.asset_information || []).forEach(row => {
                                    let asset = frappe.model.add_child(cus, 'asset_information');
                                    asset.brand = row.brand;
                                    asset.model_name_no = row.model_name_no;
                                });

                                frappe.set_route('Form', 'Custodian', cus.name);
                            });
                        }
                    }
                });
            }, __('Action'));
            frm.add_custom_button(__('Transfer Form'), function () {
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Asset Movement',
                        filters: {
                            custom_from_request: frm.doc.name,
                        },
                        fields: ['name'],
                        limit: 1
                    },
                    callback: function (res) {
                        if (res.message && res.message.length > 0) {
                            frappe.set_route('Form', 'Asset Movement', res.message[0].name);
                        } else 
                        {
                           
                            frappe.model.with_doctype('Asset Movement', function () {
                                let ass = frappe.model.get_new_doc('Asset Movement');
                                ass.custom_from_request =frm.doc.name;
                                ass.purpose ="Transfer";
                                let asset = frappe.model.add_child(ass, 'assets');
                                asset.from_employee = frm.doc.employee;
                                frappe.set_route('Form', 'Asset Movement', ass.name);
                            });
                        }
                    }
                });
            }, __('Action'));
            frm.call({
                method: "get_asset_status",
                doc: frm.doc,
                callback(r) {
                    frm.fields_dict.asset_status.$wrapper.html(r.message || "");
                }
            });
        }
	},
	 total_budget: function(frm) {
        calculate_variance(frm);
    },

    approved_budget: function(frm) {
        calculate_variance(frm);
    }
});

function calculate_variance(frm) {
    let total = frm.doc.total_budget || 0;
    let approved = frm.doc.approved_budget || 0;

    frm.set_value('variance', total - approved);

    frm.refresh_field('variance');
}

function calculate_total_budget(frm) {
    let total = 0;

    (frm.doc.asset_information || []).forEach(row => {
        total += flt(row.value);
    });

    frm.set_value('total_value', total);
    frm.set_value('approved_budget', total);
}
frappe.ui.form.on('Asset Information', {

    value: function(frm, cdt, cdn) {
        calculate_total_budget(frm);
        calculate_variance(frm);
    },

    asset_information_add: function(frm) {
        calculate_total_budget(frm);
        calculate_variance(frm);
    },

    asset_information_remove: function(frm) {
        calculate_total_budget(frm);
        calculate_variance(frm);
    }
});

function open_selection_dialog(frm) {

    let rows = frm.doc.asset_information || [];

    if (!rows.length) {
        frappe.msgprint("No Asset Information found");
        return;
    }

    let fields = [];

    rows.forEach((row, idx) => {

        fields.push({
            fieldtype: 'Check',
            label: row.description,
            fieldname: `select_${idx}`,
            default: 0
        });

        fields.push({
            fieldtype: 'Data',
            fieldname: `name_${idx}`,
            default: row.description,
            hidden: 1
        });

        fields.push({
            fieldtype: 'Section Break'
        });

    });

    let d = new frappe.ui.Dialog({
        title: 'Select Items to Create',
        fields: fields,
        primary_action_label: 'Create Items',
        primary_action(values) {

    let selected = [];

    rows.forEach((row, idx) => {
        if (values[`select_${idx}`]) {
            selected.push(row.description);
        }
    });

    if (selected.length > 1) {
        frappe.msgprint({
            title: "Not Allowed",
            message: "Please select only ONE item",
            indicator: "red"
        });
        return;
    }

    if (selected.length === 0) {
        frappe.msgprint("Please select at least one item");
        return;
    }

    create_items(frm,selected);

    d.hide();
}
    });

    d.show();
}
function create_items(frm,item_list) {

    if (!item_list.length) return;

    let idx = 0;

    function open_next() {

        if (idx >= item_list.length) {
            frappe.msgprint("All Item forms opened");
            return;
        }

        let name = item_list[idx];

        frappe.new_doc("Item", {
            item_code: name,
            item_name: name,
            custom_item_type: "asset",
            item_group: "Fixed Assets Register (FAR)",
            auto_create_assets: 1,
            stock_uom: "Nos",
            is_stock_item: 0,
            is_fixed_asset: 1,
            custom_from_asset_request:frm.doc.name
        });

        idx++;
    }

    open_next();
}