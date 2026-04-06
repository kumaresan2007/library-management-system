"""
management/commands/run_daily_tasks.py
=======================================
Run this daily via a cron job or Celery Beat:

    python manage.py run_daily_tasks

What it does:
  1. Sends due-date reminder notifications for books due in exactly 2 days.
  2. Marks overdue issues.
  3. Expires reservations whose 24-hr claim window has passed.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from library.models import BookIssue, Reservation, Notification


class Command(BaseCommand):
    help = "Send due-date reminders, mark overdue issues, expire reservations."

    def handle(self, *args, **options):
        self._send_due_reminders()
        self._mark_overdue()
        self._expire_reservations()
        self.stdout.write(self.style.SUCCESS("Daily library tasks completed."))

    # ── 1. Due-date reminders (2 days prior) ──────────────────────
    def _send_due_reminders(self):
        two_days_from_now = timezone.now().date() + timedelta(days=2)

        # Find active issues due in 2 days, reminder not yet sent
        due_soon = BookIssue.objects.filter(
            status="active",
            due_date=two_days_from_now,
            reminder_sent=False,
        ).select_related("member", "book")

        for issue in due_soon:
            msg = (
                f"Dear {issue.member.first_name}, "
                f"your copy of '{issue.book.title}' is due on "
                f"{issue.due_date}. Please return it on time."
            )

            # Save to Notification table
            Notification.objects.create(
                member=issue.member,
                book=issue.book,
                notification_type="due_reminder",
                message=msg,
            )

            # ── Swap this print() with send_mail() in production ──
            print(f"[REMINDER] {msg}")

            # Mark sent so it doesn't trigger again tomorrow
            issue.reminder_sent = True
            issue.save(update_fields=["reminder_sent"])

        self.stdout.write(f"  Due reminders sent: {due_soon.count()}")

    # ── 2. Mark overdue issues ─────────────────────────────────────
    def _mark_overdue(self):
        today = timezone.now().date()

        overdue_qs = BookIssue.objects.filter(
            status="active",
            due_date__lt=today,
        ).select_related("member", "book")

        count = 0
        for issue in overdue_qs:
            issue.status = "overdue"
            issue.save(update_fields=["status"])

            Notification.objects.create(
                member=issue.member,
                book=issue.book,
                notification_type="overdue_alert",
                message=(
                    f"Your book '{issue.book.title}' was due on "
                    f"{issue.due_date} and is now overdue. "
                    f"Please return it immediately."
                ),
            )
            count += 1

        self.stdout.write(f"  Issues marked overdue: {count}")

    # ── 3. Expire lapsed reservations ─────────────────────────────
    def _expire_reservations(self):
        now = timezone.now()

        lapsed = Reservation.objects.filter(
            status="reserved",
            claim_deadline__lt=now,
        ).select_related("member", "book")

        count = 0
        for reservation in lapsed:
            reservation.expire()   # releases copy, notifies next waiter
            count += 1

        self.stdout.write(f"  Reservations expired: {count}")