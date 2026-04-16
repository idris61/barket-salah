import frappe

from barketsalah.api.quotation_acceptance import _set_quotation_ordered_after_acceptance


def execute():
    """Backfill Ordered status for quotations already linked to a sales invoice from acceptance."""
    meta = frappe.get_meta("Quotation")
    if not meta.has_field("custom_sales_invoice"):
        return

    names = frappe.get_all(
        "Quotation",
        filters={
            "docstatus": 1,
            "custom_sales_invoice": ["is", "set"],
            "status": ["in", ["Open", "Replied"]],
        },
        pluck="name",
    )
    for name in names:
        try:
            _set_quotation_ordered_after_acceptance(name)
        except Exception:
            frappe.log_error(f"sync_accepted_quotation_ordered_status failed for {name}")
