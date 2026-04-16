# Copyright (c) 2026, barketsalah and contributors
# For license information, please see license.txt

"""
Runs once per site: create Quotation.custom_customer if missing (fixtures are not auto-imported
on migrate), then backfill from party_name.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
    if not frappe.db.exists("Custom Field", "Quotation-custom_customer"):
        create_custom_field(
            "Quotation",
            {
                "fieldname": "custom_customer",
                "fieldtype": "Link",
                "options": "Customer",
                "label": "Customer",
                "insert_after": "party_name",
                "hidden": 1,
                "read_only": 1,
                "allow_on_submit": 1,
                "print_hide": 1,
                "module": "Barketsalah",
                "description": (
                    "Synced from Party when Quotation To is Customer. "
                    "Created by patch if fixture was not imported."
                ),
            },
            is_system_generated=False,
        )

    frappe.clear_cache(doctype="Quotation")

    if not frappe.db.has_column("Quotation", "custom_customer"):
        return

    frappe.db.sql(
        """
		update `tabQuotation`
		set `custom_customer` = `party_name`
		where `quotation_to` = 'Customer'
		  and ifnull(`party_name`, '') != ''
		  and (`custom_customer` is null or `custom_customer` = '')
		"""
    )
