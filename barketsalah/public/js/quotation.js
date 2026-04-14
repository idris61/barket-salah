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

// When switching Margin Type to Percentage, users often still have an amount in the same field.
// ERPNext will treat that as % (e.g. 1000 => 1000%), producing unexpected prices.
// Normalize by clearing the value when it looks like an amount.
frappe.ui.form.on("Quotation Item", "margin_type", (frm, cdt, cdn) => {
	if (frm.doc.doctype !== "Quotation" || frm.doc.docstatus !== 0) return;
	const row = locals[cdt]?.[cdn];
	if (!row) return;
	if (row.margin_type === "Percentage" && flt(row.margin_rate_or_amount) > 100) {
		frappe.model.set_value(cdt, cdn, "margin_rate_or_amount", 0);
	}
});

QTN_GRID_SYNC_FIELDS.forEach((fieldname) => {
	frappe.ui.form.on("Quotation Item", fieldname, (frm, cdt, cdn) => {
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
	refresh(frm) {
		if (frm.doc.docstatus !== 0 || !frm.fields_dict.items) {
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
		if (frm.doc.doctype === "Quotation") {
			frm.trigger("barketsalah_update_total_profit");
		}
	});
});
