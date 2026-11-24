// Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Interim Payment Certificate", {
	refresh(frm) {
        if(frm.doc.docstatus==0){
            frm.add_custom_button(
                __("Delivery Note"),
                function () {
                    erpnext.utils.map_current_doc({
                        method: "jgb.jgb.doctype.interim_payment_certificate.interim_payment_certificate.update_ipc_values",
                        source_doctype: "Delivery Note",
                        target: frm,
                        date_field: "posting_date",

                        setters: {
                            customer: frm.doc.customer
                        },

                        get_query: function () {
                            return {
                                query: "erpnext.controllers.queries.get_delivery_notes_to_be_billed",
                                filters: {
                                    company: frm.doc.company,
                                    customer: frm.doc.customer,
                                    is_return: 0
                                }
                            };
                        }
                    });
                },
                __("Get Items From")
            );


            frm.add_custom_button(
                __("Sales Order"),
                function () {
                    erpnext.utils.map_current_doc({
                        method: "jgb.jgb.doctype.interim_payment_certificate.interim_payment_certificate.make_ipc_values",
                        source_doctype: "Sales Order",
                        target: frm,
                        date_field: "transaction_date",

                        setters: {
                            customer: frm.doc.customer
                        },

                        get_query_filters: {
                            docstatus: 1,
                            company: frm.doc.company,
                            customer: frm.doc.customer,
                            status: ["not in", ["Closed", "On Hold"]],
                            per_billed: ["<", 100]
                        }
                    });
                },
                __("Get Items From")
            );


        }

	},
});
