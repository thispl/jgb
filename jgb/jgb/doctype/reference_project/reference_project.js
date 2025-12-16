// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Reference Project", {
	refresh(frm) {
        update_labels(frm);
	},
    currency(frm) {
		update_labels(frm);
		update_labels_and_conversion(frm);
	},
    project_value(frm){
        update_labels_and_conversion(frm);
    }
});
frappe.ui.form.on("Project Parties", {
    name1(frm, cdt, cdn) {
        console.log("Triggered name1");
        update_doc_name(frm, cdt, cdn);
    },
    type_name(frm, cdt, cdn) {
        console.log("Triggered type_name");
        update_doc_name(frm, cdt, cdn);
    }
});

function update_labels(frm) {
	if (frm.doc.currency) {
		frm.set_df_property("project_value", "label", `Project Value (${frm.doc.currency})`);
	}
	frm.set_df_property("project_value_company_currency", "label", "Project Value (SAR)");
}

function update_labels_and_conversion(frm) {
	const from_currency = frm.doc.currency;
	const to_currency = "SAR"; // hardcoded company currency
	const amount = frm.doc.project_value;

	if (from_currency && amount) {
		frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				from_currency: from_currency,
				to_currency: to_currency
			},
			callback: function (r) {
				if (r.message) {
					const exchange_rate = r.message;
					const converted = flt(amount) * flt(exchange_rate);
					frm.set_value("project_value_company_currency", converted);
				} else {
					frappe.msgprint("Could not fetch exchange rate.");
				}
			}
		});
	}
}


function update_doc_name(frm, cdt, cdn) {
	console.log("inside")
    const row = locals[cdt][cdn];
    if (row.name1 === 'Lead') {
        frappe.db.get_value('Lead', row.type_name, 'company_name')
            .then(r => {
                if (r && r.message) {
                    frappe.model.set_value(cdt, cdn, 'doc_name', r.message.company_name);
                }
            });
    } else if (row.name1 === 'Customer') {
        frappe.db.get_value('Customer', row.type_name, 'customer_name')
            .then(r => {
                if (r && r.message) {
                    frappe.model.set_value(cdt, cdn, 'doc_name', r.message.customer_name);
                }
            });
    }
}
