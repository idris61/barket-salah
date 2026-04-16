// Copyright (c) 2026, barketsalah and contributors
// Opportunity UX: only allow creating Supplier Quotation from the Create menu,
// and style the Create button as primary (black in this theme).

frappe.ui.form.on("Opportunity", {
	refresh(frm) {
		// Limit create menu options to Supplier Quotation only
		const create_group = __("Create");
		const keep = new Set([__("Supplier Quotation")]);
		[
			__("Quotation"),
			__("Request For Quotation"),
			__("Customer"),
		].forEach((label) => {
			if (!keep.has(label)) {
				frm.remove_custom_button(label, create_group);
			}
		});

		// Some buttons may be added conditionally after refresh; retry once.
		setTimeout(() => {
			[
				__("Quotation"),
				__("Request For Quotation"),
				__("Customer"),
			].forEach((label) => frm.remove_custom_button(label, create_group));
		}, 0);

		style_create_menu_primary(frm);
		style_create_menu_supplier_quotation_red(frm);
	},

	onload_post_render(frm) {
		// Ensure styling after page actions are mounted
		style_create_menu_primary(frm);
		style_create_menu_supplier_quotation_red(frm);
	},
});

function style_create_menu_primary(frm) {
	// The "Create" menu is a dropdown in the page actions area.
	const try_apply = () => {
		const $wrap = $(frm.page?.wrapper || frm.wrapper);
		const create_labels = new Set([__("Create"), __("Oluştur"), "Create"]);

		// Prefer matching dropdown toggle by its visible label
		let $target = $wrap
			.find(".page-actions .btn-group .dropdown-toggle")
			.filter((_, el) => create_labels.has($(el).text().trim()))
			.first();

		// Fallback: in some layouts the create button is the first actions dropdown
		if (!$target.length) {
			$target = $wrap.find(".page-actions .btn-group .dropdown-toggle").first();
		}

		if ($target.length) {
			$target.removeClass("btn-default btn-secondary btn-light").addClass("btn-primary");
		}
	};

	// Apply a few times to beat async renders
	setTimeout(try_apply, 0);
	setTimeout(try_apply, 150);
	setTimeout(try_apply, 600);
}

function style_create_menu_supplier_quotation_red(frm) {
	const label = __("Supplier Quotation");

	const paint = () => {
		const $wrap = $(frm.page?.wrapper || frm.wrapper);
		$wrap.find(".page-actions .dropdown-menu .dropdown-item").each(function () {
			const $el = $(this);
			if ($el.text().trim() === label) {
				$el.addClass("barketsalah-dropdown-item-danger");
			} else {
				$el.removeClass("barketsalah-dropdown-item-danger");
			}
		});
	};

	setTimeout(paint, 0);
	setTimeout(paint, 150);
	setTimeout(paint, 600);

	if (!frm._barketsalah_opp_create_menu_paint) {
		frm._barketsalah_opp_create_menu_paint = true;
		$(frm.wrapper).on(
			"shown.bs.dropdown hidden.bs.dropdown",
			".page-actions .dropdown",
			() => setTimeout(paint, 0)
		);
		$(frm.wrapper).on("click", ".page-actions .btn-group .dropdown-toggle", () =>
			setTimeout(paint, 200)
		);
	}
}

