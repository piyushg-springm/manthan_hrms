# Copyright (c) 2026, Piyush Gupta and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today

DECLARATION_FIELDS = (
	"no_criminal_conviction",
	"no_regulatory_action",
	"no_disciplinary_proceedings",
	"not_insolvent",
	"no_conflict_of_interest",
	"certifications_valid",
)


class FitandProperDeclaration(Document):
	def validate(self):
		self.validate_duplicate()
		self.validate_declarations()

	def before_submit(self):
		# submitted only through the review workflow (Approved / Rejected), so record the reviewer
		self.reviewed_by = frappe.session.user
		self.review_date = today()

	def validate_duplicate(self):
		existing = frappe.db.exists(
			"Fit and Proper Declaration",
			{
				"employee": self.employee,
				"financial_year": self.financial_year,
				"docstatus": ["!=", 2],
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(
				_("{0} already has a declaration for {1}: {2}").format(
					frappe.bold(self.employee_name or self.employee), self.financial_year, existing
				)
			)

	def validate_declarations(self):
		if not self.employee_confirmation:
			frappe.throw(_("Please confirm the declaration is true and complete"))

		unticked = [self.meta.get_label(field) for field in DECLARATION_FIELDS if not self.get(field)]
		if unticked and not (self.disclosures or "").strip():
			frappe.throw(
				_("Explain under Disclosures why these are not ticked: {0}").format("<br>".join(unticked))
			)
