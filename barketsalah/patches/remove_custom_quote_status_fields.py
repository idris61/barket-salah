import frappe


def execute():
    # Quotation: remove custom status field
    q_field = "Quotation-custom_custom_quote_status"
    if frappe.db.exists("Custom Field", q_field):
        frappe.delete_doc("Custom Field", q_field, force=True)

    # Supplier Quotation: remove customer decision field
    sq_field = "Supplier Quotation-custom_customer_decision"
    if frappe.db.exists("Custom Field", sq_field):
        frappe.delete_doc("Custom Field", sq_field, force=True)

