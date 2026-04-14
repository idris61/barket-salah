# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

"""Select default Charge Types for logistics quotes using Shipping Request context."""

import frappe
from frappe.utils import cint


@frappe.whitelist()
def list_charge_type_names_for_shipping_request(shipping_request: str | None) -> list[str]:
    """
    Returns `Charge Type.name` values (is_default=1) filtered by a Shipping Request (SR).

    Notes:
    - `Charge Type.name` is auto-named from `charge_name` in this app (so it's typically the human-readable value).
    - This function is whitelisted so it can be called from the client.

    Rules:
    - Category Insurance: only if insurance_requested.
    - Category Ocean: only for Sea (or blank transport_mode).
    - only_for_dangerous_goods: only if dangerous_goods.
    """
    sr = (
        frappe.db.get_value(
            "Shipping Request",
            shipping_request,
            ["transport_mode", "insurance_requested", "dangerous_goods"],
            as_dict=True,
        )
        if shipping_request
        else None
    )

    transport = ((sr.get("transport_mode") if sr else None) or "").strip()
    insurance = cint(sr.get("insurance_requested") if sr else 0)
    dangerous = cint(sr.get("dangerous_goods") if sr else 0)

    filters: list[list] = [["is_default", "=", 1]]
    if not insurance:
        filters.append(["category", "!=", "Insurance"])
    if transport and transport != "Sea":
        filters.append(["category", "!=", "Ocean"])
    if not dangerous:
        filters.append(["only_for_dangerous_goods", "!=", 1])

    rows = frappe.get_all("Charge Type", filters=filters, fields=["name"], order_by="name asc")
    if not rows:
        return []

    return [r.name for r in rows]
