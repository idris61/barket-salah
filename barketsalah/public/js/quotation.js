// Copyright (c) 2026, barketsalah and contributors
// Grid UX: editable cost (price list rate); after margin/cost/discount/rate edits, refresh the row
// so read-only columns (e.g. rate_with_margin) and depends_on columns stay in sync without opening the modal.

const QTN_GRID_SYNC_FIELDS = [
	"margin_type",
	"margin_rate_or_amount",
	"price_list_rate",
	"discount_percentage",
	"discount_amount",
	"rate",
];

function barketsalah_is_portal_user() {
	return (frappe.user_roles || []).includes("Portal User");
}

function barketsalah_toggle_portal_quotation_profit_visibility(frm) {
	if (frm.doctype !== "Quotation") {
		return;
	}
	if (!frappe.meta.get_docfield(frm.doctype, "custom_total_profit_amount")) {
		return;
	}
	const hide = barketsalah_is_portal_user();
	frm.set_df_property("custom_total_profit_amount", "hidden", hide ? 1 : 0);
	if (frappe.meta.get_docfield(frm.doctype, "custom_totals_mid_col_break")) {
		frm.set_df_property("custom_totals_mid_col_break", "hidden", hide ? 1 : 0);
	}
	if (frm.layout) {
		frm.layout.refresh_sections();
	}
}

// Portal users should not see cost/margin/discount plumbing in the Quotation child grid,
// and must not be able to re-enable those columns via the grid column picker (gear icon).
const PORTAL_QUOTATION_ITEM_GRID_ALLOW = new Set(["item_code", "qty", "rate"]);

function barketsalah_strip_portal_quotation_items_chrome(grid) {
	if (!grid?.wrapper?.length) {
		return;
	}
	grid.wrapper
		.find(".grid-heading-row .grid-row:not(.filter-row) .grid-static-col.pointer")
		.each(function () {
			const $c = $(this);
			if ($c.find("use[href*='#icon-settings'], svg[data-icon='settings']").length) {
				$c.remove();
			}
		});
	grid.wrapper.find(".grid-body .btn-open-row").remove();
	try {
		grid.toggle_checkboxes(false);
	} catch {
		// ignore
	}
}

function barketsalah_schedule_portal_quotation_grid_strip(frm) {
	if (!barketsalah_is_portal_user() || frm.doctype !== "Quotation") {
		return;
	}
	const run = () => {
		if (cur_frm !== frm) {
			return;
		}
		const g = frm.fields_dict?.items?.grid;
		if (g) {
			barketsalah_strip_portal_quotation_items_chrome(g);
		}
	};
	[0, 120, 400, 1200, 2800].forEach((ms) => setTimeout(run, ms));
}

async function barketsalah_sanitize_quotation_gridview_user_settings() {
	if (!barketsalah_is_portal_user()) return;

	const settings = await frappe.model.user_settings.get("Quotation");
	const grid_view = settings.GridView || {};
	const rows = grid_view["Quotation Item"];

	if (!rows || !rows.length) return;

	const allowed_rows = rows.filter((r) => PORTAL_QUOTATION_ITEM_GRID_ALLOW.has(r.fieldname));
	if (allowed_rows.length === rows.length) return;

	grid_view["Quotation Item"] = allowed_rows;
	await frappe.model.user_settings.save("Quotation", "GridView", grid_view);
}

function barketsalah_lock_portal_quotation_items_grid(frm) {
	if (!barketsalah_is_portal_user() || !frm?.fields_dict?.items?.grid) {
		return;
	}

	const grid = frm.fields_dict.items.grid;

	(grid.docfields || []).forEach((df) => {
		if (!df.fieldname || frappe.model.layout_fields.includes(df.fieldtype)) return;
		df.hidden = PORTAL_QUOTATION_ITEM_GRID_ALLOW.has(df.fieldname) ? 0 : 1;
	});

	// Drop any persisted per-user grid column selections that would bypass the allowlist.
	grid.visible_columns = [];
	grid.user_defined_columns = [];

	barketsalah_strip_portal_quotation_items_chrome(grid);
	barketsalah_schedule_portal_quotation_grid_strip(frm);

	// After every grid redraw, heading (gear) is recreated — strip again.
	grid.wrapper.off("change.barketsalah_portal_strip");
	grid.wrapper.on("change.barketsalah_portal_strip", () => {
		if (!barketsalah_is_portal_user() || cur_frm !== frm) {
			return;
		}
		barketsalah_strip_portal_quotation_items_chrome(grid);
		barketsalah_schedule_portal_quotation_grid_strip(frm);
	});

	// DOM mutations (late async render): keep chrome removed even if "change" fired early.
	if (!frm._barketsalah_portal_items_grid_mo && grid.wrapper[0]) {
		const debounced = frappe.utils.debounce(() => {
			if (!barketsalah_is_portal_user() || cur_frm !== frm) {
				return;
			}
			const g = frm.fields_dict?.items?.grid;
			if (g) {
				barketsalah_strip_portal_quotation_items_chrome(g);
			}
		}, 40);
		frm._barketsalah_portal_items_grid_mo = new MutationObserver(debounced);
		frm._barketsalah_portal_items_grid_mo.observe(grid.wrapper[0], { childList: true, subtree: true });
	}

	// Capture on stable form wrapper: survives grid innerHTML refreshes; runs before child handlers.
	if (!frm._barketsalah_portal_items_grid_click_guard && frm.$wrapper?.[0]) {
		frm._barketsalah_portal_items_grid_click_guard = true;

		const portalStopGridUi = (ev) => {
			if (!barketsalah_is_portal_user() || cur_frm !== frm) {
				return;
			}
			const target = ev.target;
			if (!(target instanceof Element)) {
				return;
			}
			const gridRoot = frm.fields_dict?.items?.grid?.wrapper?.[0];
			if (!gridRoot || !gridRoot.contains(target)) {
				return;
			}

			if (target.closest(".grid-heading-row .grid-row:not(.filter-row) .grid-static-col.pointer")) {
				ev.preventDefault();
				ev.stopPropagation();
				ev.stopImmediatePropagation();
				return;
			}

			const icon = target.closest("use[href*='#icon-settings'], svg[data-icon='settings']");
			if (icon && target.closest(".grid-heading-row")) {
				ev.preventDefault();
				ev.stopPropagation();
				ev.stopImmediatePropagation();
				return;
			}

			const dataRow = target.closest(".grid-body .grid-row .data-row");
			if (dataRow) {
				ev.preventDefault();
				ev.stopPropagation();
				ev.stopImmediatePropagation();
			}
		};

		frm.$wrapper[0].addEventListener("click", portalStopGridUi, true);
		frm.$wrapper[0].addEventListener("dblclick", portalStopGridUi, true);
	}
}

// When switching Margin Type to Percentage, users often still have an amount in the same field.
// ERPNext will treat that as % (e.g. 1000 => 1000%), producing unexpected prices.
// Normalize by clearing the value when it looks like an amount.
frappe.ui.form.on("Quotation Item", "margin_type", (frm, cdt, cdn) => {
	if (barketsalah_is_portal_user()) return;
	if (frm.doc.doctype !== "Quotation" || frm.doc.docstatus !== 0) return;
	const row = locals[cdt]?.[cdn];
	if (!row) return;
	if (row.margin_type === "Percentage" && flt(row.margin_rate_or_amount) > 100) {
		frappe.model.set_value(cdt, cdn, "margin_rate_or_amount", 0);
	}
});

QTN_GRID_SYNC_FIELDS.forEach((fieldname) => {
	frappe.ui.form.on("Quotation Item", fieldname, (frm, cdt, cdn) => {
		if (barketsalah_is_portal_user()) return;
		if (frm.doc.doctype !== "Quotation" || frm.doc.docstatus !== 0) {
			return;
		}
		setTimeout(() => {
			const grid_row = frm.fields_dict.items?.grid?.get_row(cdn);
			if (grid_row) {
				grid_row.refresh();
			}
		}, 0);
	});
});

frappe.ui.form.on("Quotation", {
	async before_load(frm) {
		if (frm.doctype !== "Quotation") return;
		if (!barketsalah_is_portal_user()) return;
		await barketsalah_sanitize_quotation_gridview_user_settings();
	},

	refresh(frm) {
		if (frm.doc.doctype !== "Quotation") return;

		barketsalah_toggle_portal_quotation_profit_visibility(frm);

		const accept_label = __("Teklifi Kabul Et");
		frm.remove_custom_button(accept_label);

		// Accept flow: Portal User only; visibility + rules from server (invoice, Lost, sibling accepted).
		if (barketsalah_is_portal_user() && !frm.is_new() && frm.doc.quotation_to === "Customer" && frm.doc.docstatus !== 2) {
			const qname = frm.doc.name;
			frappe.call({
				method: "barketsalah.api.quotation_acceptance.quotation_accept_button_state",
				args: { quotation: qname },
				callback(r) {
					if (frm.doc.name !== qname || !r.message?.show) {
						return;
					}
					frm.remove_custom_button(accept_label);
					const $accept = frm.add_custom_button(accept_label, () => {
						frappe.confirm(
							__("Bu teklifi kabul edip satış/satınalma faturaları oluşturulsun mu?"),
							() => {
								frappe.call({
									method: "barketsalah.api.quotation_acceptance.accept_customer_quotation",
									args: { quotation: frm.doc.name },
									freeze: true,
									freeze_message: __("Processing..."),
									callback(res) {
										const msg = res.message || {};
										if (msg.sales_invoice) {
											frappe.set_route("Form", "Sales Invoice", msg.sales_invoice);
										} else {
											frappe.show_alert({ message: __("Done"), indicator: "green" });
											frm.reload_doc();
										}
									},
								});
							}
						);
					});
					$accept?.removeClass?.("btn-default btn-secondary");
					$accept?.addClass?.("btn-danger barketsalah-btn-danger");
				},
			});
		}

		barketsalah_lock_portal_quotation_items_grid(frm);

		if (frm.doc.docstatus !== 0 || !frm.fields_dict.items) {
			return;
		}
		if (barketsalah_is_portal_user()) {
			return;
		}
		frm.fields_dict.items.grid.update_docfield_property("price_list_rate", "read_only", 0);

		// Update profit display on load/refresh
		if (frm.doc.custom_total_profit_amount != null) {
			frm.trigger("barketsalah_update_total_profit");
		}
	},

	barketsalah_update_total_profit(frm) {
		if (frm.doc.doctype !== "Quotation") return;
		let total = 0;
		(frm.doc.items || []).forEach((d) => {
			const qty = flt(d.qty || 0);
			if (!qty) return;
			const rate = flt(d.rate || 0);
			const cost = flt(d.price_list_rate || 0);
			total += (rate - cost) * qty;
		});
		frm.set_value("custom_total_profit_amount", total);
	},
});

// Recalculate on relevant item changes
["rate", "price_list_rate", "qty"].forEach((fieldname) => {
	frappe.ui.form.on("Quotation Item", fieldname, (frm) => {
		if (barketsalah_is_portal_user()) return;
		if (frm.doc.doctype === "Quotation") {
			frm.trigger("barketsalah_update_total_profit");
		}
	});
});
