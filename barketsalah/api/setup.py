import frappe
from frappe import _
from frappe.utils import flt

from barketsalah.api.utils import log_api_event


def _compute_total_profit_for_quotation(doc) -> float:
    """
    Profit = sum((rate - price_list_rate) * qty) across item rows.
    Assumes `price_list_rate` is used as cost basis in this workflow.
    """
    total = 0.0
    for row in doc.get("items") or []:
        qty = flt(row.get("qty") or 0)
        if not qty:
            continue
        rate = flt(row.get("rate") or 0)
        cost = flt(row.get("price_list_rate") or 0)
        total += (rate - cost) * qty
    return flt(total)


def quotation_before_save(doc, method=None) -> None:
    if doc.doctype != "Quotation":
        return
    meta_q = frappe.get_meta("Quotation")
    meta_sq = frappe.get_meta("Supplier Quotation")

    # Mirror Customer as a real Link field so core User Permissions apply (party_name is Dynamic Link).
    if meta_q.has_field("custom_customer"):
        if doc.get("quotation_to") == "Customer" and doc.get("party_name"):
            doc.custom_customer = doc.party_name
        else:
            doc.custom_customer = None

    # Keep Total Profit in sync for UI/reporting.
    if meta_q.has_field("custom_total_profit_amount"):
        doc.custom_total_profit_amount = _compute_total_profit_for_quotation(doc)

    if doc.is_new():
        sq_name = doc.get("custom_source_supplier_quotation")
        if not sq_name and meta_q.has_field("supplier_quotation"):
            sq_name = doc.get("supplier_quotation")
        if sq_name and frappe.db.exists("Supplier Quotation", sq_name):
            from barketsalah.api.sales_from_carrier import existing_active_customer_quotation_for_sq

            existing = existing_active_customer_quotation_for_sq(sq_name)
            if existing:
                frappe.throw(
                    _("A customer quotation already exists for this supplier quotation: {0}").format(
                        existing
                    ),
                    title=_("Already exists"),
                )

    if meta_q.has_field("custom_carrier_supplier_name"):
        sq_name = doc.get("custom_source_supplier_quotation")
        if sq_name:
            sq = frappe.get_cached_doc("Supplier Quotation", sq_name)
            doc.custom_carrier_supplier_name = sq.supplier_name or (
                frappe.db.get_value("Supplier", sq.supplier, "supplier_name") if sq.get("supplier") else None
            )
        else:
            doc.custom_carrier_supplier_name = None

    if doc.get("custom_source_supplier_quotation") and meta_q.has_field("supplier_quotation"):
        doc.supplier_quotation = doc.custom_source_supplier_quotation

    if not doc.get("opportunity"):
        return


def _sync_opportunity_insurance_flag(opportunity_name: str | None) -> None:
    if not opportunity_name:
        log_api_event("setup.sync_insurance.skipped_missing_opportunity")
        return

    meta_opp = frappe.get_meta("Opportunity")
    if not meta_opp.has_field("custom_shipping_request"):
        log_api_event(
            "setup.sync_insurance.skipped_missing_opportunity_field",
            opportunity=opportunity_name,
            fieldname="custom_shipping_request",
            level="warning",
        )
        return

    shipping_request = frappe.db.get_value("Opportunity", opportunity_name, "custom_shipping_request")
    if not shipping_request:
        log_api_event(
            "setup.sync_insurance.skipped_missing_shipping_request",
            opportunity=opportunity_name,
        )
        return

    if not frappe.db.exists("Shipping Request", shipping_request):
        log_api_event(
            "setup.sync_insurance.skipped_shipping_request_not_found",
            opportunity=opportunity_name,
            shipping_request=shipping_request,
            level="warning",
        )
        return

    insurance_requested = frappe.db.get_value("Shipping Request", shipping_request, "insurance_requested")
    if not insurance_requested:
        log_api_event(
            "setup.sync_insurance.skipped_insurance_not_requested",
            opportunity=opportunity_name,
            shipping_request=shipping_request,
        )
        return

    if frappe.db.get_value("Opportunity", opportunity_name, "custom_insurance_requested"):
        log_api_event(
            "setup.sync_insurance.skipped_already_checked",
            opportunity=opportunity_name,
            shipping_request=shipping_request,
        )
        return

    frappe.db.set_value(
        "Opportunity",
        opportunity_name,
        "custom_insurance_requested",
        1,
        update_modified=False,
    )
    log_api_event(
        "setup.sync_insurance.updated",
        opportunity=opportunity_name,
        shipping_request=shipping_request,
    )


