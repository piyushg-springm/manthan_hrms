"""Brand assets and colours, taken from manthan-os-monorepo `packages/branding` (tenants/*.ts, assets/*).

Logos are copied into public/images/brands; large PNGs were resized for the desk navbar.
"""

import frappe

ASSETS = "/assets/manthan_hrms/images/brands"

BRANDS = {
	"manthan": {
		"name": "Manthan",
		"logo": f"{ASSETS}/manthan/logo.svg",
		"nav_logo": f"{ASSETS}/manthan/nav-logo.svg",
		"favicon": f"{ASSETS}/manthan/favicon.ico",
		# primary, primaryDark, secondaryDark
		"shades": ["#30AB84", "#268A6A", "#1E6E55"],
	},
	"prudeno": {
		"name": "Prudeno Wealth",
		"logo": f"{ASSETS}/prudeno/logo.png",
		"nav_logo": f"{ASSETS}/prudeno/nav-logo.png",
		"favicon": f"{ASSETS}/prudeno/favicon.ico",
		"shades": ["#1DB390", "#0C7987"],
	},
	"nswealth": {
		"name": "NS Wealth",
		"logo": f"{ASSETS}/nswealth/logo.png",
		"nav_logo": f"{ASSETS}/nswealth/nav-logo.png",
		"favicon": f"{ASSETS}/nswealth/favicon.ico",
		"shades": ["#5B8A37", "#4A702D"],
	},
}

# WCAG 1.4.3: Frappe draws white labels on --btn-primary
MIN_TEXT_CONTRAST = 4.5


def get_brand(key):
	brand = frappe._dict(BRANDS[key], key=key)
	brand.primary = brand.shades[0]
	# first shade dark enough for white text, else the darkest one
	brand.button = next(
		(shade for shade in brand.shades if contrast_with_white(shade) >= MIN_TEXT_CONTRAST), brand.shades[-1]
	)
	return brand


def contrast_with_white(hex_color):
	def channel(value):
		value /= 255
		return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

	red, green, blue = (channel(int(hex_color[i : i + 2], 16)) for i in (1, 3, 5))
	luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
	return 1.05 / (luminance + 0.05)
