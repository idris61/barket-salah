frappe.ui.form.on("Shipping Request", {
	refresh(frm) {
		toggle_dangerous_doc_requirement(frm);
		hide_linked_doc_create_buttons(frm);

		const is_portal_user =
			typeof frappe.user?.has_role === "function"
				? frappe.user.has_role("Portal User")
				: (Array.isArray(frappe.user_roles) ? frappe.user_roles : []).indexOf("Portal User") !== -1;

		const is_draft =
			typeof frappe.utils?.cint === "function" ? frappe.utils.cint(frm.doc.docstatus) === 0 : frm.doc.docstatus == 0;

		if (!is_portal_user && !frm.doc.opportunity && is_draft) {
			const btn = frm.add_custom_button(__("Make Opportunity"), () => {
				frappe.call({
					method: "barketsalah.api.freight.make_opportunity",
					args: {
						shipping_request: frm.doc.name,
					},
					freeze: true,
					callback(r) {
						if (r.message) {
							frappe.set_route("Form", "Opportunity", r.message);
						}
					},
				});
			});
			// Match primary action styling (theme uses black primary buttons).
			btn?.addClass?.("btn-primary");
		}
	},

	dangerous_goods(frm) {
		toggle_dangerous_doc_requirement(frm);

		if (frm.doc.dangerous_goods) {
			frappe.msgprint({
				title: __("Dangerous Goods Document Required"),
				message: __(
					"Please upload a document in the Dangerous Goods Document field before saving this Shipping Request."
				),
				indicator: "orange",
			});
		}
	},
});

function toggle_dangerous_doc_requirement(frm) {
	frm.toggle_reqd("dangerous_doc", !!frm.doc.dangerous_goods);
}

function hide_linked_doc_create_buttons(frm) {
	// The form dashboard shows linked doctypes with a "+" (create) button.
	// For Shipping Request we only want quick access to already created docs,
	// not creating new ones from the connections bar.
	setTimeout(() => {
		const doctypes_to_disable_create = ["Opportunity", "Sales Order", "Supplier Quotation", "Purchase Order"];
		doctypes_to_disable_create.forEach((dt) => {
			frm.dashboard?.links_area?.body
				?.find?.(`.document-link[data-doctype="${dt}"] .btn-new`)
				?.addClass?.("hidden");
		});
	}, 0);
}
