frappe.pages['stock-dashboard'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Stock Dashboard',
		single_column: true
	});
	page.stock_dashboard = new StockDashboard(page);
};

const ST_COLORS = ['#1f77b4', '#2f9be8', '#28a745', '#ffc107', '#fd7e14', '#dc3545', '#9b59b6', '#17a2b8', '#e91e63', '#607d8b'];

class StockDashboard {
	constructor(page) {
		this.page = page;
		this.charts = {};
		this.make_filters();
		this.make_body();
		this.refresh();
	}

	make_filters() {
		const me = this;
		this.period = this.page.add_field({
			fieldtype: 'Select', label: 'Period', fieldname: 'period',
			options: 'Today\nThis Week\nThis Month\nThis Quarter\nThis Year\nAll Time\nCustom',
			default: 'Today',
			change() {
				me.$ason_wrapper.toggle(this.get_value() === 'Custom');
				me.refresh();
			}
		});
		this.$ason = this.page.add_field({
			fieldtype: 'Date', label: 'As On Date', fieldname: 'to_date',
			default: frappe.datetime.get_today(), change() { me.refresh(); }
		});
		this.$ason_wrapper = this.$ason.$wrapper.hide();
		this.$company = this.page.add_field({
			fieldtype: 'Link', label: 'Company', fieldname: 'company',
			options: 'Company', default: frappe.defaults.get_default('company'),
			change() { me.refresh(); }
		});
		this.$item_group = this.page.add_field({
			fieldtype: 'Link', label: 'Item Group', fieldname: 'item_group',
			options: 'Item Group', change() { me.refresh(); }
		});
		this.$warehouse = this.page.add_field({
			fieldtype: 'Link', label: 'Warehouse', fieldname: 'warehouse',
			options: 'Warehouse', change() { me.refresh(); }
		});
	}

	get_as_on_date() {
		const period = this.period.get_value();
		if (period === 'Custom') return this.$ason.get_value();
		const today = new Date();
		if (period === 'This Week') {
			const d = new Date(today);
			d.setDate(today.getDate() - today.getDay()); // week start (Sunday)
			return frappe.datetime.obj_to_user(d);
		}
		if (period === 'This Month') return frappe.datetime.month_start();
		if (period === 'This Quarter') {
			const q = Math.floor(today.getMonth() / 3);
			return frappe.datetime.obj_to_user(new Date(today.getFullYear(), q * 3, 1));
		}
		if (period === 'This Year') return frappe.datetime.year_start();
		return frappe.datetime.get_today(); // Today / All Time (full ledger till today)
	}

	make_body() {
		this.$container = $(`
			<div class="sd-wrap">
				<div class="sd-kpis row"></div>
				<div class="sd-grid sd-grid-3">
					<div class="sd-card"><div class="sd-card-title">Stock Value by Item Group</div>
						<div class="sd-donut-flex"><div id="st-category" class="sd-donut"></div><div class="sd-donut-legend" id="st-category-legend"></div></div>
					</div>
					<div class="sd-card"><div class="sd-card-title">Stock Balance (Qty) by Item Group</div><div id="st-qty" class="sd-chart"></div></div>
					<div class="sd-card"><div class="sd-card-title">Item Group Summary</div><div class="sd-table" id="st-group-table"></div></div>
				</div>
				<div class="sd-grid sd-grid-3">
					<div class="sd-card"><div class="sd-card-title">Top 10 Items by Stock Value</div><div class="sd-table" id="st-items"></div></div>
					<div class="sd-card"><div class="sd-card-title">Stock Value by Warehouse</div><div id="st-warehouse" class="sd-chart"></div></div>
					<div class="sd-card"><div class="sd-card-title">Key Insights</div><div class="sd-insights" id="st-insights"></div></div>
				</div>
				<div class="sd-footer">
					<span>STOCK &nbsp;|&nbsp; STORES &nbsp;|&nbsp; SUPPLY &nbsp;|&nbsp; SERVICE</span>
					<span class="sd-footer-right"></span>
				</div>
			</div>`).appendTo(this.page.main);
	}

	refresh() {
		frappe.call({
			method: 'jgb.jgb.page.stock_dashboard.stock_dashboard.get_data',
			args: {
				to_date: this.get_as_on_date(),
				company: this.$company.get_value(),
				item_group: this.$item_group.get_value(),
				warehouse: this.$warehouse.get_value()
			},
			freeze: true,
			freeze_message: __('Loading Stock Dashboard...'),
			callback: r => r.message && this.render(r.message)
		});
	}

	load_echarts() {
		if (window.echarts) return Promise.resolve();
		return new Promise(resolve => {
			const s = document.createElement('script');
			s.src = '/assets/jgb/js/echarts.min.js';
			s.onload = resolve;
			document.head.appendChild(s);
		});
	}

	fmt(v) { return format_currency(v, this.data.currency, 0); }
	fmt_qty(v) { return Math.round(v).toLocaleString(); }

	kpi_card(icon, bg, label, value) {
		return `<div class="sd-kpi col-md-3 col-sm-6">
			<div class="sd-kpi-card" style="background:${bg};">
				<div class="sd-kpi-icon"><i class="fa ${icon}"></i></div>
				<div class="sd-kpi-label">${label}</div>
				<div class="sd-kpi-value">${value}</div>
			</div>
		</div>`;
	}

	render_kpis(data) {
		const k = data.kpi;
		this.$container.find('.sd-kpis').html([
			this.kpi_card('fa-cubes', '#eaf2fb', __('Total Items in Stock'), k.total_items),
			this.kpi_card('fa-database', '#e8f7ee', __('Total Stock Value'), this.fmt(k.stock_value)),
			this.kpi_card('fa-stack-overflow', '#fdf8e3', __('Total Stock Qty'), this.fmt_qty(k.total_qty)),
			this.kpi_card('fa-tags', '#f3eefa', __('Item Groups'), k.item_groups),
			this.kpi_card('fa-warehouse', '#e6f6f8', __('Warehouses'), k.warehouses),
			this.kpi_card('fa-exclamation-triangle', '#fdecef', __('Out of Stock Items'), k.out_of_stock),
			this.kpi_card('fa-exclamation-circle', '#fdecef', __('Negative Stock Entries'), k.negative),
		].join(''));
	}

	render_category(data) {
		const el = this.$container.find('#st-category')[0];
		this.charts.category && this.charts.category.dispose();
		this.charts.category = echarts.init(el);
		const total = data.category.reduce((a, d) => a + d.value, 0);
		this.charts.category.setOption({
			tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
			title: {
				text: this.fmt(total), subtext: __('Total Stock Value'),
				left: 'center', top: '42%', textStyle: { fontSize: 15, fontWeight: 700 },
				subtextStyle: { fontSize: 10 }
			},
			series: [{
				type: 'pie', radius: ['48%', '72%'], center: ['50%', '50%'],
				label: { show: false },
				data: data.category.map((d, i) => ({
					name: d.item_group, value: d.value,
					itemStyle: { color: ST_COLORS[i % ST_COLORS.length] }
				}))
			}]
		});
		this.$container.find('#st-category-legend').html(data.category.map((d, i) =>
			`<div><span><span class="sd-dot" style="background:${ST_COLORS[i % ST_COLORS.length]}"></span>${frappe.utils.escape_html(d.item_group)}</span><b>${(d.value / (total || 1) * 100).toFixed(0)}%</b></div>`
		).join(''));
	}

	render_qty(data) {
		const el = this.$container.find('#st-qty')[0];
		this.charts.qty && this.charts.qty.dispose();
		this.charts.qty = echarts.init(el);
		const rows = data.category.slice(0, 10).reverse();
		this.charts.qty.setOption({
			tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => `${p[0].name}: ${this.fmt_qty(p.value)} ${__('Qty')}` },
			grid: { left: 150, right: 60, top: 10, bottom: 20 },
			xAxis: { type: 'value', show: false },
			yAxis: {
				type: 'category', data: rows.map(d => frappe.utils.escape_html(frappe.ellipsis(d.item_group, 24))),
				axisLine: { show: false }, axisTick: { show: false }
			},
			series: [{
				type: 'bar', barMaxWidth: 18,
				label: { show: true, position: 'right', formatter: p => this.fmt_qty(p.value) },
				itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#28a745' }, { offset: 1, color: '#2ecc71' }]) },
				data: rows.map(d => d.qty)
			}]
		});
	}

	render_group_table(data) {
		const total = data.category.reduce((a, d) => a + d.value, 0) || 1;
		this.$container.find('#st-group-table').html(`
			<table class="table table-sm sd-table">
				<thead><tr><th>${__('Item Group')}</th><th class="text-right">${__('Items')}</th>
				<th class="text-right">${__('Balance Qty')}</th><th class="text-right">${__('Stock Value')}</th><th class="text-right">%</th></tr></thead>
				<tbody>
				${data.category.map((d, i) =>
					`<tr><td><span class="sd-dot" style="background:${ST_COLORS[i % ST_COLORS.length]}"></span>${frappe.utils.escape_html(d.item_group)}</td>
					<td class="text-right">${d.items}</td><td class="text-right">${this.fmt_qty(d.qty)}</td>
					<td class="text-right">${this.fmt(d.value)}</td>
					<td class="text-right">${(d.value / (total || 1) * 100).toFixed(1)}%</td></tr>`).join('')}
				</tbody>
			</table>`);
	}

	render_items(data) {
		this.$container.find('#st-items').html(`
			<table class="table table-sm sd-table">
				<thead><tr><th>#</th><th>${__('Item')}</th><th>${__('Group')}</th>
				<th class="text-right">${__('Qty')}</th><th class="text-right">${__('Value')}</th></tr></thead>
				<tbody>
				${data.top_items.map((it, i) =>
					`<tr><td>${i + 1}</td>
					<td title="${frappe.utils.escape_html(it.item_name)}">${frappe.utils.escape_html(frappe.ellipsis(it.item_name, 35))}</td>
					<td>${frappe.utils.escape_html(it.item_group || '')}</td>
					<td class="text-right">${this.fmt_qty(it.qty)}</td>
					<td class="text-right">${this.fmt(it.value)}</td></tr>`).join('')}
				</tbody>
			</table>`);
	}

	render_warehouses(data) {
		const el = this.$container.find('#st-warehouse')[0];
		this.charts.warehouse && this.charts.warehouse.dispose();
		this.charts.warehouse = echarts.init(el);
		const rows = data.warehouses.slice(0, 8).reverse();
		this.charts.warehouse.setOption({
			tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => `${p[0].name}: ${this.fmt(p[0].value)}` },
			grid: { left: 130, right: 60, top: 10, bottom: 20 },
			xAxis: { type: 'value', show: false },
			yAxis: { type: 'category', data: rows.map(d => frappe.utils.escape_html(frappe.ellipsis(d.warehouse, 22))), axisLine: { show: false }, axisTick: { show: false } },
			series: [{
				type: 'bar', barMaxWidth: 18,
				label: { show: true, position: 'right', formatter: p => this.fmt(p.value) },
				itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#1f77b4' }, { offset: 1, color: '#2f9be8' }]) },
				data: rows.map(d => d.value)
			}]
		});
	}

	render_insights(data) {
		const k = data.kpi;
		const total = k.stock_value || 1;
		const top_grp = data.category[0];
		const top_wh = data.warehouses[0];
		const items = [
			`${__('Total stock value is')} <b>${this.fmt(k.stock_value)}</b> ${__('across')} <b>${k.total_items}</b> ${__('items')}`,
			top_grp ? `${__(top_grp.item_group)} ${__('holds')} <b>${(top_grp.value / total * 100).toFixed(0)}%</b> ${__('of stock value')} (${this.fmt(top_grp.value)})` : '',
			top_wh ? `${__('Largest warehouse:')} <b>${top_wh.warehouse}</b> (${this.fmt(top_wh.value)})` : '',
			`<b>${k.out_of_stock}</b> ${__('items are out of stock')}`,
			k.negative ? `<b>${k.negative}</b> ${__('items have negative stock — review stock reconciliation')}` : ''
		].filter(Boolean);
		this.$container.find('#st-insights').html(items.map(t =>
			`<div class="sd-insight"><i class="fa fa-check-circle"></i><span>${t}</span></div>`).join(''));
	}

	render(data) {
		this.data = data;
		if (data.empty) {
			frappe.msgprint(__('No stock data found for the selected filters.'));
			return;
		}
		this.load_echarts().then(() => {
			this.render_kpis(data);
			this.render_category(data);
			this.render_qty(data);
			this.render_group_table(data);
			this.render_items(data);
			this.render_warehouses(data);
			this.render_insights(data);
			this.$container.find('.sd-footer-right').text(
				__('Stock Balance as on') + ' ' + frappe.datetime.str_to_user(data.as_on)
				+ ' | ' + __('Last Updated') + ': ' + frappe.datetime.now_datetime(true));
		});
	}
}
