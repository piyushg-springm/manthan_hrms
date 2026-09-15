import frappe
from frappe import _

EXIT_CHECKS = {
	"client_book_handed_over": "Client Book Handed Over",
	"non_solicitation_signed": "Non-Solicitation Acknowledgement Signed",
	"system_access_revoked": "System Access Revoked",
}


def validate_exit_checklist(doc, method=None):
	"""An advisor's exit can't be submitted until client book, non-solicitation and access are closed."""
	missing = [label for fieldname, label in EXIT_CHECKS.items() if not doc.get(fieldname)]
	if not doc.get("handover_to"):
		missing.append("Handed Over To")

	if missing:
		frappe.throw(
			_("Complete the exit compliance checklist before submitting: {0}").format(", ".join(missing)),
			title=_("Exit Checklist Incomplete"),
		)
