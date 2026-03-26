frappe.ui.form.on("Shipping Request", {
	refresh(frm) {
		toggle_dangerous_doc_requirement(frm);

		if (!frm.doc.opportunity && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Make Opportunity"), () => {
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
		}
	},

	dangerous_goods(frm) {
		toggle_dangerous_doc_requirement(frm);

		if (frm.doc.dangerous_goods) {
			frappe.msgprint({
				title: __("Dangerous Goods Document Required"),
				message: __("Please upload a document in the Dangerous Doc field before saving this Shipping Request."),
				indicator: "orange",
			});
		}
	},
});

function toggle_dangerous_doc_requirement(frm) {
	frm.toggle_reqd("dangerous_doc", !!frm.doc.dangerous_goods);
}
