"""Pilot Day 2 setup (Sprint 3 + Sprint 4) for company Prudeno Wealth.

Idempotent: every step checks for an existing record first, so it is safe to re-run.
Everything is scoped to COMPANY_NAME; no global settings are changed.

    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day2.run_sprint3
    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day2.run_sprint4
    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day2.verify_day2
"""

import frappe
from frappe.utils import add_days, getdate

from manthan_hrms.setup.day1 import (
	COMPANY_DOMAIN,
	COMPANY_NAME,
	DEPARTMENTS,
	DESIGNATIONS,
	LEAVE_TYPES,
	TEST_EMPLOYEE,
	TEST_HR_USER,
	assign_leave_policy_to_all,
	create_employee_user,
	get_department,
	get_employees_without_leave_policy,
	get_holiday_list_name,
)

TARGET_HEADCOUNT = 15

# 13 made-up employees; with the Day 1 test employee and the onboarded joiner the company has 15.
# Managers come before their reports so reports_to can be resolved.
SAMPLE_EMPLOYEES = [
	("Aarav", "Sharma", "Male", "1984-03-12", "2019-04-01", "Advisory", "Relationship Manager", "Full-time", None),
	("Priya", "Nair", "Female", "1991-07-22", "2021-06-14", "Advisory", "Relationship Manager", "Full-time", "aarav"),
	("Rohan", "Mehta", "Male", "1993-11-05", "2022-02-01", "Advisory", "Relationship Manager", "Full-time", "aarav"),
	("Sneha", "Reddy", "Female", "1997-01-30", "2025-07-01", "Advisory", "Relationship Manager", "Probation", "aarav"),
	("Kavya", "Iyer", "Female", "1988-09-18", "2020-01-06", "Compliance", "Compliance Officer", "Full-time", None),
	("Siddharth", "Rao", "Male", "1995-04-09", "2023-03-15", "Compliance", "Compliance Officer", "Full-time", "kavya"),
	("Ananya", "Desai", "Female", "1990-12-02", "2020-08-17", "Operations", "Operations Executive", "Full-time", None),
	("Vikram", "Singh", "Male", "1994-06-25", "2022-10-03", "Operations", "Operations Executive", "Full-time", "ananya"),
	("Rahul", "Verma", "Male", "1998-02-14", "2025-01-20", "Operations", "Operations Executive", "Contract", "ananya"),
	("Meera", "Joshi", "Female", "1989-05-11", "2019-11-11", "Admin", "Admin Executive", "Full-time", None),
	("Arjun", "Kulkarni", "Male", "1996-08-08", "2024-04-08", "Admin", "Admin Executive", "Full-time", "meera"),
	("Neha", "Kapoor", "Female", "1987-10-27", "2021-01-04", "Research", "Research Analyst", "Full-time", None),
	("Karan", "Malhotra", "Male", "1996-03-03", "2024-09-02", "Research", "Research Analyst", "Full-time", "neha"),
]

ONBOARDING_TEMPLATE = f"{COMPANY_NAME} Standard Onboarding"
ONBOARDING_ACTIVITIES = [
	# (activity, begin_on, duration, required_for_employee_creation)
	("Collect KYC documents (PAN, Aadhaar, address proof)", 0, 2, 1),
	("Verify NISM certification and ARN/EUIN", 0, 3, 1),
	("Create company email and laptop", 3, 2, 0),
	("Sign code of conduct and confidentiality policy", 5, 1, 0),
	("First-week buddy introduction", 7, 5, 0),
]
NEW_JOINER = {
	"first_name": "Ishita",
	"last_name": "Banerjee",
	"gender": "Female",
	"date_of_birth": "1999-04-21",
	"applicant_email": f"ishita.banerjee.candidate@{COMPANY_DOMAIN}",
	"company_email": f"ishita.banerjee@{COMPANY_DOMAIN}",
	"department_name": "Research",
	"designation": "Research Analyst",
	"offer_date": "2026-08-10",
	# hrms starts the onboarding Project on date_of_joining and ERPNext rejects tasks starting earlier
	"boarding_begins_on": "2026-09-01",
	"date_of_joining": "2026-09-01",
}

# One working week (Mon-Fri, no holidays in the Prudeno Wealth 2026 list)
ATTENDANCE_WEEK_START = "2026-09-07"
ATTENDANCE_DAYS = 5

# (employee first name, leave type, from, to, days)
LEAVE_APPLICATIONS = [
	("Priya", "Casual Leave", "2026-09-09", "2026-09-09", 1),
	("Kavya", "Sick Leave", "2026-09-10", "2026-09-11", 2),
]

EXPENSE_ACCOUNTS = {
	"Travel": "Travel Expenses",
	"Food": "Entertainment Expenses",
	"Calls": "Telephone Expenses",
	"Medical": "Miscellaneous Expenses",
	"Others": "Miscellaneous Expenses",
}
EXPENSE_CLAIM_REMARK = "Pilot: client meeting in Andheri (cab + lunch)"
EXPENSE_CLAIM_ITEMS = [
	("Travel", 2450, "Cab to and from client meeting"),
	("Food", 650, "Working lunch with client"),
]
EXPENSE_CLAIM_DATE = "2026-09-10"


def email_for(first_name, last_name):
	return f"{first_name.lower()}.{last_name.lower()}@{COMPANY_DOMAIN}"


def get_employee_by_email(company_email):
	return frappe.db.get_value("Employee", {"company_email": company_email, "company": COMPANY_NAME})


def get_employee_by_first_name(first_name):
	return frappe.db.get_value("Employee", {"first_name": first_name, "company": COMPANY_NAME})


def get_active_employees():
	return frappe.get_all(
		"Employee",
		filters={"company": COMPANY_NAME, "status": "Active"},
		fields=["name", "date_of_joining"],
		order_by="name",
	)


# Sprint 3
# --------


def run_sprint3():
	create_sample_employees()
	run_onboarding()
	assign_leave_policy_to_all()
	create_employee_logins()
	frappe.db.commit()
	print("Sprint 3 setup done.")


def get_login_employees():
	"""Employees given a desk login to check what an ordinary employee can see."""
	return [
		get_employee_by_email(email)
		for email in (NEW_JOINER["company_email"], email_for("Priya", "Nair"), email_for("Kavya", "Iyer"))
	]


def create_employee_logins():
	for employee in get_login_employees():
		create_employee_user(employee, frappe.db.get_value("Employee", employee, "company_email"))


def create_sample_employees():
	has_employment_type = frappe.get_meta("Employee").has_field("employment_type")
	managers = {}
	for first, last, gender, dob, doj, department_name, designation, employment_type, manager in SAMPLE_EMPLOYEES:
		company_email = email_for(first, last)
		if not (employee := get_employee_by_email(company_email)):
			doc = frappe.new_doc("Employee")
			doc.update(
				{
					"first_name": first,
					"last_name": last,
					"gender": gender,
					"date_of_birth": dob,
					"date_of_joining": doj,
					"company": COMPANY_NAME,
					"department": get_department(department_name),
					"designation": designation,
					"holiday_list": get_holiday_list_name(),
					"company_email": company_email,
					"prefered_contact_email": "Company Email",
					"reports_to": managers.get(manager),
					"status": "Active",
				}
			)
			if has_employment_type:
				doc.employment_type = employment_type
			doc.insert(ignore_permissions=True)
			employee = doc.name
		managers[first.lower()] = employee


def create_onboarding_template():
	if existing := frappe.db.get_value(
		"Employee Onboarding Template", {"title": ONBOARDING_TEMPLATE, "company": COMPANY_NAME}
	):
		return existing

	template = frappe.new_doc("Employee Onboarding Template")
	template.title = ONBOARDING_TEMPLATE
	template.company = COMPANY_NAME
	for activity_name, begin_on, duration, required in ONBOARDING_ACTIVITIES:
		# assigned to the HR user only; a role would assign every user holding it on this shared site
		template.append(
			"activities",
			{
				"activity_name": activity_name,
				"user": TEST_HR_USER,
				"begin_on": begin_on,
				"duration": duration,
				"required_for_employee_creation": required,
			},
		)
	template.insert(ignore_permissions=True)
	return template.name


def create_job_applicant():
	if existing := frappe.db.get_value("Job Applicant", {"email_id": NEW_JOINER["applicant_email"]}):
		return existing

	applicant = frappe.new_doc("Job Applicant")
	applicant.update(
		{
			"applicant_name": f"{NEW_JOINER['first_name']} {NEW_JOINER['last_name']}",
			"email_id": NEW_JOINER["applicant_email"],
			"designation": NEW_JOINER["designation"],
			"status": "Open",
		}
	)
	applicant.insert(ignore_permissions=True)
	return applicant.name


def create_job_offer(job_applicant):
	if existing := frappe.db.get_value("Job Offer", {"job_applicant": job_applicant, "docstatus": 1}):
		return existing

	offer = frappe.new_doc("Job Offer")
	offer.update(
		{
			"job_applicant": job_applicant,
			"applicant_name": frappe.db.get_value("Job Applicant", job_applicant, "applicant_name"),
			"offer_date": NEW_JOINER["offer_date"],
			"designation": NEW_JOINER["designation"],
			"company": COMPANY_NAME,
			"status": "Accepted",
		}
	)
	offer.insert(ignore_permissions=True)
	offer.submit()
	return offer.name


def create_employee_onboarding(job_applicant, job_offer, template):
	from hrms.controllers.employee_boarding_controller import get_onboarding_details

	if existing := frappe.db.get_value(
		"Employee Onboarding", {"job_applicant": job_applicant, "docstatus": 1}
	):
		return frappe.get_doc("Employee Onboarding", existing)

	onboarding = frappe.new_doc("Employee Onboarding")
	onboarding.update(
		{
			"job_applicant": job_applicant,
			"job_offer": job_offer,
			"employee_name": f"{NEW_JOINER['first_name']} {NEW_JOINER['last_name']}",
			"date_of_joining": NEW_JOINER["date_of_joining"],
			"boarding_begins_on": NEW_JOINER["boarding_begins_on"],
			"company": COMPANY_NAME,
			"holiday_list": get_holiday_list_name(),
			"employee_onboarding_template": template,
			"notify_users_by_email": 0,
		}
	)
	for activity in get_onboarding_details(template, "Employee Onboarding Template"):
		onboarding.append("activities", activity)
	onboarding.insert(ignore_permissions=True)
	# on_submit creates the onboarding Project and one Task per activity
	onboarding.submit()
	return onboarding


def run_onboarding():
	"""Job Applicant -> Job Offer -> Employee Onboarding -> tasks done -> Employee, all through hrms."""
	from hrms.hr.doctype.employee_onboarding.employee_onboarding import make_employee

	template = create_onboarding_template()
	job_applicant = create_job_applicant()
	job_offer = create_job_offer(job_applicant)
	onboarding = create_employee_onboarding(job_applicant, job_offer, template)

	# on_submit db_sets project/boarding_status, so the in-memory doc is stale for save()
	onboarding.reload()
	if onboarding.boarding_status != "Completed":
		onboarding.mark_onboarding_as_completed()

	employee = get_employee_by_email(NEW_JOINER["company_email"])
	if not employee:
		# make_employee refuses until every task required for employee creation is completed
		doc = make_employee(onboarding.name)
		doc.update(
			{
				"first_name": NEW_JOINER["first_name"],
				"last_name": NEW_JOINER["last_name"],
				"gender": NEW_JOINER["gender"],
				"date_of_birth": NEW_JOINER["date_of_birth"],
				"company_email": NEW_JOINER["company_email"],
				"prefered_contact_email": "Company Email",
				"holiday_list": get_holiday_list_name(),
				"reports_to": get_employee_by_first_name("Neha"),
				"job_applicant": job_applicant,
			}
		)
		doc.insert(ignore_permissions=True)
		employee = doc.name

	# Onboarding department/designation are fetch_from the template, which is generic (blank), so every
	# save clears them and make_employee copies the blanks. Set both records here; re-runs repair them.
	org = {"department": get_department(NEW_JOINER["department_name"]), "designation": NEW_JOINER["designation"]}
	for doctype, name in (("Employee Onboarding", onboarding.name), ("Employee", employee)):
		if frappe.db.get_value(doctype, name, list(org), as_dict=True) != org:
			frappe.db.set_value(doctype, name, org)

	if onboarding.employee != employee:
		onboarding.db_set("employee", employee)


# Sprint 4
# --------


def run_sprint4():
	# Leave first: hrms refuses a leave application over days already marked Present, and on
	# submit it creates the "On Leave" attendance itself.
	create_leave_applications()
	mark_week_attendance()
	setup_expense_accounts()
	create_expense_claim()
	frappe.db.commit()
	print("Sprint 4 setup done.")


def get_attendance_dates():
	return [getdate(add_days(ATTENDANCE_WEEK_START, i)) for i in range(ATTENDANCE_DAYS)]


def create_leave_applications():
	from hrms.hr.doctype.leave_application.leave_application import get_leave_approver

	frappe.set_user(TEST_HR_USER)  # approve as the department leave approver
	try:
		for first_name, leave_type, from_date, to_date, _days in LEAVE_APPLICATIONS:
			employee = get_employee_by_first_name(first_name)
			if frappe.db.exists(
				"Leave Application",
				{"employee": employee, "leave_type": leave_type, "from_date": from_date, "docstatus": 1},
			):
				continue

			application = frappe.new_doc("Leave Application")
			application.update(
				{
					"employee": employee,
					"leave_type": leave_type,
					"from_date": from_date,
					"to_date": to_date,
					"posting_date": add_days(from_date, -3),
					"company": COMPANY_NAME,
					"leave_approver": get_leave_approver(employee),
					"description": "Pilot sample leave",
					"follow_via_email": 0,
					"status": "Approved",
				}
			)
			application.insert()
			application.submit()
	finally:
		frappe.set_user("Administrator")


def mark_week_attendance():
	dates = get_attendance_dates()
	for idx, employee in enumerate(get_active_employees()):
		for day, date in enumerate(dates):
			if employee.date_of_joining and date < getdate(employee.date_of_joining):
				continue
			if frappe.db.exists(
				"Attendance", {"employee": employee.name, "attendance_date": date, "docstatus": ["!=", 2]}
			):
				continue

			attendance = frappe.new_doc("Attendance")
			attendance.update(
				{
					"employee": employee.name,
					"attendance_date": date,
					"company": COMPANY_NAME,
					# a few work-from-home days so the week isn't uniform
					"status": "Work From Home" if (idx + day) % 7 == 3 else "Present",
				}
			)
			attendance.insert(ignore_permissions=True)
			attendance.submit()


def setup_expense_accounts():
	abbr = frappe.db.get_value("Company", COMPANY_NAME, "abbr")
	for expense_type, account_name in EXPENSE_ACCOUNTS.items():
		claim_type = frappe.get_doc("Expense Claim Type", expense_type)
		if any(row.company == COMPANY_NAME for row in claim_type.accounts):
			continue
		claim_type.append("accounts", {"company": COMPANY_NAME, "default_account": f"{account_name} - {abbr}"})
		claim_type.save(ignore_permissions=True)

	if not frappe.db.get_value("Company", COMPANY_NAME, "default_expense_claim_payable_account"):
		frappe.db.set_value(
			"Company", COMPANY_NAME, "default_expense_claim_payable_account", f"Creditors - {abbr}"
		)


def get_expense_claim():
	return frappe.db.get_value(
		"Expense Claim",
		{"company": COMPANY_NAME, "remark": EXPENSE_CLAIM_REMARK, "docstatus": 1},
	)


def create_expense_claim():
	"""Approve, submit (GL entries) and pay one claim — the full expense flow."""
	from hrms.hr.doctype.expense_claim.expense_claim import make_bank_entry

	if not (claim_name := get_expense_claim()):
		employee = frappe.db.get_value(
			"Employee", {"company_email": TEST_EMPLOYEE["company_email"], "company": COMPANY_NAME}
		)
		claim = frappe.new_doc("Expense Claim")
		claim.update(
			{
				"employee": employee,
				"company": COMPANY_NAME,
				"posting_date": EXPENSE_CLAIM_DATE,
				"expense_approver": TEST_HR_USER,
				"payable_account": frappe.db.get_value(
					"Company", COMPANY_NAME, "default_expense_claim_payable_account"
				),
				"cost_center": frappe.db.get_value("Company", COMPANY_NAME, "cost_center"),
				"remark": EXPENSE_CLAIM_REMARK,
				"approval_status": "Approved",
			}
		)
		for expense_type, amount, description in EXPENSE_CLAIM_ITEMS:
			claim.append(
				"expenses",
				{
					"expense_date": EXPENSE_CLAIM_DATE,
					"expense_type": expense_type,
					"description": description,
					"amount": amount,
					"sanctioned_amount": amount,
					# GL booking checks the row cost center, not the header one
					"cost_center": claim.cost_center,
				},
			)
		claim.insert(ignore_permissions=True)
		claim.submit()
		claim_name = claim.name

	if frappe.db.get_value("Expense Claim", claim_name, "status") != "Paid":
		entry = frappe.get_doc(make_bank_entry("Expense Claim", claim_name))
		entry.posting_date = EXPENSE_CLAIM_DATE
		entry.cheque_no = f"PILOT-{claim_name}"
		entry.cheque_date = EXPENSE_CLAIM_DATE
		entry.insert(ignore_permissions=True)
		entry.submit()


# Verification
# ------------


def verify_day2():
	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	employees = get_active_employees()
	checks = [
		(f"{TARGET_HEADCOUNT} active employees (got {len(employees)})", len(employees) == TARGET_HEADCOUNT),
	]

	for department_name in DEPARTMENTS:
		count = frappe.db.count(
			"Employee", {"company": COMPANY_NAME, "status": "Active", "department": get_department(department_name)}
		)
		checks.append((f"Department {department_name} has employees ({count})", count > 0))
	for designation in DESIGNATIONS:
		count = frappe.db.count(
			"Employee", {"company": COMPANY_NAME, "status": "Active", "designation": designation}
		)
		checks.append((f"Designation {designation} has employees ({count})", count > 0))

	# Onboarding
	onboarding = frappe.db.get_value(
		"Employee Onboarding",
		{"company": COMPANY_NAME, "job_applicant": ["is", "set"], "docstatus": 1},
		["name", "boarding_status", "employee", "project"],
		as_dict=True,
	)
	checks.append(("Employee Onboarding submitted", bool(onboarding)))
	if onboarding:
		open_tasks = frappe.db.count("Task", {"project": onboarding.project, "status": ["!=", "Completed"]})
		checks += [
			(f"{onboarding.name} status Completed", onboarding.boarding_status == "Completed"),
			(f"{onboarding.name} created employee {onboarding.employee}", bool(onboarding.employee)),
			(
				"Onboarded employee is active",
				frappe.db.get_value("Employee", onboarding.employee, "status") == "Active",
			),
			(f"All onboarding tasks completed ({open_tasks} open)", bool(onboarding.project) and not open_tasks),
		]

	# Employee logins: own record plus their reports (Employee is a reports_to tree and the
	# User Permission on Employee applies to descendants)
	from frappe.utils.nestedset import get_descendants_of

	for employee in get_login_employees():
		user_id = frappe.db.get_value("Employee", employee, "user_id")
		expected = sorted([employee, *get_descendants_of("Employee", employee)])
		visible = []
		if user_id:
			frappe.set_user(user_id)
			try:
				visible = sorted(frappe.get_list("Employee", pluck="name"))
			finally:
				frappe.set_user("Administrator")
		checks += [
			(f"{employee} has login {user_id}", bool(user_id) and "Employee" in frappe.get_roles(user_id)),
			(f"{user_id} sees only own record + reports ({visible})", visible == expected),
		]

	# Employee list search/filter as the HR user (same get_list the list view uses)
	frappe.set_user(TEST_HR_USER)
	try:
		research = frappe.get_list(
			"Employee", filters={"company": COMPANY_NAME, "department": get_department("Research")}, pluck="name"
		)
		rms = frappe.get_list(
			"Employee",
			filters={"company": COMPANY_NAME, "designation": "Relationship Manager", "status": "Active"},
			pluck="name",
		)
		search = frappe.get_list(
			"Employee",
			filters={"company": COMPANY_NAME},
			or_filters={"employee_name": ["like", "%kapoor%"], "name": ["like", "%kapoor%"]},
			pluck="name",
		)
		visible = frappe.get_list("Employee", filters={"company": COMPANY_NAME}, pluck="name")
	finally:
		frappe.set_user("Administrator")
	checks += [
		(f"HR user sees all {TARGET_HEADCOUNT} employees (got {len(visible)})", len(visible) == TARGET_HEADCOUNT),
		(f"Filter department=Research -> 3 (got {len(research)})", len(research) == 3),
		(f"Filter designation=Relationship Manager -> 5 (got {len(rms)})", len(rms) == 5),
		(f"Search 'kapoor' -> 1 (got {len(search)})", len(search) == 1),
	]

	# Attendance
	dates = get_attendance_dates()
	missing = [
		(employee.name, date)
		for employee in employees
		for date in dates
		if not (employee.date_of_joining and date < getdate(employee.date_of_joining))
		and not frappe.db.exists(
			"Attendance", {"employee": employee.name, "attendance_date": date, "docstatus": 1}
		)
	]
	checks.append((f"Attendance marked {dates[0]} to {dates[-1]} for everyone ({len(missing)} missing)", not missing))

	# Leave
	for first_name, leave_type, from_date, to_date, days in LEAVE_APPLICATIONS:
		employee = get_employee_by_first_name(first_name)
		approved = frappe.db.exists(
			"Leave Application",
			{"employee": employee, "leave_type": leave_type, "from_date": from_date, "status": "Approved", "docstatus": 1},
		)
		expected = LEAVE_TYPES[leave_type]["max_leaves_allowed"] - days
		balance = get_leave_balance_on(employee, leave_type, to_date)
		on_leave = frappe.db.count(
			"Attendance",
			{"employee": employee, "status": "On Leave", "attendance_date": ["between", [from_date, to_date]], "docstatus": 1},
		)
		checks += [
			(f"{first_name} {leave_type} {from_date} approved", bool(approved)),
			(f"{first_name} {leave_type} balance = {expected} (got {balance})", balance == expected),
			(f"{first_name} attendance On Leave for {days} day(s) (got {on_leave})", on_leave == days),
		]

	# Expense claim
	claim = get_expense_claim()
	checks.append(("Expense claim submitted", bool(claim)))
	if claim:
		values = frappe.db.get_value("Expense Claim", claim, ["approval_status", "status"], as_dict=True)
		checks += [
			(f"{claim} approved", values.approval_status == "Approved"),
			(f"{claim} paid (status {values.status})", values.status == "Paid"),
			(
				f"{claim} GL entries posted",
				bool(frappe.db.exists("GL Entry", {"voucher_type": "Expense Claim", "voucher_no": claim, "is_cancelled": 0})),
			),
		]

	for label, ok in checks:
		print(f"[{'PASS' if ok else 'FAIL'}] {label}")
	print(f"{sum(ok for _, ok in checks)}/{len(checks)} checks passed")
