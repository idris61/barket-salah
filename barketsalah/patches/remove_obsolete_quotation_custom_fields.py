import frappe

OBSOLETE = (
    "Quotation-custom_carrier_company",
    "Quotation-custom_transit_time_days",
    "Quotation-custom_estimated_time_of_arrival",
    "Quotation-custom_custom_charges_table",
    "Quotation-custom_quotation_charges_table",
    "Quotation-custom_charges_child_table",
    "Quotation-custom_revision_requests",
    "Quotation-custom_revision_request",
)


def execute():
    for name in OBSOLETE:
        if frappe.db.exists("Custom Field", name):
            frappe.delete_doc("Custom Field", name, force=True)
