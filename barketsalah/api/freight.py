import frappe
from frappe import _
from frappe.utils import add_days, flt, nowdate

from barketsalah.api.charge_selection import list_charge_type_names_for_shipping_request
from barketsalah.api.items import ensure_service_item
from barketsalah.api.utils import log_api_event


def _get_default_uom() -> str:
    uom = frappe.db.get_value("UOM", "Nos", "name")
    if uom:
        return uom

    fallback = frappe.db.get_value("UOM", {}, "name")
    if not fallback:
        frappe.throw(_("No UOM found. Please create a UOM first."))
    return fallback


@frappe.whitelist()
def make_opportunity(shipping_request: str) -> str:
    log_api_event("freight.make_opportunity.started", shipping_request=shipping_request)
    sr = frappe.get_doc("Shipping Request", shipping_request)

    if sr.get("opportunity"):
        existing_shipping_request = frappe.db.get_value(
            "Opportunity", sr.opportunity, "custom_shipping_request"
        )
        if not existing_shipping_request:
            frappe.db.set_value(
                "Opportunity",
                sr.opportunity,
                "custom_shipping_request",
                sr.name,
                update_modified=False,
            )
            log_api_event(
                "freight.make_opportunity.updated_existing_opportunity_shipping_request",
                shipping_request=sr.name,
                opportunity=sr.opportunity,
            )

        log_api_event(
            "freight.make_opportunity.existing_opportunity",
            shipping_request=sr.name,
            opportunity=sr.opportunity,
            insurance_requested=sr.get("insurance_requested"),
        )
        if sr.get("insurance_requested") and not frappe.db.get_value(
            "Opportunity", sr.opportunity, "custom_insurance_requested"
        ):
            frappe.db.set_value(
                "Opportunity",
                sr.opportunity,
                "custom_insurance_requested",
                1,
                update_modified=False,
            )
            log_api_event(
                "freight.make_opportunity.updated_existing_opportunity_insurance",
                shipping_request=sr.name,
                opportunity=sr.opportunity,
            )
        return sr.opportunity

    opp = frappe.new_doc("Opportunity")
    opp.opportunity_from = "Customer"
    opp.party_name = sr.customer
    opp.customer_name = frappe.db.get_value("Customer", sr.customer, "customer_name") or sr.customer
    opp.custom_shipping_request = sr.name
    if sr.get("insurance_requested"):
        opp.custom_insurance_requested = 1
        log_api_event(
            "freight.make_opportunity.set_new_opportunity_insurance",
            shipping_request=sr.name,
        )
    opp.status = "Open"
    opp.insert(ignore_permissions=True)

    sr.db_set("opportunity", opp.name)
    sr.db_set("status", "Converted to Opportunity")
    log_api_event(
        "freight.make_opportunity.created",
        shipping_request=sr.name,
        opportunity=opp.name,
        insurance_requested=sr.get("insurance_requested"),
        opportunity_insurance=opp.get("custom_insurance_requested"),
    )

    return opp.name


def _company_for_opportunity_buying(opportunity_name: str) -> str:
    company = frappe.db.get_value("Opportunity", opportunity_name, "company")
    if company:
        return company
    company = frappe.defaults.get_user_default("Company")
    if company:
        return company
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if company:
        return company
    frappe.throw(
        _("Set Company on the Opportunity, or a user / global default Company, before creating supplier quotations.")
    )


def _company_default_currency(company: str) -> str:
    currency = frappe.db.get_value("Company", company, "default_currency")
    if not currency:
        frappe.throw(_("Company {0} has no default currency.").format(company))
    return currency


def _open_supplier_quotation_exists(opportunity: str, supplier: str) -> bool:
    return bool(
        frappe.get_all(
            "Supplier Quotation",
            filters={
                "opportunity": opportunity,
                "supplier": supplier,
                "docstatus": ["<", 2],
            },
            limit=1,
            pluck="name",
        )
    )


def _shipping_request_for_opportunity(opportunity_name: str, linked_name: str | None) -> str | None:
    """
    Prefer Opportunity.custom_shipping_request when valid; otherwise resolve via
    Shipping Request.opportunity (SR → Fırsat zinciri, fırsatta link bazen boş kalabiliyor).
    """
    if linked_name and frappe.db.exists("Shipping Request", linked_name):
        return linked_name
    candidates = frappe.get_all(
        "Shipping Request",
        filters={"opportunity": opportunity_name},
        fields=["name", "customer"],
        order_by="modified desc",
    )
    if not candidates:
        return None
    party = frappe.db.get_value("Opportunity", opportunity_name, "party_name")
    if party:
        for row in candidates:
            if row.get("customer") == party:
                return row.name
    return candidates[0].name


@frappe.whitelist()
def generate_carrier_supplier_quotations(opportunity: str) -> list[str]:
    """One draft Supplier Quotation per transporter supplier, lines from Charge Types filtered by Shipping Request."""
    log_api_event("freight.generate_carrier_supplier_quotations.started", opportunity=opportunity)
    opp = frappe.get_doc("Opportunity", opportunity)

    shipping_request = _shipping_request_for_opportunity(opp.name, opp.get("custom_shipping_request"))
    if shipping_request and not frappe.db.exists("Shipping Request", shipping_request):
        frappe.throw(_("Linked Shipping Request {0} was not found.").format(shipping_request))

    if (
        shipping_request
        and frappe.get_meta("Opportunity").has_field("custom_shipping_request")
        and not opp.get("custom_shipping_request")
    ):
        frappe.db.set_value(
            "Opportunity",
            opp.name,
            "custom_shipping_request",
            shipping_request,
            update_modified=False,
        )
        opp.custom_shipping_request = shipping_request

    company = _company_for_opportunity_buying(opp.name)
    currency = _company_default_currency(company)

    charge_names = list_charge_type_names_for_shipping_request(shipping_request)
    if not charge_names:
        frappe.throw(
            _(
                "No charge lines apply for this shipping request. Check default Charge Types "
                "(and categories: Insurance only when requested; Ocean only for Sea; dangerous-goods-only rows)."
            )
        )

    carriers = frappe.get_all(
        "Supplier",
        filters={"disabled": 0, "is_transporter": 1},
        fields=["name"],
        order_by="name asc",
    )
    if not carriers:
        frappe.throw(_("No suppliers are marked as transporter (Nakliyeci)."))

    valid_till = add_days(nowdate(), 14)
    created: list[str] = []

    for carrier in carriers:
        supplier_name = carrier.name
        if _open_supplier_quotation_exists(opp.name, supplier_name):
            log_api_event(
                "freight.generate_carrier_supplier_quotations.skipped_existing",
                opportunity=opp.name,
                supplier=supplier_name,
            )
            continue

        sq = frappe.new_doc("Supplier Quotation")
        sq.supplier = supplier_name
        sq.company = company
        sq.currency = currency
        sq.conversion_rate = 1.0
        sq.transaction_date = nowdate()
        sq.valid_till = valid_till
        sq.opportunity = opp.name
        if frappe.get_meta("Supplier Quotation").has_field("custom_shipping_request") and shipping_request:
            sq.custom_shipping_request = shipping_request

        for charge_name in charge_names:
            item_code = ensure_service_item(charge_name)
            stock_uom = frappe.db.get_value("Item", item_code, "stock_uom") or _get_default_uom()
            sq.append(
                "items",
                {
                    "item_code": item_code,
                    "qty": 1,
                    "rate": flt(0),
                    "uom": stock_uom,
                    "stock_uom": stock_uom,
                    "conversion_factor": 1,
                },
            )

        sq.run_method("set_missing_values")
        sq.insert(ignore_permissions=True)
        created.append(sq.name)
        log_api_event(
            "freight.generate_carrier_supplier_quotations.created",
            opportunity=opp.name,
            supplier=supplier_name,
            supplier_quotation=sq.name,
        )

    if created:
        # ERPNext standard Opportunity status (options include "Quotation").
        terminal = frozenset({"Lost", "Closed", "Converted"})
        if opp.status not in terminal:
            frappe.db.set_value(
                "Opportunity",
                opp.name,
                "status",
                "Quotation",
                update_modified=True,
            )
        log_api_event(
            "freight.generate_carrier_supplier_quotations.opportunity_status_set",
            opportunity=opp.name,
            created=len(created),
        )

    return created


@frappe.whitelist()
def create_shipment(sales_order: str) -> str:
    existing = frappe.db.get_value("Shipments", {"sales_order": sales_order}, "name")
    if existing:
        return existing

    so = frappe.get_doc("Sales Order", sales_order)

    shipment = frappe.new_doc("Shipments")
    shipment.customer = so.customer
    shipment.sales_order = so.name
    shipment.status = "Booked"
    shipment.insert(ignore_permissions=True)

    return shipment.name
