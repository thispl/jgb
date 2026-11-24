frappe.ui.form.on("Accounts Receivable Dashboard", {
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
        window.open(_ar_dashboard_url(frm, "download_excel"), "_blank");
    },

    print(frm) {
        if (!frm.doc.company) {
            frappe.msgprint("Kindly choose the company.");
            return;
        }

        var fmt_map = {
            "Customer Wise": "AR Customer Wise Aging",
            "Salesperson Wise": "AR Salesperson Wise Aging",
            "Division Wise": "AR Division Wise Aging",
            "Region Wise": "AR Region Wise Aging"
        };
        var print_format = fmt_map[frm.doc.primary_grouping] || "AR Customer Wise Aging";

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

function _ar_dashboard_url(frm, method) {
    var params = [
        "company=" + encodeURIComponent(frm.doc.company || ""),
        "report_view_type=" + encodeURIComponent(frm.doc.report_view_type || "Summary"),
        "primary_grouping=" + encodeURIComponent(frm.doc.primary_grouping || "Customer Wise"),
        "customer=" + encodeURIComponent(frm.doc.customer || ""),
        "sales_person=" + encodeURIComponent(frm.doc.sales_person || ""),
        "division=" + encodeURIComponent(frm.doc.division || ""),
        "region=" + encodeURIComponent(frm.doc.region || ""),
        "as_of_date=" + encodeURIComponent(frm.doc.as_of_date || ""),
        "aging_method__basis=" + encodeURIComponent(frm.doc.aging_method__basis || "Due Date"),
        "show_unapplied_payments_and_credits_as_separate_line=" + encodeURIComponent(frm.doc.show_unapplied_payments_and_credits_as_separate_line || 0),
        "advance_sales_invoice=" + encodeURIComponent(frm.doc.advance_sales_invoice || 0)
    ].join("&");

    return frappe.urllib.get_full_url(
        "/api/method/jgb.jgb.doctype.accounts_receivable_dashboard.accounts_receivable_dashboard." + method + "?" + params
    );
}
