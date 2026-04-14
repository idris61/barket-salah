# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def make_supplier_quotation_from_opportunity(source_name, target_doc=None):
    """
    ERPNext `make_supplier_quotation` yalnızca Opportunity kalemlerini eşler; nakliye fırsatında
    kalem olmayınca boş Supplier Quotation açılır. Nakliye talebi (veya fırsata bağlı SR)
    varsa nakliyeci başına teklif üretimine yönlendiririz.
    """
    opp = frappe.get_doc("Opportunity", source_name)

    from barketsalah.api.freight import _shipping_request_for_opportunity, generate_carrier_supplier_quotations

    sr = _shipping_request_for_opportunity(opp.name, opp.get("custom_shipping_request"))

    if not sr:
        from erpnext.crm.doctype.opportunity.opportunity import make_supplier_quotation as core_make_sq

        return core_make_sq(source_name, target_doc)

    created = generate_carrier_supplier_quotations(source_name)
    if not created:
        frappe.throw(
            _(
                "No new carrier supplier quotations were created. "
                "Each transporter may already have an open quotation for this opportunity."
            )
        )

    if len(created) > 1:
        frappe.msgprint(
            _("Other carrier quotations created: {0}").format(", ".join(created[1:])),
            indicator="green",
            alert=True,
        )

    return frappe.get_doc("Supplier Quotation", created[0])
