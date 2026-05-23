"""
Notify borrowers once per loan when a book becomes overdue (email).
Includes running fine estimate. Schedule daily, e.g.:
  python manage.py notify_overdue_books
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from issues.models import Issue
from library_system.notifications import notify_user


class Command(BaseCommand):
    help = "Email users for active loans past due (one notification per issue)."

    def handle(self, *args, **options):
        today = timezone.localdate()
        site = getattr(settings, "SITE_NAME", "Digital Library")
        qs = Issue.objects.filter(
            status=Issue.STATUS_ACTIVE,
            due_date__lt=today,
            overdue_notice_sent=False,
        ).select_related("user", "book")

        sent = 0
        for issue in qs:
            days = (today - issue.due_date).days
            fine_amount = days * settings.FINE_PER_DAY
            try:
                notify_user(
                    issue.user,
                    "Book overdue",
                    (
                        f"Hello {issue.user.name},\n\n"
                        f'Your borrowed book "{issue.book.title}" is overdue.\n'
                        f"Due date: {issue.due_date}\n"
                        f"Overdue days: {days}\n"
                        f"Estimated fine so far: ₹{fine_amount}\n\n"
                        f"Please return the book as soon as possible.\n\n"
                        f"— {site}"
                    ),
                )
            except Exception as exc:
                self.stderr.write(f"Failed for issue {issue.pk}: {exc}")
                continue
            issue.overdue_notice_sent = True
            issue.save(update_fields=["overdue_notice_sent"])
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} overdue notice(s)."))
