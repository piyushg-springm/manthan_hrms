"""Pilot Day 1 setup (Sprint 1 + Sprint 2) for one client site.

Idempotent: every step checks for an existing record first, so it is safe to re-run.
The client (company name, abbreviation, domain) comes from `manthan_hrms_client` in site_config.json,
see manthan_hrms.setup.clients.

    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day1.run_sprint1
    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day1.run_sprint2
    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day1.verify_day1
"""

import frappe
from frappe.utils import getdate, today

from manthan_hrms.setup.clients import MODULE_PROFILE, get_client

CLIENT = get_client(strict=True)  # every setup module imports these constants from here
COMPANY_NAME = CLIENT.company_name
COMPANY_ABBR = CLIENT.company_abbr
COMPANY_DOMAIN = CLIENT.company_domain
YEAR = 2026

HR_ROLE_PROFILE = "HR"  # created by hrms setup (hrms/setup.py DEFAULT_ROLE_PROFILES)
TEST_HR_USER = f"hr.test@{COMPANY_DOMAIN}"

# Modules HR users keep in the sidebar. Everything else (framework, ERPNext business modules and
# the Manthan product apps installed on this site) is blocked via the Module Profile.
# Blocking only hides sidebar workspaces; doctype access still follows role permissions.
ALLOWED_APPS = {"hrms", "india_payroll", "manthan_hrms"}

DEPARTMENTS = ["Advisory", "Compliance", "Operations", "Admin", "Research"]
DESIGNATIONS = [
	"Relationship Manager",
	"Compliance Officer",
	"Operations Executive",
	"Admin Executive",
	"Research Analyst",
]


# National holidays + common gazetted holidays (2026 dates)
HOLIDAYS = [
	("2026-01-26", "Republic Day"),
	("2026-03-04", "Holi"),
	("2026-03-21", "Id-ul-Fitr"),
	("2026-04-03", "Good Friday"),
	("2026-05-01", "Maharashtra Day"),
	("2026-08-15", "Independence Day"),
	("2026-09-14", "Ganesh Chaturthi"),
	("2026-10-02", "Gandhi Jayanti"),
	("2026-10-20", "Dussehra"),
	("2026-11-08", "Diwali"),
	("2026-12-25", "Christmas"),
]
WEEKLY_OFFS = ["Saturday", "Sunday"]

LEAVE_TYPES = {
	"Casual Leave": {"max_leaves_allowed": 12},
	"Sick Leave": {"max_leaves_allowed": 12},
	"Earned Leave": {"max_leaves_allowed": 15, "is_carry_forward": 1},
}
LEAVE_POLICY = f"{COMPANY_NAME} Standard Leave Policy"

TEST_EMPLOYEE = {
	"first_name": "Test",
	"last_name": "Employee",
	"gender": "Female",
	"date_of_birth": "1995-06-15",
	"date_of_joining": f"{YEAR}-01-01",
	"department_name": "Advisory",
	"designation": "Relationship Manager",
	"company_email": f"test.employee@{COMPANY_DOMAIN}",
}


# Sprint 1
# --------


def run_sprint1():
	create_company()
	create_module_profile()
	create_test_hr_user()
	frappe.db.commit()
	print("Sprint 1 setup done.")


def create_company():
	if frappe.db.exists("Company", COMPANY_NAME):
		return

	existing = frappe.db.get_value("Company", {"abbr": COMPANY_ABBR})
	if existing:
		frappe.throw(f"Company abbreviation {COMPANY_ABBR} is already used by {existing}")

	company = frappe.new_doc("Company")
	company.update(
		{
			"company_name": COMPANY_NAME,
			"abbr": COMPANY_ABBR,
			"country": "India",
			"default_currency": "INR",
			"create_chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": "Standard",
		}
	)
	company.insert(ignore_permissions=True)


def get_blocked_modules():
	return frappe.get_all(
		"Module Def", filters={"app_name": ["not in", list(ALLOWED_APPS)]}, pluck="name", order_by="name"
	)


def create_module_profile():
	if frappe.db.exists("Module Profile", MODULE_PROFILE):
		profile = frappe.get_doc("Module Profile", MODULE_PROFILE)
	else:
		profile = frappe.new_doc("Module Profile")
		profile.module_profile_name = MODULE_PROFILE

	# Rebuilt on every run so modules from newly installed apps are blocked too
	blocked_modules = get_blocked_modules()
	if not profile.is_new() and {d.module for d in profile.block_modules} == set(blocked_modules):
		return

	profile.set("block_modules", [{"module": module} for module in blocked_modules])
	profile.save(ignore_permissions=True)

	# on_update queues update_all_users behind a document lock; apply it now and release the
	# lock so re-runs work on benches without a background worker.
	profile.update_all_users()
	profile.unlock()


def create_test_hr_user():
	if frappe.db.exists("User", TEST_HR_USER):
		user = frappe.get_doc("User", TEST_HR_USER)
	else:
		user = frappe.new_doc("User")
		user.update(
			{
				"email": TEST_HR_USER,
				"first_name": "HR",
				"last_name": "Test User",
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		)

	# keep a profile set later (Day 3 moves this user to a reviewer profile built on HR)
	if not user.role_profile_name:
		user.role_profile_name = HR_ROLE_PROFILE
	user.module_profile = MODULE_PROFILE
	user.default_workspace = "HR"
	user.save(ignore_permissions=True)


# Sprint 2
# --------


def run_sprint2():
	create_departments()
	set_department_approvers()
	disable_unused_departments()
	create_designations()
	create_holiday_list()
	create_leave_types()
	create_leave_policy()
	employee = create_test_employee()
	create_employee_user(employee)
	assign_leave_policy_to_all()
	frappe.db.commit()
	print("Sprint 2 setup done.")


def create_departments():
	for department_name in DEPARTMENTS:
		if frappe.db.exists("Department", {"department_name": department_name, "company": COMPANY_NAME}):
			continue
		frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": department_name,
				"company": COMPANY_NAME,
				"parent_department": "All Departments",
			}
		).insert(ignore_permissions=True)


def create_designations():
	for designation in DESIGNATIONS:
		if not frappe.db.exists("Designation", designation):
			frappe.get_doc({"doctype": "Designation", "designation_name": designation}).insert(
				ignore_permissions=True
			)


def get_holiday_list_name():
	return f"{COMPANY_NAME} {YEAR}"


def create_holiday_list():
	name = get_holiday_list_name()
	if not frappe.db.exists("Holiday List", name):
		holiday_list = frappe.new_doc("Holiday List")
		holiday_list.update(
			{"holiday_list_name": name, "from_date": f"{YEAR}-01-01", "to_date": f"{YEAR}-12-31"}
		)
		for day in WEEKLY_OFFS:
			holiday_list.weekly_off = day
			holiday_list.get_weekly_off_dates()

		weekly_off_dates = {getdate(d.holiday_date) for d in holiday_list.holidays}
		for date, description in HOLIDAYS:
			if getdate(date) not in weekly_off_dates:
				holiday_list.append("holidays", {"holiday_date": date, "description": description})

		holiday_list.weekly_off = None
		holiday_list.insert(ignore_permissions=True)

	frappe.db.set_value("Company", COMPANY_NAME, "default_holiday_list", name)


def create_leave_types():
	for leave_type_name, values in LEAVE_TYPES.items():
		if frappe.db.exists("Leave Type", leave_type_name):
			continue
		frappe.get_doc({"doctype": "Leave Type", "leave_type_name": leave_type_name, **values}).insert(
			ignore_permissions=True
		)


def create_leave_policy():
	existing = frappe.db.get_value("Leave Policy", {"title": LEAVE_POLICY, "docstatus": 1})
	if existing:
		return existing

	policy = frappe.new_doc("Leave Policy")
	policy.title = LEAVE_POLICY
	for leave_type_name, values in LEAVE_TYPES.items():
		policy.append(
			"leave_policy_details",
			{"leave_type": leave_type_name, "annual_allocation": values["max_leaves_allowed"]},
		)
	policy.insert(ignore_permissions=True)
	policy.submit()
	return policy.name


def get_department(department_name):
	return frappe.db.get_value("Department", {"department_name": department_name, "company": COMPANY_NAME})


def create_test_employee():
	filters = {
		"first_name": TEST_EMPLOYEE["first_name"],
		"last_name": TEST_EMPLOYEE["last_name"],
		"company": COMPANY_NAME,
	}
	if existing := frappe.db.get_value("Employee", filters):
		return existing

	employee = frappe.new_doc("Employee")
	employee.update(
		{
			"first_name": TEST_EMPLOYEE["first_name"],
			"last_name": TEST_EMPLOYEE["last_name"],
			"gender": TEST_EMPLOYEE["gender"],
			"date_of_birth": TEST_EMPLOYEE["date_of_birth"],
			"date_of_joining": TEST_EMPLOYEE["date_of_joining"],
			"company": COMPANY_NAME,
			"department": get_department(TEST_EMPLOYEE["department_name"]),
			"designation": TEST_EMPLOYEE["designation"],
			"holiday_list": get_holiday_list_name(),
			"status": "Active",
		}
	)
	employee.insert(ignore_permissions=True)
	return employee.name


def set_department_approvers():
	"""Leave/expense approvals route to the department's first approver (hrms get_leave_approver)."""
	for department_name in DEPARTMENTS:
		department = frappe.get_doc("Department", get_department(department_name))
		changed = False
		for table in ("leave_approvers", "expense_approvers"):
			if TEST_HR_USER not in {row.approver for row in department.get(table)}:
				department.append(table, {"approver": TEST_HR_USER})
				changed = True
		if changed:
			department.save(ignore_permissions=True)


def get_unused_departments():
	"""Company departments other than DEPARTMENTS — ERPNext auto-creates 13 generic ones per company."""
	return frappe.get_all(
		"Department",
		filters={"company": COMPANY_NAME, "is_group": 0, "department_name": ["not in", DEPARTMENTS]},
		pluck="name",
	)


def disable_unused_departments():
	for department in get_unused_departments():
		if frappe.db.exists("Employee", {"department": department}):
			continue
		frappe.db.set_value("Department", department, "disabled", 1)


def create_employee_user(employee, company_email=TEST_EMPLOYEE["company_email"]):
	"""Give the employee a login (Employee role + User Permission on their own Employee record)."""
	from erpnext.setup.doctype.employee.employee import create_user

	doc = frappe.get_doc("Employee", employee)
	if not doc.user_id:
		doc.company_email = company_email
		doc.prefered_contact_email = "Company Email"
		doc.create_user_permission = 1
		doc.save(ignore_permissions=True)
		# Employee.on_update adds the Employee role and the User Permission once user_id is linked
		create_user(employee)
		doc.reload()

	user = frappe.get_doc("User", doc.user_id)
	if user.module_profile != MODULE_PROFILE or user.default_workspace != "Leaves":
		user.module_profile = MODULE_PROFILE
		user.default_workspace = "Leaves"
		user.save(ignore_permissions=True)


def get_employees_without_leave_policy():
	assigned = frappe.get_all(
		"Leave Policy Assignment",
		filters={
			"company": COMPANY_NAME,
			"docstatus": 1,
			"effective_from": ["<=", f"{YEAR}-12-31"],
			"effective_to": [">=", f"{YEAR}-01-01"],
		},
		pluck="employee",
	)
	return frappe.get_all(
		"Employee",
		filters={"company": COMPANY_NAME, "status": "Active", "name": ["not in", assigned or [""]]},
		pluck="name",
	)


def assign_leave_policy_to_all():
	"""One leave policy for every active employee, assigned in bulk through Leave Control Panel."""
	employees = get_employees_without_leave_policy()
	if not employees:
		return

	panel = frappe.get_doc(
		{
			"doctype": "Leave Control Panel",
			"company": COMPANY_NAME,
			"dates_based_on": "Custom Range",
			"from_date": f"{YEAR}-01-01",
			"to_date": f"{YEAR}-12-31",
			"allocate_based_on_leave_policy": 1,
			"leave_policy": create_leave_policy(),
		}
	)
	panel.allocate_leave(employees)

	# Leave Control Panel only logs per-employee failures, so check the outcome explicitly
	if failed := get_employees_without_leave_policy():
		frappe.throw(f"Leave Policy Assignment failed for: {', '.join(failed)} (see Error Log)")


# Verification
# ------------


def verify_day1():
	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	installed = set(frappe.get_installed_apps())
	employee = frappe.db.get_value("Employee", {"first_name": TEST_EMPLOYEE["first_name"], "company": COMPANY_NAME})
	blocked = set(frappe.get_all("Block Module", {"parent": TEST_HR_USER, "parenttype": "User"}, pluck="module"))

	checks = [
		("Apps installed: erpnext, hrms, india_payroll", {"erpnext", "hrms", "india_payroll"} <= installed),
		(f"Company {COMPANY_NAME} exists", bool(frappe.db.exists("Company", COMPANY_NAME))),
		(
			"Test HR user blocked from Selling/Buying/Stock/Accounts/Manufacturing/CRM",
			{"Selling", "Buying", "Stock", "Accounts", "Manufacturing", "CRM"} <= blocked,
		),
		(
			"Test HR user keeps HR + Payroll",
			not ({"HR", "Payroll"} & blocked),
		),
		(">= 3 departments", frappe.db.count("Department", {"company": COMPANY_NAME}) >= 3),
		(">= 5 designations", all(frappe.db.exists("Designation", d) for d in DESIGNATIONS)),
		(
			"Holiday list active on company",
			frappe.db.get_value("Company", COMPANY_NAME, "default_holiday_list") == get_holiday_list_name(),
		),
		("3 leave types", all(frappe.db.exists("Leave Type", lt) for lt in LEAVE_TYPES)),
		("Leave policy submitted", bool(frappe.db.exists("Leave Policy", {"title": LEAVE_POLICY, "docstatus": 1}))),
		("Every active employee has the leave policy", not get_employees_without_leave_policy()),
		(
			"Departments have leave + expense approver",
			all(
				frappe.db.exists(
					"Department Approver",
					{"parent": get_department(d), "parentfield": table, "approver": TEST_HR_USER},
				)
				for d in DEPARTMENTS
				for table in ("leave_approvers", "expense_approvers")
			),
		),
		(
			"Unused auto-created departments disabled",
			all(frappe.db.get_value("Department", dept, "disabled") for dept in get_unused_departments()),
		),
	]

	if employee:
		from hrms.hr.doctype.leave_application.leave_application import get_leave_approver

		user_id = frappe.db.get_value("Employee", employee, "user_id")
		checks += [
			(f"{employee} linked to login user {user_id}", bool(user_id)),
			("Employee user has Employee role", bool(user_id) and "Employee" in frappe.get_roles(user_id)),
			(
				"Employee user restricted to own Employee record",
				bool(
					frappe.db.exists(
						"User Permission", {"user": user_id, "allow": "Employee", "for_value": employee}
					)
				),
			),
			(f"Leave approver resolves to {TEST_HR_USER}", get_leave_approver(employee) == TEST_HR_USER),
		]
		for leave_type_name, values in LEAVE_TYPES.items():
			balance = get_leave_balance_on(employee, leave_type_name, today())
			checks.append(
				(
					f"{employee} {leave_type_name} balance = {values['max_leaves_allowed']} (got {balance})",
					balance == values["max_leaves_allowed"],
				)
			)
	else:
		checks.append(("Test employee exists", False))

	for label, ok in checks:
		print(f"[{'PASS' if ok else 'FAIL'}] {label}")
	print(f"{sum(ok for _, ok in checks)}/{len(checks)} checks passed")
