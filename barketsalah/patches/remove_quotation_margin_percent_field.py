import frappe


def execute():
    name = "Quotation-custom_margin_percent"
    if frappe.db.exists("Custom Field", name):
        frappe.delete_doc("Custom Field", name, force=True)
