import frappe


def mask_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return "***"

    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*" if local else "*"
    else:
        masked_local = local[:2] + "*" * (len(local) - 2)
    return f"{masked_local}@{domain}"


def log_api_event(event: str, level: str = "info", **kwargs) -> None:
    logger = frappe.logger("barketsalah_api", allow_site=True, file_count=20)
    req = getattr(frappe.local, "request", None)

    payload = {
        "event": event,
        "method": getattr(req, "method", None),
        "path": getattr(req, "path", None),
        "ip": getattr(frappe.local, "request_ip", None),
        "user": getattr(frappe.session, "user", None),
    }
    payload.update(kwargs or {})

    message = frappe.as_json(payload)

    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)
