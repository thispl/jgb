// Copyright (c) 2025, TEAMPRO and contributors
// For license information, please see license.txt

frappe.ui.form.on('Logistics Request', {
	after_save(frm){
		frm.refresh()
		frm.reload_doc();
	},
	before_workflow_action(frm){
		
	if (frm.doc.workflow_state === 'Draft' && frm.selected_workflow_action === "Schedule") {
        setTimeout(() => {
            frm.scroll_to_field("date_of_shipment");
        }, 100); // slight delay so it runs before freeze
    }
	if (frm.doc.workflow_state === 'Scheduled' && frm.selected_workflow_action === "Dispatch") {
        setTimeout(() => {
            frm.scroll_to_field("support_documents");
        }, 100); // slight delay so it runs before freeze
    }
	if (frm.doc.workflow_state === 'Scheduled' && frm.selected_workflow_action === "Out for Delivery") {
        setTimeout(() => {
            frm.scroll_to_field("table_gqxd");
        }, 100); // slight delay so it runs before freeze
    }
	if (frm.doc.workflow_state === 'Dispatched' && frm.selected_workflow_action === "Pay") {
        setTimeout(() => {
            frm.scroll_to_field("lr_costing_payment");
        }, 100); // slight delay so it runs before freeze
    }
	if (frm.doc.workflow_state === 'Payment' && frm.selected_workflow_action === "Out for Delivery") {
        setTimeout(() => {
            frm.scroll_to_field("table_gqxd");
        }, 100); // slight delay so it runs before freeze
    }
	if (frm.doc.workflow_state === 'Out for Delivery' && frm.selected_workflow_action === "Arrived") {
        setTimeout(() => {
            frm.scroll_to_field("attachment");
        }, 100); // slight delay so it runs before freeze
    }
	},
	

	 

	
	download(frm) {
		let selected_files = []
		let selected_docs = frm.fields_dict.support_documents.grid.get_selected_children();
			frm.call({
				method: "get_supporting_docs",
				args: { "selected_docs": selected_docs },
			}).then((r) => {
				open_url_post("/api/method/frappe.core.api.file.zip_files", {
					files: JSON.stringify(r.message),
				});
			});
	},
	order_no(frm){
		if (frm.doc.__islocal) {
			
			if (frm.doc.order_no) {
				frappe.call({
					method: 'frappe.client.get',
					args: {
						'doctype': frm.doc.po_so,
						'name': frm.doc.order_no,
					},
					callback(r) {
						if (frm.doc.po_so == 'Purchase Order'){
							frm.set_value('product_description', r.message.items)
							frm.refresh_fields('product_description')
						}
						
						frm.set_value('grand_total', r.message.grand_total)
						
						frm.set_value('custom_duty', r.message.grand_total * 0.45)
						frm.set_value('supplier', r.message.supplier)
						frm.set_value('customer', r.message.customer)
						frm.set_value('company', r.message.company)
						
						if (frm.doc.po_so == 'Sales Invoice'){
							
							frm.set_value('cargo_type', r.message.custom_cargo_mode)
							frm.set_value('inventory_destination', 'Direct to Customer')
							
						}
						frm.set_value('consignment_type', r.message.consignment_type)
						
						if (frm.doc.po_so == 'Delivery Note'){
							
							frm.set_value('cargo_type', r.message.custom_cargo_type)
							frm.set_value('source', r.message.source)
							frm.set_value('shipping_address_name', r.message.shipping_address_name)
							frm.set_value('shipping_address', r.message.shipping_address)
							frm.set_value('inventory_destination', 'Direct to Customer')
							
						}
						frm.set_value('requester_name', r.message.owner)
					}
				})
			}
		}
	},
	customer_primary_address: function (frm) {
		if (frm.doc.customer_primary_address) {
			frappe.call({
				method: "frappe.contacts.doctype.address.address.get_address_display",
				args: {
					address_dict: frm.doc.customer_primary_address,
				},
				callback: function (r) {
					let cleaned = r.message
						.split(/<br\s*\/?>/i)
						.map(line => line.trim())
						.filter((line, idx, arr) =>
							line && (idx === 0 || line !== arr[idx - 1])
						)
						.join('<br>');
					
					frm.set_value("shipping_address", cleaned);
				},
			});
		}
		if (!frm.doc.customer_primary_address) {
			frm.set_value("shipping_address", "");
		}
	},
	refresh: function (frm) {
		if (frm.doc.inventory_destination === "JGB Warehouse") {
            frm.set_df_property('warehouse', 'label', 'Warehouse');
        } else {
            frm.set_df_property('warehouse', 'label', 'Final Destination');
        }
frm.set_query('recommended_ffw', () => {
            const ffw_names = (frm.doc.ffw_quotation || []).map(row => row.ffw_name).filter(Boolean);
            return {
                filters: [
                    ['name', 'in', ffw_names]
                ]
            };
        });
		if (frm.doc.logistic_type=="Local Delivery"){
			frm.set_query('cargo_type', () => {
				return {
					filters: [
						['name', 'in',["Courier","JGB Vehicle","Road","Supplier Scope","Customer Scope"]]
					]
				};
			});
		}


frappe.after_ajax(() => {
    const grid = frm.fields_dict["support_documents"]?.grid;
    if (!grid || !grid.wrapper) return;

    const $grid_buttons = $(grid.wrapper).find('.grid-buttons');
    if (!$grid_buttons.length) return;

    // Avoid duplicate
    if ($grid_buttons.find('.custom-download-wrapper').length === 0) {
		 $grid_buttons.css({
                    display: 'flex',
                    'justify-content': 'flex-start',
                    'align-items': 'center',
                    'flex-wrap': 'wrap',
					 'margin-top': '-20px',
            'padding-top': '0px'
                });
        const $download_wrapper = $(`
            <div class="custom-download-wrapper" style="display: flex; flex-direction: column; align-items: flex-start; margin-left: 10px;margin-top:20px;">
                <button class="btn btn-xs btn-default custom-download-btn" style="margin-bottom: 3px;">
                    Download
                </button>
                <div class="custom-download-desc" style="font-size: 13px;">
                    *Select the list of files to be downloaded.
                </div>
            </div>
        `);

        $download_wrapper.find('.custom-download-btn').on('click', () => {
            const selected_docs = frm.fields_dict.support_documents.grid.get_selected_children();
            frm.call({
                method: "get_supporting_docs",
                args: { "selected_docs": selected_docs },
            }).then((r) => {
                open_url_post("/api/method/frappe.core.api.file.zip_files", {
                    files: JSON.stringify(r.message),
                });
            });
        });

        // Append the wrapper but float it independently
        $grid_buttons.css('display', 'flex').append($download_wrapper);
    }
});

		if(frm.doc.po_so=="Sales Invoice"){
			frm.set_query("customer_primary_address", function () {
				return {
					filters: {
						link_doctype: "Customer",
						link_name: frm.doc.custom_customer_final_destination,
					},
				};
			});
			frm.set_query("shipping_address_name", function () {
				return {
					filters: {
						link_doctype: "Customer",
						link_name: frm.doc.custom_customer_final_destination,
					},
				};
			});
		}
		else{
			frm.set_query("customer_primary_address", function () {
				return {
					filters: {
						link_doctype: "Customer",
						link_name: frm.doc.customer,
					},
				};
			});
			frm.set_query("shipping_address_name", function () {
				return {
					filters: {
						link_doctype: "Customer",
						link_name: frm.doc.customer,
					},
				};
			});
		}
		if (frm.doc.status == "Variation - Pending for Finance") {
			if (frappe.user.has_role("Accounts User")) {
				frm.add_custom_button(__("Approve"), function () {
					frappe.call({
						method: "jgb.jgb.doctype.logistics_request.logistics_request.update_status",
						args: {
							"name": frm.doc.name,
						},
					});
				}).addClass("btn-danger");
			}
		}
		if ((frm.doc.workflow_state === 'Arrived' && frm.doc.logistic_type=='Import')) {
		frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Purchase Receipt',
					filters: {
						custom_logistics_request: frm.doc.name,
						docstatus: ('!=', 2)
					},
					fields: ['name'],
					limit: 1
				},
				callback: function (r) {
					if (r.message && r.message.length > 0) {
						frm.add_custom_button(__('View PR'), function () {
							frappe.set_route('Form', 'Purchase Receipt', r.message[0].name);
						});
					} else {
						
						if(frm.doc.has_purchase_receipt==0){

frm.page.add_action_item(__('Create PR'), async function () {
    const rows = frm.doc.product_description || [];

    if (!rows.length) {
        frappe.msgprint("No product description entries found.");
        return;
    }

    const voucherMap = {};
    rows.forEach(row => {
        if (row.voucher_no) {
            if (!voucherMap[row.voucher_no]) {
                voucherMap[row.voucher_no] = [];
            }
            voucherMap[row.voucher_no].push(row);
        }
    });

    const voucherNos = Object.keys(voucherMap);

    if (!voucherNos.length) {
        frappe.msgprint("No voucher_no (PO IDs) found in the table.");
        return;
    }

    frappe.model.with_doctype('Purchase Receipt', () => {
        let pr = frappe.model.get_new_doc('Purchase Receipt');
        pr.custom_logistics_request = frm.doc.name;

        const addItemsFromPO = (index = 0) => {
            if (index >= voucherNos.length) {
                frappe.call({
                    method: "frappe.client.insert",
                    args: { doc: pr },
                    callback: function (saved) {

                        if (saved.message) {
                            const pr_name = saved.message.name;
                            frappe.set_route("Form", "Purchase Receipt", pr_name);
                            
                        }
                    }
                });

                return;
            }

            const po_id = voucherNos[index];

            frappe.call({
                method: 'frappe.client.get',
                args: { doctype: 'Purchase Order', name: po_id },
                callback: function (res) {
                    const po = res.message;

                    if (!pr.supplier) pr.supplier = po.supplier;
                    if (!pr.custom_division) pr.custom_division = po.custom_division;
                    if (!pr.purchase_order) pr.purchase_order = po.name;
                    pr.currency = po.currency;
                    pr.conversion_rate = po.conversion_rate;
					if(frm.doc.warehouse){
						pr.set_warehouse=frm.doc.warehouse;
					}
                    const source_rows = voucherMap[po_id];

                    source_rows.forEach(source_row => {
                        (po.items || []).forEach(po_item => {
                            if (po_item.item_code === source_row.item_code) {
                                let item = frappe.model.add_child(pr, 'items');
                                item.item_code = po_item.item_code;
                                item.item_name = po_item.item_name;
                                item.qty =source_row.qty || 0;
                                item.received_qty = source_row.qty || 0;
                                item.uom = po_item.uom;
                                item.rate = source_row.rate;
                                item.amount = source_row.amount;
                                item.base_amount = source_row.base_amount;
                                item.base_rate = source_row.base_rate;
                                item.schedule_date = po_item.schedule_date;
								item.warehouse=frm.doc.warehouse || po_item.warehouse,
                                item.purchase_order = source_row.voucher_no;
                            }
                        });
                    });

                    addItemsFromPO(index + 1);
                }
            });
        };

        addItemsFromPO();
    });
});

						}

					}
				}
			});
		}
		
		if(frm.doc.workflow_state=="Closed" ||frm.doc.workflow_state=="Completed"){
			frm.fields.forEach(function(field) {
			frm.set_df_property(field.df.fieldname, "read_only", 1);
		});
		}
		if ((frm.doc.workflow_state === 'Arrived' || frm.doc.workflow_state === 'Closed') && frm.doc.logistic_type=='Import') {
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Purchase Receipt',
					filters: {
						custom_logistics_request: frm.doc.name,
						docstatus: ['in', [0, 1]]
					},
					fields: ['name'],
					limit: 1
				},
				callback: function (r) {
					if (r.message && r.message.length > 0) {
						frm.add_custom_button(__('View PR'), function () {
							frappe.set_route('Form', 'Purchase Receipt', r.message[0].name);
						});
					}
				}
			});
		}

		// if(!frm.doc.__islocal){
		// 	frm.add_custom_button(__("Packing List"), function () {
		// 	var f_name = frm.doc.name
		// 	var print_format = "Packing List Logistics";
		// 	window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
		// 		+ "doctype=" + encodeURIComponent("Logistics Request")
		// 		+ "&name=" + encodeURIComponent(f_name)
		// 		+ "&trigger_print=1"
		// 		+ "&format=" + print_format
		// 		+ "&no_letterhead=0"
		// 	));
		// });

		
		// }
		
		frappe.breadcrumbs.add("Buying", "Logistics Request");
		// if (frm.doc.workflow_state == "Arrived") {
		// 	frm.add_custom_button(__('Purchase Receipt'), function () {
		// 		frappe.call({
		// 			method: 'jgb.jgb.custom.create_pr',
		// 			args: {
		// 				'company': frm.doc.company,
		// 				'supplier': frm.doc.supplier,
		// 				'product_description': frm.doc.product_description,
		// 				'logistic': frm.doc.name,
		// 				'total': frm.doc.total
		// 			},
		// 			callback(r) {
		// 				if (r.message) {
		// 					frappe.set_route("Form", "Purchase Receipt", r.message)
		// 				}
		// 			}
		// 		})
		// 	})
		// }

		// frm.set_query("purchase_order", function () {
		// 	return {
		// 		filters: {
		// 			"supplier": frm.doc.ffw
		// 		}
		// 	}
		// })

		if (frm.doc.po_so == 'Sales Invoice' && frm.doc.order_no) {
			frappe.call({
				method: 'jgb.jgb.doctype.logistics_request.logistics_request.get_box_pallet_summary',
				args: {
					'sales_invoice': frm.doc.order_no,
				},
				callback(d) {
					if (d.message) {
						frm.get_field("box_summary").$wrapper.html(d.message);
					}
				}
			})
		}
	},
	
	setup: function (frm) {
		// 	if(frm.doc.add_sub){
		frm.set_query("ffw_name", "ffw_quotation", function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: [
					['Supplier', 'ffw', '=', 1]
				]
			};
		});

		frm.set_query("warehouse", function () {
			return {
				filters: {
					"company": frm.doc.company,
					"is_group":0
				}
			}
		})

		frm.set_query("pol_airport", function () {
			return {
                filters: {
                    cargo_type: (frm.doc.cargo_type || "").toUpperCase(),
                }
            };
		});
		frm.set_query("pol_seaport", function () {
			return {
                filters: {
                    cargo_type: (frm.doc.cargo_type || "").toUpperCase(),
                }
            };
		});
		frm.set_query("pod_airport", function () {
			return {
                filters: {
                    cargo_type: (frm.doc.cargo_type || "").toUpperCase(),
                }
            };
		});
		frm.set_query("pod_seaport", function () {
			return {
                filters: {
                    cargo_type: (frm.doc.cargo_type || "").toUpperCase(),
                }
            };
		});
	},
	
	po_so(frm) {
		frm.set_value('order_no', '')
		if (frm.doc.__islocal) {
				if(frm.doc.logistic_type == 'Export' && frm.doc.cargo_type!="Sea"){
					var data = [{ 'title': 'Commercial Invoice' },
					{ 'title': 'Packing List' },
					{ 'title': 'Fumigation Certificate (if needed)' },
					]
					$.each(data, function (i, v) {
						frm.add_child('document_attached', {
							title: v.title,
						})
						frm.refresh_field('document_attached')
					})
					var data2 = [{ 'title': 'Shipping Bill' },
					{ 'title': 'Bill of Landing (B/L)' },
					{ 'title': 'Certificate of Origin' },
					]
					$.each(data2, function (i, v) {
						frm.add_child('support_documents', {
							document_type: v.title,
						})
						frm.refresh_field('support_documents')
					})
				}
				if(frm.doc.logistic_type == 'Import' && frm.doc.cargo_type!="Sea"){
					var data = [{ 'title': 'Commercial Invoice' },
					{ 'title': 'Packing List' },
					{ 'title': 'MTC / MTR Report' },
					{ 'title': 'Form 1' },
					{ 'title': 'Material BOM' },
					{ 'title': 'Catelog' },
					{ 'title': 'FTA (Free Trade Agreement)' },
					{ 'title': 'BIS / NOC' },
					]
					$.each(data, function (i, v) {
						frm.add_child('document_attached', {
							title: v.title,
						})
						frm.refresh_field('document_attached')
					})
					var data2 = [{ 'title': 'Bill of Entry' },
					{ 'title': 'Bill of Landing (B/L)' },
					
					]
					$.each(data2, function (i, v) {
						frm.add_child('support_documents', {
							document_type: v.title,
						})
						frm.refresh_field('support_documents')
					})
				}
				if(frm.doc.cargo_type=="Sea"){
					var data2 = [{ 'title': 'Port / Handling Charges' },
					{ 'title': 'Delivery Order' },
					{ 'title': 'Mawani Charges' },
					]
					$.each(data2, function (i, v) {
						frm.add_child('support_documents', {
							document_type: v.title,
						})
						frm.refresh_field('support_documents')
					})
				}
				if(frm.doc.cargo_type=="Air"){
					var data2 = [{ 'title': 'SAL Charges' },
					{ 'title': 'Customs ' },
					]
					$.each(data2, function (i, v) {
						frm.add_child('support_documents', {
							document_type: v.title,
						})
						frm.refresh_field('support_documents')
					})
				}

			
				

			// }
		}
	},
	logistic_type(frm) {
		frm.set_df_property('cargo_type', 'read_only', 0);

		// logistics_set_query(frm);
		

		if (frm.doc.logistic_type === 'Export') {
			frm.set_value('po_so', 'Sales Invoice');
		} else if (frm.doc.logistic_type === 'Import') {
			frm.set_value('po_so', 'Purchase Order');
		} else if (frm.doc.logistic_type === 'Local Delivery') {
			frm.set_value('po_so', 'Delivery Note');
			frm.set_value('cargo_type', 'Road');
			frm.set_df_property('cargo_type', 'read_only', 1);
		}
	},

	validate: function(frm) {
		if(frm.doc.workflow_state=="Scheduled"){
frm.set_value("custom_details",1)	
		}
		if(frm.doc.workflow_state=="Dispatched"){
frm.set_value("custom_schedule",1)	
		}
		if(frm.doc.workflow_state=="Out for Delivery" && frm.doc.logistic_type == "Local Delivery"){
frm.set_value("custom_schedule",1)	
		}
		if(frm.doc.workflow_state=="Payment"){
frm.set_value("custom_dispatched",1)	
		}
		if(frm.doc.workflow_state=="Out for Delivery" && !frm.doc.logistic_type == "Local Delivery"){
frm.set_value("custom_payment",1)	
		}
		if(frm.doc.workflow_state=="Arrived"){
frm.set_value("custom_arrived",1)	
		}
		
        if (frm.doc.grand_total && frm.doc.grand_total > 0) {
            frm.set_value("custom_duty", frm.doc.grand_total * 0.45);
			const conversion_rate = frm.doc.conversion_rate || 1;
        	frm.set_value("grand_total_sar", frm.doc.grand_total * conversion_rate);
        }
    },
	validate_ffw_quotation: function(frm) {
        if (frm.doc.ffw_quotation && frm.doc.ffw_quotation.length > 0) {
            let total = 0;

            if (frm.doc.product_description && frm.doc.product_description.length > 0) {
                frm.doc.product_description.forEach(row => {
                    total += flt(row.amount);
                });
            }

            frm.set_value('grand_total', total);

            let quoted = false;
            if (frm.doc.recommended_ffw) {
                frm.doc.ffw_quotation.forEach(row => {
                    if (row.ffw_name === frm.doc.recommended_ffw) {
                        quoted = true;
                    }
                });
            }

            if (!quoted) {
                frappe.throw(__('Recommended FFW not present in FFW Quotation table'));
            }
			if (frm.doc.quoted_currency === 'SAR') {
				if (flt(frm.doc.quoted_amount) !== flt(frm.doc.total_shipment_cost)) {
					if (!frm.doc.comments || !frm.doc.revised_quote) {
						frappe.custom_modal();
					}
				}
			} else {
				if (flt(frm.doc.quoted_value_in_company_currency) !== flt(frm.doc.total_shipment_cost)) {
					if (!frm.doc.comments || !frm.doc.revised_quote) {
						frappe.custom_modal();
					}
				}
			}
        }
    },

	show_dialogue_on_quoted_amount(frm) {
		let d = new frappe.ui.Dialog({
			title: 'Reason for Discrepancy',
			fields: [
				{
					label: 'Comments',
					fieldname: 'comments',
					fieldtype: 'Small Text',
					placeholder: 'Please provide comments for the quoted amount discrepancy',
					reqd: 1
				},
				{
					label: 'Revised Quote',
					fieldname: 'revised_quote',
					fieldtype: 'Data',
					hidden: 1
				}
			],
			primary_action_label: 'Submit',
			primary_action(values) {
				d.hide();
			}
		});
		d.show();
                frappe.d.$wrapper.find('.modal').modal({
                    backdrop: 'static',  
                    keyboard: false     
                });
	},
	// price_list_currency(frm){
	// 	frm.trigger("currency")
	// },
	// currency(frm){
	// 	frappe.call({
	// 		method: "jgb.jgb.doctype.logistics_request.logistics_request.return_conversion",
	// 		args:{
	// 			"currency":frm.doc.currency,
	// 			"price_list_currency":frm.doc.price_list_currency
	// 		},
	// 		callback(r){
	// 			if(r){
	// 				frm.set_value('conv_rate',r.message)
	// 			}
	// 		}
	// 	})
	// 	$.each(frm.doc.ffw_quotation,function(i,j){
	// 		j.percentage_on_purchase_value = (j.total / (frm.doc.grand_total * frm.doc.conv_rate)) * 100
	// 	})
	// 	frm.refresh_field("ffw_quotation")
		
		
	// },
	recommended_ffw(frm) {
		if (frm.doc.recommended_ffw) {
			console.log('HI')
			let found = false;
			(frm.doc.ffw_quotation || []).forEach(row => {
				if (row.ffw_name === frm.doc.recommended_ffw) {
					console.log('1')
					frm.set_value('quoted_amount_sar', row.quoted_value_sar);
					found = true;
				}
			});
			if (!found) {
				console.log('2')
				frappe.msgprint('Recommended FFW not in the FFW Quotation list');
				frm.set_value('recommended_ffw', '');
				frm.set_value('quoted_amount_sar', 0);
			}
		} else {
			console.log('3')
			frm.set_value('quoted_amount_sar', 0);
		}
	},
	inventory_destination(frm) {
        if (frm.doc.inventory_destination === "JGB Warehouse") {
            frm.set_df_property('warehouse', 'label', 'Warehouse');
        } else {
            frm.set_df_property('warehouse', 'label', 'Final Destination');
        }
    },
	onload: function (frm) {
		if (frm.doc.inventory_destination === "JGB Warehouse") {
            frm.set_df_property('warehouse', 'label', 'Warehouse');
        } else {
            frm.set_df_property('warehouse', 'label', 'Final Destination');
        }
		if(frm.doc.logistics_type=="Local Delivery" && !frm.doc.inventory_destination){
			frm.set_value("inventory_destination","Direct to Customer")
		}
		if(frm.doc.inventory_destination && !frm.doc.warehouse && frm.doc.inventory_destination=="Warehouse Bonded"){
			frappe.db.get_value("Warehouse", {
					company: frm.doc.company,
					is_group: 0
				}, "name").then(r => {
					if (r.message && r.message.name) {
						frappe.after_ajax(() => {
							frm.set_value("warehouse", r.message.name);
						});
					} 
				});
			}
		
		
		// logistics_set_query(frm);
		if (frm.doc.logistic_type) {
			frm.set_df_property('logistic_type', 'read_only', 1);
		}
		else {
			frm.set_df_property('logistic_type', 'read_only', 0);
		}
        frm.set_query("recommended_ffw", function() {
            return {
				filters: {
					"ffw": 1
				}
			}
        });
		
		if (frm.doc.__islocal) {
			if (frm.doc.order_no) {
				frappe.call({
					method: 'frappe.client.get',
					args: {
						'doctype': frm.doc.po_so,
						'name': frm.doc.order_no,
					},
					callback(r) {
						if (frm.doc.po_so == 'Purchase Order'){
							// frm.set_value('product_description', r.message.items)
							// frm.refresh_fields('product_description')
							frm.set_value('requester_name', r.message.owner)
							frm.set_value('cargo_type', r.message.custom_cargo_type)
						}
						frm.set_value('grand_total', r.message.grand_total)
						frm.set_value('custom_duty', r.message.grand_total* 0.45)
						// if (r.message.currency=='SAR'){
						// 	frm.set_value('custom_duty', r.message.grand_total * 0.45)
						// }
						// else{
						// 	frm.set_value('custom_duty', r.message.base_grand_total * 0.45)
						// }
						frm.set_value('supplier', r.message.supplier)
						frm.set_value('customer', r.message.customer)
						frm.set_value('company', r.message.company)
						if (frm.doc.po_so == 'Sales Invoice'){
							frm.set_value('inventory_destination', 'Direct to Customer')
							frm.set_value('jgb_incoterms', r.message.incoterm || '')
							frm.set_value('requester_name', r.message.owner)
						}
						
						
						
					}
				})
			}
		}
		

		if (frm.doc.__islocal) {
			// frm.clear_table('document_attached')
			// frm.clear_table('support_documents')
				if(frm.doc.logistic_type == 'Export' && frm.doc.cargo_type=="Sea" && frm.doc.cargo_type=="Air"){
					// frm.clear_table('document_attached')
					var data = [{ 'title': 'Commercial Invoice' },
					{ 'title': 'Packing List' },
					{ 'title': 'Fumigation Certificate (if needed)' },
					{ 'title': 'E-way Bill / Transport Document' },
					]
					$.each(data, function (i, v) {
						frm.add_child('document_attached', {
							title: v.title,
						})
						frm.refresh_field('document_attached')
					})
					var data2 = [{ 'title': 'Shipping Bill' },
					{ 'title': 'Bill of Lading (B/L)' },
					{ 'title': 'Certificate of Origin' },
					]
					$.each(data2, function (i, v) {
						frm.add_child('support_documents', {
							document_type: v.title,
						})
						frm.refresh_field('support_documents')
					})
				}
				if(frm.doc.logistic_type == 'Import' && frm.doc.cargo_type=="Sea" && frm.doc.cargo_type=="Air"){
					var data = [{ 'title': 'Commercial Invoice' },
					{ 'title': 'Packing List' },
					{ 'title': 'MTC / MTR Report' },
					{ 'title': 'Form 1' },
					{ 'title': 'Material BOM' },
					{ 'title': 'Catelog' },
					{ 'title': 'FTA (Free Trade Agreement)' },
					{ 'title': 'BIS / NOC' },
					]
					$.each(data, function (i, v) {
						frm.add_child('document_attached', {
							title: v.title,
						})
						frm.refresh_field('document_attached')
					})
					var data2 = [{ 'title': 'Bill of Entry' },
					{ 'title': 'Bill of Lading (B/L)' },
					
					]
					$.each(data2, function (i, v) {
						frm.add_child('support_documents', {
							document_type: v.title,
						})
						frm.refresh_field('support_documents')
					})
				}
				if(frm.doc.cargo_type=="Sea"){
					var data2 = [{ 'title': 'Port / Handling Charges' },
					{ 'title': 'Delivery Order' },
					{ 'title': 'Mawani Charges' },
					]
					$.each(data2, function (i, v) {
						frm.add_child('support_documents', {
							document_type: v.title,
						})
						frm.refresh_field('support_documents')
					})
				}
				if(frm.doc.cargo_type=="Air"){
					var data2 = [{ 'title': 'SAL Charges' },
					{ 'title': 'Customs ' },
					]
					$.each(data2, function (i, v) {
						frm.add_child('support_documents', {
							document_type: v.title,
						})
						frm.refresh_field('support_documents')
					})
				}

			
		}
		
		frm.set_query("ffw", function () {
			return {
				filters: {
					"ffw": 1
				}
			}
		})
		
		frm.set_query("pol_seaportairport", function () {
			return {
				filters: {
					"cargo_type": frm.doc.cargo_type
				}
			}
		})
		frm.set_query("pod_seaportairport", function () {
			return {
				filters: {
					"cargo_type": frm.doc.cargo_type,
					// "pod'_seaportairport" : 
				}
			}
		})
		
	},
	eta(frm) {
		frm.trigger('transit_time')
		
	},
	
	etd(frm) {
		frm.trigger('transit_time')
	},
	transit_time(frm) {
		if (frm.doc.eta && frm.doc.etd) {
			if(frm.doc.eta<frm.doc.etd){
				frm.set_value('eta','')
				frm.set_value('transit_time', '')
				frappe.msgprint('ETA cannot be before ETD')
			}
			else{
				var transit_time = frappe.datetime.get_diff(frm.doc.eta, frm.doc.etd)
				frm.set_value('transit_time', transit_time)
			}
		}
	},
	 
	
	
	
});



frappe.ui.form.on('Logistics Request Item', {
	qty(frm, cdt, cdn) {
		var child = locals[cdt][cdn]
		if (child.qty && child.rate) {
			child.amount = child.qty * child.rate
		}
		var total = 0
		$.each(frm.doc.product_description, function (i, v) {
			total = total + v.amount
		})
		frm.refresh_fields('product_description')
		frm.set_value('grand_total', total)
		// frm.set_value('freight_rate', total)
		// frm.set_value('custom_duty', total * 0.45)
	},
	product_description_remove(frm) {
		var total = 0
		$.each(frm.doc.product_description, function (i, v) {
			if (v.amount) {
				total = total + v.amount
			}
		})
		frm.set_value('grand_total', total)
		// frm.set_value('freight_rate', total)
		// frm.set_value('custom_duty', total * 0.45)
	},
// 	payment_challan(frm) {
// 		if (frm.doc.payment_challan) {
// 			frm.set_value('customs_clearance_status', 'Payment Done')
// 		}
// 	}
})



frappe.ui.form.on('Supporting Document', {
	attach(frm, cdt, cdn) {
		var child = locals[cdt][cdn]
		if (child.attach) {
			if (child.document_type == 'Bill of Entry') {
				
			}
		}
	},
	currency(frm, cdt, cdn) {
		update_cost_in_sar(frm, cdt, cdn);
	},

	cost(frm, cdt, cdn) {
		update_cost_in_sar(frm, cdt, cdn);
	},
})
frappe.ui.form.on('LR Costing', {
	currency(frm, cdt, cdn) {
		update_cost_in_sar(frm, cdt, cdn);
	},

	cost(frm, cdt, cdn) {
		update_cost_in_sar(frm, cdt, cdn);
	},
	
	attach_challan(frm, cdt, cdn){
		const child = locals[cdt][cdn];

    if (!child.attach_challan) {
        frappe.msgprint("Please attach a challan before proceeding.");
        return;
    }

    frappe.call({
        method: "jgb.jgb.doctype.logistics_request.logistics_request.send_accounts_mail",
        args: {
            parent_name: frm.doc.name,
            row_title: child.title,
            cost: child.cost,
            attach_challan: child.attach_challan
        },
        callback: function(r) {
            if (!r.exc) {
                // frappe.msgprint("Accounts team has been notified.");
            }
        }
    });
	}
});
frappe.ui.form.on('LR Costing Payment', {
	attach_payment(frm, cdt, cdn){
		const child = locals[cdt][cdn];

	if(child.attach_payment){
		frappe.call({
			method: "jgb.jgb.doctype.logistics_request.logistics_request.send_lr_team_mail",
			args: {
				parent_name: frm.doc.name,
				row_title: child.title,
				cost: child.cost,
				attach_payment: child.attach_payment
			},
			callback: function(r) {
				if (!r.exc) {
					// frappe.msgprint("Logistics team has been notified.");
				}
			}
		});
	}
	},
	
})
frappe.ui.form.on('LR Costing Payment PO', {
	cost(frm, cdt, cdn){
		const child = locals[cdt][cdn];
		update_cost_in_sar(frm, cdt, cdn);
	},
	currency(frm, cdt, cdn){
		const child = locals[cdt][cdn];
		update_cost_in_sar(frm, cdt, cdn);
	},
	attach_payment(frm, cdt, cdn){
		const child = locals[cdt][cdn];

	if(child.attach_payment){
		frappe.call({
			method: "jgb.jgb.doctype.logistics_request.logistics_request.send_lr_team_mail",
			args: {
				parent_name: frm.doc.name,
				row_title: child.title,
				cost: child.cost,
				attach_payment: child.attach_payment,
				
			},
			callback: function(r) {
				if (!r.exc) {
					// frappe.msgprint("Logistics team has been notified.");
				}
			}
		});
	}
	},
	book_invoice(frm, cdt, cdn){
		const child = locals[cdt][cdn];
		if(!child.purchase_invoice){
			frappe.call({
				method: "jgb.jgb.doctype.logistics_request.logistics_request.create_pi_for_lr",
				args: {
					parent_name: frm.doc.name,
					row_title: child.title,
					cost: child.cost,
					supplier: child.supplier,
					currency: child.currency,
					cost_sar: child.cost_in_sar,
					lr_type:frm.doc.logistic_type
				},
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt,cdn,"purchase_invoice",r.message)
						frappe.model.set_value(cdt,cdn,"status","Draft")
						 frm.save();
						frappe.msgprint("Purchase Invoice created Successfully");
					}
				}
			});
		}
		else{
			frappe.msgprint("Purchase Invoice already created")
		}
	}
})
function update_cost_in_sar(frm, cdt, cdn) {
	let child = locals[cdt][cdn];

	if (child.currency && child.cost > 0) {
		if (child.currency !== 'SAR') {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Currency Exchange",
					filters: {
						from_currency: child.currency,
						to_currency: "SAR"
					},
					fields: ["exchange_rate", "date"],
					order_by: "date desc",
					limit_page_length: 1
				},
				callback: function (r) {
					if (r.message && r.message.length > 0) {
						let rate = flt(r.message[0].exchange_rate);
						child.cost_in_sar = flt(child.cost) * rate;
					} else {
						child.cost_in_sar = 0;
						frappe.msgprint("No currency exchange rate found for " + child.currency + " to SAR.");
					}
					frm.refresh_field('support_documents');
				}
			});
		} else {
			child.cost_in_sar = flt(child.cost);
			frm.refresh_field('support_documents');
		}
	} else {
		child.cost_in_sar = 0;
		frm.refresh_field('support_documents');
	}
}


frappe.ui.form.on('FFW Quotation', {
	quoted_value(frm, cdt, cdn) {
		var child = locals[cdt][cdn]

		if (!child.currency) {
			frappe.msgprint(__('Please select a currency in the row.'));
			return;
		}

		if (child.currency !== 'SAR') {
			frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Currency Exchange",
				filters: {
					from_currency: child.currency,
					to_currency: "SAR"
				},
				fields: ["exchange_rate", "date"],
				order_by: "date desc",
				limit_page_length: 1
			},
			callback: function (r) {
				if (r.message && r.message.length > 0) {
					let rate = flt(r.message[0].exchange_rate);
					child.quoted_value_sar = flt(child.quoted_value) * rate;
					child.exchange_rate = rate;
					frm.refresh_field('ffw_quotation');
				} else {
					frappe.msgprint("No currency exchange rate found for " + child.currency + " to SAR.");
				}
					}
				});
		} else {
			child.quoted_value_sar = child.quoted_value;
		}
		child.percentage_on_purchase_value = (child.quoted_value / (frm.doc.grand_total * frm.doc.conv_rate)) * 100
		child.total = child.quoted_value

		frm.refresh_fields('ffw_quotation')
		
	},
	clearance_amount(frm, cdt, cdn) {
		var child = locals[cdt][cdn]
		child.total = child.quoted_value + child.clearance_amount
		child.percentage_on_purchase_value = (child.total / (frm.doc.grand_total * frm.doc.conv_rate)) * 100


		frm.refresh_fields('ffw_quotation')
	},
})


frappe.custom_modal = function () {
	const modal_html = `
	<style>
		.browse-btn {
			background-color: #f3f3f3;
			color: #525252;
			border: none;
			padding: 5px 15px;
			border-radius: 8px;
			font-size: 13px;
			cursor: pointer;
			transition: background-color 0.3s;
			font-weight: 500;
			margin-top: 5px;
		}
		.browse-btn:hover {
			background-color: #e2e2e2;
		}
	</style>
	<div class="modal fade custom-gst-modal" tabindex="-1" role="dialog">
		<div class="modal-dialog" role="document">
			<div class="modal-content">
				<div class="modal-header">
					<h5 class="modal-title">Discrepancy in Quoted Amount</h5>
				</div>
				<div class="modal-body">
					<p>Comments</p>
					<textarea class="form-control" id="comments" rows="3" placeholder="Enter reason for discrepancy in Quote Amount"></textarea>

					<p class="mt-3 mb-1">Revised Quote</p>
					<label class="browse-btn" for="fileInput">Attach File</label>
					<input type="file" id="fileInput" hidden>
					<small id="file-name" class="text-muted"></small>
				</div>
				<div class="ml-auto mr-4 mt-1 mb-3">
					<button type="button" class="btn btn-primary" id="submit_comments">Submit</button>
				</div>
			</div>
		</div>
	</div>`;

	// Remove existing modals
	$('.custom-gst-modal').remove();

	// Append modal to body and show it
	$('body').append(modal_html);
	const modal = $('.custom-gst-modal');
	modal.modal({ backdrop: 'static', keyboard: false });
	modal.modal('show');

	// Show selected file name
	$(document).on('change', '#fileInput', function () {
		const fileName = this.files.length ? this.files[0].name : '';
		$('#file-name').text(fileName);
	});

	// Submit handler
	$('#submit_comments').on('click', function () {
	const reason = $('#comments').val();
	const fileInput = $('#fileInput')[0];

	if (!reason) {
		frappe.msgprint('Reason is required.');
		return;
	}

	if (!fileInput.files.length) {
		frappe.msgprint('Please select a file to attach.');
		return;
	}

	const file = fileInput.files[0];
	const formData = new FormData();
	formData.append('file', file);
	formData.append('doctype', cur_frm.doctype);
	formData.append('docname', cur_frm.docname);
	formData.append('fieldname', 'revised_quote');
	formData.append('is_private', 0); // Set to 1 if you want it private

	$.ajax({
		url: '/api/method/upload_file',
		type: 'POST',
		data: formData,
		contentType: false,
		processData: false,
		headers: {
			'X-Frappe-CSRF-Token': frappe.csrf_token
		},
		success: function (response) {
			if (response.message && response.message.file_url) {
				cur_frm.set_value('revised_quote', response.message.file_url);
				cur_frm.set_value('comments', reason);
				cur_frm.set_value('status', "Variation - Pending for Finance");
				frappe.msgprint('File uploaded successfully.');
				cur_frm.save()
			} else {
				frappe.msgprint('Upload succeeded, but no file URL returned.');
			}
			$('.custom-gst-modal').modal('hide');
		},
		error: function (xhr) {
			console.error(xhr.responseText);
			frappe.msgprint('File upload failed.');
		}
	});
});


};

function logistics_set_query(frm) {
    frm.set_query("cargo_type", function() {
        if (frm.doc.logistic_type !== "Local Delivery") {
            return {
                filters: {
                    type: ["!=", "Local Delivery"]
                }
            };
        } else {
            return {};
        }
    });
}

