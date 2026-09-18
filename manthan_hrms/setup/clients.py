"""Per-client pilot configuration (Sprint 8 package).

The same setup code builds every client site; `manthan_hrms_client` in the site's site_config.json
picks the client (sites without it are Prudeno Wealth):

    bench --site nswealth.localhost set-config manthan_hrms_client ns-wealth

Kept free of site-level imports: the branding boot hook reads it on every desk load.
"""

import frappe

MODULE_PROFILE = "Manthan HR Only"
DEFAULT_CLIENT = "prudeno-wealth"

CLIENTS = {
	"prudeno-wealth": {
		"company_name": "Prudeno Wealth",
		"company_abbr": "PW",
		"company_domain": "prudenowealth.example",  # fake domain: no real client data in the pilot
		"brand": "prudeno",
	},
	"ns-wealth": {
		"company_name": "NS Wealth",
		"company_abbr": "NSW",
		"company_domain": "nswealth.example",
		"brand": "nswealth",
	},
}


def get_client_key(strict=False):
	"""strict: refuse to guess on a dedicated client site. Setup code passes it, so a site whose
	manthan_hrms_client was never set fails loudly instead of being built as the default client."""
	key = frappe.conf.get("manthan_hrms_client")
	if not key:
		if strict and frappe.conf.get("manthan_hrms_dedicated_site"):
			frappe.throw(
				f"Site {frappe.local.site} is a dedicated client site but site_config.json has no "
				f"manthan_hrms_client. Set it before running setup:\n"
				f"    bench --site {frappe.local.site} set-config manthan_hrms_client <{'|'.join(CLIENTS)}>"
			)
		key = DEFAULT_CLIENT
	if key not in CLIENTS:
		frappe.throw(f"Unknown manthan_hrms_client {key!r} in site_config.json, expected one of: {', '.join(CLIENTS)}")
	return key


def get_client(strict=False):
	key = get_client_key(strict)
	return frappe._dict(CLIENTS[key], key=key)
