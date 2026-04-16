# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, nowdate

from barketsalah.api.utils import log_api_event


def existing_active_customer_quotation_for_sq(sq_name: str) -> str | None:
    """
    Return the name of a draft or submitted customer Quotation already tied to this
    Supplier Quotation (not cancelled). Used to block creating two sales quotations
    from the same carrier quote.
    """
    meta_q = frappe.get_meta("Quotation")
    base = {"docstatus": ["<", 2]}

    if meta_q.has_field("custom_source_supplier_quotation"):
        rows = frappe.get_all(
            "Quotation",
            filters={**base, "custom_source_supplier_quotation": sq_name},
            pluck="name",
            limit=1,
        )
        if rows:
            return rows[0]

    if meta_q.has_field("supplier_quotation"):
        rows = frappe.get_all(
            "Quotation",
            filters={**base, "supplier_quotation": sq_name},
            pluck="name",
            limit=1,
        )
        if rows:
            return rows[0]

    meta_sq = frappe.get_meta("Supplier Quotation")
    if meta_sq.has_field("custom_linked_customer_quotation"):
        linked = frappe.db.get_value("Supplier Quotation", sq_name, "custom_linked_customer_quotation")
        if linked and frappe.db.exists("Quotation", linked):
            if frappe.db.get_value("Quotation", linked, "docstatus") in (0, 1):
                return linked

    return None


def _raise_if_customer_quotation_exists_for_sq(sq_name: str) -> None:
    existing = existing_active_customer_quotation_for_sq(sq_name)
    if existing:
        frappe.throw(
            _("A customer quotation already exists for this supplier quotation: {0}").format(existing),
            title=_("Already exists"),
        )


def _align_quotation_items_with_supplier_cost(qt, supplier_rates: list[float]) -> None:
    """
    ERPNext applies margin on price_list_rate (see taxes_and_totals.apply_pricing_rule_on_item /
    calculate_margin). Copying only `rate` from Supplier Quotation leaves price_list_rate filled
    from the selling price list (or empty), so margin %/amount uses the wrong base. After
    set_missing_values, force each line's list price to the supplier cost and reset margin/discount
    so the user can add markup on top of carrier rates reliably.
    """
    items = qt.get("items") or []
    if len(items) != len(supplier_rates):
        frappe.log_error(
            title="sales_from_carrier: item/rate length mismatch",
            message=f"quotation lines={len(items)} supplier_rates={len(supplier_rates)}",
        )
    for item_row, supplier_rate in zip(items, supplier_rates):
        cost = flt(supplier_rate)
        item_row.price_list_rate = cost
        item_row.rate = cost
        item_row.margin_type = ""
        item_row.margin_rate_or_amount = 0
        item_row.discount_percentage = 0
        item_row.discount_amount = 0
        item_row.distributed_discount_amount = 0
        item_row.pricing_rules = ""
        item_row.rate_with_margin = 0
        item_row.base_rate_with_margin = 0
    qt.calculate_taxes_and_totals()


@frappe.whitelist()
def make_customer_quotation_from_supplier_quotation(supplier_quotation: str) -> str:
    """
    Build a selling Quotation for the Opportunity customer from carrier Supplier Quotation lines.
    Supplier unit rates are copied; price_list_rate is set to the same cost so ERPNext margin
    (Kâr Türü / %) applies on the carrier quote, not on the standard selling price list.
    """
    sq = frappe.get_doc("Supplier Quotation", supplier_quotation)

    if not sq.get("opportunity"):
        frappe.throw(_("Supplier Quotation must be linked to an Opportunity."))

    _raise_if_customer_quotation_exists_for_sq(sq.name)

    opp = frappe.get_doc("Opportunity", sq.opportunity)
    customer = opp.party_name
    if not customer:
        frappe.throw(_("Opportunity must have a Customer."))

    company = opp.company or sq.company
    if not company:
        frappe.throw(_("Set Company on the Opportunity or Supplier Quotation."))

    qt = frappe.new_doc("Quotation")
    qt.quotation_to = "Customer"
    qt.party_name = customer
    if frappe.get_meta("Quotation").has_field("custom_customer"):
        qt.custom_customer = customer
    qt.customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
    qt.company = company
    qt.opportunity = sq.opportunity
    if frappe.get_meta("Quotation").has_field("supplier_quotation"):
        qt.supplier_quotation = sq.name
    qt.transaction_date = nowdate()
    qt.valid_till = add_days(nowdate(), 14)
    if frappe.get_meta("Quotation").has_field("custom_source_supplier_quotation"):
        qt.custom_source_supplier_quotation = sq.name
    if frappe.get_meta("Quotation").has_field("custom_carrier_supplier_name"):
        qt.custom_carrier_supplier_name = sq.supplier_name or (
            frappe.db.get_value("Supplier", sq.supplier, "supplier_name") if sq.get("supplier") else None
        )

    supplier_rates: list[float] = []
    for row in sq.get("items") or []:
        if not row.get("item_code"):
            continue
        supplier_rates.append(flt(row.get("rate") or 0))
        qt.append(
            "items",
            {
                "item_code": row.item_code,
                "qty": flt(row.get("qty") or 1),
                "rate": flt(row.get("rate") or 0),
                "uom": row.uom,
                "stock_uom": row.stock_uom or row.uom,
                "conversion_factor": flt(row.get("conversion_factor") or 1),
            },
        )

    if not qt.get("items"):
        frappe.throw(_("Supplier Quotation has no item lines to copy."))

    qt.run_method("set_missing_values")
    _align_quotation_items_with_supplier_cost(qt, supplier_rates)
    _raise_if_customer_quotation_exists_for_sq(sq.name)
    qt.insert(ignore_permissions=True)

    if frappe.get_meta("Supplier Quotation").has_field("custom_linked_customer_quotation"):
        frappe.db.set_value(
            "Supplier Quotation",
            sq.name,
            {
                "custom_linked_customer_quotation": qt.name,
            },
            update_modified=True,
        )

    log_api_event(
        "sales_from_carrier.created_customer_quotation",
        supplier_quotation=sq.name,
        quotation=qt.name,
    )

    return qt.name
