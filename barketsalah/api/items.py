# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def ensure_service_item(item_code: str) -> str:
    """Ensure a non-stock Item exists for logistics / charge lines (item_code = code)."""
    if frappe.db.exists("Item", item_code):
        return item_code

    item_group = frappe.db.get_value("Item Group", "All Item Groups", "name")
    if not item_group:
        item_group = frappe.db.get_value("Item Group", {}, "name")
    if not item_group:
        frappe.throw(_("No Item Group found. Please create an Item Group first."))

    uom = frappe.db.get_value("UOM", "Nos", "name")
    if not uom:
        uom = frappe.db.get_value("UOM", {}, "name")
    if not uom:
        frappe.throw(_("No UOM found. Please create a UOM first."))

    item = frappe.new_doc("Item")
    item.item_code = item_code
    item.item_name = item_code
    item.item_group = item_group
    item.stock_uom = uom
    item.is_stock_item = 0
    item.insert(ignore_permissions=True)

    return item_code
