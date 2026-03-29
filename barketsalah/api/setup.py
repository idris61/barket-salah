import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate


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
        return

    shipping_request = frappe.db.get_value("Opportunity", opportunity_name, "custom_shipping_request")
    if not shipping_request:
        return

    if not frappe.db.exists("Shipping Request", shipping_request):
        return

    insurance_requested = frappe.db.get_value("Shipping Request", shipping_request, "insurance_requested")
    if not insurance_requested:
        return

    if frappe.db.get_value("Opportunity", opportunity_name, "custom_insurance_requested"):
        return

    frappe.db.set_value(
        "Opportunity",
        opportunity_name,
        "custom_insurance_requested",
        1,
        update_modified=False,
    )


def quotation_create_sales_order_on_accept(doc, method=None) -> None:
    if doc.doctype != "Quotation":
        return

    # ERPNext maps Sales Order from submitted Quotations.
    if doc.docstatus != 1:
        return

    if doc.get("custom_custom_quote_status") != "Accepted":
        return

    if _get_existing_sales_order_for_quotation(doc.name):
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
    _sync_opportunity_insurance_flag(doc.get("opportunity"))

    frappe.msgprint(
        _("Sales Order {0} was created automatically.").format(frappe.bold(sales_order.name)),
        alert=True,
    )
