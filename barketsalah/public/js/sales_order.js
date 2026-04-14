frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus === 2) {
			return;
		}

		frm.add_custom_button(__("Create Shipment"), () => {
			frappe.new_doc("Cargo App Shipment", {
				sales_order: frm.doc.name,
			});
		});
	},
});
