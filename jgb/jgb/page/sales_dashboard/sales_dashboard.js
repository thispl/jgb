frappe.pages['sales-dashboard'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Sales Dashboard',
		single_column: true
	});
	page.sales_dashboard = new SalesDashboard(page);
};

const SD_COLORS = ['#1f77b4', '#2f9be8', '#28a745', '#ffc107', '#fd7e14', '#dc3545', '#9b59b6', '#95a5a6'];

class SalesDashboard {
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
			options: 'This Year\nLast Year\nThis Quarter\nThis Month\nCustom',
			default: 'This Year',
			change() {
				const v = this.get_value();
				me.$from_wrapper.toggle(v === 'Custom');
				me.$to_wrapper.toggle(v === 'Custom');
				me.refresh();
			}
		});
		this.$from = this.page.add_field({
			fieldtype: 'Date', label: 'From Date', fieldname: 'from_date',
			default: frappe.datetime.year_start(), change() { me.refresh(); }
		});
		this.$to = this.page.add_field({
			fieldtype: 'Date', label: 'To Date', fieldname: 'to_date',
			default: frappe.datetime.get_today(), change() { me.refresh(); }
		});
		this.$from_wrapper = this.$from.$wrapper;
		this.$to_wrapper = this.$to.$wrapper;
		this.$customer = this.page.add_field({
			fieldtype: 'Link', label: 'Customer', fieldname: 'customer',
			options: 'Customer', change() { me.refresh(); }
		});
		this.$category = this.page.add_field({
			fieldtype: 'Link', label: 'Product Category', fieldname: 'item_group',
			options: 'Item Group', change() { me.refresh(); }
		});
		this.$salesperson = this.page.add_field({
			fieldtype: 'Link', label: 'Salesperson', fieldname: 'sales_person',
			options: 'Sales Person', change() { me.refresh(); }
		});
		this.$region = this.page.add_field({
			fieldtype: 'Link', label: 'Region', fieldname: 'region',
			options: 'Region', change() { me.refresh(); }
		});
		this.$from_wrapper.hide();
		this.$to_wrapper.hide();
	}

	get_filter_values() {
		const period = this.period.get_value();
		let from_date, to_date;
		const today = frappe.datetime.get_today();
		if (period === 'This Year') {
			from_date = frappe.datetime.year_start(); to_date = today;
		} else if (period === 'Last Year') {
			const y = new Date().getFullYear() - 1;
			from_date = `${y}-01-01`; to_date = `${y}-12-31`;
		} else if (period === 'This Quarter') {
			const q = Math.floor(new Date().getMonth() / 3);
			const start = new Date(new Date().getFullYear(), q * 3, 1);
			from_date = frappe.datetime.obj_to_user(start); to_date = today;
		} else if (period === 'This Month') {
			from_date = frappe.datetime.month_start(); to_date = today;
		} else {
			from_date = this.$from.get_value(); to_date = this.$to.get_value();
		}
		return {
			from_date, to_date,
			company: frappe.defaults.get_default('company') || '',
			customer: this.$customer.get_value(),
			item_group: this.$category.get_value(),
			sales_person: this.$salesperson.get_value(),
			region: this.$region.get_value()
		};
	}

	make_body() {
		if (!document.querySelector('link[href*="sales_dashboard.css"]')) {
			$('<link rel="stylesheet" type="text/css" href="/assets/jgb/css/sales_dashboard.css?v='
				+ Date.now() + '">').appendTo('head');
		}
		this.$container = $(`
			<div class="sd-wrap">
				<div class="sd-kpis row"></div>
				<div class="sd-grid sd-grid-3">
					<div class="sd-card"><div class="sd-card-title">Sales Pipeline</div>
						<div class="sd-funnel-flex"><div id="sd-funnel" class="sd-funnel-chart"></div><div class="sd-funnel-legend"></div></div>
					</div>
					<div class="sd-card"><div class="sd-card-title">Monthly Sales Performance</div><div id="sd-monthly" class="sd-chart"></div></div>
					<div class="sd-card"><div class="sd-card-title">Sales by Product Category</div>
						<div class="sd-donut-flex"><div id="sd-category" class="sd-donut"></div><div class="sd-donut-legend" id="sd-category-legend"></div></div>
					</div>
				</div>
				<div class="sd-grid sd-grid-3">
					<div class="sd-card"><div class="sd-card-title">Quotation Status</div><div class="sd-table" id="sd-quo-status"></div></div>
					<div class="sd-card"><div class="sd-card-title">Order Fulfillment Status</div>
						<div class="sd-donut-flex"><div id="sd-fulfillment" class="sd-donut"></div><div class="sd-donut-legend" id="sd-fulfillment-legend"></div></div>
					</div>
					<div class="sd-card"><div class="sd-card-title">Top 5 Customers by Sales Value</div><div class="sd-table" id="sd-customers"></div></div>
				</div>
				<div class="sd-grid sd-grid-3">
					<div class="sd-card"><div class="sd-card-title">Top 5 Products by Sales Value</div><div class="sd-table" id="sd-products"></div></div>
					<div class="sd-card"><div class="sd-card-title">Sales by Region</div><div id="sd-region" class="sd-chart"></div></div>
					<div class="sd-card"><div class="sd-card-title">Key Insights</div><div class="sd-insights" id="sd-insights"></div></div>
				</div>
				<div class="sd-footer">
					<span class="sd-footer-right"></span>
				</div>
			</div>`).appendTo(this.page.main);
	}

	refresh() {
		frappe.call({
			method: 'jgb.api.get_sales_dashboard_data',
			args: this.get_filter_values(),
			freeze: true,
			freeze_message: __('Loading Sales Dashboard...'),
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

	render(data) {
		this.data = data;
		this.load_echarts().then(() => {
			this.render_kpis(data);
			this.render_funnel(data);
			this.render_monthly(data);
			this.render_category(data);
			this.render_quo_status(data);
			this.render_fulfillment(data);
			this.render_customers(data);
			this.render_products(data);
			this.render_region(data);
			this.render_insights(data);
			this.$container.find('.sd-footer-right').text(
				'Last Updated: ' + frappe.datetime.now_datetime(true));
		});
	}

	fmt(v) { return format_currency(v, this.data.currency, 0); }

	kpi_card(icon, bg, label, value, pct, extra) {
		let change = '';
		if (pct !== null && pct !== undefined) {
			const up = pct >= 0;
			change = `<div class="sd-kpi-pct ${up ? 'up' : 'down'}">${up ? '▲' : '▼'} ${Math.abs(pct)}% <span>vs previous period</span></div>`;
		}
		return `<div class="sd-kpi col-md-3 col-sm-6">
			<div class="sd-kpi-card" style="background:${bg};">
				<div class="sd-kpi-icon"><i class="fa ${icon}"></i></div>
				<div class="sd-kpi-label">${label}</div>
				<div class="sd-kpi-value">${value}</div>
				${change}
			</div>
		</div>`;
	}

	render_kpis(data) {
		const k = data.kpi;
		this.$container.find('.sd-kpis').html([
			this.kpi_card('fa-file-text-o', '#eaf2fb', __('Enquiries Received'), k.enquiries, k.enquiries_pct),
			this.kpi_card('fa-files-o', '#f3eefa', __('Quotations Created'), k.quotations, k.quotations_pct),
			this.kpi_card('fa-check-circle', '#e8f7ee', __('Quotations Converted'), `${k.converted} <small>${k.conversion_rate}%</small>`, null),
			this.kpi_card('fa-shopping-cart', '#fdf8e3', __('Sales Orders'), k.orders, k.orders_pct),
			this.kpi_card('fa-truck', '#e6f6f8', __('Delivered Orders'), `${k.delivered} <small>${k.fulfillment_rate}%</small>`, null),
			this.kpi_card('fa-pencil-square-o', '#fdecef', __('Invoices Raised'), k.invoices, k.invoices_pct),
			this.kpi_card('fa-database', '#e8f7ee', __('Total Sales Revenue'), this.fmt(k.revenue), k.revenue_pct),
		].join(''));
	}

	render_funnel(data) {
		const el = this.$container.find('#sd-funnel')[0];
		this.charts.funnel && this.charts.funnel.dispose();
		this.charts.funnel = echarts.init(el);
		// % relative to the largest stage (first non-zero), not Enquiries
		const total = data.funnel.reduce((a, f) => Math.max(a, f[1]), 0) || 1;
		this.charts.funnel.setOption({
			tooltip: { trigger: 'item', formatter: '{b}: {c}' },
			series: [{
				type: 'funnel', left: '5%', right: '5%', top: 5, bottom: 5,
				minSize: '30%', sort: 'descending', gap: 2,
				label: { show: true, position: 'inside', formatter: '{b}\n{c}', color: '#fff', fontSize: 11 },
				data: data.funnel.map((f, i) => ({
					name: f[0], value: f[1],
					itemStyle: { color: SD_COLORS[i] }
				}))
			}]
		});
		this.$container.find('.sd-funnel-legend').html(data.funnel.map(f =>
			`<div class="sd-funnel-row"><span>${__(f[0])}</span><b>${f[1]} (${(f[1] / (total || 1) * 100).toFixed(0)}%)</b></div>`).join(''));
	}

	render_monthly(data) {
		const el = this.$container.find('#sd-monthly')[0];
		this.charts.monthly && this.charts.monthly.dispose();
		this.charts.monthly = echarts.init(el);
		this.charts.monthly.setOption({
			tooltip: { trigger: 'axis' },
			legend: { bottom: 0, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11 } },
			grid: { left: 60, right: 20, top: 20, bottom: 40 },
			xAxis: { type: 'category', data: data.monthly.labels },
			yAxis: { type: 'value', axisLabel: { formatter: v => v >= 1e6 ? (v / 1e6) + 'M' : v >= 1e3 ? (v / 1e3) + 'K' : v } },
			series: [
				{ name: __('Quotation Value'), type: 'line', smooth: true, symbolSize: 6, data: data.monthly.quotation, itemStyle: { color: '#1f77b4' }, lineStyle: { color: '#1f77b4' } },
				{ name: __('Order Value'), type: 'bar', data: data.monthly.order, itemStyle: { color: '#2ecc71' }, barMaxWidth: 14 },
				{ name: __('Invoice Value'), type: 'bar', data: data.monthly.invoice, itemStyle: { color: '#f39c12' }, barMaxWidth: 14 }
			]
		});
	}

	render_category(data) {
		const el = this.$container.find('#sd-category')[0];
		this.charts.category && this.charts.category.dispose();
		this.charts.category = echarts.init(el);
		const total = data.category.reduce((a, d) => a + d.value, 0);
		this.charts.category.setOption({
			tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
			title: {
				text: this.fmt(total), subtext: __('Total Sales'),
				left: 'center', top: '42%', textStyle: { fontSize: 15, fontWeight: 700 },
				subtextStyle: { fontSize: 10 }
			},
			series: [{
				type: 'pie', radius: ['48%', '72%'], center: ['50%', '50%'],
				label: { show: false },
				data: data.category.map((d, i) => ({
					name: d.item_group || __('Not Set'), value: d.value,
					itemStyle: { color: SD_COLORS[i % SD_COLORS.length] }
				}))
			}]
		});
		this.$container.find('#sd-category-legend').html(data.category.map((d, i) =>
			`<div><span><span class="sd-dot" style="background:${SD_COLORS[i % SD_COLORS.length]}"></span>${d.item_group || __('Not Set')}</span><b>${(d.value / (total || 1) * 100).toFixed(0)}%</b></div>`
		).join(''));
	}

	render_quo_status(data) {
		const qs = data.quotation_status;
		const dots = { Converted: '#28a745', Open: '#1f77b4', Lost: '#dc3545' };
		this.$container.find('#sd-quo-status').html(`
			<table class="table table-sm sd-table">
				<thead><tr><th>${__('Status')}</th><th class="text-right">${__('Count')}</th><th class="text-right">${__('Value')}</th><th class="text-right">%</th></tr></thead>
				<tbody>
				${['Converted', 'Open', 'Lost'].map(st => {
					const r = qs[st] || [0, 0];
					return `<tr><td><span class="sd-dot" style="background:${dots[st]}"></span>${__(st)}</td>
						<td class="text-right">${r[0]}</td><td class="text-right">${this.fmt(r[1])}</td>
						<td class="text-right">${(r[0] / ((qs.Converted[0] + qs.Open[0] + qs.Lost[0]) || 1) * 100).toFixed(1)}%</td></tr>`;
				}).join('')}
				</tbody>
			</table>`);
	}

	render_fulfillment(data) {
		const el = this.$container.find('#sd-fulfillment')[0];
		this.charts.fulfillment && this.charts.fulfillment.dispose();
		this.charts.fulfillment = echarts.init(el);
		const f = data.fulfillment;
		this.charts.fulfillment.setOption({
			tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
			title: {
				text: f.Total, subtext: __('Total Orders'),
				left: 'center', top: '40%', textStyle: { fontSize: 18, fontWeight: 700 },
				subtextStyle: { fontSize: 10 }
			},
			series: [{
				type: 'pie', radius: ['50%', '72%'], center: ['50%', '50%'],
				label: { show: false },
				data: [
					{ name: __('Delivered'), value: f['Delivered'], itemStyle: { color: '#28a745' } },
					{ name: __('Partially Delivered'), value: f['Partially Delivered'], itemStyle: { color: '#ffc107' } },
					{ name: __('Pending'), value: f['Pending'], itemStyle: { color: '#dc3545' } }
				]
			}]
		});
		const total = f.Total || 1;
		this.$container.find('#sd-fulfillment-legend').html([
			['Delivered', f['Delivered'], '#28a745'],
			['Partially Delivered', f['Partially Delivered'], '#ffc107'],
			['Pending', f['Pending'], '#dc3545']
		].map(([label, val, color]) =>
			`<div class="sd-ful-row"><span class="sd-dot" style="background:${color}"></span>${__(label)}<b>${val} <small>(${(val / total * 100).toFixed(1)}%)</small></b></div>`).join(''));
	}

	render_customers(data) {
		this.$container.find('#sd-customers').html(`
			<table class="table table-sm sd-table">
				<thead><tr><th>#</th><th>${__('Customer Name')}</th><th class="text-right">${__('Sales Value')}</th><th class="text-right">${__('Orders')}</th></tr></thead>
				<tbody>
				${data.top_customers.map((c, i) =>
					`<tr><td>${i + 1}</td><td>${frappe.utils.escape_html(c.customer_name || c.customer)}</td>
					<td class="text-right">${this.fmt(c.value)}</td><td class="text-right">${c.orders}</td></tr>`).join('')}
				</tbody>
			</table>`);
	}

	render_products(data) {
		this.$container.find('#sd-products').html(`
			<table class="table table-sm sd-table">
				<thead><tr><th>#</th><th>${__('Product')}</th><th class="text-right">${__('Sales Value')}</th><th class="text-right">${__('Qty Sold')}</th></tr></thead>
				<tbody>
				${data.top_products.map((p, i) =>
					`<tr><td>${i + 1}</td><td title="${frappe.utils.escape_html(p.item_name)}">${frappe.utils.escape_html(frappe.ellipsis(p.item_name, 40))}</td>
					<td class="text-right">${this.fmt(p.value)}</td><td class="text-right">${Math.round(p.qty).toLocaleString()}</td></tr>`).join('')}
				</tbody>
			</table>`);
	}

	render_region(data) {
		const el = this.$container.find('#sd-region')[0];
		this.charts.region && this.charts.region.dispose();
		this.charts.region = echarts.init(el);
		const total = data.region.reduce((a, d) => a + d.value, 0) || 1;
		const rows = data.region.slice(0, 7).reverse();
		this.charts.region.setOption({
			tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => `${p[0].name}: ${this.fmt(p[0].value)} (${(p[0].value / total * 100).toFixed(0)}%)` },
			grid: { left: 90, right: 60, top: 10, bottom: 20 },
			xAxis: { type: 'value', show: false },
			yAxis: { type: 'category', data: rows.map(d => d.custom_region || __('Not Set')), axisLine: { show: false }, axisTick: { show: false } },
			series: [{
				type: 'bar', barMaxWidth: 18,
				label: { show: true, position: 'right', formatter: p => (p.value / total * 100).toFixed(0) + '%' },
				itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#1f77b4' }, { offset: 1, color: '#2f9be8' }]) },
				data: rows.map(d => d.value)
			}]
		});
	}

	render_insights(data) {
		const k = data.kpi;
		const cat_total = data.category.reduce((a, d) => a + d.value, 0) || 1;
		const top_cat = data.category[0];
		const cust_total = data.top_customers.reduce((a, c) => a + c.value, 0);
		const rev_total = data.region.reduce((a, d) => a + d.value, 0) || 1;
		const items = [
			`${__('Quotation conversion rate is')} <b>${k.conversion_rate}%</b>`,
			`${__('Total sales revenue reached')} <b>${this.fmt(k.revenue)}</b>${k.revenue_pct !== null ? ` (▲ ${k.revenue_pct}%)` : ''}`,
			`${__('Order fulfillment rate is')} <b>${k.fulfillment_rate}%</b>`,
			top_cat ? `${__(top_cat.item_group)} ${__('contributes')} <b>${(top_cat.value / cat_total * 100).toFixed(0)}%</b> ${__('of total sales')}` : '',
			`${__('Top 5 customers contribute')} <b>${(cust_total / rev_total * 100).toFixed(0)}%</b> ${__('of revenue')}`,
			`${__('Focus on')} <b>${data.fulfillment.Pending}</b> ${__('pending orders to improve invoicing and cash flow')}`
		].filter(Boolean);
		this.$container.find('#sd-insights').html(items.map(t =>
			`<div class="sd-insight"><i class="fa fa-check-circle"></i><span>${t}</span></div>`).join(''));
	}
}
