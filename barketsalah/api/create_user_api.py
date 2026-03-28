import hashlib
import hmac
import time

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address
from frappe.exceptions import PermissionError, ValidationError


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _normalize_name(first_name: str) -> str:
    return (first_name or "").strip()


def _get_required_header(name: str) -> str:
    value = (frappe.request.headers.get(name) or "").strip()
    if not value:
        frappe.throw(_("Unauthorized request"), PermissionError)
    return value


def _assert_valid_signed_request(email: str, first_name: str) -> None:
    secret = (frappe.conf.get("website_user_create_secret") or "").strip()
    if not secret:
        frappe.throw(_("Server is not configured for this endpoint."), ValidationError)

    ts = _get_required_header("X-Barketsalah-Timestamp")
    nonce = _get_required_header("X-Barketsalah-Nonce")
    signature = _get_required_header("X-Barketsalah-Signature")

    try:
        ts_int = int(ts)
    except ValueError:
        frappe.throw(_("Unauthorized request"), PermissionError)

    # 5 dakikadan eski / ileri istekleri kabul etme
    if abs(int(time.time()) - ts_int) > 300:
        frappe.throw(_("Unauthorized request"), PermissionError)

    # Replay attack koruması
    nonce_cache_key = f"create-user-nonce:{nonce}"
    if frappe.cache.get_value(nonce_cache_key):
        frappe.throw(_("Unauthorized request"), PermissionError)

    frappe.cache.set_value(nonce_cache_key, 1, expires_in_sec=300)

    payload = f"{ts}.{nonce}.{email}.{first_name}"
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        frappe.throw(_("Unauthorized request"), PermissionError)


def _create_user_from_website(email: str, first_name: str) -> dict:
    if frappe.request.method != "POST":
        frappe.throw(_("Method Not Allowed"), PermissionError)

    email = _normalize_email(email)
    first_name = _normalize_name(first_name)

    if not email:
        return {"status": "error", "message": "Email required"}

    if not validate_email_address(email):
        return {"status": "error", "message": "Invalid email"}

    if not first_name:
        first_name = email.split("@")[0]

    if len(first_name) > 140:
        first_name = first_name[:140]

    _assert_valid_signed_request(email=email, first_name=first_name)

    if frappe.db.exists("User", email):
        return {"status": "exists"}

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "enabled": 1,
            "send_welcome_email": 0,
        }
    )

    user.insert(ignore_permissions=True)

    return {"status": "created"}


# Önce rate limit uygula
create_user_from_website = rate_limit(
    limit=20,
    seconds=60,
    methods="POST",
)(_create_user_from_website)

# Sonra whitelist uygula
create_user_from_website = frappe.whitelist(allow_guest=True)(
    create_user_from_website
)


@frappe.whitelist(allow_guest=True)
def test_endpoint():
    return {"message": "ok"}