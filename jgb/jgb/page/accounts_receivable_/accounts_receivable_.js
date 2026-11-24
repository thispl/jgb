frappe.pages['accounts-receivable-'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Accounts Receivable Aging Report',
		single_column: true
	});

	$ar_aging = new ARAgingReport(wrapper, page);
};

class ARAgingReport {
	constructor(wrapper, page) {
		this.wrapper = wrapper;
		this.page = page;
		this.body = $(wrapper).find('.layout-main-section');
		this.company = frappe.defaults.get_default('Company') || '';
		this.columns = [];
		this.rows = [];
		this.currency = 'SAR';
		this.is_initial_load = true;

		this.add_page_styles();
		this.make_filters();
		this.make_report_area();
		this.bind_events();

		// Auto-load all data on page open
		this.get_report(false);
		this.is_initial_load = false;
	}

	add_page_styles() {
		var css = [
			'<style>',
			'#page-accounts-receivable- .page-head { margin-bottom: 0; }',
			'#page-accounts-receivable- .page-form {',
			'  display: flex; flex-wrap: wrap; align-items: flex-end;',
			'  gap: 10px 16px; padding: 12px 18px; background: #fff;',
			'  border-bottom: 1px solid #E2E6E9; margin-bottom: 0;',
			'}',
			'#page-accounts-receivable- .page-form .frappe-control {',
			'  flex: 1 1 180px; min-width: 160px; max-width: 260px; margin-bottom: 0;',
			'}',
			'#page-accounts-receivable- .page-form .frappe-control .control-label {',
			'  font-size: 12px; font-weight: 600; color: #555; margin-bottom: 2px;',
			'}',
			'#page-accounts-receivable- .page-form .checkbox .control-label {',
			'  font-weight: normal; font-size: 12px; color: #333;',
			'}',
			'.ar-report-area { background: #fff; padding: 12px 18px; }',
			'.ar-meta { margin-bottom: 12px; }',
			'.ar-table-scroll { overflow: auto; max-height: calc(100vh - 270px); border: 1px solid #D0D0D0; }',
			'.ar-table { width: 100%; border-collapse: collapse; font-family: Calibri, Arial, sans-serif; font-size: 11px; }',
			'.ar-table th, .ar-table td { border: 1px solid #D0D0D0; padding: 4px 6px; vertical-align: middle; }',
			'.ar-table th { background: #1F3864; color: #fff; font-weight: 600; text-align: center; }',
			'.ar-table td { text-align: right; font-variant-numeric: tabular-nums; }',
			'.ar-table td.ar-left { text-align: left; }',
			'.ar-table td.ar-center { text-align: center; }',
			'.ar-group-row td { background: #4472C4; color: #fff; font-weight: 700; font-size: 12px; text-align: center; }',
			'.ar-subtotal-row td { background: #D9E1F2; color: #1F3864; font-weight: 700; }',
			'.ar-custsub-row td, .ar-unapplied-row td { background: #E9EEF7; color: #1F3864; font-weight: 700; }',
			'.ar-grand-row td, .ar-net-row td { background: #1F3864; color: #fff; font-weight: 700; }',
			'.ar-alt td { background: #F7F9FC; }',
			'.ar-loading, .ar-empty { padding: 50px; text-align: center; color: #999; font-size: 14px; }',
			'.ar-negative { color: red; }',
			'</style>'
		].join('\n');
		this.body.before(css);
	}

	make_filters() {
		var me = this;

		this.page.add_field({
			fieldname: 'company',
			label: __('Company'),
			fieldtype: 'Link',
			options: 'Company',
			default: this.company,
			reqd: 1,
			change: function () { me.company = this.get_value(); }
		});

		this.page.add_field({
			fieldname: 'view_type',
			label: __('Report View Type'),
			fieldtype: 'Select',
			options: ['Summary', 'Detailed'],
			default: 'Summary'
		});

		this.page.add_field({
			fieldname: 'grouping',
			label: __('Primary Grouping'),
			fieldtype: 'Select',
			options: ['Customer Wise', 'Salesperson Wise', 'Division Wise', 'Region Wise'],
			default: 'Customer Wise',
			change: function () { me.refresh_entity_options(); }
		});

		this.page.add_field({
			fieldname: 'entities',
			label: __('Entity Selection'),
			fieldtype: 'MultiSelectList',
			placeholder: __('All Entities'),
			get_data: function (txt) { return me.get_entity_data(txt); }
		});

		this.page.add_field({
			fieldname: 'as_of_date',
			label: __('As-of Date (Cut-off)'),
			fieldtype: 'Date',
			default: frappe.datetime.get_today()
		});

		this.page.add_field({
			fieldname: 'aging_method',
			label: __('Aging Method / Basis'),
			fieldtype: 'Select',
			options: ['Due Date (Credit View)', 'Invoice Date (Commercial View)'],
			default: 'Due Date (Credit View)'
		});

		this.page.add_field({
			fieldname: 'show_unapplied',
			label: __('Show Unapplied Payments & Credits as Separate Line'),
			fieldtype: 'Check',
			default: 0
		});

		this.page.add_field({
			fieldname: 'export_format',
			label: __('Output / Export Format'),
			fieldtype: 'Select',
			options: ['Excel', 'PDF'],
			default: 'Excel'
		});

		this.page.set_primary_action(__('Get Report'), function () { me.get_report(true); });
		this.page.add_menu_item(__('Export Excel'), function () { me.export_report('Excel'); });
		this.page.add_menu_item(__('Export PDF'), function () { me.export_report('PDF'); });
	}

	bind_events() {
		var me = this;
		this.page.$title_area.find('.title-text').css('color', '#1F3864');
	}

	get_entity_data(txt) {
		var me = this;
		var company = me.company || (me.page.fields_dict.company ? me.page.fields_dict.company.get_value() : '');
		var grouping = me.page.fields_dict.grouping ? me.page.fields_dict.grouping.get_value() : 'Customer Wise';
		return new Promise(function (resolve) {
			if (!company) { resolve([]); return; }
			frappe.call({
				method: 'jgb.jgb.page.accounts_receivable_.accounts_receivable_aging.get_entity_options',
				args: { company: company, grouping: grouping, search: txt || '' },
				callback: function (r) { resolve(r && r.message ? r.message : []); },
				error: function () { resolve([]); }
			});
		});
	}

	refresh_entity_options() {
		var field = this.page.fields_dict.entities;
		if (field) { field.set_data([]); field.set_value([]); }
	}

	make_report_area() {
		this.report_area = $(
			'<div class="ar-report-area">' +
			'<div class="ar-meta"></div>' +
			'<div class="ar-table-scroll"></div>' +
			'</div>'
		);
		this.body.append(this.report_area);
	}

	get_filter_values() {
		var entities = this.page.fields_dict.entities ? this.page.fields_dict.entities.get_value() : [];
		if (typeof entities === 'string') entities = [];
		var aging = this.page.fields_dict.aging_method ? this.page.fields_dict.aging_method.get_value() : 'Due Date (Credit View)';
		return {
			company: this.page.fields_dict.company ? this.page.fields_dict.company.get_value() : this.company,
			view_type: this.page.fields_dict.view_type ? this.page.fields_dict.view_type.get_value() : 'Summary',
			grouping: this.page.fields_dict.grouping ? this.page.fields_dict.grouping.get_value() : 'Customer Wise',
			entities: entities,
			as_of_date: this.page.fields_dict.as_of_date ? this.page.fields_dict.as_of_date.get_value() : frappe.datetime.get_today(),
			aging_method: aging.replace(' (Credit View)', '').replace(' (Commercial View)', ''),
			show_unapplied: this.page.fields_dict.show_unapplied ? this.page.fields_dict.show_unapplied.get_value() : 0,
			export_format: this.page.fields_dict.export_format ? this.page.fields_dict.export_format.get_value() : 'Excel',
		};
	}

	get_report(show_msg) {
		var me = this;
		var args = this.get_filter_values();
		if (!args.company) {
			if (show_msg) frappe.msgprint('Kindly choose the company.');
			this.report_area.find('.ar-table-scroll').html('<div class="ar-empty">' + __('Select a company to view the report.') + '</div>');
			return;
		}

		this.report_area.find('.ar-table-scroll').html('<div class="ar-loading">' + __('Loading report...') + '</div>');

		frappe.call({
			method: 'jgb.jgb.page.accounts_receivable_.accounts_receivable_aging.get_report_data',
			args: args,
			callback: function (r) {
				if (r && r.message) {
					me.columns = r.message.columns;
					me.rows = r.message.rows;
					me.currency = r.message.currency;
					me.meta = {
						company: r.message.company,
						currency: r.message.currency,
						as_of_date: r.message.as_of_date,
						report_date: r.message.report_date,
					};
					me.render_report();
				} else {
					me.report_area.find('.ar-table-scroll').html('<div class="ar-empty">' + __('No data returned.') + '</div>');
				}
			},
			error: function (r) {
				me.report_area.find('.ar-table-scroll').html('<div class="ar-empty">' + __('Error loading report: ') + (r ? (r.message || '') : '') + '</div>');
			}
		});
	}

	render_report() {
		var me = this;
		var meta = this.meta || {};

		this.report_area.find('.ar-meta').html(
			'<div class="text-center">' +
			'<h3 style="margin:0; color:#1F3864; font-size:18px;">' + esc(meta.company || '') + '</h3>' +
			'<h4 style="margin:4px 0; color:#1F3864; font-size:16px;">Accounts Receivable Aging Report</h4>' +
			'<div style="font-size:12px; color:#404040;">' +
			'As-of Date: ' + esc(meta.as_of_date || '') + ' &nbsp;|&nbsp; ' +
			'Report Date: ' + esc(meta.report_date || '') + ' &nbsp;|&nbsp; ' +
			'Currency: ' + esc(meta.currency || '') +
			'</div></div>'
		);

		if (!me.columns || !me.rows || me.rows.length === 0) {
			this.report_area.find('.ar-table-scroll').html('<div class="ar-empty">' + __('No records found for the selected filters.') + '</div>');
			return;
		}

		var html = '<table class="ar-table">';
		html += '<thead><tr>';
		this.columns.forEach(function (col) {
			html += '<th>' + esc(col.label) + '</th>';
		});
		html += '</tr></thead><tbody>';

		var text_cols = 0;
		for (var c = 0; c < me.columns.length; c++) {
			if (me.columns[c].type === 'text' || me.columns[c].type === 'int') {
				text_cols++;
			} else {
				break;
			}
		}

		var alt = false;
		this.rows.forEach(function (row) {
			var first = String(row[0] || '');
			var is_group = first.startsWith('GROUP:');
			var is_custsub = first.startsWith('Customer Subtotal:');
			var is_subtotal = first.startsWith('Subtotal:');
			var is_unapplied = first.startsWith('Unapplied');
			var is_net = first.startsWith('NET RECEIVABLES');
			var is_grand = first === 'GRAND TOTAL';
			var tr_cls = '';

			if (is_group) tr_cls = 'ar-group-row';
			else if (is_grand || is_net) tr_cls = 'ar-grand-row';
			else if (is_subtotal) tr_cls = 'ar-subtotal-row';
			else if (is_custsub || is_unapplied) tr_cls = 'ar-custsub-row';
			else if (alt) tr_cls = 'ar-alt';

			html += '<tr class="' + tr_cls + '">';
			row.forEach(function (cell, idx) {
				if (is_group && idx > 0) return;

				var col = me.columns[idx];
				var td_cls = 'ar-left';
				var val = cell;

				if (cell === null || cell === undefined || cell === '') {
					val = '';
				} else if (col && col.type === 'currency' && typeof cell === 'number') {
					val = me.format_currency(cell);
					td_cls = '';
				} else if (typeof cell === 'number') {
					val = frappe.utils.format_number(cell);
					td_cls = '';
				}

				if (col && (col.type === 'currency' || col.type === 'int')) {
					td_cls = '';
				}

				if (is_group) {
					html += '<td class="' + td_cls + '" colspan="' + me.columns.length + '">' + esc(val) + '</td>';
					return;
				}

				if ((is_subtotal || is_custsub || is_grand || is_net || is_unapplied) && idx === 0) {
					html += '<td class="' + td_cls + '" colspan="' + text_cols + '">' + esc(val) + '</td>';
					return;
				}
				if ((is_subtotal || is_custsub || is_grand || is_net || is_unapplied) && idx > 0 && idx < text_cols) {
					return;
				}

				html += '<td class="' + td_cls + '">' + esc(val) + '</td>';
			});
			html += '</tr>';
			if (!is_group) alt = !alt;
		});

		html += '</tbody></table>';
		this.report_area.find('.ar-table-scroll').html(html);
	}

	format_currency(val) {
		if (typeof val !== 'number') return val;
		var s = val < 0 ? '-' : '';
		var n = Math.abs(val).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
		if (val < 0) {
			return '<span class="ar-negative">' + s + n + '</span>';
		}
		return s + n;
	}

	export_report(format) {
		var me = this;
		var args = this.get_filter_values();
		if (!args.company) {
			frappe.msgprint('Kindly choose the company.');
			return;
		}

		if (format === 'Excel') {
			var url = frappe.urllib.get_full_url('/api/method/jgb.jgb.page.accounts_receivable_.accounts_receivable_aging.download_excel?'
				+ 'company=' + encodeURIComponent(args.company)
				+ '&view_type=' + encodeURIComponent(args.view_type)
				+ '&grouping=' + encodeURIComponent(args.grouping)
				+ '&entities=' + encodeURIComponent(JSON.stringify(args.entities || []))
				+ '&as_of_date=' + encodeURIComponent(args.as_of_date || '')
				+ '&aging_method=' + encodeURIComponent(args.aging_method)
				+ '&show_unapplied=' + encodeURIComponent(args.show_unapplied || 0)
			);
			window.open(url);
		} else {
			me.print_report();
		}
	}

	print_report() {
		var print_contents = this.report_area.html();
		var win = window.open('', '_blank');
		win.document.write('<html><head><title>Accounts Receivable Aging Report</title>');
		win.document.write('<style>');
		win.document.write('body { font-family: Arial, sans-serif; font-size: 11px; }');
		win.document.write('table { border-collapse: collapse; width: 100%; }');
		win.document.write('th, td { border: 1px solid #999; padding: 3px 5px; }');
		win.document.write('th { background: #1F3864; color: #fff; }');
		win.document.write('h3, h4 { text-align: center; color: #1F3864; }');
		win.document.write('td { text-align: right; }');
		win.document.write('td.ar-left { text-align: left; }');
		win.document.write('@media print { .ar-group-row td { background: #4472C4 !important; color: #fff !important; -webkit-print-color-adjust: exact; } .ar-grand-row td { background: #1F3864 !important; color: #fff !important; -webkit-print-color-adjust: exact; } .ar-subtotal-row td { background: #D9E1F2 !important; -webkit-print-color-adjust: exact; } .ar-custsub-row td { background: #E9EEF7 !important; -webkit-print-color-adjust: exact; } }');
		win.document.write('</style></head><body>');
		win.document.write(print_contents);
		win.document.write('</body></html>');
		win.document.close();
		win.focus();
		setTimeout(function () { win.print(); }, 500);
	}
}

function esc(s) {
	return (s === null || s === undefined) ? '' : String(s)
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}
