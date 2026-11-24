# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AssetAndSIMRequest(Document):
	# pass
    def before_submit(self):
        if not self.approved_budget or self.approved_budget <= 0:
        	frappe.throw("Kindly update the Approved Budget before submitting the Asset Request.")

    @frappe.whitelist()
    def get_asset_status(self):
        items = frappe.get_all(
            "Item",
            filters={"custom_from_asset_request": self.name},
            fields=["name", "item_code", "item_name", "asset_category"],
            order_by="creation asc"
        )

        if not items:
            return """
            <div style="
                padding:20px;
                text-align:center;
                background:#f8f9fa;
                border:1px solid #ddd;
                border-radius:8px;
                color:#6c757d;">
                No Items Created
            </div>
            """

        html = """
        <style>
            .asset-status-card{
                border:1px solid #e5e5e5;
                border-radius:10px;
                overflow:hidden;
                box-shadow:0 2px 8px rgba(0,0,0,.08);
                margin-top:10px;
            }

            .asset-status-title{
                background:#6F4A68;
                color:#fff;
                padding:12px 18px;
                font-size:18px;
                font-weight:700;
                display:flex;
                justify-content:center;
                align-items:center;
            }

            .asset-status-table{
                width:100%;
                border-collapse:collapse;
                font-size:14px;
            }

            .asset-status-table thead th{
                background:#6F4A68;
                color:#fff;
                padding:12px;
                text-align:left;
                border:1px solid #86637f;
                font-weight:600;
            }

            .asset-status-table tbody td{
                padding:12px;
                border:1px solid #ececec;
                background:#fff;
            }

            .asset-status-table tbody tr:nth-child(even){
                background:#fafafa;
            }

            .asset-status-table tbody tr:hover td{
                background:#f5eef4;
            }

            .asset-status-table a{
                color:#6F4A68;
                font-weight:600;
                text-decoration:none;
            }

            .asset-status-table a:hover{
                text-decoration:underline;
            }

            .asset-badge{
                display:inline-block;
                background:#f2e8ef;
                color:#6F4A68;
                padding:4px 10px;
                border-radius:20px;
                font-size:12px;
                font-weight:600;
            }

            .asset-footer{
                background:#fafafa;
                padding:10px 15px;
                text-align:right;
                font-weight:600;
                border-top:1px solid #e5e5e5;
            }
        </style>

        <div class="asset-status-card">

            <div class="asset-status-title">
                Asset Status
            </div>

            <table class="asset-status-table">
                <thead>
                    <tr>
                        <th width="5%">#</th>
                        <th width="25%">Item Code</th>
                        <th width="40%">Item Name</th>
                        <th width="30%">Asset Category</th>
                    </tr>
                </thead>

                <tbody>
        """

        for i, d in enumerate(items, 1):
            html += f"""
                <tr>
                    <td>{i}</td>

                    <td>
                        <a href="/app/item/{d.name}" target="_blank">
                            {d.item_code}
                        </a>
                    </td>

                    <td>{d.item_name or "-"}</td>

                    <td>
                        <span class="asset-badge">
                            {d.asset_category or "-"}
                        </span>
                    </td>
                </tr>
            """

        html += f"""
                </tbody>
            </table>

            <div class="asset-footer">
                Total Items Created : {len(items)}
            </div>

        </div>
        """

        return html
