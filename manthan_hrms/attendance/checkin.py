"""One-click self check-in from the HR workspace (public/js/quick_checkin.js).

The employee and the log time come from the session and the server clock, never from the client, so
a user can only log themselves at the current time. The insert keeps normal permissions, so hrms'
own validation (duplicates, shift fetch, geolocation radius) still applies.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

LOG_TYPES = ("IN", "OUT")


def get_session_employee(user=None):
	return frappe.db.get_value(
		"Employee",
		{"user_id": user or frappe.session.user, "status": "Active"},
		["name", "first_name", "employee_name"],
		as_dict=True,
	)


def is_self_checkin_allowed():
	# the hrms PWA's switch for employees logging their own check-ins
	return bool(frappe.db.get_single_value("HR Settings", "allow_employee_checkin_from_mobile_app"))


@frappe.whitelist()
def get_quick_checkin_status():
	employee = get_session_employee()
	if not employee:
		return {"employee": None}

	last_log = frappe.db.get_value(
		"Employee Checkin",
		{"employee": employee.name},
		["name", "log_type", "time"],
		order_by="time desc, creation desc",
		as_dict=True,
	)
	return {
		"employee": employee.name,
		"first_name": employee.first_name or employee.employee_name,
		"allowed": is_self_checkin_allowed(),
		"last_log": last_log,
		# same rule as the hrms PWA: alternate from the latest log
		"next_log_type": "OUT" if last_log and last_log.log_type == "IN" else "IN",
		"geolocation_required": bool(frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")),
	}


@frappe.whitelist(methods=["POST"])
def quick_checkin(log_type, latitude=None, longitude=None):
	if log_type not in LOG_TYPES:
		frappe.throw(_("Log type must be IN or OUT."))
	if not is_self_checkin_allowed():
		frappe.throw(_("Self check-in is turned off in HR Settings."), frappe.PermissionError)

	employee = get_session_employee()
	if not employee:
		frappe.throw(_("No active employee is linked to your user."), frappe.PermissionError)

	frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee.name,
			"log_type": log_type,
			"time": now_datetime(),
			"latitude": latitude,
			"longitude": longitude,
		}
	).insert()
	return get_quick_checkin_status()
