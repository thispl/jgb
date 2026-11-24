import frappe


def check():
    # Check supplier S-00172
    supplier = frappe.db.get_value("Supplier", "S-00172", ["name", "supplier_name"], as_dict=True)
    print(f"Supplier S-00172: {supplier}")

    # Check PRJGBKSA200003 details
    pr = frappe.get_doc("Purchase Receipt", "PRJGBKSA200003")
    print(f"\n=== Purchase Receipt PRJGBKSA200003 ===")
    print(f"  Supplier: {pr.supplier} ({pr.supplier_name})")
    print(f"  Posting Date: {pr.posting_date}")
    print(f"  DocStatus: {pr.docstatus}")
    print(f"  Total: {pr.total}")
    print(f"  Grand Total: {pr.grand_total}")
    for item in pr.items:
        print(
            f"  Item: {item.item_code}, Qty: {item.qty}, Rate: {item.rate}, "
            f"Amount: {item.amount}, Warehouse: {item.warehouse}"
        )

    # Check if linked to Purchase Order
    print(f"\n  Purchase Order: {pr.purchase_order if hasattr(pr, 'purchase_order') else 'N/A'}")

    # Check linked Purchase Invoice
    pis = frappe.db.sql(
        """
        SELECT pi.name, pi.posting_date, pi.docstatus, pi.supplier, pi.total
        FROM `tabPurchase Invoice` pi
        JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
        WHERE pii.purchase_receipt = %s
        ORDER BY pi.posting_date DESC
    """,
        ("PRJGBKSA200003",),
        as_dict=True,
    )
    print(f"\n  Linked Purchase Invoices: {len(pis)}")
    for pi in pis:
        ds = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
        print(f"    {pi.name} | {pi.posting_date} | {ds.get(pi.docstatus)} | Total: {pi.total}")

    # Check GL entries for this PR
    print(f"\n  GL Entries for PRJGBKSA200003:")
    gles = frappe.db.sql(
        """
        SELECT account, debit, credit, against
        FROM `tabGL Entry`
        WHERE voucher_type = 'Purchase Receipt' AND voucher_no = %s
        ORDER BY debit DESC, credit DESC
    """,
        ("PRJGBKSA200003",),
        as_dict=True,
    )
    for gle in gles:
        print(f"    Account: {gle.account}, Debit: {gle.debit}, Credit: {gle.credit}, Against: {gle.against}")

    # Check if any delivery notes consumed stock from this PR
    # (Check SLEs that reference this PR as incoming and subsequent outgoing)
    print(f"\n  Stock Ledger for PRJGBKSA200003:")
    sle_pr = frappe.db.sql(
        """
        SELECT posting_date, actual_qty, qty_after_transaction, valuation_rate, warehouse
        FROM `tabStock Ledger Entry`
        WHERE voucher_type = 'Purchase Receipt' AND voucher_no = %s AND is_cancelled = 0
        ORDER BY posting_date ASC
    """,
        ("PRJGBKSA200003",),
        as_dict=True,
    )
    for s in sle_pr:
        print(f"    Date: {s.posting_date}, Qty: {s.actual_qty}, After: {s.qty_after_transaction}, Rate: {s.valuation_rate}, WH: {s.warehouse}")

    # Check ERP purchase order for this supplier
    pos = frappe.db.sql(
        """
        SELECT name, transaction_date, docstatus, total
        FROM `tabPurchase Order`
        WHERE supplier = %s AND docstatus = 1
        ORDER BY transaction_date DESC LIMIT 10
    """,
        ("S-00172",),
        as_dict=True,
    )
    print(f"\n=== Purchase Orders for S-00172 ===")
    for po in pos:
        print(f"  {po.name} | {po.transaction_date} | Total: {po.total}")

    # Check the Zoho supplier name - "Multiple Supply Trading EST" might be S-00172
    suppliers = frappe.db.get_all(
        "Supplier",
        filters={"supplier_name": ["like", "%Multiple Supply%"]},
        fields=["name", "supplier_name"],
    )
    print(f"\n=== Suppliers matching 'Multiple Supply' ===")
    for s in suppliers:
        print(f"  {s.name}: {s.supplier_name}")
