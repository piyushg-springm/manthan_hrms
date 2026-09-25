"""Pilot Day 3 setup (Sprint 5 + Sprint 6) for company Prudeno Wealth.

Idempotent: every step checks for an existing record first, so it is safe to re-run.
Sample data is scoped to COMPANY_NAME. Site-wide pieces: Payroll Settings statutory toggles
(multi-company gated to Prudeno Wealth), the Income Tax component flag, custom fields, the
Fit and Proper Declaration DocType, its workflow and the reviewer role.

    bench --site prudeno-prod.localhost clear-cache
    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day3.run_sprint5
    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day3.run_sprint6
    bench --site prudeno-prod.localhost execute manthan_hrms.setup.day3.verify_day3
"""

import frappe
from frappe.utils import add_days, flt, getdate, today

from manthan_hrms.setup.custom_fields import NISM_CERTIFICATIONS, make_custom_fields
from manthan_hrms.setup.day1 import COMPANY_NAME, HR_ROLE_PROFILE, TEST_HR_USER
from manthan_hrms.setup.day2 import get_active_employees, get_employee_by_first_name

CURRENCY = "INR"
PAYROLL_PERIOD = f"{COMPANY_NAME} FY 2026-27"
PAYROLL_PERIOD_START = "2026-04-01"
PAYROLL_PERIOD_END = "2027-03-31"
SOURCE_TAX_SLAB = "New Tax Regime: 2025-2026"
TAX_SLAB = f"{COMPANY_NAME} New Regime 2026-27"
SALARY_STRUCTURE = f"{COMPANY_NAME} Standard"
EMPLOYMENT_STATE = "Maharashtra"

# Structure formulas: Basic = base * BASIC_SHARE, HRA = the rest
BASIC_SHARE = 0.6
DEDUCTION_ACCOUNTS = {
	"Provident Fund": "PF Payable",
	"Professional Tax": "Professional Tax Payable",
	"Income Tax": "TDS Payable",
}
EARNING_COMPONENTS = ("Basic", "House Rent Allowance")

# Monthly gross (made up). Kept out of the ₹12L-₹12.75L projected-taxable band, where hrms v15
# skips marginal relief (see apps/india_payroll/BACKPORT_V15.md).
MONTHLY_GROSS = {
	"Test": 60000,
	"Aarav": 250000,
	"Priya": 90000,
	"Rohan": 75000,
	"Sneha": 40000,
	"Kavya": 200000,
	"Siddharth": 70000,
	"Ananya": 120000,
	"Vikram": 50000,
	"Rahul": 35000,
	"Meera": 80000,
	"Arjun": 38000,
	"Neha": 150000,
	"Karan": 55000,
	"Ishita": 45000,
}

PAYROLL_START = "2026-09-01"
PAYROLL_END = "2026-09-30"
HAND_CHECK_EMPLOYEES = ("Aarav", "Priya", "Ishita")

# Feature 1: made-up firm ARN (on Company) and certificates; one expiry is moved to today + REMINDER_DAYS at run time
REMINDER_DAYS = 30
REMINDER_EMPLOYEE = "Priya"
COMPANY_ARN = "ARN-PILOT-0001"
CERTIFICATIONS = {
	"Aarav": (NISM_CERTIFICATIONS[0], "NISM-VA-PILOT-0001", "2027-08-31", "E-PILOT-0001", "2028-03-31"),
	"Priya": (NISM_CERTIFICATIONS[0], "NISM-VA-PILOT-0002", None, "E-PILOT-0002", "2028-06-30"),
	"Rohan": (NISM_CERTIFICATIONS[0], "NISM-VA-PILOT-0003", "2027-02-28", "E-PILOT-0003", "2027-12-31"),
	"Kavya": (NISM_CERTIFICATIONS[1], "NISM-XA-PILOT-0004", "2027-05-31", None, None),
	"Siddharth": (NISM_CERTIFICATIONS[1], "NISM-XA-PILOT-0005", "2027-11-30", None, None),
}
NOTIFICATIONS = {
	"NISM Certificate Expiring": (
		"nism_valid_upto",
		"NISM certificate of {{ doc.employee_name }} expires on {{ frappe.utils.formatdate(doc.nism_valid_upto) }}",
	),
	"ARN/EUIN Renewal Due": (
		"arn_valid_upto",
		"ARN/EUIN of {{ doc.employee_name }} is due for renewal on {{ frappe.utils.formatdate(doc.arn_valid_upto) }}",
	),
}

# Feature 2
FIT_AND_PROPER = "Fit and Proper Declaration"
FIT_AND_PROPER_WORKFLOW = "Fit and Proper Review"
REVIEWER_ROLE = "Manthan Compliance Reviewer"  # given to the pilot HR user only; real users hold HR/Compliance roles
REVIEWER_ROLE_PROFILE = "Manthan HR Reviewer"
DECLARATION_EMPLOYEE = "Priya"
FINANCIAL_YEAR = "2026-27"

# Feature 3
EXIT_EMPLOYEE = "Rohan"
HANDOVER_TO = "Priya"
CLIENTS_HANDED_OVER = 42
EXIT_BLOCKED_COMMENT = "Pilot check: submit with incomplete exit checklist was blocked"


def get_company_value(fieldname):
	return frappe.db.get_value("Company", COMPANY_NAME, fieldname)


def get_account(account_name):
	return f"{account_name} - {get_company_value('abbr')}"


# Sprint 5
# --------


def run_sprint5():
	configure_payroll_settings()
	create_payroll_period()
	create_tax_slab()
	setup_component_accounts()
	create_salary_structure()
	assign_salary_structure()
	frappe.db.commit()
	print("Sprint 5 setup done.")


def configure_payroll_settings():
	"""Turn on india_payroll EPF + PT for Prudeno Wealth only (multi-company mode, one company row)."""
	settings = frappe.get_single("Payroll Settings")
	changed = False
	for fieldname in ("enable_epf", "enable_professional_tax", "enable_multi_company_payroll"):
		if not settings.get(fieldname):
			settings.set(fieldname, 1)
			changed = True
	if not any(row.company == COMPANY_NAME for row in settings.company_payroll_settings):
		settings.append("company_payroll_settings", {"company": COMPANY_NAME})
		changed = True
	if changed:
		settings.save(ignore_permissions=True)


def create_payroll_period():
	if frappe.db.exists("Payroll Period", PAYROLL_PERIOD):
		return
	period = frappe.new_doc("Payroll Period")
	period.update({"company": COMPANY_NAME, "start_date": PAYROLL_PERIOD_START, "end_date": PAYROLL_PERIOD_END})
	period.insert(ignore_permissions=True, set_name=PAYROLL_PERIOD)


def create_tax_slab():
	"""FY 2026-27 new regime: same slabs, rebate limit, standard exemption and cess as FY 2025-26."""
	if frappe.db.exists("Income Tax Slab", {"name": TAX_SLAB, "docstatus": 1}):
		return
	slab = frappe.copy_doc(frappe.get_doc("Income Tax Slab", SOURCE_TAX_SLAB))
	slab.update({"company": COMPANY_NAME, "effective_from": PAYROLL_PERIOD_START, "disabled": 0})
	slab.insert(ignore_permissions=True, set_name=TAX_SLAB)
	slab.submit()


def setup_component_accounts():
	parent_account = get_account("Duties and Taxes")
	for account_name in DEDUCTION_ACCOUNTS.values():
		if frappe.db.exists("Account", get_account(account_name)):
			continue
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent_account,
				"company": COMPANY_NAME,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	accounts = {component: get_account("Salary") for component in EARNING_COMPONENTS}
	accounts.update({component: get_account(name) for component, name in DEDUCTION_ACCOUNTS.items()})

	for component_name, account in accounts.items():
		component = frappe.get_doc("Salary Component", component_name)
		changed = False
		if not any(row.company == COMPANY_NAME for row in component.accounts):
			component.append("accounts", {"company": COMPANY_NAME, "account": account})
			changed = True
		# TDS is computed from the tax slab only when the component is variable
		if component_name == "Income Tax" and not component.variable_based_on_taxable_salary:
			component.variable_based_on_taxable_salary = 1
			changed = True
		if changed:
			component.save(ignore_permissions=True)


def create_salary_structure():
	if frappe.db.exists("Salary Structure", {"name": SALARY_STRUCTURE, "docstatus": 1}):
		return

	structure = frappe.new_doc("Salary Structure")
	structure.update(
		{
			"company": COMPANY_NAME,
			"payroll_frequency": "Monthly",
			"currency": CURRENCY,
			"is_active": "Yes",
			"payroll_payable_account": get_company_value("default_payroll_payable_account"),
		}
	)
	structure.append(
		"earnings",
		{"salary_component": "Basic", "amount_based_on_formula": 1, "formula": f"base * {BASIC_SHARE}"},
	)
	structure.append(
		"earnings",
		{
			"salary_component": "House Rent Allowance",
			"amount_based_on_formula": 1,
			"formula": f"base * {round(1 - BASIC_SHARE, 2)}",
		},
	)
	# PF and PT amounts are written by india_payroll's regional deductions; Income Tax by the tax slab
	structure.append("deductions", {"salary_component": "Provident Fund", "amount": 0})
	structure.append("deductions", {"salary_component": "Professional Tax", "amount": 0})
	structure.append("deductions", {"salary_component": "Income Tax", "variable_based_on_taxable_salary": 1})
	structure.insert(ignore_permissions=True, set_name=SALARY_STRUCTURE)
	structure.submit()


def get_tax_slab_values():
	slab = frappe.get_doc("Income Tax Slab", TAX_SLAB)
	return frappe._dict(
		standard_exemption=flt(slab.standard_tax_exemption_amount),
		relief_limit=flt(slab.tax_relief_limit),
		marginal_relief_limit=flt(slab.get("marginal_relief_limit")),
		slabs=[(flt(row.from_amount), flt(row.to_amount), flt(row.percent_deduction)) for row in slab.slabs],
		cess=sum(flt(row.percent) for row in slab.other_taxes_and_charges),
	)


def get_remaining_months():
	start, end = getdate(PAYROLL_START), getdate(PAYROLL_PERIOD_END)
	return (end.year - start.year) * 12 + end.month - start.month + 1


def get_projected_taxable(gross, tax=None):
	tax = tax or get_tax_slab_values()
	return gross * get_remaining_months() - tax.standard_exemption


def assign_salary_structure():
	active = {employee.name for employee in get_active_employees()}
	employees = {first_name: get_employee_by_first_name(first_name) for first_name in MONTHLY_GROSS}
	if missing := active - set(employees.values()):
		frappe.throw(f"MONTHLY_GROSS has no salary for active employees: {', '.join(sorted(missing))}")

	tax = get_tax_slab_values()
	for first_name, gross in MONTHLY_GROSS.items():
		if tax.relief_limit < get_projected_taxable(gross, tax) <= tax.marginal_relief_limit:
			frappe.throw(f"{first_name}: gross {gross} falls in the marginal relief band hrms v15 does not handle")

	for first_name, gross in MONTHLY_GROSS.items():
		employee = employees[first_name]
		if frappe.db.exists(
			"Salary Structure Assignment",
			{"employee": employee, "salary_structure": SALARY_STRUCTURE, "docstatus": 1},
		):
			continue

		date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
		assignment = frappe.new_doc("Salary Structure Assignment")
		assignment.update(
			{
				"employee": employee,
				"salary_structure": SALARY_STRUCTURE,
				"company": COMPANY_NAME,
				"currency": CURRENCY,
				"from_date": max(getdate(date_of_joining), getdate(PAYROLL_PERIOD_START)),
				"base": gross,
				"income_tax_slab": TAX_SLAB,
				"employment_state": EMPLOYMENT_STATE,
				"epf_applicable": 1,
			}
		)
		assignment.insert(ignore_permissions=True)
		assignment.submit()


# Sprint 6
# --------


def run_sprint6():
	run_payroll()
	frappe.db.commit()

	make_custom_fields()
	set_certification_data()
	create_certification_notifications()
	send_certification_reminders()
	frappe.db.commit()

	setup_fit_and_proper()
	frappe.db.commit()
	test_fit_and_proper_declaration()
	frappe.db.commit()

	test_exit_checklist()
	frappe.db.commit()
	print("Sprint 6 setup done.")


def get_payroll_entry():
	return frappe.db.get_value(
		"Payroll Entry", {"company": COMPANY_NAME, "start_date": PAYROLL_START, "docstatus": 1}
	)


def run_payroll():
	"""One Payroll Entry for September 2026: slips created on submit, then submitted (accrual JE)."""
	if name := get_payroll_entry():
		entry = frappe.get_doc("Payroll Entry", name)
	else:
		entry = frappe.new_doc("Payroll Entry")
		entry.update(
			{
				"company": COMPANY_NAME,
				"posting_date": PAYROLL_END,
				"payroll_frequency": "Monthly",
				"start_date": PAYROLL_START,
				"end_date": PAYROLL_END,
				"currency": CURRENCY,
				"exchange_rate": 1,
				"cost_center": get_company_value("cost_center"),
				"payroll_payable_account": get_company_value("default_payroll_payable_account"),
				"payment_account": get_account("Cash"),
			}
		)
		entry.fill_employee_details()
		entry.insert(ignore_permissions=True)
		entry.submit()  # on_submit creates the salary slips (synchronously for <= 30 employees)

	if frappe.db.count("Salary Slip", {"payroll_entry": entry.name, "docstatus": 0}):
		# payslip emails would go to made-up addresses with no outgoing account configured
		frappe.flags.mute_emails = True
		try:
			entry.reload()
			entry.submit_salary_slips()
		finally:
			frappe.flags.mute_emails = False


def set_certification_data():
	company = frappe.get_doc("Company", COMPANY_NAME)
	company.arn_number = COMPANY_ARN
	company.save()  # on_update pushes the ARN to every employee of the company
	for first_name, (certification, certificate_no, nism_valid_upto, euin, arn_valid_upto) in CERTIFICATIONS.items():
		if first_name == REMINDER_EMPLOYEE:
			nism_valid_upto = add_days(today(), REMINDER_DAYS)
		frappe.db.set_value(
			"Employee",
			get_employee_by_first_name(first_name),
			{
				"nism_certification": certification,
				"nism_certificate_no": certificate_no,
				"nism_valid_upto": nism_valid_upto,
				"euin_number": euin,
				"arn_valid_upto": arn_valid_upto,
			},
		)


def create_certification_notifications():
	for name, (date_field, subject) in NOTIFICATIONS.items():
		if frappe.db.exists("Notification", name):
			continue
		notification = frappe.new_doc("Notification")
		notification.update(
			{
				"subject": subject,
				"document_type": "Employee",
				"event": "Days Before",
				"date_changed": date_field,
				"days_in_advance": REMINDER_DAYS,
				"channel": "System Notification",
				"condition": f'doc.company == "{COMPANY_NAME}" and doc.status == "Active"',
				"message": subject,
				"module": "Manthan HRMS",
				"enabled": 1,
			}
		)
		notification.append("recipients", {"cc": TEST_HR_USER})
		notification.insert(ignore_permissions=True, set_name=name)


def get_reminder_log(employee, since=None):
	"""since: only reminders sent on/after this date. The send path passes today so a re-run does not
	notify twice; verification passes nothing, because the reminder stays valid on later days."""
	filters = {
		"for_user": TEST_HR_USER,
		"document_type": "Employee",
		"document_name": employee,
		"subject": ["like", "%NISM%"],
	}
	if since:
		filters["creation"] = [">=", since]
	return frappe.db.exists("Notification Log", filters)


def send_certification_reminders():
	"""What the daily scheduler does, run only for the two certification notifications."""
	for name in NOTIFICATIONS:
		notification = frappe.get_doc("Notification", name)
		for doc in notification.get_documents_for_today():
			if not get_reminder_log(doc.name, since=today()):
				notification.send(doc)


def setup_fit_and_proper():
	if not frappe.db.exists("Role", REVIEWER_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": REVIEWER_ROLE, "desk_access": 1}).insert(
			ignore_permissions=True
		)
	assign_reviewer_role_profile()

	frappe.reload_doc("manthan_hrms", "doctype", "fit_and_proper_declaration")
	create_fit_and_proper_workflow()


def assign_reviewer_role_profile():
	"""A user's Role Profile rewrites their roles on every save, so the reviewer role goes through a
	profile: the standard HR profile's roles plus REVIEWER_ROLE."""
	roles = [row.role for row in frappe.get_doc("Role Profile", HR_ROLE_PROFILE).roles] + [REVIEWER_ROLE]
	if frappe.db.exists("Role Profile", REVIEWER_ROLE_PROFILE):
		profile = frappe.get_doc("Role Profile", REVIEWER_ROLE_PROFILE)
	else:
		profile = frappe.new_doc("Role Profile")
		profile.role_profile = REVIEWER_ROLE_PROFILE

	if {row.role for row in profile.roles} != set(roles):
		profile.set("roles", [{"role": role} for role in roles])
		profile.save(ignore_permissions=True)

	user = frappe.get_doc("User", TEST_HR_USER)
	if user.role_profile_name != REVIEWER_ROLE_PROFILE or REVIEWER_ROLE not in frappe.get_roles(TEST_HR_USER):
		user.role_profile_name = REVIEWER_ROLE_PROFILE
		user.save(ignore_permissions=True)


def create_fit_and_proper_workflow():
	if frappe.db.exists("Workflow", FIT_AND_PROPER_WORKFLOW):
		return

	for state, style in (("Draft", ""), ("Pending Review", "Warning"), ("Approved", "Success"), ("Rejected", "Danger")):
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(
				ignore_permissions=True
			)
	for action in ("Submit for Review", "Approve", "Reject"):
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
				ignore_permissions=True
			)

	workflow = frappe.new_doc("Workflow")
	workflow.update(
		{
			"workflow_name": FIT_AND_PROPER_WORKFLOW,
			"document_type": FIT_AND_PROPER,
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"send_email_alert": 0,
		}
	)
	for state, doc_status, allow_edit in (
		("Draft", "0", "Employee"),
		("Pending Review", "0", REVIEWER_ROLE),
		("Approved", "1", REVIEWER_ROLE),
		("Rejected", "1", REVIEWER_ROLE),
	):
		workflow.append("states", {"state": state, "doc_status": doc_status, "allow_edit": allow_edit})
	for state, action, next_state, allowed in (
		("Draft", "Submit for Review", "Pending Review", "Employee"),
		("Pending Review", "Approve", "Approved", REVIEWER_ROLE),
		("Pending Review", "Reject", "Rejected", REVIEWER_ROLE),
	):
		workflow.append(
			"transitions", {"state": state, "action": action, "next_state": next_state, "allowed": allowed}
		)
	workflow.insert(ignore_permissions=True)


def get_declaration():
	return frappe.db.get_value(
		FIT_AND_PROPER,
		{
			"employee": get_employee_by_first_name(DECLARATION_EMPLOYEE),
			"financial_year": FINANCIAL_YEAR,
			"docstatus": ["!=", 2],
		},
		["name", "workflow_state", "docstatus", "reviewed_by"],
		as_dict=True,
	)


def test_fit_and_proper_declaration():
	"""Employee files the declaration from their own login; the reviewer approves it."""
	from frappe.model.workflow import apply_workflow

	from manthan_hrms.manthan_hrms.doctype.fit_and_proper_declaration.fit_and_proper_declaration import (
		DECLARATION_FIELDS,
	)

	employee = get_employee_by_first_name(DECLARATION_EMPLOYEE)
	if not get_declaration():
		frappe.set_user(frappe.db.get_value("Employee", employee, "user_id"))
		try:
			declaration = frappe.new_doc(FIT_AND_PROPER)
			declaration.update(
				{
					"employee": employee,
					"financial_year": FINANCIAL_YEAR,
					"declaration_date": today(),
					"employee_confirmation": 1,
					**{field: 1 for field in DECLARATION_FIELDS},
				}
			)
			declaration.insert()
			apply_workflow(declaration, "Submit for Review")
		finally:
			frappe.set_user("Administrator")

	declaration = get_declaration()
	if declaration.workflow_state == "Pending Review":
		frappe.set_user(TEST_HR_USER)
		try:
			doc = frappe.get_doc(FIT_AND_PROPER, declaration.name)
			doc.review_remarks = "Pilot review: declarations and NISM/ARN details checked"
			doc.save()
			apply_workflow(doc, "Approve")
		finally:
			frappe.set_user("Administrator")


def get_separation(docstatus):
	return frappe.db.get_value(
		"Employee Separation",
		{"employee": get_employee_by_first_name(EXIT_EMPLOYEE), "company": COMPANY_NAME, "docstatus": docstatus},
	)


def test_exit_checklist():
	"""Dummy advisor exit: submit is blocked until the checklist is complete, then goes through."""
	if get_separation(1):
		return

	if name := get_separation(0):
		separation = frappe.get_doc("Employee Separation", name)
	else:
		separation = frappe.new_doc("Employee Separation")
		separation.update(
			{
				"employee": get_employee_by_first_name(EXIT_EMPLOYEE),
				"company": COMPANY_NAME,
				"resignation_letter_date": "2026-09-15",
				"boarding_begins_on": "2026-09-15",
				"notify_users_by_email": 0,
			}
		)
		separation.insert(ignore_permissions=True)

	if not frappe.db.exists(
		"Comment", {"reference_doctype": "Employee Separation", "reference_name": separation.name, "content": EXIT_BLOCKED_COMMENT}
	):
		try:
			separation.submit()
		except frappe.ValidationError:
			frappe.clear_messages()
			separation.reload()
			separation.add_comment("Comment", EXIT_BLOCKED_COMMENT)
		else:
			frappe.throw("Employee Separation was submitted with an incomplete exit checklist")

	separation.update(
		{
			"client_book_handed_over": 1,
			"handover_to": get_employee_by_first_name(HANDOVER_TO),
			"clients_handed_over": CLIENTS_HANDED_OVER,
			"handover_date": "2026-09-25",
			"non_solicitation_signed": 1,
			"non_solicitation_signed_on": "2026-09-25",
			"system_access_revoked": 1,
			"system_access_revoked_on": "2026-09-30",
		}
	)
	separation.save(ignore_permissions=True)
	separation.submit()


# Verification
# ------------


def calculate_expected_slip(gross, tax):
	"""Hand calculation, independent of hrms: statutory rates and the FY 2026-27 slab rates."""
	basic = flt(gross * BASIC_SHARE, 2)
	hra = flt(gross - basic, 2)
	pf = int(min(basic, 15000) * 0.12 + 0.5)  # EPF 12% of PF wage capped at ₹15,000
	pt = 200 if gross > 10000 else 0  # Maharashtra, not February

	months = get_remaining_months()
	annual_taxable = get_projected_taxable(gross, tax)
	annual_tax = 0.0
	if annual_taxable > tax.relief_limit:
		for from_amount, to_amount, percent in tax.slabs:
			lower = max(from_amount - 1, 0)
			upper = to_amount or annual_taxable
			if annual_taxable > lower:
				annual_tax += (min(annual_taxable, upper) - lower) * percent / 100
		annual_tax *= 1 + tax.cess / 100
	income_tax = annual_tax / months

	return frappe._dict(
		basic=basic, hra=hra, pf=pf, pt=pt, income_tax=flt(income_tax, 2), net_pay=flt(gross - pf - pt - income_tax, 2)
	)


def get_slip_values(slip_name):
	slip = frappe.get_doc("Salary Slip", slip_name)
	rows = {row.salary_component: flt(row.amount) for row in slip.earnings + slip.deductions}
	return frappe._dict(
		basic=rows.get("Basic", 0),
		hra=rows.get("House Rent Allowance", 0),
		pf=rows.get("Provident Fund", 0),
		pt=rows.get("Professional Tax", 0),
		income_tax=rows.get("Income Tax", 0),
		net_pay=flt(slip.net_pay),
	)


def verify_day3():
	checks = []
	active = get_active_employees()

	# Sprint 5
	structure_components = frappe.get_all(
		"Salary Detail", {"parenttype": "Salary Structure", "parent": SALARY_STRUCTURE}, pluck="salary_component"
	)
	assignments = frappe.db.count(
		"Salary Structure Assignment", {"company": COMPANY_NAME, "salary_structure": SALARY_STRUCTURE, "docstatus": 1}
	)
	checks += [
		(
			f"Salary structure submitted with {len(structure_components)} components",
			bool(frappe.db.exists("Salary Structure", {"name": SALARY_STRUCTURE, "docstatus": 1}))
			and len(structure_components) >= 5,
		),
		(f"Structure assigned to all {len(active)} employees (got {assignments})", assignments == len(active)),
		(f"Payroll period {PAYROLL_PERIOD} exists", bool(frappe.db.exists("Payroll Period", PAYROLL_PERIOD))),
		(
			f"Tax slab {TAX_SLAB} submitted, effective {PAYROLL_PERIOD_START}",
			frappe.db.get_value("Income Tax Slab", TAX_SLAB, ["docstatus", "effective_from"])
			== (1, getdate(PAYROLL_PERIOD_START)),
		),
	]

	# Payroll run
	entry = get_payroll_entry()
	slips = frappe.get_all(
		"Salary Slip",
		{"company": COMPANY_NAME, "start_date": PAYROLL_START, "docstatus": 1},
		["name", "employee", "employee_name"],
	)
	slip_names = [slip.name for slip in slips]
	without_statutory = [
		slip.employee_name
		for slip in slips
		if not {"Provident Fund", "Professional Tax"}
		<= set(frappe.get_all("Salary Detail", {"parent": slip.name, "parentfield": "deductions", "amount": [">", 0]}, pluck="salary_component"))
	]
	checks += [
		("Payroll Entry for Sep 2026 submitted", bool(entry)),
		(f"{len(active)} salary slips submitted (got {len(slips)})", len(slips) == len(active)),
		(f"Every slip has PF + PT from india_payroll (missing: {without_statutory})", bool(slips) and not without_statutory),
		(
			"Accrual Journal Entry posted",
			bool(entry)
			and bool(frappe.db.exists("Journal Entry Account", {"reference_type": "Payroll Entry", "reference_name": entry, "docstatus": 1})),
		),
		(
			"Income tax deducted for high earners",
			bool(slip_names)
			and bool(frappe.db.exists("Salary Detail", {"parent": ["in", slip_names], "salary_component": "Income Tax", "amount": [">", 0]})),
		),
	]

	# Hand check
	tax = get_tax_slab_values()
	print(f"\nHand check, Sep 2026 ({get_remaining_months()} months left in FY, standard exemption {tax.standard_exemption:,.0f})")
	print(f"{'Employee':<18}{'Field':<12}{'Expected':>12}{'Slip':>12}")
	for first_name in HAND_CHECK_EMPLOYEES:
		employee = get_employee_by_first_name(first_name)
		slip = next((s for s in slips if s.employee == employee), None)
		if not slip:
			checks.append((f"Hand check {first_name}: slip exists", False))
			continue
		expected = calculate_expected_slip(MONTHLY_GROSS[first_name], tax)
		actual = get_slip_values(slip.name)
		for field in expected:
			print(f"{slip.employee_name:<18}{field:<12}{expected[field]:>12,.2f}{actual[field]:>12,.2f}")
		mismatched = [field for field in expected if abs(expected[field] - actual[field]) > 1]
		checks.append((f"Hand check {slip.name} {slip.employee_name} (mismatch: {mismatched})", not mismatched))
	print()

	# Feature 1
	reminder_employee = get_employee_by_first_name(REMINDER_EMPLOYEE)
	checks += [
		(
			"Certification fields on Employee",
			all(frappe.get_meta("Employee").has_field(f) for f in ("nism_certification", "nism_valid_upto", "arn_number", "euin_number", "arn_valid_upto")),
		),
		("Regulatory codes on Company", frappe.get_meta("Company").has_field("arn_number")),
		(
			"Company ARN on all its employees",
			not frappe.db.count("Employee", {"company": COMPANY_NAME, "arn_number": ["!=", COMPANY_ARN]}),
		),
		(
			f"Certificate data on {len(CERTIFICATIONS)} employees",
			frappe.db.count("Employee", {"company": COMPANY_NAME, "nism_certificate_no": ["is", "set"]}) == len(CERTIFICATIONS),
		),
		("Reminder notifications enabled", all(frappe.db.get_value("Notification", n, "enabled") for n in NOTIFICATIONS)),
		(f"Reminder sent to {TEST_HR_USER} for {reminder_employee}", bool(get_reminder_log(reminder_employee))),
	]

	# Feature 2
	declaration = get_declaration() if frappe.db.exists("DocType", FIT_AND_PROPER) else None
	checks += [
		(
			f"Workflow {FIT_AND_PROPER_WORKFLOW} active",
			bool(frappe.db.get_value("Workflow", FIT_AND_PROPER_WORKFLOW, "is_active")),
		),
		(
			f"Fit & Proper Declaration approved ({declaration})",
			bool(declaration)
			and declaration.workflow_state == "Approved"
			and declaration.docstatus == 1
			and declaration.reviewed_by == TEST_HR_USER,
		),
	]

	# Feature 3
	separation = get_separation(1)
	values = (
		frappe.db.get_value(
			"Employee Separation",
			separation,
			["client_book_handed_over", "non_solicitation_signed", "system_access_revoked", "handover_to"],
			as_dict=True,
		)
		if separation
		else {}
	)
	checks += [
		(
			f"Exit separation submitted with full checklist ({separation})",
			bool(separation)
			and values.client_book_handed_over
			and values.non_solicitation_signed
			and values.system_access_revoked
			and values.handover_to == get_employee_by_first_name(HANDOVER_TO),
		),
		(
			"Submit with incomplete checklist was blocked",
			bool(frappe.db.exists("Comment", {"reference_doctype": "Employee Separation", "content": EXIT_BLOCKED_COMMENT})),
		),
		(
			f"{EXIT_EMPLOYEE} still active for payroll",
			frappe.db.get_value("Employee", get_employee_by_first_name(EXIT_EMPLOYEE), "status") == "Active",
		),
	]

	for label, ok in checks:
		print(f"[{'PASS' if ok else 'FAIL'}] {label}")
	print(f"{sum(bool(ok) for _, ok in checks)}/{len(checks)} checks passed")
