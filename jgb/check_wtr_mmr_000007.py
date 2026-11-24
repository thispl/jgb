import frappe
import openpyxl
import os


def check():
    # 1. Check ERP stock balance for WTR-MMR-000007
    print("=" * 80)
    print("ERP STOCK BALANCE FOR WTR-MMR-000007")
    print("=" * 80)

    bins = frappe.db.get_all(
        "Bin",
        filters={"item_code": "WTR-MMR-000007"},
        fields=["warehouse", "actual_qty", "stock_value", "valuation_rate"],
    )
    print(f"\nCurrent Bin (warehouse-level) stock:")
    for b in bins:
        print(
            f"  Warehouse: {b.warehouse}, Qty: {b.actual_qty}, "
            f"Valuation Rate: {b.valuation_rate}, Stock Value: {b.stock_value}"
        )

    total_qty = sum(b.actual_qty for b in bins)
    print(f"\nTotal current ERP stock: {total_qty}")

    # 2. Check Stock Ledger Entries up to 31/05/2026
    print("\n" + "=" * 80)
    print("STOCK LEDGER ENTRIES UP TO 31/05/2026")
    print("=" * 80)

    sles = frappe.db.sql(
        """
        SELECT sle.name, sle.posting_date, sle.posting_time, sle.actual_qty,
               sle.qty_after_transaction, sle.valuation_rate, sle.stock_value,
               sle.voucher_type, sle.voucher_no, sle.warehouse, sle.item_code
        FROM `tabStock Ledger Entry` sle
        WHERE sle.item_code = %s
        AND sle.posting_date <= '2026-05-31'
        AND sle.is_cancelled = 0
        ORDER BY sle.posting_date ASC, sle.posting_time ASC, sle.creation ASC
    """,
        ("WTR-MMR-000007",),
        as_dict=True,
    )

    print(f"\nTotal SLEs up to 31/05/2026: {len(sles)}")
    running_qty = 0
    for sle in sles:
        running_qty += sle.actual_qty
        print(
            f"  Date: {sle.posting_date}, Voucher: {sle.voucher_type} / {sle.voucher_no}, "
            f"Qty: {sle.actual_qty}, After: {sle.qty_after_transaction}, "
            f"Rate: {sle.valuation_rate}, Warehouse: {sle.warehouse}"
        )

    print(f"\nBalance as of 31/05/2026 (from SLE running total): {running_qty}")

    # 3. Check ALL Stock Ledger Entries (including after 31/05/2026)
    print("\n" + "=" * 80)
    print("ALL STOCK LEDGER ENTRIES (including after 31/05/2026)")
    print("=" * 80)

    all_sles = frappe.db.sql(
        """
        SELECT sle.name, sle.posting_date, sle.posting_time, sle.actual_qty,
               sle.qty_after_transaction, sle.valuation_rate, sle.stock_value,
               sle.voucher_type, sle.voucher_no, sle.warehouse, sle.is_cancelled
        FROM `tabStock Ledger Entry` sle
        WHERE sle.item_code = %s
        ORDER BY sle.posting_date ASC, sle.posting_time ASC, sle.creation ASC
    """,
        ("WTR-MMR-000007",),
        as_dict=True,
    )

    print(f"\nTotal all SLEs: {len(all_sles)}")
    for sle in all_sles:
        status = "CANCELLED" if sle.is_cancelled else "ACTIVE"
        print(
            f"  Date: {sle.posting_date}, Voucher: {sle.voucher_type} / {sle.voucher_no}, "
            f"Qty: {sle.actual_qty}, After: {sle.qty_after_transaction}, "
            f"Rate: {sle.valuation_rate}, Warehouse: {sle.warehouse}, Status: {status}"
        )

    # 4. Check Stock Entries for this item
    print("\n" + "=" * 80)
    print("STOCK ENTRIES FOR WTR-MMR-000007")
    print("=" * 80)

    ses = frappe.db.sql(
        """
        SELECT se.name, se.purpose, se.posting_date, se.docstatus, se.stock_entry_type,
               sed.qty, sed.s_warehouse, sed.t_warehouse, sed.basic_rate, sed.valuation_rate,
               sed.serial_and_batch_bundle
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE sed.item_code = %s
        ORDER BY se.posting_date DESC
    """,
        ("WTR-MMR-000007",),
        as_dict=True,
    )

    print(f"\nTotal Stock Entries: {len(ses)}")
    for se in ses:
        docstatus_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
        print(
            f"  SE: {se.name}, Purpose: {se.purpose}, Date: {se.posting_date}, "
            f"Status: {docstatus_map.get(se.docstatus, se.docstatus)}, "
            f"Qty: {se.qty}, From: {se.s_warehouse}, To: {se.t_warehouse}, "
            f"Rate: {se.basic_rate}"
        )

    # 5. Check Purchase Receipts for this item
    print("\n" + "=" * 80)
    print("PURCHASE RECEIPTS FOR WTR-MMR-000007")
    print("=" * 80)

    prs = frappe.db.sql(
        """
        SELECT pr.name, pr.posting_date, pr.docstatus, pr.supplier,
               pri.qty, pri.warehouse, pri.rate, pri.amount
        FROM `tabPurchase Receipt` pr
        JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
        WHERE pri.item_code = %s
        ORDER BY pr.posting_date DESC
    """,
        ("WTR-MMR-000007",),
        as_dict=True,
    )

    print(f"\nTotal Purchase Receipts: {len(prs)}")
    for pr in prs:
        docstatus_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
        print(
            f"  PR: {pr.name}, Date: {pr.posting_date}, "
            f"Status: {docstatus_map.get(pr.docstatus, pr.docstatus)}, "
            f"Supplier: {pr.supplier}, Qty: {pr.qty}, Warehouse: {pr.warehouse}, Rate: {pr.rate}"
        )

    # 6. Check item details
    print("\n" + "=" * 80)
    print("ITEM DETAILS")
    print("=" * 80)

    item = frappe.db.get_value(
        "Item",
        "WTR-MMR-000007",
        [
            "name",
            "item_name",
            "stock_uom",
            "valuation_method",
            "has_batch_no",
            "has_serial_no",
            "is_stock_item",
            "opening_stock",
            "valuation_rate",
        ],
        as_dict=True,
    )
    print(f"Item: {item}")

    # 7. Read Zoho Inventory Summary
    print("\n" + "=" * 80)
    print("ZOHO INVENTORY SUMMARY")
    print("=" * 80)

    zoho_file = "/home/ubuntu/frappe-bench/Zoho Inventory Summary 2025.xlsx"
    if os.path.exists(zoho_file):
        wb = openpyxl.load_workbook(zoho_file, data_only=True)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            print(f"\nSheet: {sheet_name}")
            for row in ws.iter_rows(
                min_row=1, max_row=min(ws.max_row, 500), values_only=False
            ):
                for cell in row:
                    if cell.value and "WTR-MMR-000007" in str(cell.value):
                        row_num = cell.row
                        for r in range(
                            max(1, row_num - 2), min(ws.max_row + 1, row_num + 3)
                        ):
                            context = [
                                ws.cell(row=r, column=c).value
                                for c in range(1, min(ws.max_column + 1, 15))
                            ]
                            print(f"    Row {r}: {context}")
                        break
    else:
        print(f"File not found: {zoho_file}")

    # Also check the other Zoho file
    zoho_file2 = (
        "/home/ubuntu/frappe-bench/2025/Openings/Zoho Inventory Summary 2025.xlsx"
    )
    if os.path.exists(zoho_file2):
        wb2 = openpyxl.load_workbook(zoho_file2, data_only=True)
        for sheet_name in wb2.sheetnames:
            ws2 = wb2[sheet_name]
            print(f"\nZoho Openings Sheet: {sheet_name}")
            for row in ws2.iter_rows(
                min_row=1, max_row=min(ws2.max_row, 500), values_only=False
            ):
                for cell in row:
                    if cell.value and "WTR-MMR-000007" in str(cell.value):
                        row_num = cell.row
                        for r in range(
                            max(1, row_num - 2), min(ws2.max_row + 1, row_num + 3)
                        ):
                            context = [
                                ws2.cell(row=r, column=c).value
                                for c in range(1, min(ws2.max_column + 1, 15))
                            ]
                            print(f"    Row {r}: {context}")
                        break
