import frappe
from frappe.cache_manager import clear_doctype_cache


def _clear_supplier_quotation_link_to_customer_quotation(quotation_name: str) -> None:
    """Remove Supplier Quotation → Quotation back-link so delete/cancel is not blocked."""
    if not quotation_name:
        return
    if not frappe.get_meta("Supplier Quotation").has_field("custom_linked_customer_quotation"):
        return

    sq_names = frappe.get_all(
        "Supplier Quotation",
        filters={"custom_linked_customer_quotation": quotation_name},
        pluck="name",
    )
    if not sq_names:
        return

    meta = frappe.get_meta("Supplier Quotation")
    if meta.has_field("custom_customer_decision"):
        frappe.db.sql(
            """
            UPDATE `tabSupplier Quotation`
            SET `custom_linked_customer_quotation` = NULL,
                `custom_customer_decision` = %s
            WHERE `custom_linked_customer_quotation` = %s
            """,
            ("Pending", quotation_name),
        )
    else:
        frappe.db.sql(
            """
            UPDATE `tabSupplier Quotation`
            SET `custom_linked_customer_quotation` = NULL
            WHERE `custom_linked_customer_quotation` = %s
            """,
            (quotation_name,),
        )

    for sq_name in sq_names:
        frappe.clear_document_cache("Supplier Quotation", sq_name)
    clear_doctype_cache("Supplier Quotation")


def _clear_customer_quotation_link_to_supplier_quotation(supplier_quotation_name: str) -> None:
    """Remove Quotation → Supplier Quotation links so cancel/delete is not blocked."""
    if not supplier_quotation_name:
        return

    meta_q = frappe.get_meta("Quotation")
    base = {"docstatus": ["<", 2]}

    filters_list = []
    if meta_q.has_field("custom_source_supplier_quotation"):
        filters_list.append({**base, "custom_source_supplier_quotation": supplier_quotation_name})
    if meta_q.has_field("supplier_quotation"):
        filters_list.append({**base, "supplier_quotation": supplier_quotation_name})

    quotation_names: set[str] = set()
    for flt in filters_list:
        quotation_names.update(
            frappe.get_all("Quotation", filters=flt, pluck="name")  # type: ignore[arg-type]
        )

    if not quotation_names:
        return

    update = {}
    if meta_q.has_field("custom_source_supplier_quotation"):
        update["custom_source_supplier_quotation"] = None
    if meta_q.has_field("supplier_quotation"):
        update["supplier_quotation"] = None

    for qn in quotation_names:
        frappe.db.set_value("Quotation", qn, update, update_modified=False)
        frappe.clear_document_cache("Quotation", qn)


def supplier_quotation_before_cancel(doc, method=None) -> None:
    if doc.doctype != "Supplier Quotation":
        return
    # Clear both directions of the link, so cancel is not blocked.
    if doc.get("custom_linked_customer_quotation"):
        _clear_supplier_quotation_link_to_customer_quotation(doc.custom_linked_customer_quotation)
    _clear_customer_quotation_link_to_supplier_quotation(doc.name)


def supplier_quotation_on_trash(doc, method=None) -> None:
    if doc.doctype != "Supplier Quotation":
        return
    if doc.get("custom_linked_customer_quotation"):
        _clear_supplier_quotation_link_to_customer_quotation(doc.custom_linked_customer_quotation)
    _clear_customer_quotation_link_to_supplier_quotation(doc.name)


def quotation_on_trash(doc, method=None) -> None:
    if doc.doctype != "Quotation":
        return
    _clear_supplier_quotation_link_to_customer_quotation(doc.name)


def quotation_before_cancel(doc, method=None) -> None:
    if doc.doctype != "Quotation":
        return
    _clear_supplier_quotation_link_to_customer_quotation(doc.name)


def opportunity_on_trash(doc, method=None) -> None:
    if not doc.get("custom_shipping_request"):
        return
    sr_name = doc.custom_shipping_request
    if not frappe.db.exists("Shipping Request", sr_name):
        return
    frappe.db.set_value(
        "Shipping Request",
        sr_name,
        {
            "opportunity": None,
            "status": "Draft",
        },
        update_modified=True,
    )
    frappe.clear_document_cache("Shipping Request", sr_name)
