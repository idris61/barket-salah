import frappe


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
