import frappe
from frappe import _
from frappe.utils import flt

from barketsalah.api.utils import log_api_event


def _compute_total_profit_for_quotation(doc) -> float:
    """
    Profit = sum((rate - price_list_rate) * qty) across item rows.
    Assumes `price_list_rate` is used as cost basis in this workflow.
    """
    total = 0.0
    for row in doc.get("items") or []:
        qty = flt(row.get("qty") or 0)
        if not qty:
            continue
        rate = flt(row.get("rate") or 0)
        cost = flt(row.get("price_list_rate") or 0)
        total += (rate - cost) * qty
    return flt(total)


def quotation_before_save(doc, method=None) -> None:
    if doc.doctype != "Quotation":
        return

    # Keep Total Profit in sync for UI/reporting.
    if frappe.get_meta("Quotation").has_field("custom_total_profit_amount"):
        doc.custom_total_profit_amount = _compute_total_profit_for_quotation(doc)

    if doc.is_new():
        sq_name = doc.get("custom_source_supplier_quotation")
        if not sq_name and frappe.get_meta("Quotation").has_field("supplier_quotation"):
            sq_name = doc.get("supplier_quotation")
        if sq_name and frappe.db.exists("Supplier Quotation", sq_name):
            from barketsalah.api.sales_from_carrier import existing_active_customer_quotation_for_sq

            existing = existing_active_customer_quotation_for_sq(sq_name)
            if existing:
                frappe.throw(
                    _("A customer quotation already exists for this supplier quotation: {0}").format(
                        existing
                    ),
                    title=_("Already exists"),
                )

    if frappe.get_meta("Quotation").has_field("custom_carrier_supplier_name"):
        sq_name = doc.get("custom_source_supplier_quotation")
        if sq_name:
            sq = frappe.get_cached_doc("Supplier Quotation", sq_name)
            doc.custom_carrier_supplier_name = sq.supplier_name or (
                frappe.db.get_value("Supplier", sq.supplier, "supplier_name") if sq.get("supplier") else None
            )
        else:
            doc.custom_carrier_supplier_name = None

    if doc.get("custom_source_supplier_quotation") and frappe.get_meta("Quotation").has_field(
        "supplier_quotation"
    ):
        doc.supplier_quotation = doc.custom_source_supplier_quotation

    if not doc.get("opportunity"):
        return

    old_status = None
    if not doc.is_new():
        old_status = frappe.db.get_value("Quotation", doc.name, "custom_custom_quote_status")

    new_status = doc.get("custom_custom_quote_status")

    if new_status == "Accepted" and old_status != "Accepted":
        for quote in frappe.get_all(
            "Quotation",
            filters={"opportunity": doc.opportunity, "docstatus": ["<", 2]},
            fields=["name"],
        ):
            if quote.name == doc.name:
                continue
            frappe.db.set_value(
                "Quotation",
                quote.name,
                "custom_custom_quote_status",
                "Rejected",
                update_modified=False,
            )
        sync_supplier_quotations_for_accepted_quotation(doc)

    if new_status == "Rejected" and old_status != "Rejected":
        sync_supplier_quotation_lost_from_rejected_customer_quote(doc)


def sync_supplier_quotations_for_accepted_quotation(doc) -> None:
    if not doc.get("custom_source_supplier_quotation"):
        return
    if not frappe.get_meta("Supplier Quotation").has_field("custom_customer_decision"):
        return
    win = doc.custom_source_supplier_quotation
    opp = doc.opportunity
    win_sr = None
    if frappe.get_meta("Supplier Quotation").has_field("custom_shipping_request"):
        win_sr = frappe.db.get_value("Supplier Quotation", win, "custom_shipping_request")

    for name in frappe.get_all(
        "Supplier Quotation",
        filters={"opportunity": opp, "docstatus": ["<", 2]},
        pluck="name",
    ):
        if win_sr is not None:
            other_sr = frappe.db.get_value("Supplier Quotation", name, "custom_shipping_request")
            if other_sr != win_sr:
                continue
        decision = "Won" if name == win else "Lost"
        frappe.db.set_value(
            "Supplier Quotation",
            name,
            "custom_customer_decision",
            decision,
            update_modified=False,
        )


def sync_supplier_quotation_lost_from_rejected_customer_quote(doc) -> None:
    sq = doc.get("custom_source_supplier_quotation")
    if not sq or not frappe.get_meta("Supplier Quotation").has_field("custom_customer_decision"):
        return
    frappe.db.set_value(
        "Supplier Quotation",
        sq,
        "custom_customer_decision",
        "Lost",
        update_modified=False,
    )


def _sync_opportunity_insurance_flag(opportunity_name: str | None) -> None:
    if not opportunity_name:
        log_api_event("setup.sync_insurance.skipped_missing_opportunity")
        return

    if not frappe.get_meta("Opportunity").has_field("custom_shipping_request"):
        log_api_event(
            "setup.sync_insurance.skipped_missing_opportunity_field",
            opportunity=opportunity_name,
            fieldname="custom_shipping_request",
            level="warning",
        )
        return

    shipping_request = frappe.db.get_value("Opportunity", opportunity_name, "custom_shipping_request")
    if not shipping_request:
        log_api_event(
            "setup.sync_insurance.skipped_missing_shipping_request",
            opportunity=opportunity_name,
        )
        return

    if not frappe.db.exists("Shipping Request", shipping_request):
        log_api_event(
            "setup.sync_insurance.skipped_shipping_request_not_found",
            opportunity=opportunity_name,
            shipping_request=shipping_request,
            level="warning",
        )
        return

    insurance_requested = frappe.db.get_value("Shipping Request", shipping_request, "insurance_requested")
    if not insurance_requested:
        log_api_event(
            "setup.sync_insurance.skipped_insurance_not_requested",
            opportunity=opportunity_name,
            shipping_request=shipping_request,
        )
        return

    if frappe.db.get_value("Opportunity", opportunity_name, "custom_insurance_requested"):
        log_api_event(
            "setup.sync_insurance.skipped_already_checked",
            opportunity=opportunity_name,
            shipping_request=shipping_request,
        )
        return

    frappe.db.set_value(
        "Opportunity",
        opportunity_name,
        "custom_insurance_requested",
        1,
        update_modified=False,
    )
    log_api_event(
        "setup.sync_insurance.updated",
        opportunity=opportunity_name,
        shipping_request=shipping_request,
    )


def quotation_submit_create_invoices_on_accept(doc, method=None) -> None:
    if doc.doctype != "Quotation":
        return
    if doc.docstatus != 1:
        return
    if doc.get("custom_custom_quote_status") != "Accepted":
        log_api_event("setup.submit_invoices.skipped_not_accepted", quotation=doc.name)
        return

    from erpnext.selling.doctype.quotation.quotation import make_sales_invoice

    if frappe.get_meta("Quotation").has_field("custom_sales_invoice"):
        existing_si = doc.get("custom_sales_invoice") or frappe.db.get_value(
            "Quotation", doc.name, "custom_sales_invoice"
        )
        if existing_si and frappe.db.exists("Sales Invoice", existing_si):
            log_api_event(
                "setup.submit_invoices.skipped_si_exists",
                quotation=doc.name,
                sales_invoice=existing_si,
            )
        else:
            si = make_sales_invoice(doc.name)
            si.flags.ignore_permissions = True
            si.insert(ignore_permissions=True)
            frappe.db.set_value(
                "Quotation",
                doc.name,
                "custom_sales_invoice",
                si.name,
                update_modified=False,
            )
            frappe.msgprint(
                _("Draft sales invoice {0} was created.").format(frappe.bold(si.name)),
                alert=True,
            )
            log_api_event("setup.submit_invoices.si_created", quotation=doc.name, sales_invoice=si.name)

    sq_name = doc.get("custom_source_supplier_quotation")
    if (
        sq_name
        and frappe.get_meta("Supplier Quotation").has_field("custom_purchase_invoice")
        and frappe.db.exists("Supplier Quotation", sq_name)
    ):
        existing_pi = frappe.db.get_value("Supplier Quotation", sq_name, "custom_purchase_invoice")
        if existing_pi and frappe.db.exists("Purchase Invoice", existing_pi):
            log_api_event(
                "setup.submit_invoices.skipped_pi_exists",
                supplier_quotation=sq_name,
                purchase_invoice=existing_pi,
            )
        else:
            sq_doc = frappe.get_doc("Supplier Quotation", sq_name)
            if sq_doc.docstatus != 1:
                frappe.msgprint(
                    _("Submit supplier quotation {0} first; purchase invoice was not created.").format(
                        frappe.bold(sq_name)
                    ),
                    indicator="orange",
                )
                log_api_event(
                    "setup.submit_invoices.skipped_sq_not_submitted",
                    supplier_quotation=sq_name,
                )
            else:
                from erpnext.buying.doctype.supplier_quotation.supplier_quotation import (
                    make_purchase_invoice,
                )

                pi = make_purchase_invoice(sq_name)
                pi.flags.ignore_permissions = True
                pi.insert(ignore_permissions=True)
                frappe.db.set_value(
                    "Supplier Quotation",
                    sq_name,
                    "custom_purchase_invoice",
                    pi.name,
                    update_modified=False,
                )
                frappe.msgprint(
                    _("Draft purchase invoice {0} was created.").format(frappe.bold(pi.name)),
                    alert=True,
                )
                log_api_event(
                    "setup.submit_invoices.pi_created",
                    quotation=doc.name,
                    supplier_quotation=sq_name,
                    purchase_invoice=pi.name,
                )

    _sync_opportunity_insurance_flag(doc.get("opportunity"))
