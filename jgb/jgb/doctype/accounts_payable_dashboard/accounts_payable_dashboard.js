frappe.ui.form.on("Accounts Payable Dashboard", {
    refresh(frm) {
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
        window.open(_ap_dashboard_url(frm, "download_excel"), "_blank");
    },

    print(frm) {
        if (!frm.doc.company) {
            frappe.msgprint("Kindly choose the company.");
            return;
        }

        var fmt_map = {
            "Supplier Wise": "AP Supplier Wise Aging",
            "Vendor Wise": "AP Supplier Wise Aging",
            "Division Wise": "AP Division Wise Aging"
        };
        var print_format = fmt_map[frm.doc.primary_grouping] || "AP Supplier Wise Aging";

        var open_pdf = function () {
            var name = frm.doc.name || frm.doc.doctype;
            var url = frappe.urllib.get_full_url(
                "/api/method/frappe.utils.print_format.download_pdf?" +
                "doctype=" + encodeURIComponent(frm.doc.doctype) +
                "&name=" + encodeURIComponent(name) +
                "&trigger_print=1" +
                "&format=" + encodeURIComponent(print_format) +
                "&no_letterhead=0"
            );
            window.open(url, "_blank");
        };

        if (frm.is_dirty()) {
            frm.save_or_update().then(open_pdf);
        } else {
            open_pdf();
        }
    }
});

function _ap_dashboard_url(frm, method) {
    var params = [
        "company=" + encodeURIComponent(frm.doc.company || ""),
        "report_view_type=" + encodeURIComponent(frm.doc.report_view_type || "Summary"),
        "primary_grouping=" + encodeURIComponent(frm.doc.primary_grouping || "Supplier Wise"),
        "supplier=" + encodeURIComponent(frm.doc.supplier || ""),
        "division=" + encodeURIComponent(frm.doc.division || ""),
        "as_of_date=" + encodeURIComponent(frm.doc.as_of_date || ""),
        "aging_method__basis=" + encodeURIComponent(frm.doc.aging_method__basis || "Due Date"),
        "show_unapplied_payments_and_credits_as_separate_line=" + encodeURIComponent(frm.doc.show_unapplied_payments_and_credits_as_separate_line || 0),
        "purchase_type=" + encodeURIComponent(frm.doc.purchase_type || ""),
        "currency=" + encodeURIComponent(frm.doc.currency || "")
    ].join("&");

    return frappe.urllib.get_full_url(
        "/api/method/jgb.jgb.doctype.accounts_payable_dashboard.accounts_payable_dashboard." + method + "?" + params
    );
}
