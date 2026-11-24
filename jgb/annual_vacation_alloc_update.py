"""One-off data fix: Annual Vacation leave allocations.

Case 1 - employee has exactly ONE submitted Annual Vacation allocation:
    set to_date = 2100-12-31 on the allocation and its linked
    Leave Ledger Entry rows.  (DONE - 62 employees)

Case 2 - >1 submitted allocation, NO Leave Application in any docstatus:
    cancel the most recent allocation, transfer its new_leaves_allocated
    to the previous allocation, update to_date.  (DONE - 26 employees)

Case 3 - >1 submitted allocation AND at least one Leave Application:
    same as case 2, except the cancel may need the
    validate_leave_allocation_against_leave_application guard bypassed
    (application ledger rows reference the Leave Application - they are
    never touched by the cancel delete).

Run via:
    bench --site erp.jgbksa.com execute jgb.annual_vacation_alloc_update.classify
    bench --site erp.jgbksa.com execute \
        jgb.annual_vacation_alloc_update.run_for_employee \
        --kwargs "{'employee': 'HR-EMP-00001'}"
    bench --site erp.jgbksa.com execute jgb.annual_vacation_alloc_update.run_case3_all
"""

import frappe
from frappe.utils import flt

import hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry as lle_module
from hrms.hr.utils import create_additional_leave_ledger_entry

LEAVE_TYPE = "Annual Vacation"
TARGET_TO_DATE = "2100-12-31"


def _submitted_allocations():
    return frappe.db.sql(
        """
        SELECT name, employee, employee_name, from_date, to_date,
               carry_forward, expired, new_leaves_allocated,
               total_leaves_allocated
        FROM `tabLeave Allocation`
        WHERE leave_type = %s AND docstatus = 1
        ORDER BY employee, from_date
        """,
        LEAVE_TYPE,
        as_dict=True,
    )


def _by_employee():
    by_employee = {}
    for row in _submitted_allocations():
        by_employee.setdefault(row.employee, []).append(row)
    return by_employee


def _employees_with_leave_applications():
    """Employees with an Annual Vacation Leave Application in ANY docstatus
    (draft 0, submitted 1, cancelled 2 all count as 'applied')."""
    rows = frappe.db.sql(
        """
        SELECT DISTINCT employee
        FROM `tabLeave Application`
        WHERE leave_type = %s
        """,
        LEAVE_TYPE,
    )
    return {r[0] for r in rows}


def classify():
    """Bucket employees into the three cases. Returns a summary dict."""
    by_employee = _by_employee()
    app_employees = _employees_with_leave_applications()

    single, multi_no_app, multi_with_app = [], [], []
    for emp, allocs in by_employee.items():
        if len(allocs) == 1:
            single.append(emp)
        elif emp in app_employees:
            multi_with_app.append(emp)
        else:
            multi_no_app.append(emp)

    out = {
        "single_allocation": sorted(single),
        "multi_no_leave_application": sorted(multi_no_app),
        "multi_with_leave_application": sorted(multi_with_app),
    }
    print(
        "single={} multi_no_app={} multi_with_app={}".format(
            len(single), len(multi_no_app), len(multi_with_app)
        )
    )
    return out


def _state(alloc_name):
    alloc = frappe.db.get_value(
        "Leave Allocation",
        alloc_name,
        ["name", "employee", "from_date", "to_date", "docstatus",
         "expired", "new_leaves_allocated", "total_leaves_allocated",
         "carry_forward"],
        as_dict=True,
    )
    ledger = frappe.db.sql(
        """
        SELECT name, from_date, to_date, leaves, is_carry_forward,
               is_expired, docstatus
        FROM `tabLeave Ledger Entry`
        WHERE transaction_type = 'Leave Allocation'
          AND transaction_name = %s
        ORDER BY name
        """,
        alloc_name,
        as_dict=True,
    )
    return alloc, ledger


def _print_state(alloc_name, label):
    alloc, ledger = _state(alloc_name)
    print("\n--- {} : {} ---".format(label, alloc_name))
    if alloc:
        print(
            "alloc: emp={} {} -> {} docstatus={} expired={} new={} total={} cf={}".format(
                alloc.employee, alloc.from_date, alloc.to_date, alloc.docstatus,
                alloc.expired, alloc.new_leaves_allocated,
                alloc.total_leaves_allocated, alloc.carry_forward,
            )
        )
    else:
        print("alloc: <missing>")
    for l in ledger:
        print(
            "  lle {}: {} -> {} leaves={} cf={} expired={} ds={}".format(
                l.name, l.from_date, l.to_date, l.leaves,
                l.is_carry_forward, l.is_expired, l.docstatus,
            )
        )


def _update_to_date(alloc_name):
    """Set to_date=TARGET on the allocation and all its linked LLE rows.
    Resets the `expired` flag if no expiry ledger rows remain for it."""
    frappe.db.set_value(
        "Leave Allocation", alloc_name, "to_date", TARGET_TO_DATE,
        update_modified=False,
    )
    frappe.db.sql(
        """
        UPDATE `tabLeave Ledger Entry`
        SET to_date = %s
        WHERE transaction_type = 'Leave Allocation'
          AND transaction_name = %s
        """,
        (TARGET_TO_DATE, alloc_name),
    )
    has_expired_rows = frappe.db.count(
        "Leave Ledger Entry",
        {"transaction_type": "Leave Allocation",
         "transaction_name": alloc_name, "is_expired": 1},
    )
    frappe.db.set_value(
        "Leave Allocation", alloc_name, "expired", 1 if has_expired_rows else 0,
        update_modified=False,
    )


def _cancel_allocation(alloc_name):
    """Cancel a Leave Allocation via the standard doc.cancel() flow.

    HRMS blocks cancelling an allocation when a Leave Application ledger
    entry falls inside the allocation's own window. Application ledger
    rows reference the Leave Application (not this allocation), so the
    cancel delete never removes them -- the guard is bypassed only for
    the duration of this cancel. Returns the overlapping-app count."""
    doc = frappe.get_doc("Leave Allocation", alloc_name)
    overlapping = frappe.db.count(
        "Leave Ledger Entry",
        {
            "employee": doc.employee,
            "leave_type": doc.leave_type,
            "transaction_type": "Leave Application",
            "from_date": (">=", doc.from_date),
            "to_date": ("<=", doc.to_date),
        },
    )
    if overlapping:
        orig = lle_module.validate_leave_allocation_against_leave_application
        lle_module.validate_leave_allocation_against_leave_application = (
            lambda *a, **k: None
        )
        try:
            doc.cancel()
        finally:
            lle_module.validate_leave_allocation_against_leave_application = orig
    else:
        doc.cancel()
    return overlapping


def _process_multi(allocs, verbose=False):
    """Cancel the most recent allocation, transfer its total allocated
    leaves to the previous (surviving) allocation, update to_date."""
    allocs = sorted(allocs, key=lambda a: a.from_date)
    cancel_alloc = allocs[-1]
    survivor = allocs[-2]

    if verbose:
        _print_state(cancel_alloc.name, "BEFORE (to cancel)")
        _print_state(survivor.name, "BEFORE (survivor)")

    # Transfer the cancelled allocation's FULL total (new + carry-forward
    # unused). Using only new_leaves_allocated silently drops the carry-forward
    # (unused_leaves) the employee is entitled to.
    cancelled_new_leaves = flt(cancel_alloc.total_leaves_allocated) or flt(
        cancel_alloc.new_leaves_allocated
    )
    overlapping = _cancel_allocation(cancel_alloc.name)
    if verbose and overlapping:
        print(
            "  ({} application ledger row(s) inside cancelled window - "
            "bypassed link guard; application entries untouched)".format(
                overlapping
            )
        )

    if verbose:
        _print_state(cancel_alloc.name, "AFTER CANCEL")

    if cancelled_new_leaves:
        survivor_doc = frappe.get_doc("Leave Allocation", survivor.name)
        survivor_doc.db_set(
            "new_leaves_allocated",
            flt(survivor_doc.new_leaves_allocated) + cancelled_new_leaves,
            update_modified=False,
        )
        survivor_doc.db_set(
            "total_leaves_allocated",
            flt(survivor_doc.total_leaves_allocated) + cancelled_new_leaves,
            update_modified=False,
        )
        _update_to_date(survivor.name)
        # keep the in-memory doc in sync so the additional ledger entry
        # passes validate (from_date must precede to_date)
        survivor_doc.to_date = TARGET_TO_DATE
        create_additional_leave_ledger_entry(
            survivor_doc, cancelled_new_leaves, survivor.from_date
        )
        survivor_doc.add_comment(
            "Info",
            "{0} leaves transferred from cancelled allocation {1}".format(
                cancelled_new_leaves, cancel_alloc.name
            ),
        )
    else:
        _update_to_date(survivor.name)

    # any further survivors (employees with >2 allocs) get to_date only
    for extra in allocs[:-2]:
        _update_to_date(extra.name)

    if verbose:
        _print_state(survivor.name, "AFTER (survivor)")


def run_for_employee(employee, verbose=True):
    """Process one employee (multi-allocation cases). For verification."""
    allocs = _by_employee().get(employee, [])
    if len(allocs) < 2:
        print("{} has {} submitted allocation(s) - nothing to do".format(
            employee, len(allocs)))
        return
    _process_multi(allocs, verbose=verbose)
    frappe.db.commit()
    print("\nDone - committed for {}.".format(employee))


def run_case3_all(exclude=("HR-EMP-00001",)):
    groups = classify()
    by_employee = _by_employee()

    for emp in groups["multi_with_leave_application"]:
        if emp in exclude:
            continue
        _process_multi(by_employee[emp])
        print("case3 done {}".format(emp))

    frappe.db.commit()
    print("\ncase3 done")


def dry_run_accrual(employee="HR-EMP-00001", run_date=None):
    """Run the real accrual path for one employee inside a transaction,
    print the resulting state, then roll back. Nothing is committed."""
    from frappe.utils import getdate
    from jgb.jgb.teampro.leave_allocation import _accrue_for_employee

    doj = frappe.db.get_value("Employee", employee, "date_of_joining")
    rd = getdate(run_date) if run_date else getdate()
    print("employee={} doj={} run_date={}".format(employee, doj, rd))

    _accrue_for_employee(employee, doj, rd)

    allocs = frappe.db.sql(
        """SELECT name, from_date, to_date, docstatus,
                  new_leaves_allocated, total_leaves_allocated
           FROM `tabLeave Allocation`
           WHERE employee=%s AND leave_type='Annual Vacation'
           ORDER BY from_date""",
        employee, as_dict=True)
    for a in allocs:
        print("  alloc {}: {} -> {} ds={} new={} total={}".format(
            a.name, a.from_date, a.to_date, a.docstatus,
            a.new_leaves_allocated, a.total_leaves_allocated))

    lles = frappe.db.sql(
        """SELECT name, from_date, to_date, leaves, transaction_type,
                  transaction_name, docstatus
           FROM `tabLeave Ledger Entry`
           WHERE employee=%s AND leave_type='Annual Vacation'
           ORDER BY name""",
        employee, as_dict=True)
    for l in lles:
        print("  lle {}: {} -> {} leaves={} via {}:{} ds={}".format(
            l.name, l.from_date, l.to_date, l.leaves,
            l.transaction_type, l.transaction_name, l.docstatus))

    comments = frappe.get_all(
        "Comment",
        {"reference_doctype": "Leave Allocation",
         "comment_type": "Info",
         "content": ("like", "%accrual%")},
        ["reference_name", "content"])
    for c in comments:
        if frappe.db.get_value("Leave Allocation", c.reference_name, "employee") == employee:
            print("  comment on {}: {}".format(c.reference_name, c.content))

    frappe.db.rollback()
    print("\n*** ROLLED BACK - nothing committed ***")
