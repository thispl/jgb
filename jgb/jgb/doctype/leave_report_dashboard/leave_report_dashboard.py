# Copyright (c) 2025, abdulla.pi@groupteampro.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class LeaveReportDashboard(Document):
	pass


@frappe.whitelist()
def get_leave_details(employee, year):
    emp = frappe.db.get_value("Employee",employee,["employee", "employee_name", "department", "designation"], as_dict=True)
    if not emp:
        return ""
    
    from_date = f"{year}-01-01"
    to_date = f"{year}-12-31"

    leaves = frappe.get_all("Leave Application",filters={"employee": employee,"from_date": ["between", [from_date, to_date]], "docstatus":["!=",2] , "workflow_state":["!=", "Rejected"]},fields=["from_date","to_date","total_leave_days","leave_type","description"], order_by="from_date")
    html = f"""
    <div style="padding:15px;">

        <h3 style="margin-bottom:15px;">
            Leave Details for Year - {year}
        </h3>

        <table class="table table-bordered" style="width:100%;margin-bottom:20px;">
            <tr>
                <th style="width:20%;">Employee ID</th>
                <td style="width:30%;">{emp.employee}</td>
                <th style="width:20%;">Employee Name</th>
                <td style="width:30%;">{emp.employee_name}</td>
            </tr>
            <tr>
                <th>Department</th>
                <td>{emp.department or '-'}</td>
                <th>Designation</th>
                <td>{emp.designation or '-'}</td>
            </tr>
        </table>

        <table class="table table-bordered table-striped" style="width:100%;">
            <thead>
                <tr>
                    <th>S.No</th>
                    <th>From Date</th>
                    <th>To Date</th>
                    <th>No. of Days</th>
                    <th>Type of Leave</th>
                    <th>Reason</th>
                </tr>
            </thead>
            <tbody>
    """

    if leaves:
        for idx, l in enumerate(leaves, start=1):
            html += f"""
                <tr>
                    <td>{idx}</td>
                    <td>{l.from_date}</td>
                    <td>{l.to_date}</td>
                    <td>{l.total_leave_days}</td>
                    <td>{l.leave_type}</td>
                    <td>{l.description or '-'}</td>
                </tr>
            """
    else:
        html += """
            <tr>
                <td colspan="6" style="text-align:center;">
                    No Leave Records Found
                </td>
            </tr>
        """

    html += """
            </tbody>
        </table>

    </div>
    """

    return html
