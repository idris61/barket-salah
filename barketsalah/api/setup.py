import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate
from barketsalah.api.utils import log_api_event


def quotation_before_save(doc, method=None) -> None:
    if doc.doctype != "Quotation":
        return

    if doc.get("custom_custom_quote_status") != "Accepted" or not doc.get("opportunity"):
        return

    quotations = frappe.get_all(
        "Quotation",
        filters={"opportunity": doc.opportunity, "docstatus": ["<", 2]},
        fields=["name"],
    )

    for quote in quotations:
        if quote.name == doc.name:
            continue

        frappe.db.set_value(
            "Quotation",
            quote.name,
            "custom_custom_quote_status",
            "Rejected",
            update_modified=False,
        )


def _get_existing_sales_order_for_quotation(quotation_name: str) -> str | None:
    existing = frappe.get_all(
        "Sales Order Item",
        filters={
            "prevdoc_docname": quotation_name,
            "docstatus": ["<", 2],
        },
        fields=["parent"],
        limit=1,
    )
    return existing[0].parent if existing else None


def _sync_opportunity_insurance_flag(opportunity_name: str | None) -> None:
    if not opportunity_name:
        log_api_event("setup.sync_insurance.skipped_missing_opportunity")
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


def quotation_create_sales_order_on_accept(doc, method=None) -> None:
    log_api_event(
        "setup.create_so_on_accept.started",
        quotation=doc.get("name"),
        quote_status=doc.get("custom_custom_quote_status"),
        docstatus=doc.docstatus,
        opportunity=doc.get("opportunity"),
    )

    if doc.doctype != "Quotation":
        log_api_event("setup.create_so_on_accept.skipped_not_quotation", doctype=doc.doctype)
        return

    # ERPNext maps Sales Order from submitted Quotations.
    if doc.docstatus != 1:
        log_api_event(
            "setup.create_so_on_accept.skipped_not_submitted",
            quotation=doc.get("name"),
            docstatus=doc.docstatus,
        )
        return

    if doc.get("custom_custom_quote_status") != "Accepted":
        log_api_event(
            "setup.create_so_on_accept.skipped_not_accepted",
            quotation=doc.get("name"),
            quote_status=doc.get("custom_custom_quote_status"),
        )
        return

    if existing_so := _get_existing_sales_order_for_quotation(doc.name):
        log_api_event(
            "setup.create_so_on_accept.skipped_so_exists",
            quotation=doc.get("name"),
            sales_order=existing_so,
        )
        return

    from erpnext.selling.doctype.quotation.quotation import make_sales_order

    sales_order = make_sales_order(doc.name)
    default_delivery_date = add_days(getdate(doc.get("transaction_date") or nowdate()), 7)
    sales_order.delivery_date = default_delivery_date
    for item in sales_order.get("items") or []:
        if not item.get("delivery_date"):
            item.delivery_date = default_delivery_date

    sales_order.flags.ignore_permissions = True
    sales_order.insert(ignore_permissions=True)
    log_api_event(
        "setup.create_so_on_accept.created",
        quotation=doc.get("name"),
        sales_order=sales_order.name,
        opportunity=doc.get("opportunity"),
    )
    _sync_opportunity_insurance_flag(doc.get("opportunity"))

    frappe.msgprint(
        _("Sales Order {0} was created automatically.").format(frappe.bold(sales_order.name)),
        alert=True,
    )
