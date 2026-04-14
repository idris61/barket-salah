import frappe


def execute():
    name = "Request for Quotation-custom_shipping_request"
    if frappe.db.exists("Custom Field", name):
        frappe.delete_doc("Custom Field", name, force=True)
