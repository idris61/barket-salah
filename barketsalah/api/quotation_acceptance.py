# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt


def _opportunity_has_other_accepted_quotation(opportunity: str, exclude_quotation: str) -> bool:
    """Another non-cancelled customer quotation on this opportunity already accepted (invoice linked or ordered)."""
    if not opportunity:
        return False

    meta = frappe.get_meta("Quotation")
    base_filters: dict = {
        "opportunity": opportunity,
        "name": ["!=", exclude_quotation],
        "docstatus": ["<", 2],
    }
    if meta.has_field("custom_sales_invoice"):
        names = frappe.get_all(
            "Quotation",
            filters={**base_filters, "custom_sales_invoice": ["is", "set"]},
            limit=1,
            pluck="name",
        )
        if names:
            return True

    names = frappe.get_all(
        "Quotation",
        filters={**base_filters, "status": ["in", ["Ordered", "Partially Ordered"]]},
        limit=1,
        pluck="name",
    )
    return bool(names)


def _get_linked_supplier_quotation(qt) -> str | None:
    meta_q = frappe.get_meta("Quotation")
    if meta_q.has_field("custom_source_supplier_quotation") and qt.get("custom_source_supplier_quotation"):
        return qt.custom_source_supplier_quotation
    if meta_q.has_field("supplier_quotation") and qt.get("supplier_quotation"):
        return qt.supplier_quotation
    return None


def _mark_other_customer_quotations_lost(winner) -> list[str]:
    if not winner.get("opportunity"):
        return []

    others = frappe.get_all(
        "Quotation",
        filters={"opportunity": winner.opportunity, "docstatus": ["<", 2], "name": ["!=", winner.name]},
        pluck="name",
    )
    if not others:
        return []

    reason = _("Customer accepted quotation {0}.").format(winner.name)
    meta = frappe.get_meta("Quotation")
    updated: list[str] = []
    for name in others:
        # Avoid ERPNext's declare_enquiry_lost side effects on Opportunity.
        # Use direct DB updates so users without read/write on sibling quotations in the same
        # Opportunity (e.g. portal roles with only their own Quotation readable) can still accept.
        row = frappe.db.get_value(
            "Quotation",
            name,
            ["docstatus", "status"],
            as_dict=True,
        )
        if not row:
            continue
        if cint(row.docstatus) == 2:
            continue
        # If already ordered, don't force Lost.
        if row.status in ("Ordered", "Partially Ordered"):
            continue
        values = {"status": "Lost"}
        if meta.has_field("order_lost_reason"):
            values["order_lost_reason"] = reason
        frappe.db.set_value("Quotation", name, values, update_modified=False)
        updated.append(name)
    return updated


def _stop_or_cancel_other_supplier_quotations(winner_sq: str, opportunity: str) -> list[str]:
    others = frappe.get_all(
        "Supplier Quotation",
        filters={"opportunity": opportunity, "docstatus": ["<", 2], "name": ["!=", winner_sq]},
        fields=["name", "docstatus"],
    )
    updated = []
    for row in others:
        try:
            # Prefer "Stopped" (Rejected) over cancellation to preserve submitted history.
            # Status is a core field on Supplier Quotation.
            frappe.db.set_value("Supplier Quotation", row.name, "status", "Stopped", update_modified=False)
        except Exception:
            # Don't block the main acceptance flow if one SQ can't be stopped/cancelled.
            frappe.log_error(
                title="quotation_acceptance: supplier quotation stop/cancel failed",
                message=f"winner_sq={winner_sq} other_sq={row.name}",
            )
        else:
            updated.append(row.name)
    return updated


def _ensure_submitted(doc) -> None:
    if doc.docstatus == 0:
        doc.flags.ignore_permissions = True
        doc.submit()


def _set_quotation_ordered_after_acceptance(quotation_name: str) -> None:
    """
    Customer acceptance creates a draft Sales Invoice; ERPNext only bumps Quotation Item
    ordered_qty from submitted Sales Orders, so status stays Open. Mirror a full order so
    list/form show Ordered and get_status stays consistent on save.
    """
    rows = frappe.get_all(
        "Quotation Item",
        filters={"parent": quotation_name},
        fields=["name", "qty"],
    )
    for row in rows:
        qty = flt(row.qty)
        if qty <= 0:
            continue
        frappe.db.set_value(
            "Quotation Item",
            row.name,
            "ordered_qty",
            qty,
            update_modified=False,
        )

    doc = frappe.get_doc("Quotation", quotation_name)
    doc.set_status(update=True)


def _create_sales_invoice_from_quotation(quotation_name: str) -> str:
    from erpnext.selling.doctype.quotation.quotation import _make_sales_invoice

    si = _make_sales_invoice(quotation_name, ignore_permissions=True)
    si.flags.ignore_permissions = True
    si.insert(ignore_permissions=True)
    return si.name


@frappe.whitelist()
def quotation_accept_button_state(quotation: str) -> dict:
    """Portal list/form: whether to show *Teklifi Kabul Et* (server-side, tamper-resistant)."""
    try:
        qt = frappe.get_doc("Quotation", quotation)
    except frappe.DoesNotExistError:
        return {"show": False}

    if qt.get("quotation_to") != "Customer":
        return {"show": False}
    if cint(qt.docstatus) == 2:
        return {"show": False}

    meta = frappe.get_meta("Quotation")
    if meta.has_field("custom_sales_invoice") and qt.get("custom_sales_invoice"):
        return {"show": False}

    if qt.status in ("Ordered", "Partially Ordered", "Lost", "Cancelled", "Expired"):
        return {"show": False}

    if qt.opportunity and _opportunity_has_other_accepted_quotation(qt.opportunity, qt.name):
        return {"show": False}

    return {"show": True}


@frappe.whitelist()
def accept_customer_quotation(quotation: str) -> dict:
    """
    "Teklifi Kabul Et" action:
    - Ensure Quotation is submitted
    - Create Sales Invoice from Quotation (draft)
    - Mark other customer quotations in same Opportunity as Lost (without changing Opportunity)
    - Submit linked Supplier Quotation (accepted) if present
    - Stop/cancel other supplier quotations in same Opportunity (rejected, best-effort)
    """
    qt = frappe.get_doc("Quotation", quotation)

    if qt.get("quotation_to") != "Customer":
        frappe.throw(_("Only Customer quotations can be accepted."))

    if qt.docstatus == 2:
        frappe.throw(_("Cancelled quotations cannot be accepted."))

    # Prevent double-acceptance
    if frappe.get_meta("Quotation").has_field("custom_sales_invoice") and qt.get("custom_sales_invoice"):
        _set_quotation_ordered_after_acceptance(qt.name)
        return {"sales_invoice": qt.custom_sales_invoice}

    if qt.opportunity and _opportunity_has_other_accepted_quotation(qt.opportunity, qt.name):
        frappe.throw(
            _("Another quotation for this opportunity has already been accepted."),
            title=_("Already accepted"),
        )

    _ensure_submitted(qt)

    sales_invoice = _create_sales_invoice_from_quotation(qt.name)
    if frappe.get_meta("Quotation").has_field("custom_sales_invoice"):
        qt.db_set("custom_sales_invoice", sales_invoice, update_modified=False)

    lost_quotations = _mark_other_customer_quotations_lost(qt)

    stopped_supplier_quotations: list[str] = []

    sq_name = _get_linked_supplier_quotation(qt)
    if sq_name and frappe.db.exists("Supplier Quotation", sq_name):
        # Caller may not have Supplier Quotation read/submit via Role; link is validated from Quotation.
        sq = frappe.get_doc("Supplier Quotation", sq_name, check_permission=False)
        _ensure_submitted(sq)

        if qt.get("opportunity"):
            stopped_supplier_quotations = _stop_or_cancel_other_supplier_quotations(sq.name, qt.opportunity)

    _set_quotation_ordered_after_acceptance(qt.name)

    return {
        "sales_invoice": sales_invoice,
        "lost_quotations": lost_quotations,
        "stopped_supplier_quotations": stopped_supplier_quotations,
    }

