// Copyright (c) 2026, barketsalah and contributors
//
// Desk UX: Role Permission may grant only Read on Sales Invoice while the child grid still
// shows row edit (pencil) / column picker (gear) and can open the line form (editable_grid).
// Lock all Table fields when the user has no level-0 Write on the parent, and block the
// remaining grid interactions in capture phase (same pattern as quotation.js for portal).

function barketsalah_sales_invoice_can_mutate(frm) {
	return !!(frm.perm && frm.perm[0] && frm.perm[0].write);
}

function barketsalah_lock_read_only_sales_invoice_tables(frm) {
	if (barketsalah_sales_invoice_can_mutate(frm)) {
		return;
	}

	for (const df of frm.meta.fields) {
		if (df.fieldtype !== "Table") {
			continue;
		}
		frm.set_df_property(df.fieldname, "read_only", 1);
		frm.set_df_property(df.fieldname, "cannot_add_rows", 1);
		frm.set_df_property(df.fieldname, "cannot_delete_rows", 1);
	}
}

function barketsalah_sales_invoice_apply_grid_ui_lock(frm) {
	if (barketsalah_sales_invoice_can_mutate(frm)) {
		return;
	}

	for (const df of frm.meta.fields) {
		if (df.fieldtype !== "Table") {
			continue;
		}

		const field = frm.get_field(df.fieldname);
		const grid = field && field.grid;
		const el = grid && grid.wrapper && grid.wrapper[0];
		if (!grid || !el) {
			continue;
		}

		const key = `_barketsalah_si_grid_capture_${df.fieldname}`;
		if (!frm[key]) {
			frm[key] = true;
			const stop = (ev) => {
				if (barketsalah_sales_invoice_can_mutate(frm)) {
					return;
				}
				const target = ev.target;
				if (!(target instanceof Element)) {
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
			el.addEventListener("click", stop, true);
			el.addEventListener("dblclick", stop, true);
		}

		grid.wrapper
			.find(".grid-heading-row .grid-row .grid-static-col.pointer")
			.has("use[href*='#icon-settings']")
			.remove();

		grid.wrapper.find(".grid-body .btn-open-row").remove();

		try {
			grid.toggle_checkboxes(false);
		} catch {
			// ignore
		}
	}
}

function barketsalah_sales_invoice_schedule_grid_lock(frm) {
	if (barketsalah_sales_invoice_can_mutate(frm)) {
		return;
	}

	const run = () => barketsalah_sales_invoice_apply_grid_ui_lock(frm);
	run();
	frappe.after_ajax(() => run());
	setTimeout(run, 0);
	setTimeout(run, 150);
}

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		barketsalah_lock_read_only_sales_invoice_tables(frm);
		barketsalah_sales_invoice_schedule_grid_lock(frm);
	},
});
