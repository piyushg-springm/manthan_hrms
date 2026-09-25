import frappe

from manthan_hrms.setup.custom_fields import COMPANY_REGULATORY_FIELDS


def sync_regulatory_codes(doc, method=None):
	"""Push the firm's ARN/RIA/PMS/RA/AIF codes to all its employees (read-only there)."""
	if any(doc.has_value_changed(fieldname) for fieldname in COMPANY_REGULATORY_FIELDS):
		update_employees(doc.name, {fieldname: doc.get(fieldname) for fieldname in COMPANY_REGULATORY_FIELDS})


def sync_all_companies():
	"""Backfill: align every employee with its company's codes (fetch_from only refreshes on employee save)."""
	if not frappe.get_meta("Company").has_field(COMPANY_REGULATORY_FIELDS[0]):
		return
	for company in frappe.get_all("Company", fields=["name", *COMPANY_REGULATORY_FIELDS]):
		update_employees(company.pop("name"), company)


def update_employees(company, values):
	employee = frappe.qb.DocType("Employee")
	query = frappe.qb.update(employee).where(employee.company == company)
	for fieldname, value in values.items():
		query = query.set(employee[fieldname], value)
	query.run()
