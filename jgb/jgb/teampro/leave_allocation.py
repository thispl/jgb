import frappe
from frappe import _
from frappe.utils import nowdate, getdate, add_years, formatdate, flt
from frappe.utils.data import date_diff, now_datetime, nowdate, today, add_days

@frappe.whitelist()
def allocate_sl():

	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "date_of_joining"]
	)

	current_date = getdate(today())
	current_year = current_date.year

	for emp in employees:
		try:
			if not emp.date_of_joining:
				continue

			doj = getdate(emp.date_of_joining)
			first_anniversary = add_years(doj, 1)

			if current_date < first_anniversary:

				from_date = doj
				to_date = add_days(first_anniversary, -1)

			else:
				try:
					current_year_anniversary = doj.replace(year=current_year)
				except ValueError:
					current_year_anniversary = doj.replace(year=current_year, day=28)

				if current_date < current_year_anniversary:
					from_date = add_years(current_year_anniversary, -1)
					to_date = add_days(current_year_anniversary, -1)
				else:
					from_date = current_year_anniversary
					next_anniversary = add_years(current_year_anniversary, 1)
					to_date = add_days(next_anniversary, -1)

			allocations = frappe.get_all(
				"Leave Allocation",
				filters={
					"employee": emp.name,
					"leave_type": "Sick Leave",
					"docstatus": 1,
				},
				fields=["from_date", "to_date"],
			)

			# already covered through the end of this service year
			if any(
				getdate(a.from_date) <= to_date <= getdate(a.to_date)
				for a in allocations
			):
				continue

			# stale allocations that only partly overlap this window must not
			# block it - start the new allocation the day after they end
			for a in sorted(allocations, key=lambda x: getdate(x.to_date)):
				if getdate(a.from_date) <= from_date <= getdate(a.to_date):
					from_date = add_days(getdate(a.to_date), 1)

			if from_date > to_date:
				continue

			leave = frappe.get_doc({
				"doctype": "Leave Allocation",
				"employee": emp.name,
				"leave_type": "Sick Leave",
				"from_date": from_date,
				"to_date": to_date,
				"new_leaves_allocated": 30
			})

			leave.insert(ignore_permissions=True)
			leave.submit()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				title="Sick Leave allocation failed for {0}".format(emp.name),
				message=frappe.get_traceback()
			)

	return "Sick Leave Allocation Completed"



@frappe.whitelist()
def create_sl_scheduled_job_type():
	pos = frappe.db.exists('Scheduled Job Type', 'allocate_sl')
	if not pos:
		sjt = frappe.new_doc("Scheduled Job Type")
		sjt.update({
			"method" : 'jgb.jgb.teampro.leave_allocation.allocate_sl',
			"frequency" : 'Cron',
			"cron_format":"0 1 * * *"
		})
		sjt.save(ignore_permissions=True)


@frappe.whitelist()
def check_allocations(doc,method):
	today = getdate(nowdate())
	if doc.leave_type=='Pilgrimage Leave':
		employees = frappe.db.get_value("Employee", {'name':doc.employee}, [ 'date_of_joining'])
		fifth_anniversary = add_years(employees, 1)
		retirement_date = add_years(employees, 60)
		if today < fifth_anniversary:
			frappe.throw("Employees who completed 1 years of service only eligible for <b>Pilgrimage Leave</b>")
		pilgrimage_leave = frappe.db.get_value("Leave Type",{'name':'Pilgrimage Leave'},"custom_maximum_leave_allowed")
		# if doc.new_leaves_allocated > float(pilgrimage_leave):
		#     frappe.throw(f"<b>Pilgrimage Leave</b> allocation should not exceed {pilgrimage_leave}")
		if frappe.db.exists('Leave Allocation',{'employee':doc.employee,'docstatus':['!=',2],'leave_type':doc.leave_type,'name':['!=',doc.name]}):
			docs=frappe.db.get_all('Leave Allocation',{'employee':doc.employee,'docstatus':['!=',2],'leave_type':doc.leave_type,'name':['!=',doc.name]})
			tot=0
			for i in docs:
				tot+=i.new_leaves_allocated
			tot=tot+doc.new_leaves_allocated
			if tot > float(pilgrimage_leave):
				frappe.throw(f"<b>Pilgrimage Leave</b> allocation should not exceed {pilgrimage_leave}.Already another allocation present.Kindly check.")
	elif doc.leave_type == 'Marriage Leave':

		allocations = frappe.db.get_all(    
			"Leave Allocation",
			filters={
				"employee": doc.employee,
				"leave_type": doc.leave_type,
				"docstatus": ["!=", 2],
				"name": ["!=", doc.name],
			},
			fields=["new_leaves_allocated"]
		)

		# Safe summing: None → 0
		previous_total = sum([(a.new_leaves_allocated or 0) for a in allocations])

		# Total after adding current allocation
		combined_total = previous_total + (doc.new_leaves_allocated or 0)
		marriage_leave = frappe.db.get_value("Leave Type",{'name':'Marriage Leave'},"custom_maximum_leave_allowed")
		if combined_total > marriage_leave:
			frappe.throw(
				f"<b>Marriage Leave</b> allocation cannot exceed {marriage_leave} days in total. "
				"Another allocation already exists. Kindly check."
			)

		if (doc.new_leaves_allocated or 0) > marriage_leave:
			frappe.throw(f"<b>Marriage Leave</b> allocation cannot exceed {marriage_leave} days.")

	elif doc.leave_type=='Annual Vacation':    
		employees = frappe.db.get_value("Employee", {'name':doc.employee}, [ 'date_of_joining'])
		anniversary = add_years(employees, 1)
		# if getdate(doc.from_date) < anniversary:
		#     frappe.throw("<b>Annual Vacation</b> is eligible only for employees completed 1 year.")








import frappe
from datetime import date, timedelta
import calendar
from frappe.utils import getdate, add_years, add_months

ACCRUAL_LEAVES = 2.5
ACCRUAL_MARKER = "Annual Vacation accrual"
# Employees who joined on/after this date are held exactly at ACCRUAL_LEAVES per
# monthly joining-anniversary (back-filled from the DOJ). Older joiners keep the
# original monthly +2.5 step.
ACCRUAL_REGIME_START = date(2026, 1, 1)


def _accrual_marker_exists(la_name, month_str):
	return frappe.db.exists(
		"Comment",
		{
			"reference_doctype": "Leave Allocation",
			"reference_name": la_name,
			"comment_type": "Info",
			"content": ("like", "%{0}%{1}%".format(ACCRUAL_MARKER, month_str)),
		},
	)


def _month_accrual_exists(employee, la_name, run_date):
	"""Whether the accrual for run_date's month was already posted.

	New system: marker Info comment on the allocation. For 2026-09 also
	check ledger rows actually created that month (current table +
	zbackup_av_lle, which holds rows deleted when allocations were
	cancelled) so old-system accruals are not double-posted."""
	month_str = run_date.strftime("%Y-%m")
	if _accrual_marker_exists(la_name, month_str):
		return True
	if month_str == "2026-09":
		month_end = add_months(run_date, 1)
		return bool(
			frappe.db.sql(
				"""
				SELECT 1 FROM (
					SELECT name FROM `tabLeave Ledger Entry`
					WHERE employee=%s AND leave_type='Annual Vacation'
					  AND transaction_type='Leave Allocation'
					  AND docstatus=1 AND is_carry_forward=0 AND is_expired=0
					  AND leaves>0 AND creation>=%s AND creation<%s
					UNION ALL
					SELECT name FROM `zbackup_av_lle`
					WHERE employee=%s AND leave_type='Annual Vacation'
					  AND transaction_type='Leave Allocation'
					  AND docstatus=1 AND is_carry_forward=0 AND is_expired=0
					  AND leaves>0 AND creation>=%s AND creation<%s
				) x LIMIT 1
				""",
				(
					employee,
					run_date.replace(day=1), month_end,
					employee,
					run_date.replace(day=1), month_end,
				),
			)
		)
	return False


def _post_accrual(la, run_date, note=""):
	la.new_leaves_allocated = flt(la.new_leaves_allocated) + ACCRUAL_LEAVES
	la.save(ignore_permissions=True)
	la.add_comment(
		"Info",
		"{0} {1} posted for {2}{3}".format(
			ACCRUAL_MARKER,
			ACCRUAL_LEAVES,
			run_date.strftime("%Y-%m"),
			(" " + note) if note else "",
		),
	)


def _expected_accruals(doj, run_date):
	"""Count of monthly joining-anniversary dates from doj through run_date."""
	count, year, month = 0, doj.year, doj.month
	while True:
		day = min(doj.day, calendar.monthrange(year, month)[1])
		if date(year, month, day) > run_date:
			break
		count += 1
		month += 1
		if month > 12:
			month, year = 1, year + 1
	return count


def _draft_allocation_exists(employee):
	return frappe.db.exists(
		"Leave Allocation",
		{"employee": employee, "leave_type": "Annual Vacation", "docstatus": ("<", 2)},
	)


def _create_allocation(employee, doj, leaves, run_date):
	la = frappe.new_doc("Leave Allocation")
	la.employee = employee
	la.leave_type = "Annual Vacation"
	la.from_date = doj
	la.to_date = add_years(doj, 70)
	la.carry_forward = 1
	la.new_leaves_allocated = leaves
	la.insert(ignore_permissions=True)
	la.submit()
	la.add_comment(
		"Info",
		"{0} {1} posted for {2}".format(ACCRUAL_MARKER, leaves, run_date.strftime("%Y-%m")),
	)


def _accrue_for_employee(employee, doj, run_date):
	"""Monthly accrual for one employee, as of run_date.

	One perpetual allocation per employee: from_date=DOJ, to_date=DOJ+70 years.

	Joiners on/after ACCRUAL_REGIME_START are held exactly at ACCRUAL_LEAVES per
	monthly joining-anniversary, so a late-created record is back-filled from the
	DOJ instead of silently losing the months before it existed. Older joiners
	keep the original monthly +2.5 step."""
	doj = getdate(doj)
	if not doj or run_date < doj:
		return

	la_name = frappe.db.get_value(
		"Leave Allocation",
		{"employee": employee, "leave_type": "Annual Vacation", "docstatus": 1},
		"name",
		order_by="from_date desc",
	)

	if doj >= ACCRUAL_REGIME_START:
		target = flt(ACCRUAL_LEAVES * _expected_accruals(doj, run_date))
		if not la_name:
			if _draft_allocation_exists(employee):
				return
			_create_allocation(employee, doj, target, run_date)
			return

		la = frappe.get_doc("Leave Allocation", la_name)
		if abs(flt(la.new_leaves_allocated) - target) > 0.001:
			la.new_leaves_allocated = target
			la.save(ignore_permissions=True)
			la.add_comment(
				"Info",
				"{0} set to {1} for {2}".format(ACCRUAL_MARKER, target, run_date.strftime("%Y-%m")),
			)
		return

	# legacy regime: unchanged
	# accrue on/after the monthly joining-anniversary day;
	# 31st-joiners accrue on the last day of shorter months
	last_day = calendar.monthrange(run_date.year, run_date.month)[1]
	if run_date.day < min(doj.day, last_day):
		return

	if not la_name:
		if _draft_allocation_exists(employee):
			return
		_create_allocation(employee, doj, ACCRUAL_LEAVES, run_date)
		return

	if _month_accrual_exists(employee, la_name, run_date):
		return

	_post_accrual(frappe.get_doc("Leave Allocation", la_name), run_date)


@frappe.whitelist()
def create_update_leave_allocation_new():
	run_date = getdate(date.today())
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "date_of_joining"],
	)
	for emp in employees:
		try:
			_accrue_for_employee(emp.name, emp.date_of_joining, run_date)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				title="Annual Vacation accrual failed for {0}".format(emp.name),
				message=frappe.get_traceback(),
			)
	return "Annual Vacation accrual completed"


@frappe.whitelist()
def backfill_missed_accruals(from_date="2026-09-26", to_date="2026-10-01"):
	"""Replay the accrual for each date the cron was down. Idempotent:
	the monthly accrual marker / September ledger check prevents
	double-posting for employees already accrued."""
	run_date = getdate(from_date)
	end_date = getdate(to_date)
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "date_of_joining"],
	)
	while run_date <= end_date:
		for emp in employees:
			try:
				_accrue_for_employee(emp.name, emp.date_of_joining, run_date)
				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
				frappe.log_error(
					title="Annual Vacation accrual backfill failed for {0} on {1}".format(
						emp.name, run_date
					),
					message=frappe.get_traceback(),
				)
		run_date = add_days(run_date, 1)
	return "Annual Vacation accrual backfill completed"





@frappe.whitelist()
def create_av_scheduled_job_type():
	pos = frappe.db.exists('Scheduled Job Type', 'create_update_leave_allocation_new')
	if not pos:
		sjt = frappe.new_doc("Scheduled Job Type")
		sjt.update({
			"method" : 'jgb.jgb.teampro.leave_allocation.create_update_leave_allocation_new',
			"frequency" : 'Cron',
			"cron_format":"00 1 * * *"
		})
		sjt.save(ignore_permissions=True)