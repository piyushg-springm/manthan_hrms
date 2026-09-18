// Client brand on the desk. frappe.boot.manthan_brand is only set for users who should see it
// (manthan_hrms.branding.boot.extend_bootinfo), so every other user keeps the default look.
(function () {
	const brand = frappe.boot && frappe.boot.manthan_brand;
	if (!brand) return;

	const root = document.documentElement;
	root.classList.add("manthan-branded");
	root.style.setProperty("--primary", brand.primary);
	// white text sits on these, so they use the contrast-checked shade
	root.style.setProperty("--primary-color", brand.button);
	root.style.setProperty("--btn-primary", brand.button);
	root.style.setProperty("--border-primary", brand.button);

	document.querySelectorAll('link[rel~="icon"]').forEach((link) => {
		link.href = brand.favicon;
	});
})();
