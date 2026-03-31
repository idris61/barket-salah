import hashlib
import hmac
import time

import frappe
from frappe import _
from frappe.exceptions import PermissionError, ValidationError
from frappe.utils import validate_email_address
from barketsalah.api.utils import log_api_event, mask_email

DEFAULT_WEBSITE_ROLE = "Custom Guest"


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _normalize_name(first_name: str) -> str:
    return (first_name or "").strip()


def _get_required_header(name: str) -> str:
    value = (frappe.request.headers.get(name) or "").strip()
    if not value:
        log_api_event("create_user.missing_header", level="warning", header=name)
        frappe.throw(_("Unauthorized request"), PermissionError)
    return value


def _get_request_data():
    data = frappe.request.get_json() or frappe.local.form_dict or {}

    email = (data.get("email") or "").strip().lower()
    first_name = (data.get("first_name") or "").strip()

    return email, first_name



def _assert_valid_signed_request(email: str, first_name: str) -> None:
    log_api_event(
        "create_user.signature_validation_started",
        email=mask_email(email),
        first_name_len=len(first_name or ""),
    )

    secret = (frappe.conf.get("website_user_create_secret") or "").strip()
    if not secret:
        log_api_event("create_user.secret_missing", level="error")
        frappe.throw(_("Server is not configured for this endpoint."), ValidationError)

    ts = _get_required_header("X-Barketsalah-Timestamp")
    nonce = _get_required_header("X-Barketsalah-Nonce")
    signature = _get_required_header("X-Barketsalah-Signature")

    try:
        ts_int = int(ts)
    except ValueError:
        log_api_event("create_user.invalid_timestamp", level="warning", ts=ts)
        frappe.throw(_("Unauthorized request"), PermissionError)

    if abs(int(time.time()) - ts_int) > 300:
        log_api_event("create_user.expired_timestamp", level="warning", ts=ts_int)
        frappe.throw(_("Unauthorized request"), PermissionError)

    nonce_cache_key = f"create-user-nonce:{nonce}"
    if frappe.cache.get_value(nonce_cache_key):
        log_api_event("create_user.replayed_nonce", level="warning", nonce=nonce)
        frappe.throw(_("Unauthorized request"), PermissionError)

    payload = f"{ts}.{nonce}.{email}.{first_name}"
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        log_api_event("create_user.signature_mismatch", level="warning", email=mask_email(email))
        frappe.throw(_("Unauthorized request"), PermissionError)

    frappe.cache.set_value(nonce_cache_key, 1, expires_in_sec=300)
    log_api_event("create_user.signature_validated", email=mask_email(email))


@frappe.whitelist(allow_guest=True)
def create_user_from_website():
    log_api_event("create_user.request_received")
    frappe.rate_limiter.rate_limit(
        limit=20,
        seconds=60,
        key="create_user_from_website",
    )

    if frappe.request.method != "POST":
        log_api_event("create_user.invalid_method", level="warning", method=frappe.request.method)
        frappe.throw(_("Method Not Allowed"), PermissionError)

    email, first_name = _get_request_data()

    if not email:
        log_api_event("create_user.email_missing", level="warning")
        return {"status": "error", "message": "Email required"}

    if not validate_email_address(email):
        log_api_event("create_user.email_invalid", level="warning", email=email)
        return {"status": "error", "message": "Invalid email"}

    if not first_name:
        first_name = email.split("@")[0]

    if len(first_name) > 140:
        first_name = first_name[:140]

    _assert_valid_signed_request(email=email, first_name=first_name)

    if frappe.db.exists("User", email):
        log_api_event("create_user.user_exists", email=mask_email(email))
        return {"status": "exists"}

    if not frappe.db.exists("Role", DEFAULT_WEBSITE_ROLE):
        log_api_event("create_user.default_role_missing", level="error", role=DEFAULT_WEBSITE_ROLE)
        frappe.throw(_("Default role is missing: {0}").format(DEFAULT_WEBSITE_ROLE), ValidationError)

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "enabled": 1,
            "send_welcome_email": 0,
            "roles": [{"role": DEFAULT_WEBSITE_ROLE}],
        }
    )

    user.insert(ignore_permissions=True)
    log_api_event(
        "create_user.user_created",
        email=mask_email(email),
        user=user.name,
        role=DEFAULT_WEBSITE_ROLE,
    )

    return {"status": "created"}


@frappe.whitelist(allow_guest=True)
def test_endpoint():
    log_api_event("create_user.test_endpoint_called")
    return {"message": "ok"}
