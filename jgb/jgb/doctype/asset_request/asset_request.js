// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Request", {
	refresh(frm) {
        if(frm.doc.docstatus==1){
            frm.add_custom_button(__("Print"), function () {
    			var f_name = frm.doc.name;
    			var print_format = "Asset Request";
    			window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
    				+ "doctype=" + encodeURIComponent("Asset Request")
    				+ "&name=" + encodeURIComponent(f_name)
    				+ "&trigger_print=1"
    				+ "&format=" + print_format
    				+ "&no_letterhead=0"
    		    ));
            });
        }
	},
});
