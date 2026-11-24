import frappe
from frappe import _
@frappe.whitelist()
def create_journal(name):
    la = frappe.get_doc('Leave Application', name)
    if la.custom_payment_type == 'Pay Now' and la.status == 'Approved':
        duplicate_payment = frappe.db.get_value(
            "Pending Payment", 
            {"leave_application": la.name}, 
            ["parent", "parenttype"], 
            as_dict=True
        )
        
        if duplicate_payment:
            doc_link = frappe.utils.get_url_to_form(duplicate_payment.parenttype, duplicate_payment.parent)
            
            frappe.throw(
                msg=_(
                    "This leave application has already been processed for payment via "
                    "<a href='{0}' class='variant-link'><b>{1}</b></a>."
                ).format(doc_link, duplicate_payment.parent),
                title=_("Duplicate Payment Reference")
            )
        existing_jv = frappe.db.get_value('Journal Entry', {'docstatus': ['!=', 2], 'custom_leave_application': la.name}, 'name')
        if existing_jv:
            return existing_jv
        jv = frappe.new_doc('Journal Entry')
        jv.voucher_type = 'Bank Entry'
        jv.company = la.company
        jv.posting_date = frappe.utils.today()
        jv.custom_division = frappe.db.get_value('Employee', la.employee, 'custom_division') or 'Common'
        jv.cheque_no = la.name
        jv.user_remark = f"Leave pay for the application - {la.name}"
        jv.custom_leave_application = la.name
        jv.cheque_date=jv.posting_date
        payable = frappe.db.get_value('Account', {'company': la.company, 'account_number': '2237'}, 'name')
        provision = frappe.db.get_value('Account', {'company': la.company, 'account_number': '2232'}, 'name')
        bank = frappe.db.get_value('Account', {'company': la.company, 'account_number': '1051'}, 'name')
        amount = la.custom_leave_salary_amount
        if la.custom_pending_payment:
            for i in la.custom_pending_payment:
                amount+=float(i.payable)
        jv.append('accounts', {
            'account': payable,
            'party_type': 'Employee',
            'party': la.employee,
            'debit_in_account_currency': amount
        })
        jv.append('accounts', {
            'account': provision,
            'debit_in_account_currency': amount
        })
        jv.append('accounts', {
            'account': payable,
            'party_type': 'Employee',
            'party': la.employee,
            'credit_in_account_currency': amount
        })
        jv.append('accounts', {
            'account': bank,
            'credit_in_account_currency': amount
        })

        jv.insert() 
        return jv.name


@frappe.whitelist()
def create_journal_for_ticket(name):
    la = frappe.get_doc('Leave Application', name)
    if la.status == 'Approved':
        existing_jv = frappe.db.get_value('Journal Entry', {'docstatus': ['!=', 2], 'custom_ticket_reference': la.name}, 'name')
        if existing_jv:
            return existing_jv
        jv = frappe.new_doc('Journal Entry')
        jv.voucher_type = 'Bank Entry'
        jv.company = la.company
        jv.posting_date = frappe.utils.today()
        jv.custom_division = frappe.db.get_value('Employee', la.employee, 'custom_division') or 'Common'
        jv.cheque_no = la.name
        jv.user_remark = f"Ticket pay for the application - {la.name}"
        jv.custom_ticket_reference = la.name
        jv.cheque_date=jv.posting_date
        payable = frappe.db.get_value('Account', {'company': la.company, 'account_number': '2238'}, 'name')
        provision = frappe.db.get_value('Account', {'company': la.company, 'account_number': '2233'}, 'name')
        bank = frappe.db.get_value('Account', {'company': la.company, 'account_number': '1051'}, 'name')
        ticket = 0
        return_ticket = 0
        if la.custom_approved_ticket == 1:
            ticket = (la.custom_ticket_fare or 0) + (la.custom_spouse_fare or 0) + (la.custom_child_fare or 0)
        if la.custom_approved_ticket_return==1:
            return_ticket = (la.custom_employee_return_fare or 0) + (la.custom_spouse_return_fare or 0) + (la.custom_child_return_fare or 0)
        amount = ticket + return_ticket
        jv.append('accounts', {
            'account': payable,
            'party_type': 'Employee',
            'party': la.employee,
            'debit_in_account_currency': amount
        })
        jv.append('accounts', {
            'account': provision,
            'debit_in_account_currency': amount
        })
        jv.append('accounts', {
            'account': payable,
            'party_type': 'Employee',
            'party': la.employee,
            'credit_in_account_currency': amount
        })
        jv.append('accounts', {
            'account': bank,
            'credit_in_account_currency': amount
        })

        jv.insert() 
        return jv.name

@frappe.whitelist()
def update_rejoining_fields(doc_name, rejoining_date,rejoining_form_name):
    doc = frappe.get_doc("Leave Application", doc_name)
    
    doc.custom_rejoining_date = rejoining_date
    doc.custom_rejoining_created_by_ = frappe.session.user
    doc.custom_rejoining_form = rejoining_form_name
    doc.custom_rejoining_created_on = frappe.utils.today()
    
   
    doc.db_update()
    
    return {"status": "success"}


@frappe.whitelist()
def update_return_ticket(docname, parent_data, child_data):
	doc = frappe.get_doc("Leave Application", docname)
	
	parent_dict = frappe.parse_json(parent_data)
	doc.update(parent_dict)
	
	doc.set("custom_family_details_return", [])
	for row in frappe.parse_json(child_data):
		doc.append("custom_family_details_return", row)
	
	doc.save("Update")
	return True


@frappe.whitelist()
def update_submitted_doc(docname, parent_data, child_data):
	doc = frappe.get_doc("Leave Application", docname)
	
	parent_dict = frappe.parse_json(parent_data)
	doc.update(parent_dict)
	
	doc.set("custom_family_details", [])
	for row in frappe.parse_json(child_data):
		doc.append("custom_family_details", row)
	
	doc.save("Update")
	return True


from frappe.utils import nowdate, getdate, add_years, formatdate
from frappe.utils.data import date_diff, now_datetime, nowdate, today, add_days

@frappe.whitelist()
def get_leave_year(employee, leave_date=None):

	doj = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not doj:
		frappe.throw("Date of Joining not found")

	doj = getdate(doj)

	ref_date = getdate(leave_date) if leave_date else getdate()

	from_date = doj.replace(year=ref_date.year)
	if ref_date < from_date:
		from_date = add_years(from_date, -1)

	to_date = add_days(add_years(from_date, 1), -1)

	return {
		"from_date": from_date,
		"to_date": to_date
	}



PROMOTION_FIELD_MAP = {
	"Basic": "basic",
	"HRA": "hra",
}

EMPLOYEE_FIELD_MAP = {
	"Basic": "custom_basic",
	"HRA": "custom_hra",
}

COMPONENT_OLD_DAYS_FIELD = {
	"Basic": "custom_old_salary_days",
	"HRA": "custom_old_hra_days",
}

@frappe.whitelist()
def calculate_vacation_pay(name,hra_only):
	doc = frappe.get_doc("Leave Application", name)
	employee_map = EMPLOYEE_FIELD_MAP
	promotion_map = PROMOTION_FIELD_MAP
	if doc.leave_type != "Annual Vacation" or doc.custom_payment_type != "Pay Now":
		return

	employee = frappe.get_doc("Employee", doc.employee)

	periods = split_period(getdate(doc.from_date), getdate(doc.to_date))

	from_date = getdate(doc.from_date)
	latest_promotion = get_latest_promotion_row(doc.employee)
	period_promotion = get_promotion_row(
		doc.employee,
		doc.from_date,
		doc.to_date,
	)

	results = []
	promotion_summary = []
	if hra_only==1:
		promotion_map = {
			"HRA": "hra",
		}
	for component, emp_field in employee_map.items():
		emp_amt = float(employee.get(emp_field) or 0)
		breakdown = []
		summary_added = False

		old_days = float(doc.get(COMPONENT_OLD_DAYS_FIELD.get(component)) or 0)
		if hra_only == 1 and component == "Basic" and not old_days:
			continue
		if old_days > 0:
			future_promotion = latest_promotion
			promo_date = (
				add_days(from_date, old_days)
				if future_promotion or (hra_only == 1 and component == "Basic") else None
			)
		else:
			future_promotion = period_promotion
			promo_date = (
				getdate(period_promotion.promotion_date)
				if period_promotion else None
			)
		promo_frac = old_days % 1

		for start, end in periods:
			month_days = get_month_days(start)
			days = date_diff(end, start) + 1

			old_amt = emp_amt
			new_amt = emp_amt

			if future_promotion and component in promotion_map:
				field = promotion_map[component]

				old_amt = float(
					getattr(future_promotion, field, emp_amt) or emp_amt
				)
				new_amt = float(
					getattr(future_promotion, "new_" + field, old_amt) or old_amt
				)

			if hra_only == 1 and component == "Basic":
				new_amt = 0

			is_revised = promo_date and old_amt != new_amt

			if is_revised and not summary_added and not (hra_only == 1 and component == "Basic"):
				promotion_summary.append({
					"component": component,
					"date": promo_date,
					"old": round(old_amt, 2),
					"new": round(new_amt, 2),
				})
				summary_added = True

			if promo_date and (start < promo_date <= end or (start == promo_date and promo_frac)) and is_revised:
				before_days = date_diff(add_days(promo_date, -1), start) + 1 + promo_frac
				amt1 = prorate(old_amt, before_days, month_days)

				if amt1 > 0:
					breakdown.append({
						"from": start,
						"to": promo_date if promo_frac else add_days(promo_date, -1),
						"days": before_days,
						"type": "Previous Salary",
						"amount": round(amt1, 2),
					})

				after_days = date_diff(end, promo_date) + 1 - promo_frac
				amt2 = prorate(new_amt, after_days, month_days)

				if amt2 > 0:
					breakdown.append({
						"from": promo_date,
						"to": end,
						"days": after_days,
						"type": "Revised Salary",
						"amount": round(amt2, 2),
					})

			elif promo_date and end < promo_date:
				amt = prorate(old_amt, days, month_days)
				if amt > 0:
					breakdown.append({
						"from": start,
						"to": end,
						"days": days,
						"type": "Previous Salary" if is_revised else "No Increment",
						"amount": round(amt, 2),
					})


			elif promo_date and start >= promo_date:
				amt = prorate(new_amt if is_revised else emp_amt, days, month_days)
				if amt > 0:
					breakdown.append({
						"from": start,
						"to": end,
						"days": days,
						"type": "Revised Salary" if is_revised else "No Increment",
						"amount": round(amt, 2),
					})


			else:
				# No promotion impact
				amt = prorate(emp_amt, days, month_days)
				if amt > 0:
					breakdown.append({
						"from": start,
						"to": end,
						"days": days,
						"type": "No Increment",
						"amount": round(amt, 2),
					})

		if breakdown:
			results.append({
				"component": component,
				"breakdown": breakdown,
			})

	html = ""
	html += render_promotion_summary(promotion_summary)
	html += render_html(results,hra_only)
	return html

from frappe.utils import get_first_day, get_last_day 
def split_period(from_date, to_date):
	periods = []
	current = from_date

	while current <= to_date:
		month_end = get_last_day(current)
		period_end = min(month_end, to_date)
		periods.append((current, period_end))
		current = add_days(period_end, 1)

	return periods


def get_promotion_row(employee, from_date, to_date):
	emp = frappe.get_doc("Employee", employee)

	from_date = getdate(from_date)
	to_date = getdate(to_date)

	rows = [
		r for r in emp.custom_internal_work_historys
		if r.promotion_date
		and from_date <= getdate(r.promotion_date) <= to_date
	]
	if not rows:
		return None

	rows.sort(key=lambda r: getdate(r.promotion_date))
	return rows[0]


def get_latest_promotion_row(employee):
	emp = frappe.get_doc("Employee", employee)

	rows = [r for r in emp.custom_internal_work_historys if r.promotion_date]
	if not rows:
		return None

	rows.sort(key=lambda r: getdate(r.promotion_date), reverse=True)
	return rows[0]


def get_month_days(date):
	return date_diff(get_last_day(date), get_first_day(date)) + 1


def prorate(amount, days, month_days):
	if not amount or not days:
		return 0
	return (amount / 30) * days


def render_promotion_summary(rows):
	if not rows:
		return """
		<h4>Promotion Details</h4>
		<p style="font-weight:600;color:#6c757d;">
			No promotion in the vacation period
		</p>
		"""

	html = """
	<h4>Promotion Details</h4>
	<table class="table table-bordered">
		<thead style="background:#E9E4D4 ;color:black;">
			<tr>
				<th>Component</th>
				<th>Promotion Date</th>
				<th style="color:#dc3545;">Old Value</th>
				<th style="color:#28a745;">Revised Value</th>
			</tr>
		</thead>
		<tbody>
	"""

	for r in rows:
		html += f"""
		<tr>
			<td><b>{r['component']}</b></td>
			<td>{r['date']}</td>
			<td style="color:#dc3545;font-weight:600;" align="right">{r['old']}</td>
			<td style="color:#28a745;font-weight:600;" align="right">{r['new']}</td>
		</tr>
		"""

	html += "</tbody></table><br>"
	return html


def render_html(data,hra_only):
	
	hra_only=int(hra_only)
	html = """
	<h4>Vacation Pay Calculation</h4>
	<table class="table table-bordered">
		<thead style="background:#343a40;color:white;">
			<tr>
				<th>Component</th>
				<th>From</th>
				<th>To</th>
				<th>Days</th>
				<th>Increment Type</th>
				<th style="text-align:right;">Amount</th>
			</tr>
		</thead>
		<tbody>
	"""

	total = 0

	for row in data:
		first = True
		for b in row["breakdown"]:
			if row['component'] in ['Basic','HRA']:
				
				if hra_only==0 or (hra_only==1 and row['component'] in ('Basic','HRA')) :
					html += f"""
					<tr>
						{f"<td rowspan='{len(row['breakdown'])}'><b>{row['component']}</b></td>" if first else ""}
						<td>{b['from']}</td>
						<td>{b['to']}</td>
						<td align="center">{b['days']}</td>
						<td style="
							font-weight:{'700' if b['type']=='No Increment' else '600'};
							color:{
								'#dc3545' if b['type']=='Previous Salary'
								else '#28a745' if b['type']=='Revised Salary'
								else '#000'
							};
						">
							{b['type']}
						</td>

						<td align="right">{b['amount']}</td>
					</tr>
					"""
					first = False
					total += b["amount"]

	html += f"""
		<tr style="background:#212529;color:white;font-weight:700;">
			<td colspan="5" align="right">Overall Total</td>
			<td align="right">{round(total, 2)}</td>
		</tr>
		</tbody>
	</table>
	"""

	return html


import frappe
from frappe.utils import getdate

@frappe.whitelist()
def check_ticket_taken(employee, from_date):
	year = getdate(from_date).year

	exists = frappe.db.exists(
		"Leave Application",
		{
			"employee": employee,
			"custom_ticket_required": 1,
			"docstatus": ["!=", 2],
			"from_date": ["between", [f"{year}-01-01", f"{year}-12-31"]]
		}
	)

	if exists:
		return "ALREADY_TAKEN"
	else:
		return "NOT_TAKEN"



@frappe.whitelist()
def update_family_table(employee,family):
	fam=[]
	if family=='Yes':
		emp=frappe.get_doc('Employee',employee)
		for e in emp.custom_family:
			fam.append({
				'relation': e.relation,
				'name1': e.name1
			})
	return fam


from frappe.utils import get_link_to_form
from hrms.hr.doctype.leave_application.leave_application import (
	get_leave_balance_on,
	get_number_of_leave_days,
)
from frappe.utils import flt


def validate_leave_extension(doc, new_to_date):
	"""Checks a Leave Extension request against a Leave Application.

	- new To Date must be after the current To Date
	- the available leave balance must cover the extra days
	- when Payment Type is 'Pay With Payroll', no submitted Payroll Entry may
	  already cover the leave period
	Returns the number of extension days; throws otherwise.
	"""
	if isinstance(doc, str):
		doc = frappe.get_doc("Leave Application", doc)

	new_to_date = getdate(new_to_date)
	if not doc.to_date or new_to_date <= getdate(doc.to_date):
		frappe.throw(
			_("Extension To Date must be after the current To Date {0}.").format(
				frappe.bold(formatdate(doc.to_date))
			)
		)

	extension_days = date_diff(new_to_date, getdate(doc.to_date))

	precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 2
	leave_balance = get_leave_balance_on(
		doc.employee,
		doc.leave_type,
		doc.from_date,
		to_date=new_to_date,
		consider_all_leaves_in_the_allocation_period=True,
		for_consumption=True,
	)
	available = flt((leave_balance or {}).get("leave_balance_for_consumption"), precision)
	if available < extension_days:
		frappe.throw(
			_(
				"Insufficient leave balance for Leave Type {0}. Available: {1} day(s), requested extension: {2} day(s)."
			).format(frappe.bold(doc.leave_type), available, extension_days),
			title=_("Insufficient Balance"),
		)

	if doc.custom_payment_type == "Pay With Payroll":
		payroll_entry = frappe.db.get_value(
			"Payroll Entry",
			{
				"company": doc.company,
				"docstatus": 1,
				"start_date": ("<=", new_to_date),
				"end_date": (">=", doc.from_date),
			},
		)
		if payroll_entry:
			frappe.throw(
				_(
					"Leave Extension is not allowed: Payroll Entry {0} has already been processed for this leave period."
				).format(get_link_to_form("Payroll Entry", payroll_entry)),
				title=_("Payroll Already Processed"),
			)

	return extension_days


@frappe.whitelist()
def check_leave_extension(name, to_date):
	"""Called from the Extend Leave dialog before an extension row is saved."""
	doc = frappe.get_doc("Leave Application", name)
	return {"extension_days": validate_leave_extension(doc, to_date)}


def validate_pending_leave_extension(doc, method=None):
	"""Leave Application validate hook: enforce the extension checks on
	newly added or changed unapproved extension rows before save."""
	before = {}
	doc_before_save = getattr(doc, "_doc_before_save", None)
	if doc_before_save:
		before = {
			row.name: row
			for row in doc_before_save.get("custom_extension_details") or []
		}

	for row in doc.get("custom_extension_details") or []:
		if row.approved or not row.to_date:
			continue
		previous = before.get(row.name)
		if previous and getdate(previous.to_date) == getdate(row.to_date):
			continue
		validate_leave_extension(doc, row.to_date)


def apply_pending_leave_extensions(doc, method=None):
	"""Leave Application on_update_after_submit hook: once the extension
	checks pass on save, apply each pending extension row (to_date,
	total_leave_days, Leave Ledger Entry, attendance) and mark it approved."""
	for row in doc.get("custom_extension_details") or []:
		if row.approved or not row.to_date:
			continue
		apply_leave_extension(doc, getdate(row.to_date))
		frappe.db.set_value("Extension Details", row.name, "approved", 1)


@frappe.whitelist()
def approve_leave_extension(name):
	"""Approve and apply all pending extension rows of a Leave Application."""
	doc = frappe.get_doc("Leave Application", name)
	pending = sorted(
		(
			row
			for row in doc.get("custom_extension_details") or []
			if not row.approved and row.to_date
		),
		key=lambda row: getdate(row.to_date),
	)

	for row in pending:
		apply_leave_extension(doc, getdate(row.to_date))
		frappe.db.set_value("Extension Details", row.name, "approved", 1)

	doc.reload()
	return {"applied": len(pending)}


def apply_leave_extension(doc, new_to_date):
	"""Applies a validated extension to a submitted Leave Application:
	updates to_date / total_leave_days, marks attendance On Leave for the
	extra days and adjusts the Leave Ledger Entry."""
	validate_leave_extension(doc, new_to_date)

	old_total = flt(doc.total_leave_days)
	new_total = get_number_of_leave_days(
		doc.employee,
		doc.leave_type,
		doc.from_date,
		new_to_date,
		doc.half_day,
		doc.half_day_date,
	)

	att_date = add_days(getdate(doc.to_date), 1)
	while att_date <= new_to_date:
		create_or_update_attendance(doc.employee, att_date, doc.name)
		att_date = add_days(att_date, 1)

	ledger_name = frappe.db.get_value(
		"Leave Ledger Entry",
		{"transaction_type": "Leave Application", "transaction_name": doc.name},
	)
	if ledger_name:
		frappe.db.set_value(
			"Leave Ledger Entry",
			ledger_name,
			{
				"leaves": frappe.db.get_value("Leave Ledger Entry", ledger_name, "leaves")
				- (new_total - old_total),
				"to_date": new_to_date,
			},
		)

	frappe.db.set_value(
		"Leave Application",
		doc.name,
		{"to_date": new_to_date, "total_leave_days": new_total},
	)

	doc.to_date = new_to_date
	doc.total_leave_days = new_total

	if doc.leave_type == "Annual Vacation":
		new_amount = round(
			sum(
				flt(r["amount"])
				for r in calculate_vacation_pay_by_month(
					doc.name, cint(getattr(doc, "custom_pay_hra_only", 0))
				)
			),
			2,
		)
		payment_ref = frappe.db.exists(
			"Journal Entry",
			{"docstatus": ["!=", 2], "custom_leave_application": doc.name},
		) or frappe.db.exists(
			"Pending Payment", {"leave_application": doc.name}
		)
		if payment_ref and flt(new_amount) != flt(doc.custom_leave_salary_amount):
			frappe.throw(
				_("Leave cannot be extended - payment already processed for this application."),
				title=_("Payment Already Created"),
			)
		if flt(new_amount) != flt(doc.custom_leave_salary_amount):
			doc.custom_leave_salary_amount = new_amount
			frappe.db.set_value(
				"Leave Application", doc.name,
				"custom_leave_salary_amount", new_amount, update_modified=False,
			)
		_sync_leave_deduction_months(doc)


@frappe.whitelist()
def on_extend_leave(employee, previous_to_date, current_to_date, name, row_name=None):
	doc = frappe.get_doc("Leave Application", name)
	apply_leave_extension(doc, getdate(current_to_date))
	if row_name:
		frappe.db.set_value("Extension Details", row_name, "approved", 1)



def create_or_update_attendance(employee, att_date,name):
		
	if frappe.db.exists("Attendance",{'employee':employee,"attendance_date":att_date,"docstatus":['!=',2]}):
		doc = frappe.get_doc("Attendance", {'employee':employee,"attendance_date":att_date,"docstatus":['!=',2]})
		doc.leave_type = "Annual Vacation"
		doc.leave_application = name
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.new_doc("Attendance")
		doc.employee = employee
		doc.attendance_date = att_date
		doc.leave_type = "Annual Vacation"
		doc.leave_application = name
		doc.status = "On Leave"
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
		doc.submit()




@frappe.whitelist()
def get_vacation_pay_table(employee,from_date):

	if not employee:
		return ""

	filters = {
		"employee": employee,
		"docstatus": 1
	}
	if from_date:
		filters["to_date"] = ["<", from_date]

	leave_apps = frappe.get_all(
		"Leave Application",
		filters=filters,
		fields=[
			"name", "from_date", "to_date", "total_leave_days",
			"custom_ticket_fare", "custom_employee_return_fare",
			"custom_leave_salary_amount",
			"custom_spouse_fare", "custom_child_fare",
			"custom_spouse_return_fare", "custom_child_return_fare"
		],
		order_by="from_date asc"
	)

	expense_totals = {}
	if leave_apps:
		expense_entries = frappe.get_all(
			"Direct Expense Entry",
			filters={
				"docstatus": 1,
				"reference_no": ["in", [leave.name for leave in leave_apps]]
			},
			fields=["reference_no", "total_amount"]
		)
		for entry in expense_entries:
			expense_totals[entry.reference_no] = (
				expense_totals.get(entry.reference_no, 0) + (entry.total_amount or 0)
			)

	year_counts = {}
	for leave in leave_apps:
		leave_year = getdate(leave.from_date).year
		year_counts[leave_year] = year_counts.get(leave_year, 0) + 1

	rows = ""
	count = 0
	prev_year = None
	for leave in leave_apps:
		leave_year = getdate(leave.from_date).year
		year_cell = ""
		if leave_year != prev_year:
			year_cell = f'<td rowspan="{year_counts[leave_year]}" style="text-align:center;vertical-align:middle;font-weight:bold;">{leave_year}</td>'
			prev_year = leave_year

		ticket = (leave.custom_ticket_fare or 0) + (leave.custom_employee_return_fare or 0)
		exit_entry = expense_totals.get(leave.name, 0)
		vacation = leave.custom_leave_salary_amount or 0
		family_ticket = (
			(leave.custom_spouse_fare or 0) + (leave.custom_child_fare or 0)
			+ (leave.custom_spouse_return_fare or 0) + (leave.custom_child_return_fare or 0)
		)
		count += 1
		rows += f"""
		<tr>
			{year_cell}
			<td style="text-align:center;">{formatdate(leave.from_date, "dd/MM/yy")} - {formatdate(leave.to_date, "dd/MM/yy")}</td>
			<td style="text-align:center;">{leave.total_leave_days or 0}</td>
			<td style="text-align:right;">{ticket:.2f}</td>
			<td style="text-align:right;">{exit_entry:.2f}</td>
			<td style="text-align:right;">{vacation:.2f}</td>
			<td style="text-align:right;">{family_ticket:.2f}</td>
		</tr>
		"""

	html = f"""
	<table class="table table-bordered">
		<thead>
			<tr>
				<th style="text-align:center;">Year</th>
				<th style="text-align:center;">Period</th>
				<th style="text-align:center;">No.of days</th>
				<th style="text-align:center;">Ticket</th>
				<th style="text-align:center;">Exit/entry</th>
				<th style="text-align:center;">Vacation</th>
				<th style="text-align:center;">Family Ticket</th>
			</tr>
		</thead>
		<tbody>
			{rows}
		</tbody>
	</table>
	"""
	if count==0:
		html=f"""<p style="text-align:center;"><b>No Previous payment records against {employee}</b></p>"""
	return html


@frappe.whitelist()
def download_leave_salary_excel(leave_application):

    import io
    import openpyxl

    from bs4 import BeautifulSoup
    from openpyxl.styles import Font, Alignment, Border, Side

    # Get Leave Application
    doc = frappe.get_doc("Leave Application", leave_application)

    # Get the same salary table HTML
    html = get_vacation_pay_table(
        employee=doc.employee,
        from_date=doc.from_date
    )

    if not html:
        frappe.throw("No Leave Salary Details available.")

    # Parse HTML
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")

    if not table:
        frappe.throw("Salary Details table not found.")

    # Create Excel workbook
    workbook = openpyxl.Workbook()

    worksheet = workbook.active
    worksheet.title = "Leave Salary Details"

    # Border
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    # Keep track of cells occupied by rowspan
    occupied = {}

    # Keep track of merged ranges
    merge_ranges = []

    # Process every HTML row
    for row_index, tr in enumerate(table.find_all("tr"), start=1):

        column_index = 1

        cells = tr.find_all(["th", "td"], recursive=False)

        for cell in cells:

            # Find the next free Excel column
            while (row_index, column_index) in occupied:
                column_index += 1

            # Get rowspan
            rowspan = cell.get("rowspan", 1)

            try:
                rowspan = int(rowspan)
            except (ValueError, TypeError):
                rowspan = 1

            # Get colspan
            colspan = cell.get("colspan", 1)

            try:
                colspan = int(colspan)
            except (ValueError, TypeError):
                colspan = 1

            # Prevent invalid values
            rowspan = max(rowspan, 1)
            colspan = max(colspan, 1)

            # Get cell text
            value = cell.get_text(" ", strip=True)

            # Starting cell
            start_row = row_index
            start_column = column_index

            # Ending cell
            end_row = row_index + rowspan - 1
            end_column = column_index + colspan - 1

            # Write value to top-left cell
            excel_cell = worksheet.cell(
                row=start_row,
                column=start_column,
                value=value
            )

            # Apply formatting to all cells in the merged area
            for r in range(start_row, end_row + 1):

                for c in range(start_column, end_column + 1):

                    target_cell = worksheet.cell(
                        row=r,
                        column=c
                    )

                    target_cell.border = thin_border

                    target_cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center",
                        wrap_text=True
                    )

                    # Mark cell as occupied
                    occupied[(r, c)] = True

            # Header formatting
            if cell.name == "th":
                excel_cell.font = Font(bold=True)

            # Add merge range if rowspan or colspan exists
            if rowspan > 1 or colspan > 1:

                merge_ranges.append(
                    (
                        start_row,
                        start_column,
                        end_row,
                        end_column
                    )
                )

            # Move to next column
            column_index = end_column + 1

    # Merge cells after all values have been written
    for start_row, start_column, end_row, end_column in merge_ranges:

        worksheet.merge_cells(
            start_row=start_row,
            start_column=start_column,
            end_row=end_row,
            end_column=end_column
        )

    # Adjust column widths
    for column in worksheet.columns:

        max_length = 0

        column_letter = column[0].column_letter

        for cell in column:

            if cell.value is not None:

                max_length = max(
                    max_length,
                    len(str(cell.value))
                )

        worksheet.column_dimensions[column_letter].width = min(
            max_length + 3,
            40
        )

    # Adjust row heights
    for row in worksheet.iter_rows():

        row_number = row[0].row

        worksheet.row_dimensions[row_number].height = 25

    # Save workbook to memory
    output = io.BytesIO()

    workbook.save(output)

    output.seek(0)

    # Create Frappe File
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": f"Leave_Salary_Details_{doc.name}.xlsx",
        "content": output.getvalue(),
        "attached_to_doctype": "Leave Application",
        "attached_to_name": doc.name,
        "is_private": 1
    })

    file_doc.insert(ignore_permissions=True)

    frappe.db.commit()

    return file_doc.file_url

@frappe.whitelist()
def check_annual_vacation_doj_year(employee, leave_from_date, current_doc=None):
	doj = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not doj:
		return {"eligible": True}

	doj = getdate(doj)
	leave_from_date = getdate(leave_from_date)

	years_completed = (
		leave_from_date.year - doj.year
		- ((leave_from_date.month, leave_from_date.day) < (doj.month, doj.day))
	)

	period_start = add_years(doj, years_completed)
	period_end = add_days(add_years(doj, years_completed + 1), -1)

	existing = frappe.db.get_value(
		"Leave Application",
		{
			"employee": employee,
			"custom_approval_status":"Eligible",
			"leave_type": "Annual Vacation",
			"docstatus": ["!=", 2],
			"from_date": [">=", period_start],
			"to_date": ["<=", period_end],
			"name": ["!=", current_doc],
		},
		"name",
	)

	if existing:
		return {
			"eligible": False,
			"leave_application": existing,
			"period_start": period_start,
			"period_end": period_end,
		}

	return {
		"eligible": True,
		"period_start": period_start,
		"period_end": period_end,
	}


from frappe.utils import add_months, nowdate, getdate

@frappe.whitelist()
def check_leave_validations(doc, method):
	if doc.leave_type == 'Annual Vacation' and doc.custom_pay_hra_only and not doc.custom_old_salary_days:
		doc.custom_old_salary_days = 30
	if doc.leave_type=='Marriage Leave':
		if frappe.db.exists('Leave Application',{'leave_type':doc.leave_type,'name':('!=',doc.name),'docstatus':['!=',2],'employee':doc.employee}) :
			frappe.throw(f'Already another application found.Marriage leave only allowed once.') 
	# if doc.leave_type == "Sick Leave":
	#     today = getdate(nowdate())
	#     fdate = getdate(doc.from_date)
	#     month_start = date(fdate.year, fdate.month, 1)
	#     if fdate.month == 12:
	#         next_month_start = date(fdate.year + 1, 1, 1)
	#     else:
	#         next_month_start = date(fdate.year, fdate.month + 1, 1)
	#     max_monthly_allowance = 2.5
	#     taken_leave_this_month = frappe.db.sql("""
	#         SELECT SUM(total_leave_days)
	#         FROM `tabLeave Application`
	#         WHERE employee = %s
	#         AND leave_type = 'Sick Leave'
	#         AND status NOT IN ('Rejected', 'Cancelled')
	#         AND from_date >= %s AND from_date < %s
	#         AND name != %s
	#     """, (doc.employee, month_start, next_month_start, doc.name))[0][0] or 0
	#     total_requested = taken_leave_this_month + doc.total_leave_days
	#     if total_requested > max_monthly_allowance:
	#         frappe.throw(
	#             f"You are allowed only 2.5 Sick Leave days in {today.strftime('%B')}. "
	#             f"Already requested: {taken_leave_this_month}."
	#         )
	elif doc.leave_type=='Pilgrimage Leave':
		if frappe.db.exists('Leave Application',{'leave_type':doc.leave_type,'name':('!=',doc.name),'docstatus':['!=',2],'custom_pilgrimage_for':doc.custom_pilgrimage_for,'employee':doc.employee}) :
			frappe.throw(f'Already another application found for {doc.custom_pilgrimage_for}.') 
	elif doc.leave_type=='Maternity Leave':
		gender=frappe.db.get_value('Employee',{'name':doc.employee},['gender'])
		if gender!='Female':
			frappe.throw('Maternity leave is applicable for <b>Female</b> employees only.') 
	elif doc.leave_type=="Relative's Death":
		if doc.custom_death_in=='Family Member':
			family = frappe.db.get_value("Leave Type",{'name':"Relative's Death"},"custom_maximum_leave_allowed_for_family_member")
			if doc.total_leave_days > float(family):
				frappe.throw(f'Maximum of {family} Days is applicable for death of <b>{doc.custom_death_in}</b>.') 
		else:
			close_relative = frappe.db.get_value("Leave Type",{'name':"Relative's Death"},"custom_maximum_leave_allowed_for_close_relative")
			if doc.total_leave_days > float(close_relative):
				frappe.throw(f'Maximum of {close_relative} Days is applicable for death of <b>{doc.custom_death_in}</b>.') 
	# elif doc.leave_type=="Injury Leave":
	#     current_year_start = date(getdate(nowdate()).year, 1, 1)
	#     current_year_end = date(getdate(nowdate()).year, 12, 31)

	#     total_injury_leave = frappe.db.sql("""
	#         SELECT SUM(total_leave_days)
	#         FROM `tabLeave Application`
	#         WHERE employee = %s
	#         AND leave_type = 'Injury Leave'
	#         AND status NOT IN ('Rejected', 'Cancelled')
	#         AND from_date BETWEEN %s AND %s
	#         AND name != %s
	#     """, (doc.employee, current_year_start, current_year_end, doc.name))[0][0] or 0
	#     total_requested = total_injury_leave + doc.total_leave_days
	#     if total_requested > 10:
	#         frappe.throw(f"Injury Leave cannot exceed 10 days per year. Already requested: {total_injury_leave}")
	elif doc.leave_type=="Child Birth Leave":
		total_leave = frappe.db.sql("""
			SELECT SUM(total_leave_days)
			FROM `tabLeave Application`
			WHERE employee = %s
			AND leave_type = 'Child Birth Leave'
			AND status NOT IN ('Rejected', 'Cancelled')
			AND name != %s
		""", (doc.employee, doc.name))[0][0] or 0
		total_requested = total_leave + doc.total_leave_days
		child_birth_leave = frappe.db.get_value("Leave Type",{'name':"Child Birth Leave"},'custom_maximum_leave_allowed')
		if total_requested > child_birth_leave:
			frappe.throw(f"Child Birth Leave only applicable for {child_birth_leave} days per employee .")
	elif doc.leave_type=="Annual Vacation":
		today = getdate(nowdate())
		doj = frappe.db.get_value("Employee", {'name': doc.employee}, 'date_of_joining')
		eligible_date = getdate(add_months(doj, 6))  
		# if today < eligible_date:
		#     frappe.throw("Employees who completed 6 months are only eligible to apply <b>Annual Vacation</b>")
		if doc.custom_ticket_required==1:
			anniversary = getdate(add_years(doj, 1))
			if today < anniversary:
				frappe.throw("Employees who completed 1 year are only eligible to apply along with ticket")
			from_year = getdate(doc.from_date).year
			existing_with_ticket = frappe.db.exists(
				"Leave Application",
				{
					"employee": doc.employee,
					"leave_type": "Annual Vacation",
					"custom_ticket_required": 1,
					"docstatus": ["!=", 2], 
					"name": ["!=", doc.name],  
				},
			)

			if existing_with_ticket:
				existing_doc = frappe.get_doc("Leave Application", existing_with_ticket)
				if getdate(existing_doc.from_date).year == from_year:
					frappe.throw("An Annual Vacation with ticket has already been applied for this year.")
		spouse_count=0
		child_count=0
		for f in doc.custom_family_details:
			if f.relation not in ['Spouse','Child']:
				frappe.throw('Ticket only applicable for <b>Spouse</b> and <b>Child</b> ')
			if f.relation=='Spouse':
				spouse_count+=1
			if f.relation=='Child':
				child_count+=1
			if spouse_count>1:
				frappe.throw('Ticket only applicable for one <b>Spouse</b>')
			if child_count>2:
				frappe.throw('Ticket only applicable for 2 <b>Children</b>')

		start = add_days(doc.from_date, -1)
		end = add_days(doc.to_date, 1)

		# Normalize to date objects
		start_date = ensure_date(start)
		end_date = ensure_date(end)

		start_hh = check_holiday(start_date, doc.employee)
		end_hh = check_holiday(end_date, doc.employee)

		# if start_hh:
		# 	frappe.throw(
		# 		f"<b>{start_date.strftime('%d-%m-%Y')}</b> is holiday. Annual Vacation is not allowed to club with holidays."
		# 	)

		# if end_hh:
		# 	frappe.throw(
		# 		f"<b>{end_date.strftime('%d-%m-%Y')}</b> is holiday. Annual Vacation is not allowed to club with holidays."
		# 	)

import datetime

def ensure_date(val):
	if isinstance(val, str):
		return datetime.datetime.strptime(val, "%Y-%m-%d").date()
	return val


@frappe.whitelist()
def check_holiday(date,emp):
	holiday_list = frappe.db.get_value('Employee',emp,'holiday_list')
	company = frappe.db.get_value('Employee',emp,'company')
	if not holiday_list:
		holiday_list = frappe.db.get_value('Company',company,'default_holiday_list')
	holiday = frappe.db.sql("""select `tabHoliday`.holiday_date,`tabHoliday`.weekly_off from `tabHoliday List` 
	left join `tabHoliday` on `tabHoliday`.parent = `tabHoliday List`.name where `tabHoliday List`.name = '%s' and holiday_date = '%s' """%(holiday_list,date),as_dict=True)
	if holiday:
		return 'H'



from frappe.utils import cint

def _is_used_in_submitted_slip(additional_salary):
	return bool(
		frappe.db.sql(
			"""
			SELECT 1 FROM `tabSalary Detail` sd
			JOIN `tabSalary Slip` ss ON ss.name = sd.parent
			WHERE sd.additional_salary = %s AND ss.docstatus = 1
			LIMIT 1
			""",
			additional_salary,
		)
	)


def _cancel_leave_deduction(name):
	if not frappe.db.exists("Additional Salary", {"name": name, "docstatus": 1}):
		return
	if _is_used_in_submitted_slip(name):
		frappe.log_error(
			f"Leave Deduction {name} is linked to a submitted Salary Slip and was left untouched.",
			"Leave Deduction Reconcile",
		)
		return
	try:
		ad = frappe.get_doc("Additional Salary", name)
		ad.flags.ignore_permissions = True
		ad.cancel()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"Failed to cancel Leave Deduction Additional Salary {name}",
		)


def _create_leave_deduction(employee, company, payroll_date, amount):
	add_salary = frappe.new_doc("Additional Salary")
	add_salary.employee = employee
	if company:
		add_salary.company = company
	add_salary.salary_component = "Leave Deduction"
	add_salary.payroll_date = payroll_date
	add_salary.amount = amount
	add_salary.overwrite_salary_structure_amount = 1
	add_salary.insert(ignore_permissions=True)
	add_salary.submit()
	return add_salary.name


def reconcile_leave_deduction(employee, company, period_start, period_end):
	"""Leave Deduction is no longer created - vacation pay is handled by the
	'Vacation Pay' earning (Pay With Payroll only). This now only cancels
	leftover 'Leave Deduction' Additional Salary rows in the period (duplicates
	or rows left by cancelled/type-changed leaves). Rows used in a submitted
	Salary Slip or created by the Payroll Entry hook are left untouched.
	"""
	from frappe.utils import flt, get_first_day, get_last_day, getdate

	period_start = getdate(period_start)
	period_end = getdate(period_end)

	total = 0

	existing = frappe.get_all(
		"Additional Salary",
		filters={
			"employee": employee,
			"salary_component": "Leave Deduction",
			"payroll_date": ["between", [period_start, period_end]],
			"custom_payroll_entry": ["is", "not set"],
			"docstatus": 1,
		},
		fields=["name", "amount"],
		order_by="payroll_date asc, creation asc",
	)

	if not existing:
		if total > 0:
			_create_leave_deduction(employee, company, period_start, total)
		return

	keep = existing[0]
	if total <= 0:
		for row in existing:
			_cancel_leave_deduction(row.name)
		return

	if flt(keep.amount) != total and not _is_used_in_submitted_slip(keep.name):
		frappe.db.set_value("Additional Salary", keep.name, "amount", total, update_modified=False)

	for row in existing[1:]:
		_cancel_leave_deduction(row.name)


def _sync_leave_deduction_months(doc):
	from frappe.utils import get_first_day, get_last_day, getdate

	for row in calculate_vacation_pay_by_month(doc.name, cint(getattr(doc, "custom_pay_hra_only", 0))):
		row_date = getdate(row["from_date"])
		reconcile_leave_deduction(
			doc.employee, doc.company, get_first_day(row_date), get_last_day(row_date)
		)


@frappe.whitelist()
def create_vacation_pay_deductions(doc, method=None):
	if doc.leave_type != "Annual Vacation" or doc.status != "Approved":
		return
	_sync_leave_deduction_months(doc)


@frappe.whitelist()
def cancel_vacation_pay_deductions(doc, method=None):
	if doc.leave_type != "Annual Vacation":
		return
	_sync_leave_deduction_months(doc)


def update_leave_salary_after_submit(doc, method=None):
	"""Recalculate custom_leave_salary_amount on post-submit edits
	(custom_payment_type and custom_leave_salary_amount are
	allow_on_submit). A manually edited amount is kept; the calculated
	value only applies when the amount was not touched. Blocked once
	payment is processed for the leave."""
	from frappe.utils import flt

	if doc.leave_type != "Annual Vacation":
		return

	new_amount = round(
		sum(
			flt(r["amount"])
			for r in calculate_vacation_pay_by_month(
				doc.name, cint(getattr(doc, "custom_pay_hra_only", 0))
			)
		),
		2,
	)

	payment_ref = frappe.db.exists(
		"Journal Entry",
		{"docstatus": ["!=", 2], "custom_leave_application": doc.name},
	) or frappe.db.exists(
		"Pending Payment", {"leave_application": doc.name}
	)

	if payment_ref and (
		flt(new_amount) != flt(doc.custom_leave_salary_amount)
		or doc.has_value_changed("custom_payment_type")
	):
		frappe.throw(
			_("Leave salary cannot be changed - payment already processed for this application."),
			title=_("Payment Already Created"),
		)

	if (
		not doc.has_value_changed("custom_leave_salary_amount")
		and flt(new_amount) != flt(doc.custom_leave_salary_amount)
	):
		doc.custom_leave_salary_amount = new_amount
		frappe.db.set_value(
			"Leave Application", doc.name,
			"custom_leave_salary_amount", new_amount, update_modified=False,
		)

	_sync_leave_deduction_months(doc)




@frappe.whitelist()
def calculate_vacation_pay_by_month(leave_application, hra_only=0):
	hra_only = cint(hra_only)
	if isinstance(leave_application, str):
		leave_application = frappe.get_doc("Leave Application", leave_application)
	if (
		not hasattr(leave_application, "leave_type")
		or (
			leave_application.leave_type != "Annual Vacation"
			and not frappe.get_cached_value(
				"Leave Type", leave_application.leave_type, "is_lwp"
			)
		)
	):
		return []

	employee_map = EMPLOYEE_FIELD_MAP
	promotion_map = {"HRA": "hra"} if hra_only else PROMOTION_FIELD_MAP

	employee = frappe.get_doc("Employee", leave_application.employee)
	periods = split_period(getdate(leave_application.from_date), getdate(leave_application.to_date))

	from_date = getdate(leave_application.from_date)
	latest_promotion = get_latest_promotion_row(leave_application.employee)
	period_promotion = get_promotion_row(
		leave_application.employee,
		leave_application.from_date,
		leave_application.to_date,
	)

	monthly_totals = {}

	for component, emp_field in employee_map.items():
		emp_amt = float(employee.get(emp_field) or 0)

		old_days = float(leave_application.get(COMPONENT_OLD_DAYS_FIELD.get(component)) or 0)
		if hra_only == 1 and component == "Basic" and not old_days:
			continue
		if old_days > 0:
			future_promotion = latest_promotion
			promo_date = (
				add_days(from_date, old_days)
				if future_promotion or (hra_only == 1 and component == "Basic") else None
			)
		else:
			future_promotion = period_promotion
			promo_date = (
				getdate(period_promotion.promotion_date)
				if period_promotion else None
			)
		promo_frac = old_days % 1

		for start, end in periods:
			month_days = get_month_days(start)
			days = date_diff(end, start) + 1

			old_amt = emp_amt
			new_amt = emp_amt

			if future_promotion and component in promotion_map:
				field = promotion_map[component]
				old_amt = float(getattr(future_promotion, field, emp_amt) or emp_amt)
				new_amt = float(getattr(future_promotion, "new_" + field, old_amt) or old_amt)

			if hra_only == 1 and component == "Basic":
				new_amt = 0

			is_revised = promo_date and old_amt != new_amt

			if is_revised and (start < promo_date <= end or (start == promo_date and promo_frac)):
				before_days = date_diff(add_days(promo_date, -1), start) + 1 + promo_frac
				after_days = date_diff(end, promo_date) + 1 - promo_frac

				amount = round(
					prorate(old_amt, before_days, month_days)
					+ prorate(new_amt, after_days, month_days),
					2,
				)
			elif is_revised and end < promo_date:
				amount = round(prorate(old_amt, days, month_days), 2)
			elif is_revised and start >= promo_date:
				amount = round(prorate(new_amt, days, month_days), 2)
			else:
				amount = round(prorate(emp_amt, days, month_days), 2)

			if amount:
				monthly_totals[start] = monthly_totals.get(start, 0) + amount

	return [
		{"from_date": start, "amount": round(amt, 2)}
		for start, amt in sorted(monthly_totals.items())
	]


@frappe.whitelist()
def calculate_vacation_pay_print(name, hra_only=0):
	"""Print-format copy of calculate_vacation_pay (Salary Breakup tab).

	Same computation; the tables are rendered with inline borders and
	alignment so they render correctly in print/PDF where Bootstrap
	classes may not be available. The form version is unchanged.
	"""
	hra_only = cint(hra_only)
	doc = frappe.get_doc("Leave Application", name)
	employee_map = EMPLOYEE_FIELD_MAP
	promotion_map = PROMOTION_FIELD_MAP
	if doc.leave_type != "Annual Vacation" or doc.custom_payment_type != "Pay Now":
		return

	employee = frappe.get_doc("Employee", doc.employee)

	periods = split_period(getdate(doc.from_date), getdate(doc.to_date))

	from_date = getdate(doc.from_date)
	latest_promotion = get_latest_promotion_row(doc.employee)
	period_promotion = get_promotion_row(
		doc.employee,
		doc.from_date,
		doc.to_date,
	)

	results = []
	promotion_summary = []
	if hra_only == 1:
		promotion_map = {
			"HRA": "hra",
		}
	for component, emp_field in employee_map.items():
		emp_amt = float(employee.get(emp_field) or 0)
		breakdown = []
		summary_added = False

		old_days = float(doc.get(COMPONENT_OLD_DAYS_FIELD.get(component)) or 0)
		if hra_only == 1 and component == "Basic" and not old_days:
			continue
		if old_days > 0:
			future_promotion = latest_promotion
			promo_date = (
				add_days(from_date, old_days)
				if future_promotion or (hra_only == 1 and component == "Basic") else None
			)
		else:
			future_promotion = period_promotion
			promo_date = (
				getdate(period_promotion.promotion_date)
				if period_promotion else None
			)
		promo_frac = old_days % 1

		for start, end in periods:
			month_days = get_month_days(start)
			days = date_diff(end, start) + 1

			old_amt = emp_amt
			new_amt = emp_amt

			if future_promotion and component in promotion_map:
				field = promotion_map[component]

				old_amt = float(
					getattr(future_promotion, field, emp_amt) or emp_amt
				)
				new_amt = float(
					getattr(future_promotion, "new_" + field, old_amt) or old_amt
				)

			if hra_only == 1 and component == "Basic":
				new_amt = 0

			is_revised = promo_date and old_amt != new_amt

			if is_revised and not summary_added and not (hra_only == 1 and component == "Basic"):
				promotion_summary.append({
					"component": component,
					"date": promo_date,
					"old": round(old_amt, 2),
					"new": round(new_amt, 2),
					"old_days": 0,
					"old_payment": 0,
					"new_days": 0,
					"new_payment": 0,
				})
				summary_added = True

			if promo_date and (start < promo_date <= end or (start == promo_date and promo_frac)) and is_revised:
				before_days = date_diff(add_days(promo_date, -1), start) + 1 + promo_frac
				amt1 = prorate(old_amt, before_days, month_days)

				if amt1 > 0:
					breakdown.append({
						"from": start,
						"to": promo_date if promo_frac else add_days(promo_date, -1),
						"days": before_days,
						"type": "Previous Salary",
						"amount": round(amt1, 2),
					})

				after_days = date_diff(end, promo_date) + 1 - promo_frac
				amt2 = prorate(new_amt, after_days, month_days)

				if amt2 > 0:
					breakdown.append({
						"from": promo_date,
						"to": end,
						"days": after_days,
						"type": "Revised Salary",
						"amount": round(amt2, 2),
					})

			elif promo_date and end < promo_date:
				amt = prorate(old_amt, days, month_days)
				if amt > 0:
					breakdown.append({
						"from": start,
						"to": end,
						"days": days,
						"type": "Previous Salary" if is_revised else "No Increment",
						"amount": round(amt, 2),
					})


			elif promo_date and start >= promo_date:
				amt = prorate(new_amt if is_revised else emp_amt, days, month_days)
				if amt > 0:
					breakdown.append({
						"from": start,
						"to": end,
						"days": days,
						"type": "Revised Salary" if is_revised else "No Increment",
						"amount": round(amt, 2),
					})


			else:
				amt = prorate(emp_amt, days, month_days)
				if amt > 0:
					breakdown.append({
						"from": start,
						"to": end,
						"days": days,
						"type": "No Increment",
						"amount": round(amt, 2),
					})

		if breakdown:
			results.append({
				"component": component,
				"breakdown": breakdown,
			})

			if summary_added:
				summary_row = promotion_summary[-1]
				old_rows = [b for b in breakdown if b["type"] == "Previous Salary"]
				new_rows = [b for b in breakdown if b["type"] == "Revised Salary"]
				summary_row["old_days"] = sum(b["days"] for b in old_rows)
				summary_row["old_payment"] = round(sum(b["amount"] for b in old_rows), 2)
				summary_row["new_days"] = sum(b["days"] for b in new_rows)
				summary_row["new_payment"] = round(sum(b["amount"] for b in new_rows), 2)

	html = ""
	html += render_promotion_summary_print(promotion_summary)
	html += render_vacation_pay_print(results)
	return html


def render_promotion_summary_print(rows):
	html = """
	<table width="99%" style="border-collapse:collapse;font-size:12px;margin-bottom:15px;">
		<thead>
		<tr>
			<td colspan="5" style="font-size:13px;background-color:#0F0F5C;text-align:center;color:white;font-weight:bold;padding:5px;">
				Salary Breakup
			</td>
		</tr>
		<tr>
			<td colspan="5" style="background-color:#d3d3d3;text-align:center;font-weight:bold;padding:5px;border:1px solid #d3d3d3;">
				Promotion Details
			</td>
		</tr>
	"""

	if not rows:
		html += """
		<tr>
			<td colspan="5" style="border:1px solid #d3d3d3;padding:4px 6px;text-align:center;font-weight:bold;color:#555;">
				No promotion in the vacation period
			</td>
		</tr>
	</thead>
	</table>
	"""
		return html

	html += """
		<tr style="font-weight:bold;text-align:center;">
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">Component</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">Old Value</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">Payment with Old Value</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">Revised Value</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">Payment with Revised Value</td>
		</tr>
	</thead>
	<tbody>
	"""

	for r in rows:
		html += f"""
		<tr style="page-break-inside:avoid;">
			<td style="border:1px solid #d3d3d3;padding:4px 6px;text-align:center;font-weight:bold;">{r['component']}</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;text-align:right;color:#dc3545;font-weight:600;">{r['old']:.2f}</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;text-align:center;color:#dc3545;">
				{r['old_payment']:.2f}
				<div style="font-size:10px;color:#555;">({r['old_days']} days)</div>
			</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;text-align:right;color:#28a745;font-weight:600;">{r['new']:.2f}</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;text-align:center;color:#28a745;">
				{r['new_payment']:.2f}
				<div style="font-size:10px;color:#555;">({r['new_days']} days)</div>
			</td>
		</tr>
		"""

	html += "</tbody></table>"
	return html


def render_vacation_pay_print(data):
	html = """
	<table width="99%" style="border-collapse:collapse;font-size:12px;margin-bottom:15px;">
		<thead>
		<tr>
			<td colspan="6" style="font-size:13px;background-color:#0F0F5C;text-align:center;color:white;font-weight:bold;padding:5px;">
				Vacation Pay Calculation
			</td>
		</tr>
		<tr style="font-weight:bold;text-align:center;">
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">Component</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">From</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">To</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">Days</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">Increment Type</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;">Amount</td>
		</tr>
		</thead>
		<tbody>
	"""

	total = 0
	for row in data:
		first = True
		for b in row["breakdown"]:
			color = (
				"#dc3545" if b["type"] == "Previous Salary"
				else "#28a745" if b["type"] == "Revised Salary"
				else "#000"
			)
			weight = "600" if b["type"] != "No Increment" else "700"
			component_cell = (
				f"<td rowspan='{len(row['breakdown'])}' "
				"style='border:1px solid #d3d3d3;padding:4px 6px;font-weight:bold;'>"
				f"{row['component']}</td>"
			) if first else ""
			html += f"""
			<tr style="page-break-inside:avoid;">
				{component_cell}
				<td style="border:1px solid #d3d3d3;padding:4px 6px;text-align:center;">{formatdate(b['from'], "dd-MM-yyyy")}</td>
				<td style="border:1px solid #d3d3d3;padding:4px 6px;text-align:center;">{formatdate(b['to'], "dd-MM-yyyy")}</td>
				<td style="border:1px solid #d3d3d3;padding:4px 6px;text-align:center;">{b['days']}</td>
				<td style="border:1px solid #d3d3d3;padding:4px 6px;font-weight:{weight};color:{color};">{b['type']}</td>
				<td style="border:1px solid #d3d3d3;padding:4px 6px;text-align:right;">{b['amount']:.2f}</td>
			</tr>
			"""
			first = False
			total += b["amount"]

	html += f"""
		</tbody>
		<tr style="background:#0F0F5C;color:white;font-weight:bold;page-break-inside:avoid;">
			<td colspan="5" style="border:1px solid #d3d3d3;padding:4px 6px;text-align:right;">Overall Total</td>
			<td style="border:1px solid #d3d3d3;padding:4px 6px;text-align:right;">{round(total, 2):.2f}</td>
		</tr>
	</table>
	"""

	return html


