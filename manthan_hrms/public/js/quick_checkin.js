// One-click Check In / Check Out card on the HR workspace. frappe.boot.manthan_quick_checkin is only
// set for Manthan HR users with an active Employee (manthan_hrms.branding.boot.extend_bootinfo).
(function () {
	if (!frappe.boot || !frappe.boot.manthan_quick_checkin) return;

	const WORKSPACE = "HR";
	const API = "manthan_hrms.attendance.checkin.";
	let clock_timer = null;
	let busy = false;

	const style = document.createElement("style");
	style.textContent = `
		.manthan-checkin { display: flex; align-items: center; justify-content: space-between; gap: var(--padding-md);
			flex-wrap: wrap; margin: var(--margin-md) 0 var(--margin-lg); padding: var(--padding-md) var(--padding-lg);
			background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius-lg);
			box-shadow: var(--card-shadow); }
		.manthan-checkin .mc-title { font-size: var(--text-lg); font-weight: 600; color: var(--heading-color); }
		.manthan-checkin .mc-meta { margin-top: 2px; font-size: var(--text-sm); color: var(--text-muted); }
		.manthan-checkin .mc-clock { font-variant-numeric: tabular-nums; }
		.manthan-checkin .mc-action { min-width: 140px; }
	`;
	document.head.appendChild(style);

	function is_hr_workspace() {
		const route = frappe.get_route() || [];
		return route[0] === "Workspaces" && (route[1] === WORKSPACE || route[2] === WORKSPACE);
	}

	function get_card() {
		const main = document.querySelector("#page-Workspaces .layout-main-section");
		if (!main) return null;
		let card = main.querySelector(".manthan-checkin");
		if (!card) {
			const editor = main.querySelector(".editor-js-container");
			if (!editor) return null;
			card = document.createElement("div");
			card.className = "manthan-checkin";
			editor.before(card);
		}
		return card;
	}

	function tick(card) {
		clearInterval(clock_timer);
		const update = () => {
			const el = card.querySelector(".mc-clock");
			if (!el || !document.body.contains(el)) return clearInterval(clock_timer);
			el.textContent = moment().format("ddd, D MMM · hh:mm:ss A");
		};
		update();
		clock_timer = setInterval(update, 1000);
	}

	function render(card, status) {
		const esc = frappe.utils.escape_html;
		if (!status.employee) {
			card.hidden = true;
			return;
		}
		card.hidden = false;

		const last = status.last_log;
		const last_text = last
			? __("Last {0} {1}", [
					last.log_type === "IN" ? __("check-in") : __("check-out"),
					frappe.datetime.comment_when(last.time),
			  ])
			: __("No check-ins yet");
		const list_url = `/app/employee-checkin?employee=${encodeURIComponent(status.employee)}`;
		const next_in = status.next_log_type === "IN";

		card.innerHTML = `
			<div>
				<div class="mc-title">${esc(__("Hi {0}", [status.first_name || ""]))}</div>
				<div class="mc-meta"><span class="mc-clock"></span></div>
				<div class="mc-meta">${last_text} · <a href="${list_url}">${__("View all")}</a></div>
			</div>
			${
				status.allowed
					? `<button class="btn ${next_in ? "btn-primary" : "btn-default"} btn-md mc-action">
						${next_in ? __("Check In") : __("Check Out")}</button>`
					: `<div class="mc-meta">${__("Self check-in is turned off in HR Settings")}</div>`
			}
		`;
		tick(card);
		const button = card.querySelector(".mc-action");
		if (button) button.addEventListener("click", () => submit(card, status, button));
	}

	function get_location() {
		return new Promise((resolve, reject) => {
			if (!navigator.geolocation) {
				reject(new Error(__("Geolocation is not supported by your browser")));
				return;
			}
			navigator.geolocation.getCurrentPosition(
				(pos) => resolve(pos.coords),
				(err) => reject(new Error(__("Unable to get your location: {0}", [err.message])))
			);
		});
	}

	async function submit(card, status, button) {
		if (busy) return;
		busy = true;
		button.disabled = true;
		const log_type = status.next_log_type;
		try {
			const args = { log_type };
			if (status.geolocation_required) {
				const coords = await get_location();
				args.latitude = coords.latitude;
				args.longitude = coords.longitude;
			}
			const r = await frappe.call({ method: API + "quick_checkin", args, type: "POST" });
			frappe.show_alert({
				message: log_type === "IN" ? __("Checked in") : __("Checked out"),
				indicator: "green",
			});
			render(card, r.message);
		} catch (e) {
			// server errors are already shown by frappe.call
			if (e && e.message && !e._server_messages) frappe.msgprint(e.message);
			button.disabled = false;
		} finally {
			busy = false;
		}
	}

	async function refresh() {
		const main = document.querySelector("#page-Workspaces .layout-main-section .manthan-checkin");
		if (!is_hr_workspace()) {
			if (main) main.hidden = true;
			return;
		}
		// the workspace page builds its container on first visit; wait for it
		let card = null;
		for (let i = 0; i < 40 && !(card = get_card()); i++) {
			await new Promise((r) => setTimeout(r, 100));
		}
		if (!card || !is_hr_workspace()) return;
		const r = await frappe.call({ method: API + "get_quick_checkin_status" });
		if (is_hr_workspace()) render(card, r.message || {});
	}

	frappe.router.on("change", refresh);
	$(document).ready(() => setTimeout(refresh, 0));
})();
