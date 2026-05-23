"""
Book issues: request → approve → active loan; return updates inventory and fines.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Issue(models.Model):
    """Tracks a book request/issue from pending through return."""

    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_RETURNED = "returned"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending approval"),
        (STATUS_ACTIVE, "Issued"),
        (STATUS_RETURNED, "Returned"),
        (STATUS_REJECTED, "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="book_issues",
    )
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, related_name="issues")
    issue_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    # Avoid sending the "due in 2 days" email more than once per issue
    reminder_due_sent = models.BooleanField(default=False)
    # First overdue alert (email + SMS) sent once per active loan
    overdue_notice_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.user.email} — {self.book.title} ({self.status})"

    @property
    def is_overdue(self):
        if self.status != self.STATUS_ACTIVE or not self.due_date:
            return False
        today = timezone.localdate()
        return today > self.due_date

    def computed_overdue_fine_amount(self):
        """₹5 per day after due until return (or today if still out)."""
        if self.status != self.STATUS_ACTIVE or not self.due_date:
            return 0
        end = timezone.localdate()
        if self.return_date:
            end = self.return_date
        if end <= self.due_date:
            return 0
        days = (end - self.due_date).days
        return days * settings.FINE_PER_DAY


class Fine(models.Model):
    """Recorded fine linked to an issue (typically after return)."""

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fines",
    )
    issue = models.OneToOneField(Issue, on_delete=models.CASCADE, related_name="fine_record")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Fine ₹{self.amount} — {self.user.email}"
