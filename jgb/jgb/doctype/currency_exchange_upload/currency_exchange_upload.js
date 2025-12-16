// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Currency Exchange Upload", {
	download_template(frm){
        let url = `/api/method/jgb.jgb.doctype.currency_exchange_upload.currency_exchange_upload.download_product_excel`;
        window.location.href = url;
    },
    upload(frm) {

        frappe.call({
            method: "jgb.jgb.doctype.currency_exchange_upload.currency_exchange_upload.upload_currency_exchange_excel",
            args: {
                file_url: frm.doc.file_attachment 
            },
            freeze: true,
            freeze_message:"Processing....",
            callback: function (r) {
                if (r.message && r.message.status === "success") {
                    frappe.msgprint(r.message.message);
                    frm.reload_doc(); 
                } 
            }
        });
    }

}); 
