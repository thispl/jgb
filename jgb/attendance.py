"""Three-shift attendance for JGB - manual first-IN/last-OUT marking.

Shifts (employees point at one via Employee.default_shift):
	Office Shift                    Sun-Thu  08:00-17:00  (JGBIL list: Fri+Sat off)
	Sales Shift                     Sun-Thu  07:30-16:00  (JGBIL list: Fri+Sat off;
	                                Saturdays are ad-hoc - worked Saturdays mark
	                                attendance + count toward the week, missed
	                                Saturdays are never marked Absent)
	Warehouse & Installation Shift  Sat-Thu  07:30-16:30  (JGB Six Day: Fri off only)

Status per day: hours < 4 -> Absent, 4h -> Half Day, full day -> Present
(full day = 9h for office/warehouse, 8.5h for sales).
An approved Attendance Request covering the date credits +4h (half_day_date = date)
or a full day otherwise. Sales employees additionally need 42.5h/week
(Sun-Sat, week starting Sunday): after the week is covered by a run, a
shortfall downgrades the shortest days (Present -> Half Day -> Absent).

One-time setup (creates JGB Six Day holiday list + the three Shift Types):
	bench --site erp.jgbksa.com execute jgb.attendance.setup

Then set Employee.default_shift on each employee (employee master).

Mark attendance - does not run by itself, invoke when needed:
	bench --site erp.jgbksa.com execute jgb.attendance.mark_att                 # today
	bench --site erp.jgbksa.com execute jgb.attendance.mark_att --kwargs "{'date': '2026-11-23'}"
	bench --site erp.jgbksa.com execute jgb.attendance.mark_att_manual \
		--kwargs "{'from_date': '2026-11-01', 'to_date': '2026-11-23'}"
"""

from datetime import datetime, time as dt_time, timedelta

import frappe
from frappe.utils import add_days, date_diff, getdate, time_diff_in_hours, today

WORKING_HOURS = 9
SALES_DAILY_HOURS = 8.5
HALF_DAY_HOURS = 4
SALES_SHIFT = "Sales Shift"
SALES_WEEKLY_HOURS = 42.5  # Sun-Sat week (Sun-Thu + ad-hoc Sat); 5-day base
FIVE_DAY_LIST = "JGBIL"  # Fri + Sat weekly off -> Sun-Thu
SIX_DAY_LIST = "JGB Six Day"  # Friday weekly off only -> Sat-Thu

SHIFTS = {
	"Office Shift": {"start": dt_time(8, 0), "hours": WORKING_HOURS, "holiday_list": FIVE_DAY_LIST},
	"Sales Shift": {"start": dt_time(7, 30), "hours": SALES_DAILY_HOURS, "holiday_list": FIVE_DAY_LIST},
	"Warehouse & Installation Shift": {
		"start": dt_time(7, 30),
		"hours": WORKING_HOURS,
		"holiday_list": SIX_DAY_LIST,
	},
}
SHIFT_HOLIDAY = {name: cfg["holiday_list"] for name, cfg in SHIFTS.items()}

# kept on the Shift Type docs for reference; auto attendance stays OFF,
# marking is done by mark_att() below
COMMON = {
	"determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
	"working_hours_calculation_based_on": "First Check-in and Last Check-out",
	"working_hours_threshold_for_absent": HALF_DAY_HOURS,
	"begin_check_in_before_shift_start_time": 90,
	"allow_check_out_after_shift_end_time": 90,
	"enable_auto_attendance": 0,
	"auto_update_last_sync": 0,
	"mark_auto_attendance_on_holidays": 1,
}


def _end(start, hours=WORKING_HOURS):
	return (datetime.combine(getdate("2000-01-01"), start) + timedelta(hours=hours)).time()


def _sync_six_day_list():
	"""JGB Six Day = JGBIL minus Saturday weekly-offs (Friday off + same public holidays)."""
	src = frappe.get_doc("Holiday List", FIVE_DAY_LIST)
	wanted = [
		h for h in src.holidays if not (h.weekly_off and getdate(h.holiday_date).weekday() == 5)
	]
	if frappe.db.exists("Holiday List", SIX_DAY_LIST):
		doc = frappe.get_doc("Holiday List", SIX_DAY_LIST)
		have = {getdate(h.holiday_date) for h in doc.holidays}
		for h in wanted:
			if getdate(h.holiday_date) not in have:
				doc.append(
					"holidays",
					{"holiday_date": h.holiday_date, "description": h.description, "weekly_off": h.weekly_off},
				)
		doc.to_date = max(getdate(doc.to_date), getdate(src.to_date))
		doc.save()
	else:
		doc = frappe.new_doc("Holiday List")
		doc.holiday_list_name = SIX_DAY_LIST
		doc.from_date, doc.to_date = src.from_date, src.to_date
		for h in wanted:
			doc.append(
				"holidays",
				{"holiday_date": h.holiday_date, "description": h.description, "weekly_off": h.weekly_off},
			)
		doc.insert()
	return doc.name


def setup():
	"""Create/update the JGB Six Day holiday list and the three Shift Types. Idempotent."""
	_sync_six_day_list()
	for name, cfg in SHIFTS.items():
		if frappe.db.exists("Shift Type", name):
			doc = frappe.get_doc("Shift Type", name)
		else:
			doc = frappe.new_doc("Shift Type")
			doc.__newname = name
		doc.update(
			{
				"start_time": cfg["start"],
				"end_time": _end(cfg["start"], cfg["hours"]),
				"working_hours_threshold_for_half_day": cfg["hours"],
				"holiday_list": cfg["holiday_list"],
				**COMMON,
			}
		)
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return list(SHIFTS)


# ---------------------------------------------------------------- marking


@frappe.whitelist()
def mark_att(date=None):
	"""Mark attendance for `date` (default today) - only employees with a default_shift."""
	return mark_att_manual(date or today(), date or today())


@frappe.whitelist()
def mark_att_manual(from_date, to_date):
	for date in get_dates(from_date, to_date):
		_mark_checkin_day(date)
		mark_absent(date)
	_correct_completed_sales_weeks(from_date, to_date)
	frappe.db.commit()


def _mark_checkin_day(date):
	"""Mark attendance for shift-assigned employees who punched on `date`."""
	employees = frappe.db.sql(
		"select distinct employee from `tabEmployee Checkin` where date(time) = %s",
		(date,),
		pluck="employee",
	)
	for employee in employees:
		if frappe.db.exists(
			"Employee",
			{
				"name": employee,
				"status": "Active",
				"date_of_joining": ("<=", date),
				"default_shift": ("is", "set"),
			},
		):
			mark_attendance_for_employee(employee, date)


def scheduled_mark_att():
	"""Every-10-min cron job.

	- today: refresh punched employees only (absents would be premature -
	  most people haven't punched out yet)
	- yesterday: full pass incl. mark_absent + sales weekly correction when
	  the week closes (Saturday inside the range)
	"""
	yesterday = add_days(today(), -1)
	_mark_checkin_day(today())
	mark_att_manual(yesterday, yesterday)


def mark_attendance_for_employee(employee, att_date):
	att_date = getdate(att_date)
	checkins = frappe.db.sql(
		"select name, time from `tabEmployee Checkin` where employee = %s and date(time) = %s order by time",
		(employee, att_date),
		as_dict=1,
	)
	in_time = checkins[0].time if checkins else None
	out_time = checkins[-1].time if len(checkins) > 1 else None

	hours = time_diff_in_hours(out_time, in_time) if in_time and out_time else 0.0
	shift = frappe.db.get_value("Employee", employee, "default_shift")
	full_day = SALES_DAILY_HOURS if shift == SALES_SHIFT else WORKING_HOURS

	# credit an approved Attendance Request covering the day
	ar = frappe.db.exists(
		"Attendance Request",
		{
			"employee": employee,
			"docstatus": 1,
			"from_date": ("<=", att_date),
			"to_date": (">=", att_date),
		},
	)
	if ar:
		half_day_date = frappe.db.get_value("Attendance Request", ar, "half_day_date")
		hours += HALF_DAY_HOURS if getdate(half_day_date) == att_date else full_day

	status = _status(hours, shift)

	att_name = frappe.db.exists(
		"Attendance",
		{"employee": employee, "attendance_date": att_date, "docstatus": ("!=", 2)},
	)
	if att_name:
		# don't clobber leave/WFH rows - only refresh times + hours
		cur_status = frappe.db.get_value("Attendance", att_name, "status")
		frappe.db.set_value("Attendance", att_name, "in_time", in_time)
		frappe.db.set_value("Attendance", att_name, "out_time", out_time)
		frappe.db.set_value("Attendance", att_name, "working_hours", hours)
		frappe.db.set_value("Attendance", att_name, "shift", shift)
		if cur_status not in ("On Leave", "Work From Home"):
			frappe.db.set_value("Attendance", att_name, "status", status)
	else:
		att = frappe.new_doc("Attendance")
		att.employee = employee
		att.attendance_date = att_date
		att.shift = shift
		att.status = status
		att.in_time = in_time
		att.out_time = out_time
		att.working_hours = hours
		att.insert(ignore_permissions=True)
		att.submit()
		att_name = att.name

	for c in checkins:
		frappe.db.set_value("Employee Checkin", c.name, "attendance", att_name)
		frappe.db.set_value("Employee Checkin", c.name, "skip_auto_attendance", 1)
	return att_name


def _status(hours, shift=None):
	full_day = SALES_DAILY_HOURS if shift == SALES_SHIFT else WORKING_HOURS
	if hours < HALF_DAY_HOURS:
		return "Absent"
	if hours < full_day:
		return "Half Day"
	return "Present"


def mark_absent(date):
	for emp in frappe.get_all(
		"Employee",
		filters={
			"status": "Active",
			"date_of_joining": ("<=", date),
			"default_shift": ("is", "set"),
		},
		fields=["name", "default_shift"],
	):
		if check_holiday(date, emp.name):
			continue
		if frappe.db.exists(
			"Attendance", {"employee": emp.name, "attendance_date": date, "docstatus": ("!=", 2)}
		):
			continue
		att = frappe.new_doc("Attendance")
		att.employee = emp.name
		att.attendance_date = date
		att.shift = emp.default_shift
		att.status = "Absent"
		att.insert(ignore_permissions=True)
		att.submit()


def get_dates(from_date, to_date):
	no_of_days = date_diff(add_days(to_date, 1), from_date)
	return [add_days(from_date, i) for i in range(no_of_days)]


def _sales_week_start(date):
	"""Sunday-based sales week (Sun-Sat; Sun-Thu working, Fri off, Sat ad-hoc)."""
	return getdate(date) - timedelta(days=(getdate(date).weekday() + 1) % 7)


def _correct_completed_sales_weeks(from_date, to_date):
	"""After a sales week (Sun-Sat) ends, downgrade if the week's hours < 42.5.

	Only weeks whose Saturday <= to_date are touched, so runs never fire
	mid-week. Shortfall converts to half-day steps (each ~4.25h) applied to
	the shortest-hour days first: Present -> Half Day -> Absent.
	"""
	employees = frappe.get_all(
		"Employee",
		filters={"default_shift": SALES_SHIFT, "status": "Active"},
		fields=["name", "date_of_joining"],
	)
	if not employees:
		return
	week_start = _sales_week_start(from_date)
	while week_start + timedelta(days=6) <= getdate(to_date):
		week_end = week_start + timedelta(days=6)
		for emp in employees:
			if emp.date_of_joining and getdate(emp.date_of_joining) > week_start:
				continue  # partial first week - skip
			_sales_weekly_correction(emp.name, week_start, week_end)
		week_start += timedelta(days=7)


def _sales_weekly_correction(employee, week_start, week_end):
	rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"shift": SALES_SHIFT,
			"attendance_date": ("between", [week_start, week_end]),
			"docstatus": 1,
			"status": ("in", ["Present", "Half Day", "Absent"]),
		},
		fields=["name", "status", "working_hours"],
	)
	week_hours = sum(r.working_hours or 0 for r in rows)
	if week_hours >= SALES_WEEKLY_HOURS:
		return
	# ponytail: 42.5h target is flat - public-holiday or leave weeks are NOT
	# pro-rated; pro-rate here if payroll asks for it
	deficit = SALES_WEEKLY_HOURS - week_hours
	units = round(deficit / (SALES_WEEKLY_HOURS / 10))  # half-day steps (4.25h)
	downgrade = {"Present": "Half Day", "Half Day": "Absent"}
	for row in sorted(rows, key=lambda r: r.working_hours or 0):
		while units > 0 and row.status in downgrade:
			row.status = downgrade[row.status]
			frappe.db.set_value("Attendance", row.name, "status", row.status)
			units -= 1
		if units <= 0:
			break


def check_holiday(date, emp):
	"""Weekly off / holiday for the employee per their shift's holiday list."""
	default_shift, holiday_list = frappe.db.get_value(
		"Employee", emp, ["default_shift", "holiday_list"]
	)
	holiday_list = SHIFT_HOLIDAY.get(default_shift) or holiday_list or FIVE_DAY_LIST
	holiday = frappe.db.sql(
		"""select h.weekly_off from `tabHoliday` h
		join `tabHoliday List` l on h.parent = l.name
		where l.name = %s and h.holiday_date = %s""",
		(holiday_list, date),
	)
	if holiday:
		return "WW" if holiday[0][0] else "HH"


def demo():
	assert str(_end(dt_time(8, 0))) == "17:00:00"
	assert str(_end(dt_time(7, 30))) == "16:30:00"
	assert str(_end(dt_time(7, 30), SALES_DAILY_HOURS)) == "16:00:00"
	assert _status(3.9) == "Absent"
	assert _status(4) == "Half Day"
	assert _status(9) == "Present"
	assert _status(8.5, SALES_SHIFT) == "Present"
	assert _status(8.5, "Office Shift") == "Half Day"
	assert _sales_week_start(getdate("2026-11-22")) == getdate("2026-11-22")  # Sun -> itself
	assert _sales_week_start(getdate("2026-11-20")) == getdate("2026-11-15")  # Fri -> prev Sun
	assert _sales_week_start(getdate("2026-11-21")) == getdate("2026-11-15")  # Sat -> prev Sun
	assert len(SHIFTS) == 3
	return "ok"
