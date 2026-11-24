frappe.ui.form.on("Accounts Receivable Aging Report", {
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

        var entity = "";
        if (frm.doc.grouping === "Customer Wise" && frm.doc.customer) {
            entity = frm.doc.customer;
        } else if (frm.doc.grouping === "Salesperson Wise" && frm.doc.sales_person) {
            entity = frm.doc.sales_person;
        } else if (frm.doc.grouping === "Division Wise" && frm.doc.division) {
            entity = frm.doc.division;
        } else if (frm.doc.grouping === "Region Wise" && frm.doc.region) {
            entity = frm.doc.region;
        }

        var params = [
            "company=" + encodeURIComponent(frm.doc.company),
            "view_type=" + encodeURIComponent(frm.doc.view_type || "Summary"),
            "grouping=" + encodeURIComponent(frm.doc.grouping || "Customer Wise"),
            "entities=" + encodeURIComponent(entity),
            "as_of_date=" + encodeURIComponent(frm.doc.as_of_date || ""),
            "aging_method=" + encodeURIComponent(frm.doc.aging_method || "Due Date"),
            "show_unapplied=" + encodeURIComponent(frm.doc.show_unapplied || 0),
            "export_format=" + encodeURIComponent(frm.doc.export_format || "Excel")
        ].join("&");

        var url = frappe.urllib.get_full_url(
            "/api/method/jgb.jgb.doctype.accounts_receivable_aging_report.accounts_receivable_aging_report.download_report?" + params
        );
        window.open(url, "_blank");
    },

    print(frm) {
        if (!frm.doc.company) {
            frappe.msgprint("Kindly choose the company.");
            return;
        }

        var entity = "";
        if (frm.doc.grouping === "Customer Wise" && frm.doc.customer) {
            entity = frm.doc.customer;
        } else if (frm.doc.grouping === "Salesperson Wise" && frm.doc.sales_person) {
            entity = frm.doc.sales_person;
        } else if (frm.doc.grouping === "Division Wise" && frm.doc.division) {
            entity = frm.doc.division;
        } else if (frm.doc.grouping === "Region Wise" && frm.doc.region) {
            entity = frm.doc.region;
        }

        var params = [
            "company=" + encodeURIComponent(frm.doc.company),
            "view_type=" + encodeURIComponent(frm.doc.view_type || "Summary"),
            "grouping=" + encodeURIComponent(frm.doc.grouping || "Customer Wise"),
            "entities=" + encodeURIComponent(entity),
            "as_of_date=" + encodeURIComponent(frm.doc.as_of_date || ""),
            "aging_method=" + encodeURIComponent(frm.doc.aging_method || "Due Date"),
            "show_unapplied=" + encodeURIComponent(frm.doc.show_unapplied || 0),
            "export_format=" + encodeURIComponent("PDF")
        ].join("&");

        var url = frappe.urllib.get_full_url(
            "/api/method/jgb.jgb.doctype.accounts_receivable_aging_report.accounts_receivable_aging_report.print_report?" + params
        );
        window.open(url, "_blank");
    }
});
