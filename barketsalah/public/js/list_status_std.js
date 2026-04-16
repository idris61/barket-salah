// Copyright (c) 2026, barketsalah and contributors
// Standard list column + indicator colors for Quotation / Supplier Quotation (and similar) statuses.
//
// List + filter chips: always show canonical English values (match DB / DocType options).
// Turkish (or other) UI strings for these keys live in barketsalah/translations/tr.csv for __(…) elsewhere.

frappe.provide("barketsalah.list_status");

(function () {
	const SUCCESS = new Set(["Ordered", "Partially Ordered", "Submitted"]);
	const PROGRESS = new Set(["Open", "Replied"]);
	const DANGER = new Set(["Lost", "Stopped", "Cancelled"]);
	const NEUTRAL = new Set(["Draft", "Expired"]);

	function norm(s) {
		return s || "Draft";
	}

	barketsalah.list_status.formatter_html = function (value) {
		const v = norm(value);
		let cls = "text-muted";
		if (SUCCESS.has(v)) {
			cls = "text-success";
		} else if (DANGER.has(v)) {
			cls = "text-danger";
		} else if (PROGRESS.has(v)) {
			cls = "text-primary";
		} else if (NEUTRAL.has(v)) {
			cls = "text-muted";
		}
		const label = frappe.utils.escape_html(v);
		return `<span class="${cls}">${label}</span>`;
	};

	/** @param {Record<string, any>} doc */
	barketsalah.list_status.indicator = function (doc, status_field = "status") {
		const v = norm(doc[status_field]);
		let color = "gray";
		if (SUCCESS.has(v)) {
			color = "green";
		} else if (DANGER.has(v)) {
			color = "red";
		} else if (PROGRESS.has(v)) {
			color = "blue";
		}
		return [v, color, `${status_field},=,${v}`];
	};
})();
