// Copyright (c) 2026, barketsalah and contributors
// Supplier Quotation ListView: group rows by Shipping Request with "+ expand" headers,
// similar to the sample screenshot.

frappe.listview_settings["Supplier Quotation"] = {
	add_fields: [
		"custom_shipping_request",
		"custom_opportunity_customer_name",
		"opportunity",
		"supplier_name",
		"grand_total",
		"currency",
		"status",
	],

	formatters: {
		status(value) {
			return barketsalah.list_status.formatter_html(value);
		},
	},

	get_indicator(doc) {
		return barketsalah.list_status.indicator(doc, "status");
	},

	refresh(listview) {
		// Rebuild grouping after each list refresh/render.
		setTimeout(() => apply_shipping_request_grouping(listview), 0);
	},
};

function apply_shipping_request_grouping(listview) {
	if (!listview?.data?.length || !listview?.$result) return;

	// Avoid double-applying
	if (listview.$result.find(".bksq-group-header").length) return;

	// Build groups in the same order as list data
	const groups = new Map(); // key -> {names:[], customer_name?: string}
	for (const d of listview.data) {
		const key = d.custom_shipping_request || __("Not Set");
		if (!groups.has(key)) {
			groups.set(key, {
				names: [],
				customer_name: d.custom_opportunity_customer_name || "",
			});
		}
		const g = groups.get(key);
		g.names.push(d.name);
		if (!g.customer_name && d.custom_opportunity_customer_name) {
			g.customer_name = d.custom_opportunity_customer_name;
		}
	}

	// Collect row elements
	const row_for = (name) =>
		listview.$result
			.find(`.list-row-checkbox[data-name="${encodeURIComponent(name)}"]`)
			.closest(".list-row-container");

	const $new_container = $('<div class="list-row-container bksq-grouping-root"></div>');

	let group_idx = 0;
	for (const [key, group] of groups.entries()) {
		const names = group.names || [];
		group_idx += 1;
		const group_id = `bksq-group-${group_idx}`;
		const count = names.length;
		const customer_part = group.customer_name ? ` (${frappe.utils.escape_html(group.customer_name)})` : "";

		const header_html = `
			<div class="list-row-container bksq-group-header" data-group-id="${group_id}">
				<div class="level list-row">
					<div class="level-left ellipsis">
						<div class="list-row-col ellipsis">
							<button class="btn btn-xs btn-default bksq-toggle" data-group-id="${group_id}" type="button">+</button>
							<span class="ml-2"><b>${frappe.utils.escape_html(key)}</b>${customer_part} <span class="text-muted">(${count})</span></span>
						</div>
					</div>
					<div class="level-right text-muted ellipsis"></div>
				</div>
			</div>
		`;
		$new_container.append(header_html);

		for (const name of names) {
			const $row = row_for(name);
			if ($row && $row.length) {
				$row.attr("data-group-id", group_id);
				$row.addClass("bksq-child-row").hide(); // collapsed by default
				$new_container.append($row);
			}
		}
	}

	// Replace current rows with grouped layout
	listview.$result.find(".list-row-container").not(".list-row-head").remove();
	listview.$result.append($new_container.children());

	// Bind toggle
	listview.$result.off("click.bksq", ".bksq-toggle");
	listview.$result.on("click.bksq", ".bksq-toggle", function () {
		const gid = $(this).attr("data-group-id");
		const $children = listview.$result.find(`.bksq-child-row[data-group-id="${gid}"]`);
		const is_open = $children.first().is(":visible");
		$children.toggle(!is_open);
		$(this).text(is_open ? "+" : "−");
	});
}

