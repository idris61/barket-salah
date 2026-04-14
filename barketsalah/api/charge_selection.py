# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

"""Select default Charge Types for logistics quotes using Shipping Request context."""

import frappe
from frappe.utils import cint


def list_charge_type_names_for_shipping_request(shipping_request: str | None) -> list[str]:
    """
    Returns Charge Type names (is_default=1) filtered by SR:
    - Category Insurance: only if insurance_requested.
    - Category Ocean: only for Sea (or blank transport_mode).
    - only_for_dangerous_goods: only if dangerous_goods (field on Charge Type when present).
    """
    sr = None
    if shipping_request and frappe.db.exists("Shipping Request", shipping_request):
        sr = frappe.get_doc("Shipping Request", shipping_request)

    transport = ((sr.get("transport_mode") if sr else None) or "").strip()
    insurance = cint(sr.get("insurance_requested") if sr else 0)
    dangerous = cint(sr.get("dangerous_goods") if sr else 0)

    meta = frappe.get_meta("Charge Type")
    fields = ["name", "category"]
    if meta.has_field("only_for_dangerous_goods"):
        fields.append("only_for_dangerous_goods")

    rows = frappe.get_all(
        "Charge Type",
        filters={"is_default": 1},
        fields=fields,
        order_by="name asc",
    )
    if not rows:
        return []

    selected: list[str] = []
    for row in rows:
        cat = (row.get("category") or "").strip()

        if cat == "Insurance" and not insurance:
            continue
        if cat == "Ocean" and transport and transport != "Sea":
            continue
        if row.get("only_for_dangerous_goods") and not dangerous:
            continue

        selected.append(row.name)

    return selected
