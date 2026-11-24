frappe.pages['financial-dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Financial Dashboard',
		single_column: true
	});
}