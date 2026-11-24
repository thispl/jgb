frappe.ui.form.on("Accounts Receivable Aging Dashboard", {
    refresh(frm) {
        // Set defaults on first load
        if (!frm.doc.company) {
            var def_company = frappe.defaults.get_default("Company");
            if (def_company) frm.set_value("company", def_company);
        }
        if (!frm.doc.as_of_date) {
            frm.set_value("as_of_date", frappe.datetime.get_today());
        }
    },

    download(frm) {
        if (!frm.doc.company) {
            frappe.msgprint("Kindly choose the company.");
            return;
        }
        frappe.dom.freeze("Generating report...");
        frappe.call({
            method: "jgb.jgb.doctype.accounts_receivable_aging_dashboard.accounts_receivable_aging_dashboard.download_report",
            args: { name: frm.doc.name },
            callback: function () {
                frappe.dom.unfreeze();
            },
            error: function () {
                frappe.dom.unfreeze();
            }
        });
    },

    print(frm) {
        if (!frm.doc.company) {
            frappe.msgprint("Kindly choose the company.");
            return;
        }
        var url = frappe.urllib.get_full_url(
            "/api/method/jgb.jgb.doctype.accounts_receivable_aging_dashboard.accounts_receivable_aging_dashboard.print_report"
        );
        window.open(url, "_blank");
    }
});
