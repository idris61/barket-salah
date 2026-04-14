frappe.ui.form.on("Supplier Quotation", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus === 2) {
			return;
		}
		// Add core mapper to the existing "Create" menu (ERPNext has the server method,
		// but doesn't expose it in the standard Supplier Quotation UI).
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Purchase Invoice"),
				() => {
					frappe.model.open_mapped_doc({
						method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_invoice",
						frm,
					});
				},
				__("Create")
			);
		}

		if (!frm.doc.opportunity) {
			return;
		}

		const linked = frm.doc.custom_linked_customer_quotation;
		if (linked) {
			frm.add_custom_button(__("Open customer quotation"), () => {
				frappe.set_route("Form", "Quotation", linked);
			});
			return;
		}

		frm.add_custom_button(__("Create customer quotation"), () => {
			frappe.call({
				method: "barketsalah.api.sales_from_carrier.make_customer_quotation_from_supplier_quotation",
				args: {
					supplier_quotation: frm.doc.name,
				},
				freeze: true,
				freeze_message: __("Creating..."),
				callback(r) {
					if (r.message) {
						frappe.set_route("Form", "Quotation", r.message);
					}
				},
			});
		});
	},
});
