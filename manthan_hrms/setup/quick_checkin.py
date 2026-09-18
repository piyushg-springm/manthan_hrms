"""Checks for the one-click check-in card on the HR workspace (manthan_hrms.attendance.checkin).

    bench --site prudeno-prod.localhost execute manthan_hrms.setup.quick_checkin.verify_quick_checkin

Runs as a real employee login and removes the check-ins it creates.
"""

import frappe

from manthan_hrms.attendance.checkin import get_quick_checkin_status, quick_checkin
from manthan_hrms.setup.day1 import TEST_HR_USER
from manthan_hrms.setup.day2 import email_for
from manthan_hrms.setup.day4 import get_boot_for, print_checks


def as_user(user, fn, *args, **kwargs):
	frappe.set_user(user)
	try:
		return fn(*args, **kwargs)
	finally:
		frappe.set_user("Administrator")


def verify_quick_checkin():
	employee_user = email_for("Priya", "Nair")
	employee = frappe.db.get_value("Employee", {"user_id": employee_user}, "name")
	before = set(frappe.get_all("Employee Checkin", {"employee": employee}, pluck="name"))
	checks = []
	try:
		checks.append(("employee boot has quick check-in", bool(get_boot_for(employee_user).get("manthan_quick_checkin"))))
		checks.append(("HR user without Employee has no card", not get_boot_for(TEST_HR_USER).get("manthan_quick_checkin")))
		checks.append(("non-Manthan user has no card", not get_boot_for("Administrator").get("manthan_quick_checkin")))

		status = as_user(employee_user, get_quick_checkin_status)
		checks.append(("status resolves the session employee", status["employee"] == employee))
		first = status["next_log_type"]
		second = "OUT" if first == "IN" else "IN"

		after_first = as_user(employee_user, quick_checkin, first)
		checks.append((f"{first} logged at server time", after_first["last_log"].log_type == first))
		checks.append(("next action flips", after_first["next_log_type"] == second))
		after_second = as_user(employee_user, quick_checkin, second)
		checks.append((f"{second} logged", after_second["last_log"].log_type == second))

		try:
			as_user(employee_user, quick_checkin, "LUNCH")
			checks.append(("invalid log type rejected", False))
		except frappe.ValidationError:
			checks.append(("invalid log type rejected", True))

		try:
			as_user(TEST_HR_USER, quick_checkin, "IN")
			checks.append(("user without Employee cannot check in", False))
		except frappe.PermissionError:
			checks.append(("user without Employee cannot check in", True))
	finally:
		for name in set(frappe.get_all("Employee Checkin", {"employee": employee}, pluck="name")) - before:
			frappe.delete_doc("Employee Checkin", name, ignore_permissions=True, force=True)
		frappe.db.commit()
		frappe.clear_messages()
	print_checks(checks)
