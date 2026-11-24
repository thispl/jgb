// ERPNext's core BuyingController (erpnext/public/js/controllers/buying.js)
// registers an old-style `project` handler on the items grid that copies the
// Project entered on one row into every other empty row of the same document.
// JGB records Project per item row, so we neutralise that handler on load to
// keep the Project value row-specific.
frappe.ui.form.on("Purchase Invoice", {
	onload(frm) {
		if (frm.cscript && frm.cscript.project) {
			frm.cscript.project = function () {};
		}
	},
});
