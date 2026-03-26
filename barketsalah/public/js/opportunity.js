frappe.ui.form.on("Opportunity", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus === 2) {
			return;
		}

		frm.add_custom_button(__("Generate Carrier Quotes"), () => {
			frappe.call({
				method: "barketsalah.api.freight.generate_quotes",
				args: {
					opportunity: frm.doc.name,
				},
				freeze: true,
				callback(r) {
					const created = r.message || [];
					frappe.msgprint(
						created.length
							? __("Carrier quotations created: {0}", [created.join(", ")])
							: __("No new carrier quotations were created."),
					);
				},
			});
		});
	},
});
