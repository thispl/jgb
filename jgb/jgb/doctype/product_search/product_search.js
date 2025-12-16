// Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Product Search", {
    refresh(frm) {
		frm.disable_save()
	},
	item_code(frm){
        if(frm.doc.item_code){
            frm.call('get_data').then(r=>{
                if (r.message) {
                    frm.fields_dict.html.$wrapper.empty().append(r.message)
                }
            })
        }
        else{
            frm.fields_dict.html.$wrapper.empty().append()
        }

	},
});
