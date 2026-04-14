# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

import frappe


def _customer_display_name(customer: str | None) -> str | None:
    if not customer:
        return None
    return frappe.db.get_value("Customer", customer, "customer_name") or customer


def _resolve_shipping_request_name(doc) -> str | None:
    """
    Nakliye talebi: önce SQ.custom_shipping_request, yoksa bu fırsata bağlı Shipping Request
    (party_name ile müşteri eşleşen tercih edilir).
    """
    meta = frappe.get_meta("Supplier Quotation")
    if meta.has_field("custom_shipping_request"):
        sr = doc.get("custom_shipping_request")
        if sr and frappe.db.exists("Shipping Request", sr):
            return sr
    if not doc.get("opportunity"):
        return None
    candidates = frappe.get_all(
        "Shipping Request",
        filters={"opportunity": doc.opportunity},
        fields=["name", "customer"],
        order_by="modified desc",
    )
    if not candidates:
        return None
    party = frappe.db.get_value("Opportunity", doc.opportunity, "party_name")
    if party:
        for row in candidates:
            if row.get("customer") == party:
                return row.name
    return candidates[0].name


def supplier_quotation_before_save(doc, method=None) -> None:
    if doc.doctype != "Supplier Quotation":
        return
    meta_sq = frappe.get_meta("Supplier Quotation")
    if not meta_sq.has_field("custom_opportunity_customer_name"):
        return

    sr_name = _resolve_shipping_request_name(doc)
    if sr_name and meta_sq.has_field("custom_shipping_request") and not doc.get("custom_shipping_request"):
        doc.custom_shipping_request = sr_name

    if sr_name:
        cust = frappe.db.get_value("Shipping Request", sr_name, "customer")
        if cust:
            doc.custom_opportunity_customer_name = _customer_display_name(cust)
            return

    if doc.get("opportunity"):
        row = frappe.db.get_value(
            "Opportunity",
            doc.opportunity,
            ["customer_name", "party_name"],
            as_dict=True,
        )
        doc.custom_opportunity_customer_name = (
            (row.get("customer_name") or row.get("party_name")) if row else None
        )
    else:
        doc.custom_opportunity_customer_name = None
