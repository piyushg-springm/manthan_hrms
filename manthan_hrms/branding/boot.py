"""Client branding on the desk (pilot Sprint 7).

On a shared site (prudeno-prod.localhost also hosts other Manthan apps and their users) only users on
the Manthan HR module profile get the brand; Website/Navbar Settings are left alone. A dedicated
client site sets `manthan_hrms_dedicated_site` in site_config.json: every user gets the desk brand
and `apply_site_branding` sets the login page logo, favicon, app name and colour.
"""

import frappe

from manthan_hrms.attendance.checkin import get_session_employee
from manthan_hrms.branding.brands import get_brand
from manthan_hrms.setup.clients import MODULE_PROFILE, get_client


def is_dedicated_site():
	return bool(frappe.conf.get("manthan_hrms_dedicated_site"))


def is_manthan_user(user):
	if user == "Guest":
		return False
	return is_dedicated_site() or frappe.db.get_value("User", user, "module_profile") == MODULE_PROFILE


def get_desk_brand(user):
	if not is_manthan_user(user):
		return None
	return get_brand(get_client().brand)


def extend_bootinfo(bootinfo):
	"""Runs on every desk load (after the cached bootinfo is read), so the brand follows the user."""
	if brand := get_desk_brand(frappe.session.user):
		bootinfo.app_logo_url = brand.nav_logo  # navbar logo
		bootinfo.manthan_brand = brand  # colours + favicon, applied by public/js/manthan_branding.js
	if is_manthan_user(frappe.session.user) and get_session_employee():
		bootinfo.manthan_quick_checkin = 1  # check-in card on the HR workspace, public/js/quick_checkin.js


def get_login_head_html(brand):
	# !important: the website bundle defines these on :root too, and it loads after head_html
	return (
		f"<style>:root {{ --primary: {brand.primary} !important; "
		f"--primary-color: {brand.button} !important; --btn-primary: {brand.button} !important; }}</style>"
	)


def apply_site_branding():
	if not is_dedicated_site():
		frappe.throw(
			"Site-wide branding changes the login page for every user of this site. "
			"Set manthan_hrms_dedicated_site in site_config.json only on a dedicated client site."
		)

	brand = get_brand(get_client().brand)
	website = frappe.get_single("Website Settings")
	values = {
		"app_name": brand.name,
		"app_logo": brand.logo,
		"favicon": brand.favicon,
		"head_html": get_login_head_html(brand),
	}
	if any(website.get(field) != value for field, value in values.items()):
		website.update(values)
		website.save(ignore_permissions=True)

	for doctype, field, value in (
		("Navbar Settings", "app_logo", brand.nav_logo),
		("System Settings", "app_name", brand.name),
	):
		if frappe.db.get_single_value(doctype, field) != value:
			frappe.db.set_single_value(doctype, field, value)
