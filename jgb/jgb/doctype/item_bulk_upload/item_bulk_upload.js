// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item Bulk Upload", {
	refresh(frm) {
    frm.set_query("product", function () {
				return {
					filters: {
						item_group: frm.doc.item_group,
					},
				};
			});
	},
    download__template(frm){
         let product = frm.doc.product || "";
        let item_group = frm.doc.item_group || "";

        let url = `/api/method/jgb.jgb.doctype.item_bulk_upload.item_bulk_upload.download_product_excel?product=${product}&item_group=${item_group}`;
        window.location.href = url;
    },
    upload(frm){
        if (!frm.doc.upload) {
            // Clear the created_items field
            frm.set_value("created_items", "");
        }
        setTimeout(() => {
    frappe.call({
        method: "jgb.jgb.doctype.item_bulk_upload.item_bulk_upload.upload_and_create_items",
        args: {
            file_url: frm.doc.upload
        },
        freeze: true,
        callback: function (r) {
            if (r.message && r.message.status === "success") {
                frappe.msgprint(r.message.message);
                frm.refresh();
            }
        }
    });
}, 1000);  

    },
    download_created_item(frm){
      
    let url = "/api/method/jgb.jgb.doctype.item_bulk_upload.item_bulk_upload.download_created_items";
window.location.href = url;

        }
});
