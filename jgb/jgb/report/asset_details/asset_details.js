frappe.query_reports["Asset Details"] = {
	filters: [
		{
			fieldname: "asset_name",
			label: __("Asset Name"),
			fieldtype: "Link",
			options: "Asset",
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "item_name",
			label: __("Item Name"),
			fieldtype: "Data",
		},
		{
			fieldname: "custodian",
			label: __("Custodian"),
			fieldtype: "Link",
			options: "Employee",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "name") {
			return `<span class="jgb-asset-id">${value}</span>`;
		}

		if (column.fieldname === "custodian") {
			if (data && data.custodian) {
				return `<span class="jgb-asset-pill jgb-pill-blue">
					<span class="jgb-pill-dot"></span>${value}</span>`;
			}
			return "";
		}

		return value;
	},

	onload: function (report) {
		report.page.wrapper.addClass("jgb-asset-details-report");

		if (!document.getElementById("jgb-asset-details-style")) {
			$(`<style id="jgb-asset-details-style">
				.jgb-asset-details-report .dt-header {
					background: var(--gray-50);
					border-bottom: 1px solid var(--border-color);
				}
				.jgb-asset-details-report .dt-header .dt-cell__content {
					color: var(--gray-700);
					font-weight: 600;
					font-size: 11px;
					letter-spacing: 0.4px;
					text-transform: uppercase;
					text-align: center;
					justify-content: center;
				}
				.jgb-asset-details-report .dt-scrollable > .dt-row:nth-of-type(even) .dt-cell {
					background: var(--blue-50, #f4f8ff);
				}
				.jgb-asset-id {
					font-weight: 600;
					color: var(--primary);
				}
				.jgb-asset-pill {
					display: inline-flex;
					align-items: center;
					gap: 6px;
					padding: 2px 12px;
					border-radius: 999px;
					font-size: 12px;
					font-weight: 500;
					line-height: 1.6;
					white-space: nowrap;
				}
				.jgb-pill-dot {
					width: 7px;
					height: 7px;
					border-radius: 50%;
					flex-shrink: 0;
				}
				.jgb-pill-blue {
					background: var(--blue-100, #e8f0ff);
					color: var(--blue-700, #2d5fd3);
				}
				.jgb-pill-blue .jgb-pill-dot {
					background: var(--blue-500, #4d82f1);
				}
			</style>`).appendTo("head");
		}
	},

	get_datatable_options(options) {
		return Object.assign(options, {
			serialNoColumn: false,
		});
	},
};
