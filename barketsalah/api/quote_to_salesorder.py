import frappe
from frappe import _


def _get_default_item_group() -> str:
    item_group = frappe.db.get_value("Item Group", "All Item Groups", "name")
    if item_group:
        return item_group

    fallback = frappe.db.get_value("Item Group", {}, "name")
    if not fallback:
        frappe.throw(_("No Item Group found. Please create an Item Group first."))
    return fallback


def _get_default_uom() -> str:
    uom = frappe.db.get_value("UOM", "Nos", "name")
    if uom:
        return uom

    fallback = frappe.db.get_value("UOM", {}, "name")
    if not fallback:
        frappe.throw(_("No UOM found. Please create a UOM first."))
    return fallback


def _ensure_charge_item(charge_name: str) -> str:
    if frappe.db.exists("Item", charge_name):
        return charge_name

    item = frappe.new_doc("Item")
    item.item_code = charge_name
    item.item_name = charge_name
    item.item_group = _get_default_item_group()
    item.stock_uom = _get_default_uom()
    item.is_stock_item = 0
    item.insert(ignore_permissions=True)

    return charge_name


def prepare_quote_items_for_sales_order(doc, method=None):
    if doc.doctype != "Quotation":
        return

    charge_rows = doc.get("custom_charges_child_table") or []

    new_items = []
    for charge in charge_rows:
        if not charge.charge_type:
            continue

        item_code = _ensure_charge_item(charge.charge_type)
        uom = _get_default_uom()
        qty = 1
        new_items.append(
            {
                "item_code": item_code,
                "item_name": charge.charge_type,
                "description": charge.notes or charge.charge_type,
                "qty": qty,
                "ordered_qty": 0,
                "uom": uom,
                "stock_uom": uom,
                "conversion_factor": 1,
                "rate": charge.amount or 0,
            }
        )

    doc.set("items", [])
    for row in new_items:
        doc.append("items", row)
