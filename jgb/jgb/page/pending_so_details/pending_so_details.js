frappe.pages['pending-so-details'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Stock Allocation',
		single_column: true,
	});

	let $headerContainer = $(`
		<div class="form-group" style="
			display: flex;
			justify-content: space-between;
			align-items: center;
			margin: 10px 15px 10px 15px; /* top:10px, right:15px, bottom:10px, left:15px */
			padding: 5px 10px;
		">
			<div id="left-controls" style="display: flex; gap: 10px;"></div>
			<div id="right-controls" style="display: flex; gap: 10px;"></div>
		</div>
	`).appendTo(page.main);



	let division_filter = frappe.ui.form.make_control({
   		parent: $headerContainer.find("#left-controls").get(0),
		df: {
			fieldtype: "Link",
			options: "Division",
			placeholder: "Select Division",
			change: function () {
				load_data();
			}
		},
		render_input: true
	});

	let submit_btn = $('<button class="btn btn-primary">Allocate</button>')
		.click(() => {
			submitUpdatedProjects();
		})
		.appendTo($headerContainer.find("#right-controls"));

	let $container = $('<div>').appendTo(page.main);

	function load_data() {
		let selected_division = division_filter.get_value();

		frappe.call({
			method: "jgb.jgb.page.pending_so_details.pending_so_details.get_so_pending_details",
			args: {
				division: selected_division || null
			},
			freeze: true,
			freeze_message: "Loading...",
			callback: function (r) {
				if (r.message) {
					render_table(r.message);
				}
			}
		});
	}

	function render_table(data) {
		$container.empty();

		let html = `
			<style>
				table { width: 100%; border-collapse: collapse !important; }
				table, th, td { border: 1px solid black !important; }
				th {
					background-color: #5E3B63 !important;
					color: white !important;
					text-align: center;
					padding: 10px;
				}
				td {
					padding: 8px;
					text-align: center;
				}
				.left-align { text-align: left !important; padding-left: 10px !important; }
				.parent-row {
					cursor: pointer;
					background-color: #e0e0e0;
					font-weight: bold;
				}
				.child-row { background-color: #f9f9f9; }
				.toggle-icon {
					float: right;
					font-weight: bold;
					color: #5E3B63;
				}
				.empty-row {
					background-color: #fdf2f2;
					font-style: italic;
					color: #a94442;
				}
			</style>
			<table class="table">
				<thead>
					<tr>
						<th>SI NO</th>
						<th>Item Code</th>
						<th>SO Qty</th>
						<th>DN Qty</th>
						<th>Pending Qty</th>
						<th>Reserved Qty</th>
						<th>Actual Stock</th>
						<th>Allocated Qty</th>
					</tr>
				</thead>
				<tbody>
		`;

		if (!data || data.length === 0) {
			html += `
				<tr>
					<td colspan="8">Nothing to show</td>
				</tr>
			`;
		} else {
			let serial_no = 1;
			data.forEach((item, index) => {
				const [item_code, item_name, actual_stock, so_names, pending_qtys, so_qty, dn_qty, reserved_qty] = item;
				const group_id = `group-${index}`;

				const total_pending_qty = pending_qtys.reduce((a, b) => a + b, 0);
				const total_so_qty = so_qty.reduce((a, b) => a + b, 0);
				const total_dn_qty = dn_qty.reduce((a, b) => a + b, 0);
				const total_reserved_qty = reserved_qty.reduce((a, b) => a + b, 0);
				const stock_qty = actual_stock - total_reserved_qty;

				html += `
					<tr class="parent-row" data-group="${group_id}">
						<td>${serial_no++}</td>
						<td class="left-align">${item_code} - ${item_name} <span class="toggle-icon">[+]</span></td>
						<td>${total_so_qty}</td>
						<td>${total_dn_qty}</td>
						<td>${total_pending_qty}</td>
						<td>${total_reserved_qty}</td>
						<td>${stock_qty}</td>
						<td class="parent-allocated-summary" data-group-id="${group_id}">0</td>
					</tr>
				`;

				for (let i = 0; i < so_names.length; i++) {
					html += `
						<tr class="child-row ${group_id}" style="display: none;">
							<td></td>
							<td class="left-align" data-so-name="${so_names[i]}" data-item-code="${item_code}">
								<strong>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${so_names[i]}</strong>
							</td>
							<td>${so_qty[i]}</td>
							<td>${dn_qty[i]}</td>
							<td>${pending_qtys[i]}</td>
							<td>${reserved_qty[i]}</td>
							<td></td>
							<td class="editable-cell" ${!reserved_qty[i] ? 'contenteditable="true"' : ''}></td>
						</tr>
					`;
				}
			});
		}

	html += `</tbody></table>`;
	$container.html(html);

	// Toggle child rows
	$('.parent-row').click(function () {
		let groupId = $(this).data('group');
		let icon = $(this).find('.toggle-icon');
		$(`.${groupId}`).toggle();
		icon.text(icon.text() === '[+]' ? '[-]' : '[+]');
	});

	// Live allocation sum
	$container.on("input", ".editable-cell", function () {
		const $cell = $(this);
		const $row = $cell.closest("tr");
		const group_id = $row.attr("class").split(" ").find(cls => cls.startsWith("group-"));
		if (!group_id) return;

		let total_allocated = 0;
		$(`.${group_id} .editable-cell`).each(function () {
			const val = parseFloat($(this).text().trim());
			if (!isNaN(val)) {
				total_allocated += val;
			}
		});
		$(`.parent-allocated-summary[data-group-id="${group_id}"]`).text(total_allocated);
	});
}


	function submitUpdatedProjects() {
		let validAllocations = [];

		$('.child-row').each(function () {
			let $row = $(this);
			let so_name = $row.find('td[data-so-name]').data('so-name');
			let item_code = $row.find('td[data-item-code]').data('item-code');
			let allocated_qty = parseFloat($row.find('.editable-cell').text().trim());

			if (so_name && item_code && !isNaN(allocated_qty) && allocated_qty > 0) {
				validAllocations.push({
					sales_order: so_name,
					item_code: item_code,
					qty: allocated_qty
				});
			}
		});

		if (validAllocations.length === 0) {
			frappe.msgprint("No valid allocated quantities entered.");
			return;
		}

		let selected_division = division_filter.get_value();

		frappe.call({
			method: "jgb.jgb.page.pending_so_details.pending_so_details.reservation_creation",
			args: {
				allocations: validAllocations,
				division: selected_division || null
			},
			callback: function (r) {
				if (r.message) {
					frappe.msgprint("Stock Reservation Entry created successfully.");
					load_data(); // Refresh
				}
			}
		});
	}

	load_data(); // Load once on page open
};
