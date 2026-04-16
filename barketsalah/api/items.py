# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_default_uom() -> str:
    uom = frappe.db.get_value("UOM", "Nos", "name")
    if uom:
        return uom

    fallback = frappe.db.get_value("UOM", {}, "name")
    if not fallback:
        frappe.throw(_("No UOM found. Please create a UOM first."))
    return fallback


def ensure_service_item(item_code: str) -> str:
    """Ensure a non-stock Item exists for logistics / charge lines (item_code = code)."""
    if frappe.db.exists("Item", item_code):
        return item_code

    item_group = frappe.db.get_value("Item Group", "All Item Groups", "name")
    if not item_group:
        item_group = frappe.db.get_value("Item Group", {}, "name")
    if not item_group:
        frappe.throw(_("No Item Group found. Please create an Item Group first."))

    uom = get_default_uom()

    item = frappe.new_doc("Item")
    item.item_code = item_code
    item.item_name = item_code
    item.item_group = item_group
    item.stock_uom = uom
    item.is_stock_item = 0
    item.insert(ignore_permissions=True)

    return item_code
