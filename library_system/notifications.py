"""Notification helpers for email delivery (no SMS)."""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_email_safe(subject, message, recipient_list):
    """Send email and never crash business flows on transport errors."""
    if not recipient_list:
        return {"ok": False, "response": None, "error": "missing recipient"}
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        return {"ok": True, "response": {"recipients": recipient_list}, "error": None}
    except Exception as exc:
        logger.exception("Email send failed for %s", recipient_list)
        return {"ok": False, "response": None, "error": str(exc)}


def notify_user(user, subject, message):
    """Send notification email to one user."""
    if not user:
        return
    if getattr(user, "email", ""):
        send_email_safe(subject, message, [user.email])
