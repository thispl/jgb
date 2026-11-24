// Copyright (c) 2026, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Party Payment Request", {
    onload_post_render(frm) {
        if (frm.doc.supplier && frm.is_new()) {
            frm.trigger("supplier");
        }
    },
	refresh(frm){
        // frm.set_query('bank_account', function() {
		// 	return {
		// 		filters: {
		// 			bank: frm.doc.bank
		// 		}
		// 	};p
		// });
        if(!frm.doc.__islocal){
        frm.add_custom_button(__("Print"), function () {
            if(frm.doc.docstatus == 0){
                var print_format = "Payment Request"
				var draft = 1
				}

                if(frm.doc.docstatus == 1){
                var print_format = "Payment Request"
				var draft = 0
				}
            var f_name = frm.doc.name
            window.open(frappe.urllib.get_full_url("/api/method/erpnext.utilities.pdf.download_pdf?"
                + "doctype=" + encodeURIComponent("Party Payment Request")
                + "&name=" + encodeURIComponent(f_name)
                + "&trigger_print=1"
                + "&draft=" + draft
                + "&format=" + print_format
                + "&no_letterhead=0"
               ));
            
        });
        
    }
    if (!frm.doc.__islocal && frm.doc.docstatus==1) {
        
        frm.add_custom_button(__("Payment"), function () {
            frappe.db.get_value('Payment Entry',{'custom_party_payment_request':frm.doc.name}, 'name')
             .then(r => {
             if(r.message.name){
                 frappe.set_route("Form","Payment Entry",r.message.name)
             }
             else{
           
            frappe.call({
                method: "jgb.jgb.doctype.party_payment_request.party_payment_request.get_payment_entry_route_data",
                args: { party_payment_request: frm.doc.name },
                freeze: true,
                freeze_message: "Creating Payment Entry...",
                callback(r) {
                    if (!r.message) return;

                    frappe.model.with_doctype("Payment Entry", function () {

                        let pe_name = frappe.model.make_new_doc_and_get_name("Payment Entry");
                        let pe = locals["Payment Entry"][pe_name];

                        pe.payment_type = "Pay";
                        pe.party_type = "Supplier";
                        pe.company = r.message.company;
                        pe.custom_party_payment_request = frm.doc.name;


                            pe.party = r.message.supplier;
                            pe.mode_of_payment = r.message.mode_of_payment;
                            pe.paid_amount = r.message.paid_amount;
                            pe.received_amount = r.message.received_amount;

                            frappe.set_route("Form", "Payment Entry", pe.name);

                        

                        });
                    }
                });
            }
        })

           
        }, __("Create"));
    }

        if(frm.doc.supplier){
            if(frm.doc.purchase_invoice_list.length > 0){
                frappe.call({
                    method:"jgb.jgb.doctype.party_payment_request.party_payment_request.pay_consolidated_req",
                    args:{
        				'name':frm.doc.name
                    },
                    callback(r){
                        if(r){
                            frm.get_field("payment_summary").$wrapper.html(r.message);
                        }
                    }
                })
            }
        }
    },
    chequereference_no(frm){
        $.each(frm.doc.purchase_invoice_list,function(i,d){
	        d.reference_no = frm.doc.chequereference_no
        })
	    frm.refresh_field("purchase_invoice_list");
	},
	chequereference_date(frm){
        $.each(frm.doc.purchase_invoice_list,function(i,d){
	        d.reference_date = frm.doc.chequereference_date
        })
	    frm.refresh_field("purchase_invoice_list");
	},
    grand_total(frm){
        frm.trigger('currency')
    },
    currency(frm){
        frappe.call({
            method :"jgb.jgb.doctype.party_payment_request.party_payment_request.get_currency_exchange",
            args: {
                'currency': frm.doc.currency,
            },
            callback(r){
                frm.set_value('currency_exchange',r.message)
                frm.set_value('amount_cc',frm.doc.currency_exchange * frm.doc.grand_total)
            }
        })
    },
    before_save(frm){
        if(frm.doc.__islocal){
        $.each(frm.doc.purchase_invoice_list,function(i,j){
            if(j.type == "Purchase Order" || j.type == "Purchase Invoice"){
                frappe.call({
                    method:"jgb.jgb.doctype.party_payment_request.party_payment_request.check_for_duplicate_payment",
                    args:{
        				'name':j.name1,
        				'doc_type':j.type,
        				'doc_name':frm.doc.name
                    },
                    callback(r){
                        if(r){
                            $.each(r,function(i,d){
                                if(d[1].length > 0){
                                }
                                
                            })
                            
                        }
                    }
                })
            }
        })
        }
    },
    validate(frm){
        $.each(frm.doc.purchase_invoice_list,function(i,j){
           if(j.payment_amount>j.outstanding_amount){
               frappe.msgprint("<b>"+j.name1+"</b> - Payment Amount is  less than or equal to outstanding amount ")
                frappe.validated = false
           }
        })
        var tot = 0
        var tot_cc = 0
        $.each(frm.doc.purchase_invoice_list,function(i,j){
            tot += j.payment_amount
            tot_cc += j.payment_amount_cc
            frm.set_value("payment_amount",tot)
            frm.set_value("payment_amount_cc",tot_cc)
        })
        $.each(frm.doc.purchase_invoice_list,function(i,d){
            d.payment_amount_cc = d.payment_amount * frm.doc.currency_exchange
        })
            frm.refresh_field('purchase_invoice_list')
            
    	
    },
	supplier(frm) {
	    
        frm.clear_table('purchase_invoice_list')
        frm.refresh_field('purchase_invoice_list')
        frappe.call({
            method :"jgb.jgb.doctype.party_payment_request.party_payment_request.get_def_currency",
            args: {
				'supplier': frm.doc.supplier,
			},
			callback(r){
			    if(r.message[0]){
			    frm.set_value('supplier_currency',r.message[0])
			    }
			    else{
			        frm.set_value('supplier_currency',"QAR")
			    }
			    if(r.message[1]){
			    frm.set_value('exchange_rate',r.message[1])
			    }
			    else{
			       frm.set_value('exchange_rate',"1") 
			    }
			}
        })
        
        frappe.call({
            method :"jgb.jgb.doctype.party_payment_request.party_payment_request.return_purchase_invoice",
            args: {
				'supplier': frm.doc.supplier,
				
			},

            callback(r){
            if(r.message){
                $.each(r.message[0],function(i,d){
                    if(d.currency != "SAR"){
                        frm.add_child('purchase_invoice_list',{
                            'type':"Purchase Invoice",
                            'name1':d.name,
                            'supplier':d.supplier,
                            'bill_no':"Purchase Invoice",
                            'company':d.company,
                            'grand_total':d.grand_total,
                            'grand_total_company_currency':d.grand_total*d.conversion_rate,
                            'posting_date':d.posting_date,
                            'outstanding_amount':d.outstanding_amount/d.conversion_rate,
                            'outstanding_amt':d.outstanding_amount,
                            'payment_amount':d.outstanding_amount/d.conversion_rate,
                            'payment_amount_cc':d.outstanding_amount,

                        })
                    }
                    frm.refresh_field('purchase_invoice_list')
                    if(d.currency == "SAR"){
                        frm.add_child('purchase_invoice_list',{
                            'type':"Purchase Invoice",
                            'name1':d.name,
                            'supplier':d.supplier,
                            'bill_no':"Purchase Invoice",
                            'company':d.company,
                            'posting_date':d.posting_date,
                            'grand_total':d.grand_total,
                            'grand_total_company_currency':d.grand_total*d.conversion_rate,
                            'outstanding_amount':d.outstanding_amount,
                            'payment_amount':d.outstanding_amount,
                            'payment_amount_cc':d.outstanding_amount*d.conversion_rate,
                            'outstanding_amt':d.outstanding_amount*d.conversion_rate,
                        })
                    }
                    frm.refresh_field('purchase_invoice_list')
                    
                })
                
                    $.each(r.message[1],function(i,d){ 
                        if(d.currency == "SAR"){ 
                            frm.add_child('purchase_invoice_list',{ 
                                'type':"Purchase Order",
                                'name1':d.name, 
                                'supplier':d.supplier, 
                                'bill_no':"Purchase Order", 
                                'project_number':d.project, 
                                'company':d.company, 
                                'posting_date':d.transaction_date, 
                                'outstanding_amount':(d.grand_total - d.advance_paid), 
                                'payment_amount':(d.grand_total - d.advance_paid),
                                'grand_total':d.grand_total,
                                'grand_total_company_currency':d.grand_total*d.conversion_rate,
                                'outstanding_amt':(d.grand_total - d.advance_paid)*d.conversion_rate, 
                                'payment_amount_cc':(d.grand_total - d.advance_paid)*d.conversion_rate, })
                        } 
                        frm.refresh_field('purchase_invoice_list')
                    if(d.currency != "SAR"){ 
                        frm.add_child('purchase_invoice_list',{ 
                            'type':"Purchase Order", 
                            'name1':d.name,
                            'supplier':d.supplier, 
                            'bill_no':"Purchase Order",
                            'project_number':d.project,
                            'company':d.company,
                            'posting_date':d.transaction_date, 
                            'outstanding_amount':d.grand_total - (d.advance_paid/d.conversion_rate), 
                            'payment_amount':(d.grand_total - (d.advance_paid/d.conversion_rate)),
                            'outstanding_amt':(d.grand_total - d.advance_paid)*d.conversion_rate, 
                            'grand_total':d.grand_total,
                            'grand_total_company_currency':d.grand_total*d.conversion_rate,
                            'payment_amount_cc':(d.grand_total - d.advance_paid)*d.conversion_rate, })
                        }
                        frm.refresh_field('purchase_invoice_list') 
                        
                    })
                $.each(r.message[2],function(i,d){
                    if(d.total_amount_currency == "SAR"){
                            frm.add_child('purchase_invoice_list',{
                                'type':"Journal Entry",
                                'name1':d.name,
                                'supplier':d.supplier,
                                'bill_no':"Journal Entry",
                                'company':d.company,
                                'posting_date':d.posting_date,
                                'outstanding_amount':d.total_credit,
                                'payment_amount':d.total_credit,
                                'grand_total':d.total_credit,
                                'grand_total_company_currency':d.total_credit*frm.doc.exchange_rate,
                                'outstanding_amt':d.total_credit*frm.doc.exchange_rate,
                                'payment_amount_cc':d.total_credit*frm.doc.exchange_rate,
                            })
                        
                    }
                    frm.refresh_field('purchase_invoice_list')
                    
                    if(d.total_amount_currency != "SAR"){
                        
                        frm.add_child('purchase_invoice_list',{
                            'type':"Journal Entry",
                            'name1':d.name,
                            'supplier':d.supplier,
                            'bill_no':"Journal Entry",
                            'company':d.company,
                            'posting_date':d.posting_date,
                            'outstanding_amount':d.total_credit/frm.doc.exchange_rate,
                            'payment_amount':d.total_credit/frm.doc.exchange_rate,
                            'grand_total':d.total_credit,
                            'grand_total_company_currency':d.total_credit,
                            'outstanding_amt':d.total_credit,
                            'payment_amount_cc':d.total_credit,
                        })
                        }
        
                    frm.refresh_field('purchase_invoice_list')
                })
                }
            }
        })
        
        
    }
});
frappe.ui.form.on("Purchase Invoice List", {
    payment_amount(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.name1 && row.type) {
            let doctype = row.type;

            frappe.db.get_value(
                doctype,
                row.name1,
                ["conversion_rate"],
                function (r) {
                    if (r && r.conversion_rate) {
                        let rate = flt(r.conversion_rate);
                        row.payment_amount_cc = flt(row.payment_amount) * rate;
                    } else {
                        row.payment_amount_cc = flt(row.payment_amount);
                    }

                    frm.refresh_field("purchase_invoice_list");
                }
            );
        }
    }
});