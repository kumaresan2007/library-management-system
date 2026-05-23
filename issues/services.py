"""
Business logic: approve issues, return books, fines, reservation queue notifications.
"""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from library_system.notifications import notify_user

from .models import Fine, Issue
from reservations.models import Reservation


@transaction.atomic
def approve_issue(issue, loan_days=None):
    """Admin approves a pending request: set dates, decrement available copies."""
    if issue.status != Issue.STATUS_PENDING:
        raise ValueError("Only pending issues can be approved")

    loan_days = loan_days or settings.DEFAULT_LOAN_DAYS
    book = issue.book
    if book.available_copies < 1:
        raise ValueError("No copies available")

    today = timezone.localdate()
    issue.issue_date = today
    issue.due_date = today + timedelta(days=loan_days)
    issue.status = Issue.STATUS_ACTIVE
    issue.save()

    book.available_copies -= 1
    book.save(update_fields=["available_copies"])
    site = getattr(settings, "SITE_NAME", "Digital Library")
    notify_user(
        issue.user,
        "Book issued",
        (
            f"Hello {issue.user.name},\n\n"
            f'Your book "{book.title}" has been issued.\n'
            f"Due date: {issue.due_date}\n\n"
            f"— {site}"
        ),
    )
    return issue


@transaction.atomic
def reject_issue(issue):
    """Reject a pending request without changing inventory."""
    if issue.status != Issue.STATUS_PENDING:
        raise ValueError("Only pending issues can be rejected")
    issue.status = Issue.STATUS_REJECTED
    issue.save(update_fields=["status"])
    return issue


@transaction.atomic
def return_book(issue):
    """Mark returned, restore copy, create fine if overdue, notify next reservation."""
    if issue.status != Issue.STATUS_ACTIVE:
        raise ValueError("Only active loans can be returned")

    today = timezone.localdate()
    issue.return_date = today
    issue.status = Issue.STATUS_RETURNED
    issue.save()

    book = issue.book
    book.available_copies += 1
    if book.available_copies > book.total_copies:
        book.available_copies = book.total_copies
    book.save(update_fields=["available_copies"])

    fine_record = None
    if issue.due_date and today > issue.due_date:
        days = (today - issue.due_date).days
        amount = Decimal(days * settings.FINE_PER_DAY)
        if amount > 0:
            fine_record, _ = Fine.objects.update_or_create(
                issue=issue,
                defaults={
                    "user": issue.user,
                    "amount": amount,
                    "status": Fine.STATUS_PENDING,
                },
            )

    site = getattr(settings, "SITE_NAME", "Digital Library")
    notify_user(
        issue.user,
        "Book returned",
        (
            f"Hello {issue.user.name},\n\n"
            f'Thank you for returning "{book.title}" on {today}.\n\n'
            f"— {site}"
        ),
    )
    if fine_record is not None:
        days = (today - issue.due_date).days
        notify_user(
            issue.user,
            "Library fine generated",
            (
                f"Hello {issue.user.name},\n\n"
                f'A fine was recorded for overdue return of "{book.title}".\n'
                f"Due date: {issue.due_date}\n"
                f"Overdue days: {days}\n"
                f"Fine amount: ₹{fine_record.amount}\n\n"
                f"— {site}"
            ),
        )
    _notify_next_reservation(book)
    return issue


def _notify_next_reservation(book):
    """Email the next pending student reservation when a copy becomes available."""
    next_r = (
        Reservation.objects.filter(book=book, status=Reservation.STATUS_PENDING)
        .order_by("reservation_date")
        .select_related("user")
        .first()
    )
    if not next_r:
        return
    next_r.notified_at = timezone.now()
    next_r.status = Reservation.STATUS_FULFILLED
    next_r.save(update_fields=["notified_at", "status"])
    site = getattr(settings, "SITE_NAME", "Digital Library")
    notify_user(
        next_r.user,
        f'Book available: "{book.title}"',
        (
            f"Dear {next_r.user.name},\n\n"
            f'Your reserved book "{book.title}" is now available.\n'
            f"Please log in to the library portal and place your issue request.\n\n"
            f"— {site}"
        ),
    )
