// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("No due", {
	refresh(frm) {
         if(!frm.doc.__islocal && frm.doc.docstatus!=2){
            frm.add_custom_button(__("Print"), function () {
                var f_name = frm.doc.name
                var print_format ="No Due";
                window.open(frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
                    + "doctype=" + encodeURIComponent("No due")
                    + "&name=" + encodeURIComponent(f_name)
                    + "&trigger_print=1"
                    + "&format=" + print_format
                    + "&no_letterhead=0"
                ));
            });
         }

	},
});
