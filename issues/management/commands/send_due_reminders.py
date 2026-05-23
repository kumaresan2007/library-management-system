"""
Send reminders for books due in 2 days (email).
Schedule daily via Windows Task Scheduler or cron, e.g.:
  python manage.py send_due_reminders
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from issues.models import Issue
from library_system.notifications import notify_user


class Command(BaseCommand):
    help = "Notify borrowers when a loan is due in exactly 2 days (once per issue)."

    def handle(self, *args, **options):
        today = timezone.localdate()
        target_due = today + timedelta(days=2)
        qs = Issue.objects.filter(
            status=Issue.STATUS_ACTIVE,
            due_date=target_due,
            reminder_due_sent=False,
        ).select_related("user", "book")

        sent = 0
        for issue in qs:
            try:
                notify_user(
                    issue.user,
                    f'Reminder: "{issue.book.title}" due on {issue.due_date}',
                    (
                        f"Dear {issue.user.name},\n\n"
                        f'This is a reminder that your borrowed book "{issue.book.title}" '
                        f"is due on {issue.due_date}. Please return or renew it on time "
                        f"to avoid fines (₹{settings.FINE_PER_DAY}/day after the due date).\n\n"
                        f"Thank you,\nLibrary"
                    ),
                )
            except Exception as exc:
                self.stderr.write(f"Failed for issue {issue.pk}: {exc}")
                continue
            issue.reminder_due_sent = True
            issue.save(update_fields=["reminder_due_sent"])
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} due-soon reminder(s)."))
