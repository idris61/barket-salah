frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus === 2) {
			return;
		}

		frm.add_custom_button(__("Create Shipment"), () => {
			frappe.call({
				method: "barketsalah.api.freight.create_shipment",
				args: {
					sales_order: frm.doc.name,
				},
				freeze: true,
				callback(r) {
					if (r.message) {
						frappe.set_route("Form", "Shipments", r.message);
					}
				},
			});
		});
	},
});
