// Copyright (c) 2025, TEAMPRO and contributors
// For license information, please see license.txt

frappe.ui.form.on('Logistics Request', {
	after_save(frm) {
		frm.refresh()
		frm.reload_doc();
	},
	truck_count: function (frm) {
		let count = frm.doc.truck_count || 0;
		frm.clear_table("table_gqxd");
		for (let i = 0; i < count; i++) {
			frm.add_child("table_gqxd");
		}
		frm.refresh_field("table_gqxd");
	},
	before_workflow_action(frm) {

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
	order_no(frm) {
		if (frm.doc.__islocal) {

			if (frm.doc.order_no) {
				frappe.call({
					method: 'frappe.client.get',
					args: {
						'doctype': frm.doc.po_so,
						'name': frm.doc.order_no,
					},
					callback(r) {
						if (frm.doc.po_so == 'Purchase Order') {
							frm.set_value('product_description', r.message.items)
							frm.refresh_fields('product_description')
						}

						frm.set_value('grand_total', r.message.grand_total)

						frm.set_value('custom_duty', r.message.grand_total * 0.45)
						frm.set_value('supplier', r.message.supplier)
						frm.set_value('customer', r.message.customer)
						frm.set_value('company', r.message.company)

						if (frm.doc.po_so == 'Sales Invoice') {

							frm.set_value('cargo_type', r.message.custom_cargo_mode)
							frm.set_value('inventory_destination', 'Direct to Customer')

						}
						frm.set_value('consignment_type', r.message.consignment_type)

						if (frm.doc.po_so == 'Delivery Note') {

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
		if (frm.doc.product_description && frm.doc.product_description.length > 0) {
			load_product_description(frm);
		}
		if ((frm.doc.workflow_state == "Scheduled" || frm.doc.workflow_state == "Dispatched" || frm.doc.workflow_state == "Arrived" || frm.doc.workflow_state == "Out for Delivery" || frm.doc.workflow_state == "Payment") && frappe.session.user == "bhuvaneswari.a@groupteampro.com") {
			frm.add_custom_button(__("Get Items From PO"), function () {

				let dialog = new frappe.ui.Dialog({
					title: __("Select Purchase Order"),
					fields: [
						{
							fieldname: "purchase_order",
							label: "Purchase Order",
							fieldtype: "Link",
							options: "Purchase Order",
							reqd: 1
						}
					],

					primary_action_label: __("Submit"),

					primary_action(values) {

						frappe.call({
							method: "jgb.jgb.doctype.logistics_request.logistics_request.get_po_details",
							args: {
								purchase_order: values.purchase_order
							},
							callback(r) {

								if (!r.message) return;

								let data = r.message;

								// Append Items
								data.items.forEach(item => {

									let row = frm.add_child("product_description");

									row.item_code = item.item_code;
									row.item_name = item.item_name;
									row.description = item.description;
									row.qty = item.qty;
									row.uom = item.uom;
									row.stock_uom = item.stock_uom;
									row.conversion_factor = item.conversion_factor;
									row.stock_qty = item.stock_qty;
									row.rate = item.rate;
									row.amount = item.amount;
									row.base_rate = item.base_rate;
									row.base_amount = item.base_amount;
									row.po_item = item.po_item;
									row.voucher_type = "Purchase Order";
									row.voucher_no = item.voucher_no;
									row.supplier = item.supplier;
									row.requester_name = item.requester_name;
									row.currency = item.currency;
								});

								// Update multiple_pos
								if (frm.doc.multiple_pos) {
									let pos = frm.doc.multiple_pos.split(",").map(d => d.trim());

									if (!pos.includes(values.purchase_order)) {
										pos.push(values.purchase_order);
										frm.set_value("multiple_pos", pos.join(", "));
									}
								} else {
									frm.set_value("multiple_pos", values.purchase_order);
								}

								// Set Order No if empty
								if (!frm.doc.order_no) {
									frm.set_value("order_no", values.purchase_order);
								}

								// Set Supplier if empty
								if (!frm.doc.supplier) {
									frm.set_value("supplier", data.supplier);
								}

								// Refresh child table
								frm.refresh_field("product_description");

								// Recalculate totals
								frm.trigger("calculate_totals");

								dialog.hide();

								frm.save().then(() => {
									frappe.show_alert({
										message: __("Logistics Request saved successfully"),
										indicator: "green"
									});
								});
							}
						});
					}
				});

				dialog.show();
			});
		}
		if ((frm.doc.workflow_state === "Draft" || frm.doc.workflow_state === "Arrived") && !frm.is_new()) {
			frm.add_custom_button(__("Connect Purchase Receipt"), function () {
				let dialog = new frappe.ui.Dialog({
					title: __("Connect Existing Purchase Receipt"),
					fields: [
						{
							fieldname: "purchase_receipt",
							label: "Purchase Receipt",
							fieldtype: "Link",
							options: "Purchase Receipt",
							reqd: 1,
							get_query: function () {
								let filters = {
									docstatus: ["!=", 2],
									custom_logistics_request: ["is", "not set"],
								};
								if (frm.doc.supplier) filters.supplier = frm.doc.supplier;
								if (frm.doc.company) filters.company = frm.doc.company;
								return { filters: filters };
							},
						},
					],
					primary_action_label: __("Connect"),
					primary_action(values) {
						frappe.call({
							method: "jgb.jgb.doctype.logistics_request.logistics_request.connect_purchase_receipt",
							args: {
								name: frm.doc.name,
								purchase_receipt: values.purchase_receipt,
							},
							callback(r) {
								if (!r.message) return;
								dialog.hide();
								frm.reload_doc();
								frappe.show_alert({
									message: __("Purchase Receipt {0} connected", [r.message.purchase_receipt]),
									indicator: "green",
								});
							},
						});
					},
				});
				dialog.show();
			});
		}
		if (frm.doc.workflow_state === "Completed" && frm.doc.additional == 0) {

			frm.add_custom_button(__('Create Additional Payment'), async function () {


				await frappe.call({
					method: "frappe.client.set_value",
					args: {
						doctype: frm.doctype,
						name: frm.doc.name,
						fieldname: {
							additional: 1
						}
					}
				});

				frm.reload_doc();

			}, __('Actions'));
		}
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
		if (frm.doc.logistic_type == "Local Delivery") {
			frm.set_query('cargo_type', () => {
				return {
					filters: [
						['name', 'in', ["Courier", "JGB Vehicle", "Road", "Supplier Scope", "Customer Scope"]]
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

		if (frm.doc.po_so == "Sales Invoice") {
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
		else {
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
		if ((frm.doc.workflow_state === 'Arrived' && frm.doc.logistic_type == 'Import')) {
			frappe.call({
				method: 'jgb.jgb.doctype.logistics_request.logistics_request.get_pr_conversion_status',
				args: { name: frm.doc.name },
				callback: function (r) {
					const status = r.message || {};
					if (status.has_pr) {
						frm.add_custom_button(__('View PR'), function () {
							frappe.set_route('List', 'Purchase Receipt', {
								custom_logistics_request: frm.doc.name
							});
						});
					}
					if (status.pending && status.pending.length) {



							// frm.page.add_action_item(__('Create PR'), async function () {
							//     const rows = frm.doc.product_description || [];

							//     if (!rows.length) {
							//         frappe.msgprint("No product description entries found.");
							//         return;
							//     }

							//     // Group rows by PO
							//     const voucherMap = {};
							//     rows.forEach(row => {
							//         if (row.voucher_no) {
							//             if (!voucherMap[row.voucher_no]) {
							//                 voucherMap[row.voucher_no] = [];
							//             }
							//             voucherMap[row.voucher_no].push(row);
							//         }
							//     });

							//     const voucherNos = Object.keys(voucherMap);
							//     if (!voucherNos.length) {
							//         frappe.msgprint("No Purchase Order found.");
							//         return;
							//     }

							//     frappe.model.with_doctype('Purchase Receipt', () => {
							//         let pr = frappe.model.get_new_doc('Purchase Receipt');
							//         pr.custom_logistics_request = frm.doc.name;

							//         const loadPO = (index = 0) => {
							//             if (index >= voucherNos.length) {
							//                 // Save PR
							//                 frappe.call({
							//                     method: "frappe.client.insert",
							//                     args: { doc: pr },
							//                     callback(r) {
							//                         if (r.message) {
							//                             frappe.set_route("Form", "Purchase Receipt", r.message.name);
							//                         }
							//                     }
							//                 });
							//                 return;
							//             }

							//             const po_id = voucherNos[index];

							//             frappe.call({
							//                 method: "frappe.client.get",
							//                 args: {
							//                     doctype: "Purchase Order",
							//                     name: po_id
							//                 },
							//                 callback(res) {
							//                     const po = res.message;

							//                     // Header values (set once)
							//                     if (!pr.supplier) pr.supplier = po.supplier;
							//                     if (!pr.custom_division) pr.custom_division = po.custom_division;
							//                     pr.currency = po.currency;
							//                     pr.conversion_rate = po.conversion_rate;
							//                     pr.set_warehouse = frm.doc.warehouse || "";

							//                     // ✅ ONLY product_description rows
							//                     voucherMap[po_id].forEach(row => {
							//                         let item = frappe.model.add_child(pr, "items");
							//                         item.item_code = row.item_code;
							//                         item.item_name = row.item_name;
							//                         item.qty = row.qty || 0;
							//                         item.received_qty = row.qty || 0;
							//                         item.uom = row.uom;
							//                         item.rate = row.rate;
							//                         item.amount = row.amount;
							//                         item.base_rate = row.base_rate;
							//                         item.base_amount = row.base_amount;
							//                         item.purchase_order = row.voucher_no;
							//                         item.warehouse = frm.doc.warehouse || row.warehouse;
							//                     });

							//                     loadPO(index + 1);
							//                 }
							//             });
							//         };

							//         loadPO();
							//     });
							// });
						frm.page.add_action_item(__('Create PR'), async function () {
							frappe.dom.freeze(__("Creating Purchase Receipts. Please wait..."));
							const block_unload = (e) => { e.preventDefault(); e.returnValue = ""; };
							window.addEventListener("beforeunload", block_unload);
							try {
								const res = await frappe.call({
									method: "jgb.jgb.doctype.logistics_request.logistics_request.create_purchase_receipts",
									args: { name: frm.doc.name }
								});
								const data = res.message || {};
								const created = data.created || [];
								const failed = Object.keys(data.failed || {});
								if (failed.length) {
									frappe.msgprint({
										title: __("Partially Completed"),
										message: __("Created: {0}<br>Failed for: {1}", [created.join(", ") || "-", failed.join(", ")]),
										indicator: "orange"
									});
								} else if (created.length) {
									frappe.msgprint({
										title: "Success",
										message: __("Purchase Receipts created for each Purchase Order in Logistics Request"),
										indicator: "green"
									});
								} else {
									frappe.msgprint(__("No Purchase Receipts to create."));
								}
							} finally {
								window.removeEventListener("beforeunload", block_unload);
								frappe.dom.unfreeze();
							}
						});
					}
				}
			});
		}

		if (frm.doc.workflow_state == "Closed" || frm.doc.workflow_state == "Completed") {
			frm.fields.forEach(function (field) {
				// frm.set_df_property(field.df.fieldname, "read_only", 1);
				if (fieldname != "additional_payment") {
					frm.set_df_property(field.df.fieldname, "read_only", 1);
				}
			});
		}
		if ((frm.doc.workflow_state === 'Arrived' || frm.doc.workflow_state === 'Closed') && frm.doc.logistic_type == 'Import') {
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
							// frappe.set_route('Form', 'Purchase Receipt', r.message[0].name);
							frappe.set_route('List', 'Purchase Receipt', {
								custom_logistics_request: frm.doc.name
							});
						});
					}
				}
			});
		}



		frappe.breadcrumbs.add("Buying", "Logistics Request");

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
		if (frappe.session.user == "divya.p@groupteampro.com") {
			frm.add_custom_button(__('Test'), function () {
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
				// const voucherNos = Object.keys(voucherMap).filter(
				// 	voucher => voucher === "POJGBKSA2223"
				// );

				if (!voucherNos.length) {
					frappe.msgprint("No Purchase Order found.");
					return;
				}
				frappe.model.with_doctype('Purchase Receipt', async () => {

					for (let i = 0; i < voucherNos.length; i++) {

						const po_id = voucherNos[i];

						const po_res = await frappe.call({
							method: "frappe.client.get",
							args: {
								doctype: "Purchase Order",
								name: po_id
							}
						});

						const po = po_res.message;

						let pr = frappe.model.get_new_doc('Purchase Receipt');
						pr.custom_logistics_request = frm.doc.name;
						pr.supplier = po.supplier;
						pr.custom_division = po.custom_division;
						pr.currency = po.currency;
						pr.conversion_rate = po.conversion_rate;
						pr.set_warehouse = frm.doc.warehouse || "";
						pr.apply_discount_on = po.apply_discount_on;
						pr.base_discount_amount = po.base_discount_amount;
						pr.additional_discount_percentage = po.additional_discount_percentage;
						pr.discount_amount = po.discount_amount;
						pr.custom_delivery_terms = po.custom_delivery_terms;
						pr.tc_name = po.tc_name;
						let total = 0;
						voucherMap[po_id].forEach(row => {
							let item = frappe.model.add_child(pr, "items");
							item.item_code = row.item_code;
							item.item_name = row.item_name;
							item.qty = row.qty || 0;
							item.received_qty = row.qty || 0;
							item.uom = row.uom;
							item.rate = row.rate;
							item.amount = row.amount;
							item.base_rate = row.base_rate;
							item.base_amount = row.base_amount;
							item.purchase_order = row.voucher_no;
							item.warehouse = frm.doc.warehouse || row.warehouse;
							total += flt(row.amount);
						});
						pr.custom_discount_percentage = po.custom_discount_percentage || 0;

						if (pr.custom_discount_percentage > 0) {
							pr.discount_amount =
								(total * pr.custom_discount_percentage) / 100;

							pr.apply_discount_on = "Net Total";
						}
						const pr_res = await frappe.call({
							method: "frappe.client.insert",
							args: { doc: pr }
						});


					}

					frappe.msgprint({
						title: "Success",
						message: __("Purchase Receipts created for each Purchase Order in Logistics Request"),
						indicator: "green"
					});
				});
			});
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
					"is_group": 0
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
	calculate_totals(frm) {

		let grand_total = 0;

		(frm.doc.product_description || []).forEach(row => {
			grand_total += flt(row.amount);
		});

		frm.set_value("grand_total", grand_total);

		// Example: if custom_duty = grand_total
		frm.set_value("custom_duty", grand_total);

		// If custom_duty has a different formula, replace the above line accordingly.
	},

	po_so(frm) {
		frm.set_value('order_no', '')
		if (frm.doc.__islocal) {
			if (frm.doc.logistic_type == 'Export' && frm.doc.cargo_type != "Sea") {
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
			if (frm.doc.logistic_type == 'Import' && frm.doc.cargo_type != "Sea") {
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
			if (frm.doc.cargo_type == "Sea") {
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
			if (frm.doc.cargo_type == "Air") {
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

	validate: function (frm) {
		if (frm.doc.workflow_state == "Scheduled") {
			frm.set_value("custom_details", 1)
		}
		if (frm.doc.workflow_state == "Dispatched") {
			frm.set_value("custom_schedule", 1)
		}
		if (frm.doc.workflow_state == "Out for Delivery" && frm.doc.logistic_type == "Local Delivery") {
			frm.set_value("custom_schedule", 1)
		}
		if (frm.doc.workflow_state == "Payment") {
			frm.set_value("custom_dispatched", 1)
		}
		if (frm.doc.workflow_state == "Out for Delivery" && !frm.doc.logistic_type == "Local Delivery") {
			frm.set_value("custom_payment", 1)
		}
		if (frm.doc.workflow_state == "Arrived") {
			frm.set_value("custom_arrived", 1)
		}

		if (frm.doc.grand_total && frm.doc.grand_total > 0) {
			frm.set_value("custom_duty", frm.doc.grand_total * 0.45);
			const conversion_rate = frm.doc.conversion_rate || 1;
			frm.set_value("grand_total_sar", frm.doc.grand_total * conversion_rate);
		}
	},
	validate_ffw_quotation: function (frm) {
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
		if (frm.doc.logistics_type == "Local Delivery" && !frm.doc.inventory_destination) {
			frm.set_value("inventory_destination", "Direct to Customer")
		}
		if (frm.doc.inventory_destination && !frm.doc.warehouse && frm.doc.inventory_destination == "Warehouse Bonded") {
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
		frm.set_query("recommended_ffw", function () {
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
						if (frm.doc.po_so == 'Purchase Order') {
							frm.set_value('requester_name', r.message.owner)
							// frm.set_value('cargo_type', r.message.custom_cargo_type)
						}
						frm.set_value('grand_total', r.message.grand_total)
						frm.set_value('custom_duty', r.message.grand_total * 0.45)
						frm.set_value('supplier', r.message.supplier)
						frm.set_value('customer', r.message.customer)
						frm.set_value('company', r.message.company)
						if (frm.doc.po_so == 'Sales Invoice') {
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
			if (frm.doc.logistic_type == 'Export' && frm.doc.cargo_type == "Sea" && frm.doc.cargo_type == "Air") {
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
			if (frm.doc.logistic_type == 'Import' && frm.doc.cargo_type == "Sea" && frm.doc.cargo_type == "Air") {
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
			if (frm.doc.cargo_type == "Sea") {
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
			if (frm.doc.cargo_type == "Air") {
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
			if (frm.doc.eta < frm.doc.etd) {
				frm.set_value('eta', '')
				frm.set_value('transit_time', '')
				frappe.msgprint('ETA cannot be before ETD')
			}
			else {
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

	attach_challan(frm, cdt, cdn) {
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
			callback: function (r) {
				if (!r.exc) {
					// frappe.msgprint("Accounts team has been notified.");
				}
			}
		});
	}
});
frappe.ui.form.on('LR Costing Payment', {
	// attach_payment(frm, cdt, cdn){
	// 	const child = locals[cdt][cdn];

	// if(child.attach_payment){
	// 	frappe.call({
	// 		method: "jgb.jgb.doctype.logistics_request.logistics_request.send_lr_team_mail",
	// 		args: {
	// 			parent_name: frm.doc.name,
	// 			row_title: child.title,
	// 			cost: child.cost,
	// 			attach_payment: child.attach_payment
	// 		},
	// 		callback: function(r) {
	// 			if (!r.exc) {
	// 				// frappe.msgprint("Logistics team has been notified.");
	// 			}
	// 		}
	// 	});
	// }
	// },

})
frappe.ui.form.on('LR Costing Payment PO', {
	cost(frm, cdt, cdn) {
		const child = locals[cdt][cdn];
		update_cost_in_sar(frm, cdt, cdn);
	},
	currency(frm, cdt, cdn) {
		const child = locals[cdt][cdn];
		update_cost_in_sar(frm, cdt, cdn);
	},

	book_invoice(frm, cdt, cdn) {
		const child = locals[cdt][cdn];
		if (!child.title) {
			frappe.msgprint(`Please enter a title of charge for row ${child.idx}.`);
			return;
		}
		if (!child.purchase_invoice || child.status === "Cancelled") {
			frappe.call({
				method: "jgb.jgb.doctype.logistics_request.logistics_request.create_pi_for_lr",
				args: {
					parent_name: frm.doc.name,
					row_title: child.title,
					cost: child.cost,
					supplier: child.supplier,
					currency: child.currency,
					cost_sar: child.cost_in_sar,
					lr_type: frm.doc.logistic_type
				},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "purchase_invoice", r.message)
						frappe.model.set_value(cdt, cdn, "status", "Draft")
						frm.save(frm.doc.docstatus === 1 ? "Update" : "Save");
						frappe.msgprint("Purchase Invoice created Successfully");
					}
				}
			});
		}
		else {
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
frappe.ui.form.on('Additional Payment', {
	cost(frm, cdt, cdn) {
		const child = locals[cdt][cdn];
		update_add_cost_in_sar(frm, cdt, cdn);
	},
	currency(frm, cdt, cdn) {
		const child = locals[cdt][cdn];
		update_add_cost_in_sar(frm, cdt, cdn);
	},

	book_invoice(frm, cdt, cdn) {
		const child = locals[cdt][cdn];
		if (!child.title) {
			frappe.msgprint(`Please enter a title of charge for row ${child.idx}.`);
			return;
		}
		if (!child.purchase_invoice || child.status === "Cancelled") {
			frappe.call({
				method: "jgb.jgb.doctype.logistics_request.logistics_request.create_additional_pi_for_lr",
				args: {
					parent_name: frm.doc.name,
					row_title: child.title,
					cost: child.cost,
					supplier: child.supplier,
					currency: child.currency,
					cost_sar: child.cost_in_sar,
					lr_type: frm.doc.logistic_type
				},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "purchase_invoice", r.message)
						frappe.model.set_value(cdt, cdn, "status", "Draft")
						//  frm.save();
						frm.save('Update');
						frappe.msgprint("Purchase Invoice created Successfully");
					}
				}
			});
		}
		else {
			frappe.msgprint("Purchase Invoice already created")
		}
	}
})
function update_add_cost_in_sar(frm, cdt, cdn) {
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
					frm.refresh_field('additional_payment');
				}
			});
		} else {
			child.cost_in_sar = flt(child.cost);
			frm.refresh_field('additional_payment');
		}
	} else {
		child.cost_in_sar = 0;
		frm.refresh_field('additional_payment');
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
	frm.set_query("cargo_type", function () {
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
// function load_product_description(frm) {

//     let data = frm.doc.product_description || [];

//     /* GROUP DATA */
//     let grouped = {};

//     data.forEach(function(d){
//         if(!d.voucher_type || !d.voucher_no) return;

//         if(!grouped[d.voucher_type]){
//             grouped[d.voucher_type] = new Set();
//         }

//         grouped[d.voucher_type].add(d.voucher_no);
//     });

//     let html = `
//     <div style="border:1px solid #d1d8dd;border-radius:6px;overflow:hidden;">

//     <div style="background:#75506A;color:#fff;padding:8px 10px;font-weight:bold;font-size:13px;text-align:center;">
//         Voucher Details
//     </div>

//     <div style="max-height:320px;overflow:auto;">

//     <table style="width:100%;border-collapse:collapse;font-size:13px;">

//     <thead style="position:sticky;top:0;background:#f1f3f5;">
//         <tr>
//             <th style="border:1px solid #ddd;padding:6px;width:60px;text-align:center;">#</th>
//             <th style="border:1px solid #ddd;padding:6px;text-align:left;width:180px;">Voucher Type</th>
//             <th style="border:1px solid #ddd;padding:6px;text-align:left;">Voucher No</th>
//         </tr>
//     </thead>

//     <tbody>
//     `;

//     let idx = 0;

//     Object.keys(grouped).forEach(function(voucher_type){

//         let vouchers = Array.from(grouped[voucher_type]);

//         vouchers.forEach(function(voucher_no, i){

//             idx++;

//             let row_color = idx % 2 === 0 ? "#f9fafb" : "#ffffff";

//             html += `
//             <tr style="background:${row_color};">

//                 <td style="border:1px solid #eee;padding:6px;text-align:center;">
//                     ${idx}
//                 </td>

//                 <td style="border:1px solid #eee;padding:6px;">
//                     ${voucher_type}
//                 </td>

//                 <td style="border:1px solid #eee;padding:6px;">
//                     <a href="#"
//                        style="color:#1f6feb;font-weight:500;text-decoration:none;"
//                        onclick="frappe.set_route('Form','${voucher_type}','${voucher_no}')">
//                        ${voucher_no}
//                     </a>
//                 </td>

//             </tr>
//             `;
//         });

//     });

//     if (!idx){
//         html += `
//         <tr>
//             <td colspan="3" style="text-align:center;padding:12px;color:#888;">
//                 No Voucher Details Found
//             </td>
//         </tr>`;
//     }

//     html += `
//     </tbody>
//     </table>
//     </div>
//     </div>
//     `;

//     frm.get_field("voucher_details").$wrapper.html(html);
// }
function load_product_description(frm) {

	let data = frm.doc.product_description || [];

	let grouped = {};

	data.forEach(function (d) {
		if (!d.voucher_type || !d.voucher_no) return;

		if (!grouped[d.voucher_type]) {
			grouped[d.voucher_type] = new Set();
		}

		grouped[d.voucher_type].add(d.voucher_no);
	});

	let html = `
    <div style="border:1px solid #d1d8dd;border-radius:6px;overflow:hidden;">
    
    <div style="background:#75506A;color:#fff;padding:8px 10px;font-weight:bold;font-size:13px;text-align:center;">
        Voucher Details
    </div>

    <div style="max-height:320px;overflow:auto;">
    
    <table style="width:100%;border-collapse:collapse;font-size:13px;">

    <thead style="position:sticky;top:0;background:#f1f3f5;">
        <tr>
            <th style="border:1px solid #ddd;padding:6px;width:60px;text-align:center;">#</th>
            <th style="border:1px solid #ddd;padding:6px;text-align:center;width:180px;">Voucher Type</th>
            <th style="border:1px solid #ddd;padding:6px;text-align:left;">Voucher No</th>
        </tr>
    </thead>

    <tbody>
    `;

	let idx = 0;

	Object.keys(grouped).forEach(function (voucher_type) {

		let vouchers = Array.from(grouped[voucher_type]);

		vouchers.forEach(function (voucher_no, i) {

			idx++;

			let row_color = idx % 2 === 0 ? "#f9fafb" : "#ffffff";

			html += `<tr style="background:${row_color};">`;

			html += `
                <td style="border:1px solid #eee;padding:6px;text-align:center;">
                    ${idx}
                </td>
            `;

			if (i === 0) {
				html += `
                <td rowspan="${vouchers.length}"
                    style="border:1px solid #eee;padding:6px;text-align:center;vertical-align:middle;font-weight:500;">
                    ${voucher_type}
                </td>`;
			}

			html += `
                <td style="border:1px solid #eee;padding:6px;">
                    <a href="#"
                       style="color:#1f6feb;font-weight:500;text-decoration:none;"
                       onclick="frappe.set_route('Form','${voucher_type}','${voucher_no}')">
                       ${voucher_no}
                    </a>
                </td>
            `;

			html += `</tr>`;
		});

	});

	if (!idx) {
		html += `
        <tr>
            <td colspan="3" style="text-align:center;padding:12px;color:#888;">
                No Voucher Details Found
            </td>
        </tr>`;
	}

	html += `
    </tbody>
    </table>
    </div>
    </div>
    `;

	frm.get_field("voucher_details").$wrapper.html(html);
}

frappe.ui.form.on('Logistics Request', {
	allocate_charges(frm) {
		if (!(frm.doc.additional_payment || []).length) {
			frappe.msgprint("Please add the Additional Payment rows before allocating.");
			return;
		}
		frappe.call({
			method: "jgb.jgb.doctype.logistics_request.logistics_request.get_delivery_charge_allocation",
			args: { parent_name: frm.doc.name },
			callback: function (r) {
				if (!r.message) return;
				frm.clear_table('delivery_allocation');
				r.message.forEach(row => frm.add_child('delivery_allocation', row));
				frm.refresh_field('delivery_allocation');
				if (frm.doc.allocation_basis === 'Volume') {
					frm.dirty();
					frappe.msgprint("Enter the Delivery charges manually for each Delivery Note. The total of each Title should match the Additional Payment cost.");
				} else {
					frm.save('Update');
				}
			}
		});
	}
});