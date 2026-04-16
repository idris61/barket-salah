# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

"""
Customer isolation for portal / restricted users.

Goal: If a user has User Permission(s) on Customer (e.g. "Customer = Test Müşteri"),
they must only see documents belonging to those customers.

Why this exists:
- Core SQL user-permission matching is Link-field based and (when strict perms are off)
  allows empty link values via `(link is empty OR link IN allowed)`.
- Quotation uses Dynamic Link (`party_name` via `quotation_to`) which is not covered
  by core Link-field matching.
- Sales Order / Sales Invoice have Customer as Link, but we still want to *tighten*
  the rule so empty customer never leaks and portal views behave consistently.

Operational note:
- For maximum safety across the whole site, also enable **System Settings → Apply Strict User Permissions**.
  This hook remains defense-in-depth even with strict mode on.
"""

from __future__ import annotations

import frappe
from frappe.permissions import filter_allowed_docs_for_doctype, get_user_permissions


def _allowed_customer_ids(user: str, applicable_for: str) -> list[str] | None:
    if not user or user in ("Administrator", "Guest"):
        return None
    ups = get_user_permissions(user)
    customer_perms = ups.get("Customer") or []
    if not customer_perms:
        return None
    allowed = filter_allowed_docs_for_doctype(customer_perms, applicable_for, with_default_doc=False)
    if not allowed:
        return None
    return list(allowed)


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
    if not doctype:
        return ""
    if not user:
        user = frappe.session.user

    if doctype not in ("Quotation", "Sales Order", "Sales Invoice"):
        return ""

    allowed = _allowed_customer_ids(user, doctype)
    if not allowed:
        return ""

    values = ", ".join(frappe.db.escape(c, percent=False) for c in allowed)
    if doctype == "Quotation":
        meta = frappe.get_meta("Quotation")
        # Prefer the explicit Customer Link field when present (synced in `setup.py`),
        # because it matches core user-permission mechanics and avoids Dynamic Link gaps.
        if meta.has_field("custom_customer"):
            return (
                f"(`tabQuotation`.`quotation_to` = 'Customer' AND "
                f"ifnull(`tabQuotation`.`custom_customer`, '') != '' AND "
                f"`tabQuotation`.`custom_customer` IN ({values}) AND "
                f"`tabQuotation`.`party_name` IN ({values}))"
            )
        return (
            f"(`tabQuotation`.`quotation_to` = 'Customer' AND "
            f"`tabQuotation`.`party_name` IN ({values}))"
        )

    if doctype == "Sales Order":
        # Tighten: customer must be set and allowed.
        return f"(`tabSales Order`.`customer` IS NOT NULL AND `tabSales Order`.`customer` IN ({values}))"

    # Sales Invoice
    return f"(`tabSales Invoice`.`customer` IS NOT NULL AND `tabSales Invoice`.`customer` IN ({values}))"


def quotation_has_permission(doc, ptype: str | None = None, user: str | None = None, debug: bool = False):
    if not user:
        user = frappe.session.user

    if ptype in ("create",):
        return True

    dt = doc.doctype
    if dt not in ("Quotation", "Sales Order", "Sales Invoice"):
        return True

    allowed = _allowed_customer_ids(user, dt)
    if allowed is None:
        return True

    if dt == "Quotation":
        if doc.get("quotation_to") != "Customer":
            return False
        meta = frappe.get_meta("Quotation")
        party = doc.get("party_name")
        if not party or str(party) not in allowed:
            return False
        if meta.has_field("custom_customer"):
            cc = doc.get("custom_customer")
            return bool(cc and str(cc) in allowed and str(cc) == str(party))
        return True

    # Sales Order / Sales Invoice
    customer = doc.get("customer")
    return bool(customer and str(customer) in allowed)
