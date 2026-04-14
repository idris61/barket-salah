// Copyright (c) 2026, barketsalah and contributors
// Quotation ListView: group rows by Opportunity with "+ expand" headers (same UX as Supplier Quotation list).

frappe.listview_settings["Quotation"] = {
	add_fields: ["opportunity", "customer_name", "grand_total", "currency", "transaction_date"],

	refresh(listview) {
		setTimeout(() => apply_opportunity_grouping(listview), 0);
	},
};

function apply_opportunity_grouping(listview) {
	if (!listview?.data?.length || !listview?.$result) return;

	// Avoid double-applying
	if (listview.$result.find(".bkq-group-header").length) return;

	const groups = new Map(); // opp -> {names:[], customer_name?: string}
	for (const d of listview.data) {
		const key = d.opportunity || __("Not Set");
		if (!groups.has(key)) {
			groups.set(key, { names: [], customer_name: d.customer_name || "" });
		}
		const g = groups.get(key);
		g.names.push(d.name);
		if (!g.customer_name && d.customer_name) g.customer_name = d.customer_name;
	}

	const row_for = (name) =>
		listview.$result
			.find(`.list-row-checkbox[data-name="${encodeURIComponent(name)}"]`)
			.closest(".list-row-container");

	const $new_container = $('<div class="list-row-container bkq-grouping-root"></div>');

	let group_idx = 0;
	for (const [key, group] of groups.entries()) {
		group_idx += 1;
		const group_id = `bkq-group-${group_idx}`;
		const names = group.names || [];
		const count = names.length;
		const customer_part = group.customer_name
			? ` (${frappe.utils.escape_html(group.customer_name)})`
			: "";

		const header_html = `
			<div class="list-row-container bkq-group-header" data-group-id="${group_id}">
				<div class="level list-row">
					<div class="level-left ellipsis">
						<div class="list-row-col ellipsis">
							<button class="btn btn-xs btn-default bkq-toggle" data-group-id="${group_id}" type="button">+</button>
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
				$row.addClass("bkq-child-row").hide(); // collapsed by default
				$new_container.append($row);
			}
		}
	}

	// Replace current rows with grouped layout
	listview.$result.find(".list-row-container").not(".list-row-head").remove();
	listview.$result.append($new_container.children());

	// Bind toggle
	listview.$result.off("click.bkq", ".bkq-toggle");
	listview.$result.on("click.bkq", ".bkq-toggle", function () {
		const gid = $(this).attr("data-group-id");
		const $children = listview.$result.find(`.bkq-child-row[data-group-id="${gid}"]`);
		const is_open = $children.first().is(":visible");
		$children.toggle(!is_open);
		$(this).text(is_open ? "+" : "−");
	});
}

