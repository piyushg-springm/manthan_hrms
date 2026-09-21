"""Custom fields for the advisory-firm features (pilot Sprint 6)."""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

NISM_CERTIFICATIONS = [
	"NISM-Series-V-A: Mutual Fund Distributors",
	"NISM-Series-X-A: Investment Adviser (Level 1)",
	"NISM-Series-X-B: Investment Adviser (Level 2)",
	"NISM-Series-XV: Research Analyst",
	"Other",
]

CUSTOM_FIELDS = {
	# Feature 1: Regulatory Certification & License Tracker
	"Employee": [
		{
			"fieldname": "regulatory_certification_section",
			"label": "Regulatory Certification",
			"fieldtype": "Section Break",
			"insert_after": "reports_to",
			"collapsible": 1,
		},
		{
			"fieldname": "nism_certification",
			"label": "NISM Certification",
			"fieldtype": "Select",
			"options": "\n" + "\n".join(NISM_CERTIFICATIONS),
			"insert_after": "regulatory_certification_section",
		},
		{
			"fieldname": "nism_certificate_no",
			"label": "NISM Certificate No",
			"fieldtype": "Data",
			"insert_after": "nism_certification",
		},
		{
			"fieldname": "nism_valid_upto",
			"label": "NISM Valid Upto",
			"fieldtype": "Date",
			"insert_after": "nism_certificate_no",
		},
		{
			"fieldname": "regulatory_certification_cb",
			"fieldtype": "Column Break",
			"insert_after": "nism_valid_upto",
		},
		{
			"fieldname": "arn_number",
			"label": "ARN Number",
			"fieldtype": "Data",
			"insert_after": "regulatory_certification_cb",
		},
		{
			"fieldname": "euin_number",
			"label": "EUIN",
			"fieldtype": "Data",
			"insert_after": "arn_number",
		},
		{
			"fieldname": "arn_valid_upto",
			"label": "ARN / EUIN Valid Upto",
			"fieldtype": "Date",
			"insert_after": "euin_number",
		},
		{
			"fieldname": "regulatory_codes_cb",
			"fieldtype": "Column Break",
			"insert_after": "arn_valid_upto",
		},
		{
			"fieldname": "ria_code",
			"label": "RIA Code",
			"fieldtype": "Data",
			"insert_after": "regulatory_codes_cb",
		},
		{
			"fieldname": "pms_code",
			"label": "PMS Code",
			"fieldtype": "Data",
			"insert_after": "ria_code",
		},
		{
			"fieldname": "ra_code",
			"label": "RA Code",
			"fieldtype": "Data",
			"insert_after": "pms_code",
		},
		{
			"fieldname": "aif_code",
			"label": "AIF Code",
			"fieldtype": "Data",
			"insert_after": "ra_code",
		},
	],
	# Feature 3: Client Book Handover & Exit Compliance Checklist
	"Employee Separation": [
		{
			"fieldname": "exit_compliance_section",
			"label": "Advisory Exit Compliance",
			"fieldtype": "Section Break",
			"insert_after": "exit_interview",
		},
		{
			"fieldname": "client_book_handed_over",
			"label": "Client Book Handed Over",
			"fieldtype": "Check",
			"insert_after": "exit_compliance_section",
		},
		{
			"fieldname": "handover_to",
			"label": "Handed Over To",
			"fieldtype": "Link",
			"options": "Employee",
			"insert_after": "client_book_handed_over",
		},
		{
			"fieldname": "handover_to_name",
			"label": "Handed Over To (Name)",
			"fieldtype": "Data",
			"fetch_from": "handover_to.employee_name",
			"read_only": 1,
			"insert_after": "handover_to",
		},
		{
			"fieldname": "clients_handed_over",
			"label": "Clients Handed Over",
			"fieldtype": "Int",
			"insert_after": "handover_to_name",
		},
		{
			"fieldname": "handover_date",
			"label": "Handover Date",
			"fieldtype": "Date",
			"insert_after": "clients_handed_over",
		},
		{
			"fieldname": "exit_compliance_cb",
			"fieldtype": "Column Break",
			"insert_after": "handover_date",
		},
		{
			"fieldname": "non_solicitation_signed",
			"label": "Non-Solicitation Acknowledgement Signed",
			"fieldtype": "Check",
			"insert_after": "exit_compliance_cb",
		},
		{
			"fieldname": "non_solicitation_signed_on",
			"label": "Non-Solicitation Signed On",
			"fieldtype": "Date",
			"insert_after": "non_solicitation_signed",
		},
		{
			"fieldname": "system_access_revoked",
			"label": "System Access Revoked",
			"fieldtype": "Check",
			"insert_after": "non_solicitation_signed_on",
		},
		{
			"fieldname": "system_access_revoked_on",
			"label": "System Access Revoked On",
			"fieldtype": "Date",
			"insert_after": "system_access_revoked",
		},
	],
}


def make_custom_fields():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=True)
