import frappe
from frappe import _
from frappe.utils import cstr


# Roles that participate in Sales Order visibility filtering
SALES_ENGINEER_ROLE = "Sales Engineer"
SUPPORT_ENGINEER_ROLE = "Support Engineer"
SALES_MANAGER_ROLE = "Sales Manager"

# Fields on Sales Order
SP_FIELD = "custom_sales_personuser"        # Link -> Sales Person (Sales Engineer)
SUPPORT_FIELD = "custom_support_engineer"   # Link -> User (Support Engineer)
PREPARED_BY_FIELD = "custom_prepared_by"    # Link -> User (Prepared By)


def _get_user_roles(user):
	"""Return the set of role names for the given user."""
	if not user or user == "Administrator":
		return set()
	roles = frappe.db.get_all("Has Role", filters={"parent": user}, pluck="role")
	return set(roles)


def _get_employee_for_user(user):
	"""Return the Employee name linked to this user, or None."""
	if not user:
		return None
	return frappe.db.get_value("Employee", {"user_id": user})


def _get_sales_persons_for_user(user):
	"""Return list of Sales Person names linked to this user.

	Looks up via both Sales Person.custom_user_id and
	Sales Person.employee -> Employee.user_id.
	"""
	if not user:
		return []

	sp_via_user = frappe.db.get_all(
		"Sales Person",
		filters={"custom_user_id": user},
		pluck="name",
	)

	emp = _get_employee_for_user(user)
	sp_via_emp = []
	if emp:
		sp_via_emp = frappe.db.get_all(
			"Sales Person",
			filters={"employee": emp},
			pluck="name",
		)

	return list(set(sp_via_user + sp_via_emp))


def _get_subordinate_employees(employee, visited=None):
	"""Recursively return all Employee names that report (directly or
	transitively) to the given employee.
	"""
	if visited is None:
		visited = set()
	if not employee or employee in visited:
		return []
	visited.add(employee)

	direct_reports = frappe.db.get_all(
		"Employee",
		filters={"reports_to": employee, "status": "Active"},
		pluck="name",
	)

	result = list(direct_reports)
	for emp in direct_reports:
		result.extend(_get_subordinate_employees(emp, visited))

	return result


def _get_sales_persons_for_manager(user):
	"""Return list of Sales Person names for all employees reporting to
	this user (transitively).
	"""
	emp = _get_employee_for_user(user)
	if not emp:
		return []

	subordinates = _get_subordinate_employees(emp)
	if not subordinates:
		return []

	sps = frappe.db.get_all(
		"Sales Person",
		filters={"employee": ["in", subordinates]},
		pluck="name",
	)

	sub_users = frappe.db.get_all(
		"Employee",
		filters={"name": ["in", subordinates]},
		pluck="user_id",
	)
	sub_users = [u for u in sub_users if u]
	if sub_users:
		sps_via_user = frappe.db.get_all(
			"Sales Person",
			filters={"custom_user_id": ["in", sub_users]},
			pluck="name",
		)
		sps = list(set(sps + sps_via_user))

	return sps


def _get_allowed(user, roles):
	"""Compute the allowed Sales Person names and User IDs for this user.

	Returns (allowed_sps, allowed_users) where:
	- allowed_sps: set of Sales Person names the user can see
	- allowed_users: set of User IDs (for support engineer matching)
	"""
	allowed_sps = set()
	allowed_users = set()

	if SALES_ENGINEER_ROLE in roles:
		allowed_sps.update(_get_sales_persons_for_user(user))

	if SALES_MANAGER_ROLE in roles:
		allowed_sps.update(_get_sales_persons_for_manager(user))

	if SUPPORT_ENGINEER_ROLE in roles:
		if user:
			allowed_users.add(user)

	return allowed_sps, allowed_users


def _has_relevant_roles(roles):
	"""Check if the user has any of the roles we manage."""
	relevant = {SALES_ENGINEER_ROLE, SUPPORT_ENGINEER_ROLE, SALES_MANAGER_ROLE}
	return bool(roles & relevant)


def get_permission_query_conditions(user=None, doctype="Sales Order"):
	"""Hook: permission_query_conditions for Sales Order.

	Returns a SQL WHERE clause fragment that restricts the list view
	based on the user's role and hierarchy.
	"""
	if not user:
		user = frappe.session.user

	if not user or user == "Administrator":
		return ""

	roles = _get_user_roles(user)
	if not _has_relevant_roles(roles):
		return ""

	allowed_sps, allowed_users = _get_allowed(user, roles)

	conditions = []

	if allowed_sps:
		escaped = ", ".join(
			frappe.db.escape(cstr(sp), percent=False) for sp in allowed_sps
		)
		conditions.append(
			f"`tabSales Order`.`{SP_FIELD}` in ({escaped})"
		)

	if allowed_users:
		escaped_user = frappe.db.escape(cstr(user), percent=False)
		conditions.append(
			f"`tabSales Order`.`{SUPPORT_FIELD}` = {escaped_user}"
		)
		conditions.append(
			f"`tabSales Order`.`{PREPARED_BY_FIELD}` = {escaped_user}"
		)

	if not conditions:
		# User has relevant roles but no linked SP/Employee — deny all
		return "1=0"

	return "(" + " or ".join(conditions) + ")"


def has_permission(doc, ptype="read", user=None, debug=False):
	"""Hook: has_permission for Sales Order.

	Controllers can only DENY, not grant. So:
	- Return False if user has relevant roles but the doc doesn't match.
	- Return None (no opinion) otherwise, letting standard checks proceed.
	"""
	if not user:
		user = frappe.session.user

	if ptype != "read":
		return None

	if not doc or doc.get("doctype") != "Sales Order":
		return None

	if not user or user == "Administrator":
		return None

	roles = _get_user_roles(user)
	if not _has_relevant_roles(roles):
		return None

	allowed_sps, allowed_users = _get_allowed(user, roles)

	# Check Sales Person match
	doc_sp = cstr(doc.get(SP_FIELD) or "")
	if allowed_sps and doc_sp and doc_sp in allowed_sps:
		return None  # Match — let standard permissions proceed

	# Check Support Engineer / Prepared By match
	doc_support = cstr(doc.get(SUPPORT_FIELD) or "")
	doc_prepared = cstr(doc.get(PREPARED_BY_FIELD) or "")
	if allowed_users:
		if doc_support and doc_support in allowed_users:
			return None  # Match
		if doc_prepared and doc_prepared in allowed_users:
			return None  # Match

	# User has relevant roles but nothing matched — deny
	return False
