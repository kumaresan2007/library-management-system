"""Waitlist when no copies are available; FIFO by reservation_date."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Reservation(models.Model):
    STATUS_PENDING = "pending"
    STATUS_FULFILLED = "fulfilled"
    STATUS_CANCELLED = "cancelled"
    # Backward-compatible alias for older code paths.
    STATUS_WAITING = STATUS_PENDING

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_FULFILLED, "Fulfilled"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, related_name="reservations")
    reservation_date = models.DateTimeField(auto_now_add=True)
    reserved_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["reservation_date"]
        # One active waitlist row per user+book is enforced in views (IntegrityError fallback).

    def __str__(self):
        return f"{self.user.email} — {self.book.title} ({self.status})"
