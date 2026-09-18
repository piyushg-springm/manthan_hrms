"""Pilot Day 4 setup (Sprint 7 + Sprint 8).

Sprint 7 (Prudeno Wealth): client branding on the desk and a walkthrough of everything built on
Days 1-3, run as the users who use it. On this shared site the brand is limited to Manthan HR users
(manthan_hrms.branding.boot), so the other apps' users and the login page are unchanged.

Sprint 8: the manthan_hrms app is the package (setup code, fixtures, custom fields, DocType,
branding); the client comes from site_config.json (manthan_hrms.setup.clients). On a new client
site it completes the setup wizard with the client company, applies the Day 1 module restrictions
and HR user, and brands the whole site.

    bench --site prudeno-prod.localhost clear-cache
    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day4.run_sprint7
    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day4.verify_sprint7

    bench --site nswealth.localhost execute manthan_hrms.setup.day4.run_sprint8
    bench --site nswealth.localhost execute manthan_hrms.setup.day4.verify_sprint8
"""

import contextlib
import io
import os
import re

import frappe
from frappe.utils import now_datetime

from manthan_hrms.branding.boot import apply_site_branding, get_desk_brand, is_dedicated_site
from manthan_hrms.branding.brands import MIN_TEXT_CONTRAST, contrast_with_white, get_brand
from manthan_hrms.setup.day1 import (
	ALLOWED_APPS,
	CLIENT,
	COMPANY_ABBR,
	COMPANY_NAME,
	MODULE_PROFILE,
	TEST_HR_USER,
	YEAR,
	run_sprint1,
)
from manthan_hrms.setup.clients import CLIENTS
from manthan_hrms.setup.day3 import REVIEWER_ROLE

FRAPPE_DEFAULT_PRIMARY = "#171717"  # --gray-900, Frappe's default --btn-primary / --primary-color
REQUIRED_APPS = ("erpnext", "hrms", "india_payroll", "manthan_hrms")
BLOCKED_FOR_HR = ("Selling", "Buying", "Stock", "Accounts", "Manufacturing", "CRM")

# Day 2 logins used for the employee-side walkthrough
WALKTHROUGH_EMPLOYEE = "Priya"
WALKTHROUGH_MANAGER = ("Kavya", "Siddharth")  # Siddharth reports to Kavya
HR_DOCTYPES = (
	"Employee",
	"Employee Onboarding",
	"Attendance",
	"Leave Application",
	"Expense Claim",
	"Payroll Entry",
	"Salary Slip",
	"Employee Separation",
	"Fit and Proper Declaration",
)
EMPLOYEE_CREATES = ("Leave Application", "Expense Claim", "Fit and Proper Declaration", "Attendance Request")
EMPLOYEE_DENIED = ("Payroll Entry", "Salary Structure Assignment", "Employee Separation")

EXIT_DOCTYPE = "Employee Separation"
EXIT_RIGHTS = ("read", "write", "create", "submit", "cancel", "delete", "report", "export", "print", "email", "share")

FISCAL_YEAR_START = f"{YEAR}-04-01"
FISCAL_YEAR_END = f"{YEAR + 1}-03-31"


def print_checks(checks):
	for label, ok in checks:
		print(f"[{'PASS' if ok else 'FAIL'}] {label}")
	print(f"{sum(bool(ok) for _, ok in checks)}/{len(checks)} checks passed")


# Sprint 7
# --------


def run_sprint7():
	grant_exit_checklist_access()  # walkthrough fix
	frappe.db.commit()

	# Branding on a shared site is code only (hooks + boot); settings change only on a dedicated site
	if is_dedicated_site():
		apply_site_branding()
		frappe.db.commit()
	frappe.clear_cache()
	print(f"Sprint 7 setup done ({'site-wide' if is_dedicated_site() else 'Manthan HR users only'} branding).")


def grant_exit_checklist_access():
	"""hrms v15 gives Employee Separation to System Manager only, so HR could not run an advisor exit.
	Granted to the Manthan reviewer role, not HR Manager / HR User, which real users of the shared
	site hold. Exported as a Custom DocPerm fixture for the other client sites."""
	from frappe.permissions import add_permission, update_permission_property

	if frappe.db.exists("Custom DocPerm", {"parent": EXIT_DOCTYPE, "role": REVIEWER_ROLE, "permlevel": 0}):
		return
	add_permission(EXIT_DOCTYPE, REVIEWER_ROLE, 0)
	for ptype in EXIT_RIGHTS:
		update_permission_property(EXIT_DOCTYPE, REVIEWER_ROLE, 0, ptype, 1)


def get_boot_for(user):
	"""The bootinfo the desk would load for this user, including every app's extend_bootinfo hook."""
	from frappe.boot import get_bootinfo

	frappe.set_user(user)
	try:
		bootinfo = get_bootinfo()
		for hook in frappe.get_hooks("extend_bootinfo"):
			frappe.get_attr(hook)(bootinfo=bootinfo)
		return bootinfo
	finally:
		frappe.set_user("Administrator")


def get_http_status(path):
	import requests

	url = f"http://127.0.0.1:{frappe.conf.webserver_port or 8000}{path}"
	try:
		return requests.get(url, headers={"Host": frappe.local.site}, timeout=15).status_code
	except requests.RequestException as e:
		return type(e).__name__


def get_unbranded_system_user():
	"""Any enabled desk user of the other apps on this site (not on the Manthan HR module profile)."""
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
		fields=["name", "module_profile"],
		order_by="creation",
	)
	return next((user.name for user in users if user.module_profile != MODULE_PROFILE), None)


def run_verify(method):
	"""Run an earlier day's verify function and read its 'x/y checks passed' summary."""
	output = io.StringIO()
	with contextlib.redirect_stdout(output):
		method()
	summary = re.search(r"(\d+)/(\d+) checks passed", output.getvalue())
	return bool(summary) and summary.group(1) == summary.group(2), summary.group(0) if summary else "no summary"


def get_employee_user(first_name):
	return frappe.db.get_value("Employee", {"first_name": first_name, "company": COMPANY_NAME}, ["name", "user_id"])


def verify_branding():
	brand = get_brand(CLIENT.brand)
	checks = [
		("extend_bootinfo hook registered", "manthan_hrms.branding.boot.extend_bootinfo" in frappe.get_hooks("extend_bootinfo")),
		("Branding script included on desk", "/assets/manthan_hrms/js/manthan_branding.js" in frappe.get_hooks("app_include_js")),
		(
			f"Primary colour changed from Frappe default ({brand.button}, contrast {contrast_with_white(brand.button):.2f}:1)",
			brand.button.lower() != FRAPPE_DEFAULT_PRIMARY and contrast_with_white(brand.button) >= MIN_TEXT_CONTRAST,
		),
	]

	public = frappe.get_app_path("manthan_hrms", "public")
	for url in (brand.logo, brand.nav_logo, brand.favicon, "/assets/manthan_hrms/js/manthan_branding.js"):
		relative = url.removeprefix("/assets/manthan_hrms/")
		status = get_http_status(url)
		checks.append((f"{url} on disk and served (HTTP {status})", os.path.exists(os.path.join(public, relative)) and status == 200))

	employee_user = get_employee_user(WALKTHROUGH_EMPLOYEE)[1]
	for user in (TEST_HR_USER, employee_user):
		boot = get_boot_for(user)
		checks.append(
			(
				f"{user} desk: {brand.name} logo + colours",
				boot.app_logo_url == brand.nav_logo and (boot.get("manthan_brand") or {}).get("button") == brand.button,
			)
		)

	if not is_dedicated_site():
		from frappe.core.doctype.navbar_settings.navbar_settings import get_app_logo

		default_logo = get_app_logo()
		other_users = [("Administrator", "Administrator")]
		if other := get_unbranded_system_user():
			other_users.append((other, "a user of the other apps on this site"))
		for user, label in other_users:
			boot = get_boot_for(user)
			checks.append(
				(
					f"{label} keeps the default desk (logo {boot.app_logo_url})",
					not boot.get("manthan_brand") and boot.app_logo_url == default_logo,
				)
			)
		checks.append(
			(
				"Shared site: login page settings untouched (Website Settings logo/favicon empty)",
				not frappe.db.get_single_value("Website Settings", "app_logo")
				and not frappe.db.get_single_value("Website Settings", "favicon"),
			)
		)
	return checks


def get_visible_workspaces(user):
	from frappe.desk.desktop import get_workspace_sidebar_items

	frappe.set_user(user)
	try:
		pages = get_workspace_sidebar_items().get("pages", [])
	finally:
		frappe.set_user("Administrator")
	return {page.get("name"): frappe.db.get_value("Workspace", page.get("name"), "module") for page in pages}


def verify_walkthrough():
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	from manthan_hrms.compliance.employee_separation import validate_exit_checklist

	checks = []

	# Earlier days still hold
	from manthan_hrms.setup import day1, day2, day3

	for day, method in ((1, day1.verify_day1), (2, day2.verify_day2), (3, day3.verify_day3)):
		ok, summary = run_verify(method)
		checks.append((f"Day {day} verification: {summary}", ok))

	# HR user: sidebar limited to HR apps, can open every HR screen
	workspaces = get_visible_workspaces(TEST_HR_USER)
	module_apps = {module: frappe.db.get_value("Module Def", module, "app_name") for module in set(workspaces.values()) if module}
	outside = sorted(name for name, module in workspaces.items() if module and module_apps.get(module) not in ALLOWED_APPS)
	checks += [
		(f"HR user sidebar: {len(workspaces)} workspaces, none outside HR apps (outside: {outside})", bool(workspaces) and not outside),
		("HR user sidebar has HR, Leaves, Payroll", {"HR", "Leaves", "Payroll"} <= set(workspaces)),
	]
	no_read = [doctype for doctype in HR_DOCTYPES if not frappe.has_permission(doctype, "read", user=TEST_HR_USER)]
	checks.append((f"HR user can open every HR screen (missing: {no_read})", not no_read))

	frappe.set_user(TEST_HR_USER)
	try:
		hr_slips = frappe.get_list("Salary Slip", filters={"company": COMPANY_NAME, "docstatus": 1}, pluck="name")
	finally:
		frappe.set_user("Administrator")
	checks.append((f"HR user sees all company salary slips ({len(hr_slips)})", len(hr_slips) >= 15))
	checks.append(
		(
			"Certification reminder in HR user's notification bell",
			bool(frappe.db.exists("Notification Log", {"for_user": TEST_HR_USER, "document_type": "Employee", "subject": ["like", "%NISM%"]})),
		)
	)

	# Employee self-service
	employee, employee_user = get_employee_user(WALKTHROUGH_EMPLOYEE)
	frappe.set_user(employee_user)
	try:
		own_slips = frappe.get_list("Salary Slip", fields=["employee"], filters={"docstatus": 1})
		leave_details = get_leave_details(employee, frappe.utils.today())
		own_declarations = frappe.get_list("Fit and Proper Declaration", pluck="employee")
	finally:
		frappe.set_user("Administrator")
	cannot_create = [dt for dt in EMPLOYEE_CREATES if not frappe.has_permission(dt, "create", user=employee_user)]
	can_read_denied = [dt for dt in EMPLOYEE_DENIED if frappe.has_permission(dt, "read", user=employee_user)]
	checks += [
		(
			f"{WALKTHROUGH_EMPLOYEE} sees only own payslip ({len(own_slips)})",
			bool(own_slips) and {slip.employee for slip in own_slips} == {employee},
		),
		(
			f"{WALKTHROUGH_EMPLOYEE} leave balance shown ({', '.join(leave_details.get('leave_allocation', {}))})",
			bool(leave_details.get("leave_allocation")),
		),
		(f"{WALKTHROUGH_EMPLOYEE} sees own Fit & Proper Declaration", own_declarations == [employee]),
		(f"{WALKTHROUGH_EMPLOYEE} can raise {', '.join(EMPLOYEE_CREATES)} (blocked: {cannot_create})", not cannot_create),
		(f"{WALKTHROUGH_EMPLOYEE} cannot open {', '.join(EMPLOYEE_DENIED)} (open: {can_read_denied})", not can_read_denied),
	]

	# Manager sees their report
	manager, report = (get_employee_user(name) for name in WALKTHROUGH_MANAGER)
	frappe.set_user(manager[1])
	try:
		visible = frappe.get_list("Employee", pluck="name")
	finally:
		frappe.set_user("Administrator")
	checks.append((f"{WALKTHROUGH_MANAGER[0]} sees report {WALKTHROUGH_MANAGER[1]}", report[0] in visible))

	# Exit checklist still blocks
	blank = frappe.new_doc("Employee Separation")
	try:
		validate_exit_checklist(blank)
		blocked = False
	except frappe.ValidationError:
		frappe.clear_messages()
		blocked = True
	checks.append(("Exit checklist blocks an incomplete separation", blocked))
	return checks


def verify_sprint7():
	started = now_datetime()
	checks = verify_branding() + verify_walkthrough()
	errors = frappe.get_all("Error Log", filters={"creation": [">=", started]}, pluck="method")
	checks.append((f"No errors logged during the walkthrough ({errors})", not errors))
	print_checks(checks)


# Sprint 8
# --------


def run_sprint8():
	complete_setup_wizard()
	run_sprint1()  # company check, Module Profile "Manthan HR Only", HR user
	grant_exit_checklist_access()  # normally already there from the fixture
	if is_dedicated_site():
		apply_site_branding()
	frappe.db.commit()
	frappe.clear_cache()
	print(f"Sprint 8 setup done for {COMPANY_NAME} on {frappe.local.site}.")


def get_setup_args():
	return frappe._dict(
		{
			"language": "English",
			"country": "India",
			"timezone": "Asia/Kolkata",
			"currency": "INR",
			"company_name": COMPANY_NAME,
			"company_abbr": COMPANY_ABBR,
			"chart_of_accounts": "Standard",
			"fy_start_date": FISCAL_YEAR_START,
			"fy_end_date": FISCAL_YEAR_END,
			"setup_demo": 0,
		}
	)


def complete_setup_wizard():
	"""What the ERPNext setup wizard does, for the client company (creates the one Company record)."""
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	if frappe.is_setup_complete():
		return

	result = setup_complete(get_setup_args())
	if (result or {}).get("status") != "ok" or not frappe.is_setup_complete():
		frappe.throw(f"Setup wizard failed: {result} (see Error Log)")


# Repair
# ------

# cleared before the stale company is deleted (they link to it), then rewritten by set_default_settings
STALE_POINTERS = (
	("Global Defaults", "default_company"),
	("Stock Settings", "default_warehouse"),
	("System Settings", "email_footer_address"),
)


def reset_client_site():
	"""Repair a dedicated client site that was set up before manthan_hrms_client was in site_config:
	the sprint ran as the default client, so the company, its chart of accounts and the HR user carry
	the wrong client's name. Only for an empty site; run run_sprint8 afterwards."""
	if not is_dedicated_site():
		frappe.throw("Only for a dedicated client site (manthan_hrms_dedicated_site in site_config.json)")

	stale_companies = [company for company in frappe.get_all("Company", pluck="name") if company != COMPANY_NAME]
	if not stale_companies:
		print(f"Nothing to reset: {frappe.local.site} already has only {COMPANY_NAME}.")
		return

	for doctype in ("Employee", "GL Entry"):
		if count := frappe.db.count(doctype):
			frappe.throw(f"{frappe.local.site} has {count} {doctype} records; refusing to reset a site with data")

	for doctype, fieldname in STALE_POINTERS:
		frappe.db.set_single_value(doctype, fieldname, "")
	for company in stale_companies:
		purge_company(company)
	purge_stale_users()

	create_client_company()
	frappe.db.commit()
	print(f"Reset {frappe.local.site}: {', '.join(stale_companies)} -> {COMPANY_NAME} ({COMPANY_ABBR}).")


def purge_company(company):
	"""Company.on_trash drops the accounts and cost centers itself (no GL entries here), but Frappe
	refuses to delete a document other records link to, so the auto-created masters go first."""
	for doctype in ("Department", "Warehouse"):
		# nested sets: deepest first, a group cannot be deleted while it has children
		for name in frappe.get_all(doctype, filters={"company": company}, pluck="name", order_by="lft desc"):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)

	frappe.db.delete("Mode of Payment Account", {"company": company})
	frappe.delete_doc("Company", company, ignore_permissions=True)


def purge_stale_users():
	"""The pilot HR user of another client, created here by the mis-configured run (fake domains)."""
	other_domains = {values["company_domain"] for key, values in CLIENTS.items() if key != CLIENT.key}
	for user in frappe.get_all("User", filters={"module_profile": MODULE_PROFILE}, pluck="name"):
		if user.rsplit("@", 1)[-1] in other_domains:
			frappe.delete_doc("User", user, ignore_permissions=True, force=True)


def create_client_company():
	"""The company the setup wizard would have made; it cannot run again once setup is complete."""
	from erpnext.setup.setup_wizard.operations.defaults_setup import set_default_settings
	from erpnext.setup.setup_wizard.operations.install_fixtures import install_company

	args = get_setup_args()
	if not frappe.db.exists("Company", COMPANY_NAME):
		install_company(args)  # Company.on_update builds accounts, warehouses, cost center, departments
	set_default_settings(args)


def verify_sprint8():
	installed = set(frappe.get_installed_apps())
	blocked = set(frappe.get_all("Block Module", {"parent": TEST_HR_USER, "parenttype": "User"}, pluck="module"))
	checks = [
		(f"Apps installed: {', '.join(REQUIRED_APPS)} (missing: {set(REQUIRED_APPS) - installed})", set(REQUIRED_APPS) <= installed),
		("Setup wizard complete", frappe.is_setup_complete()),
		(f"Company {COMPANY_NAME} ({COMPANY_ABBR}) exists", frappe.db.get_value("Company", COMPANY_NAME, "abbr") == COMPANY_ABBR),
		# package contents
		(f"Module Profile {MODULE_PROFILE} (built for this site's modules by Day 1)",bool(frappe.db.exists("Module Profile", MODULE_PROFILE))),
		("Leave types + designations (fixtures)", all(frappe.db.exists("Leave Type", lt) for lt in ("Casual Leave", "Sick Leave", "Earned Leave"))),
		("Fit and Proper Review workflow + reviewer role (fixtures)", bool(frappe.db.exists("Workflow", "Fit and Proper Review")) and bool(frappe.db.exists("Role", "Manthan Compliance Reviewer"))),
		("Fit and Proper Declaration DocType", bool(frappe.db.exists("DocType", "Fit and Proper Declaration"))),
		(
			"Advisory custom fields (certification, exit checklist)",
			frappe.get_meta("Employee").has_field("nism_valid_upto") and frappe.get_meta("Employee Separation").has_field("client_book_handed_over"),
		),
		("india_payroll components + tax slabs", bool(frappe.db.exists("Salary Component", "Professional Tax")) and bool(frappe.db.exists("Income Tax Slab", "New Tax Regime: 2025-2026"))),
		# non-HR menus hidden
		(f"HR user {TEST_HR_USER} exists", bool(frappe.db.exists("User", TEST_HR_USER))),
		(f"Non-HR menus hidden for HR user ({', '.join(BLOCKED_FOR_HR)})", set(BLOCKED_FOR_HR) <= blocked),
		("HR user keeps HR + Payroll", not ({"HR", "Payroll"} & blocked)),
	]
	if frappe.db.exists("User", TEST_HR_USER):
		outside = [
			name
			for name, module in get_visible_workspaces(TEST_HR_USER).items()
			if module and frappe.db.get_value("Module Def", module, "app_name") not in ALLOWED_APPS
		]
		checks.append((f"HR user sidebar shows only HR apps (outside: {outside})", not outside))

	if is_dedicated_site():
		brand = get_brand(CLIENT.brand)
		checks += [
			(f"Exactly one Company ({frappe.get_all('Company', pluck='name')})", frappe.db.count("Company") == 1),
			(
				f"Login page brand: {brand.name} logo + favicon",
				frappe.db.get_single_value("Website Settings", "app_logo") == brand.logo
				and frappe.db.get_single_value("Website Settings", "favicon") == brand.favicon,
			),
			("Desk brand for every user", bool(get_desk_brand("Administrator"))),
			(f"No errors logged on this site ({frappe.db.count('Error Log')})", not frappe.db.count("Error Log")),
		]

	print_checks(checks)
