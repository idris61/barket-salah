import frappe
from frappe import _
from frappe.utils import add_days, nowdate
from barketsalah.api.utils import log_api_event


def _get_default_item_group() -> str:
    item_group = frappe.db.get_value("Item Group", "All Item Groups", "name")
    if item_group:
        return item_group

    fallback = frappe.db.get_value("Item Group", {}, "name")
    if not fallback:
        frappe.throw(_("No Item Group found. Please create an Item Group first."))
    return fallback


def _get_default_uom() -> str:
    uom = frappe.db.get_value("UOM", "Nos", "name")
    if uom:
        return uom

    fallback = frappe.db.get_value("UOM", {}, "name")
    if not fallback:
        frappe.throw(_("No UOM found. Please create a UOM first."))
    return fallback


def _ensure_ocean_freight_item() -> str:
    item_code = "Ocean Freight"
    if frappe.db.exists("Item", item_code):
        return item_code

    item = frappe.new_doc("Item")
    item.item_code = item_code
    item.item_name = item_code
    item.item_group = _get_default_item_group()
    item.stock_uom = _get_default_uom()
    item.is_stock_item = 0
    item.insert(ignore_permissions=True)

    return item_code



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


@frappe.whitelist()
def generate_quotes(opportunity: str) -> list[str]:
    opp = frappe.get_doc("Opportunity", opportunity)

    if not opp.party_name:
        frappe.throw(_("Opportunity must have a Customer."))

    shipping_request = opp.get("custom_shipping_request")
    if shipping_request and not frappe.db.exists("Shipping Request", shipping_request):
        frappe.throw(_("Linked Shipping Request {0} was not found.").format(shipping_request))

    carriers = frappe.get_all(
        "Supplier",
        filters={"disabled": 0},
        or_filters={"is_transporter": 1, "supplier_type": "Carrier"},
        fields=["name"],
        order_by="name asc",
    )
    if not carriers:
        frappe.throw(_("No carrier suppliers found."))

    charge_types = frappe.get_all(
        "Charge Type",
        filters={"is_default": 1},
        fields=["name", "category"],
        order_by="name asc",
    )
    if not charge_types:
        frappe.throw(_("No default Charge Type records found."))

    item_code = _ensure_ocean_freight_item()
    created_quotes = []

    for carrier in carriers:
        carrier_name = carrier.name

        if frappe.db.exists(
            "Quotation",
            {
                "opportunity": opp.name,
                "custom_carrier_company": carrier_name,
                "docstatus": ["<", 2],
            },
        ):
            continue

        quotation = frappe.new_doc("Quotation")
        quotation.quotation_to = "Customer"
        quotation.party_name = opp.party_name
        quotation.customer_name = (
            frappe.db.get_value("Customer", opp.party_name, "customer_name") or opp.party_name
        )
        quotation.opportunity = opp.name
        quotation.transaction_date = nowdate()
        quotation.valid_till = add_days(nowdate(), 7)
        quotation.custom_carrier_company = carrier_name
        quotation.custom_custom_quote_status = "Draft"
        quotation.append(
            "items",
            {
                "item_code": item_code,
                "qty": 1,
                "rate": 0,
            },
        )

        for charge in charge_types:
            quotation.append(
                "custom_charges_child_table",
                {
                    "charge_type": charge.name,
                    "amount": 0,
                },
            )

        quotation.insert(ignore_permissions=True)
        created_quotes.append(quotation.name)

    return created_quotes


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
