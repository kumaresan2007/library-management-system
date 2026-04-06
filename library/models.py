from django.db import models

"""
models.py — Digital Library Management System (DLMS)
=====================================================
Covers:
  • Member         — library user accounts
  • Book           — catalogue with real-time availability flag
  • BookIssue      — active borrow record (tracks due dates)
  • Reservation    — waitlist when a book is already borrowed
  • Notification   — in-app / email alert log

Features baked in:
  ✔ Real-time availability  (Book.is_available)
  ✔ Due-date reminders      (BookIssue.reminder_sent flag + management command hook)
  ✔ Reservation / waitlist  (Reservation with FIFO ordering)
  ✔ 24-hr claim window      (Reservation.claim_deadline auto-set on book return)
  ✔ Notification log        (Notification model — plugs into email/SMS/push)
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


# ─────────────────────────────────────────────
# 1.  MEMBER  (extends Django's built-in User)
# ─────────────────────────────────────────────
class Member(AbstractUser):
    """
    Represents a library member.
    Extends AbstractUser so we get login, password hashing,
    and admin integration for free.
    """
    # Fix for reverse accessor clash with auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='library_members',   # ← this fixes the clash
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='library_members',   # ← this fixes the clash
        blank=True
    )
    
    # Extra profile fields
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        help_text="Used for SMS reminders."
    )
    address = models.TextField(blank=True)
    membership_id = models.CharField(
        max_length=20,
        unique=True,
        help_text="Human-readable library card number, e.g. LIB-00042."
    )
    membership_expiry = models.DateField(
        null=True, blank=True,
        help_text="Leave blank for non-expiring memberships."
    )

    # Track how many books the member currently holds
    # (denormalised for quick UI display; updated on issue/return)
    books_borrowed_count = models.PositiveSmallIntegerField(default=0)

    MAX_BORROW_LIMIT = 5          # class-level constant

    def is_membership_active(self):
        """Return True if membership has no expiry or hasn't expired yet."""
        if self.membership_expiry is None:
            return True
        return self.membership_expiry >= timezone.now().date()

    def can_borrow(self):
        """Return True if member is active and under the borrow limit."""
        return self.is_membership_active() and \
               self.books_borrowed_count < self.MAX_BORROW_LIMIT

    def __str__(self):
        return f"{self.get_full_name()} ({self.membership_id})"

    class Meta:
        verbose_name = "Member"
        verbose_name_plural = "Members"


# ─────────────────────────────────────────────
# 2.  BOOK
# ─────────────────────────────────────────────
class Book(models.Model):
    """
    Represents a single physical (or digital) book in the catalogue.
    'is_available' is the single source of truth for real-time status.
    """

    title       = models.CharField(max_length=255)
    author      = models.CharField(max_length=255)
    isbn        = models.CharField(
        max_length=13, unique=True,
        help_text="13-digit ISBN without dashes."
    )
    publisher   = models.CharField(max_length=255, blank=True)
    genre       = models.CharField(max_length=100, blank=True)
    total_copies = models.PositiveIntegerField(
        default=1,
        help_text="Total physical copies owned by the library."
    )
    available_copies = models.PositiveIntegerField(
        default=1,
        help_text="Copies currently on the shelf. Auto-managed."
    )

    # ── Real-time availability flag ──────────────────────────────
    # True  → at least one copy is on the shelf
    # False → all copies are borrowed
    is_available = models.BooleanField(
        default=True,
        db_index=True,        # speeds up availability filter queries
        help_text="Auto-updated when a book is issued or returned."
    )

    added_on = models.DateTimeField(auto_now_add=True)
    cover_image = models.ImageField(
        upload_to="book_covers/", null=True, blank=True
    )
    description = models.TextField(blank=True)

    def update_availability(self):
        """
        Call this after any issue/return to keep is_available in sync.
        Saves only the two affected fields for efficiency.
        """
        self.is_available = self.available_copies > 0
        self.save(update_fields=["available_copies", "is_available"])

    def __str__(self):
        status = "✔ Available" if self.is_available else "✘ Borrowed"
        return f"{self.title} — {self.author}  [{status}]"

    class Meta:
        ordering = ["title"]


# ─────────────────────────────────────────────
# 3.  BOOK ISSUE  (active borrow record)
# ─────────────────────────────────────────────
class BookIssue(models.Model):
    """
    Created when a member borrows a book; updated when returned.
    Drives both due-date reminders and the reservation cascade.
    """

    STATUS_CHOICES = [
        ("active",   "Active"),       # currently borrowed
        ("returned", "Returned"),     # back on shelf
        ("overdue",  "Overdue"),      # past due_date, not returned
    ]

    BORROW_PERIOD_DAYS = 14           # default loan period

    member  = models.ForeignKey(
        Member, on_delete=models.PROTECT,
        related_name="issued_books"
    )
    book    = models.ForeignKey(
        Book, on_delete=models.PROTECT,
        related_name="issue_records"
    )
    issued_on  = models.DateTimeField(auto_now_add=True)
    due_date   = models.DateField(
        help_text="Calculated automatically as issued_on + 14 days."
    )
    returned_on = models.DateTimeField(null=True, blank=True)
    status      = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="active"
    )

    # ── Reminder flag ────────────────────────────────────────────
    # Set to True by the daily management command once the 2-day
    # reminder email/SMS has been dispatched.  Prevents duplicates.
    reminder_sent = models.BooleanField(
        default=False,
        help_text="True once the 2-day due-date reminder has been sent."
    )

    def save(self, *args, **kwargs):
        """Auto-calculate due_date on first save."""
        if not self.pk:                       # only on creation
            self.due_date = (
                timezone.now() + timedelta(days=self.BORROW_PERIOD_DAYS)
            ).date()
        super().save(*args, **kwargs)

    def mark_returned(self):
        """
        Call this from the 'return book' view.
        1. Stamps returned_on & sets status.
        2. Increments available_copies and refreshes is_available.
        3. Triggers reservation cascade (promote first waiter → Reserved).
        4. Decrements member's borrow counter.
        """
        # 1. Update issue record
        self.returned_on = timezone.now()
        self.status = "returned"
        self.save(update_fields=["returned_on", "status"])

        # 2. Update book availability
        self.book.available_copies += 1
        self.book.update_availability()

        # 3. Promote the earliest reservation (if any)
        next_reservation = (
            Reservation.objects
            .filter(book=self.book, status="waiting")
            .order_by("requested_on")      # FIFO
            .first()
        )
        if next_reservation:
            next_reservation.promote()     # sets claim_deadline, notifies

        # 4. Update member counter
        self.member.books_borrowed_count = max(
            0, self.member.books_borrowed_count - 1
        )
        self.member.save(update_fields=["books_borrowed_count"])

    def is_overdue(self):
        return (
            self.status == "active"
            and timezone.now().date() > self.due_date
        )

    def days_until_due(self):
        return (self.due_date - timezone.now().date()).days

    def __str__(self):
        return (
            f"{self.member.membership_id} → "
            f"'{self.book.title}' | due {self.due_date} [{self.status}]"
        )

    class Meta:
        ordering = ["-issued_on"]


# ─────────────────────────────────────────────
# 4.  RESERVATION  (waitlist)
# ─────────────────────────────────────────────
class Reservation(models.Model):
    """
    Created when a member requests a book that is currently borrowed.

    Lifecycle:
      waiting   → book is still borrowed by someone else
      reserved  → book was returned; this member has 24 hrs to collect
      fulfilled → member collected the book (a new BookIssue was created)
      expired   → 24-hr window lapsed without collection; book goes back
      cancelled → member withdrew their reservation
    """

    STATUS_CHOICES = [
        ("waiting",   "Waiting"),
        ("reserved",  "Reserved"),    # 24-hr claim window open
        ("fulfilled", "Fulfilled"),
        ("expired",   "Expired"),
        ("cancelled", "Cancelled"),
    ]

    CLAIM_WINDOW_HOURS = 24

    member       = models.ForeignKey(
        Member, on_delete=models.CASCADE,
        related_name="reservations"
    )
    book         = models.ForeignKey(
        Book, on_delete=models.CASCADE,
        related_name="reservations"
    )
    requested_on = models.DateTimeField(auto_now_add=True)
    status       = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="waiting"
    )

    # Set when the book becomes available for this reserver
    claim_deadline = models.DateTimeField(
        null=True, blank=True,
        help_text="24-hr window expiry. Set automatically on promote()."
    )

    def promote(self):
        """
        Called by BookIssue.mark_returned() when this reservation
        reaches the front of the queue.
        Sets status → 'reserved', stamps claim_deadline,
        decrements available_copies (holds the copy), and fires a
        Notification.
        """
        self.status = "reserved"
        self.claim_deadline = timezone.now() + timedelta(
            hours=self.CLAIM_WINDOW_HOURS
        )
        self.save(update_fields=["status", "claim_deadline"])

        # Hold the copy so no one else can take it
        self.book.available_copies = max(
            0, self.book.available_copies - 1
        )
        self.book.update_availability()

        # Fire a notification
        Notification.objects.create(
            member=self.member,
            book=self.book,
            notification_type="reservation_ready",
            message=(
                f"Great news! '{self.book.title}' is now available for you. "
                f"Please collect it before "
                f"{self.claim_deadline.strftime('%d %b %Y %H:%M')}."
            ),
        )

    def expire(self):
        """
        Called by the daily management command when claim_deadline has
        passed without the member collecting the book.
        Returns the held copy to the shelf and checks for the next
        waiter in the queue.
        """
        self.status = "expired"
        self.save(update_fields=["status"])

        # Release the held copy back
        self.book.available_copies += 1
        self.book.update_availability()

        # Notify next waiter (if any)
        next_reservation = (
            Reservation.objects
            .filter(book=self.book, status="waiting")
            .order_by("requested_on")
            .first()
        )
        if next_reservation:
            next_reservation.promote()

        # Notify the expired member
        Notification.objects.create(
            member=self.member,
            book=self.book,
            notification_type="reservation_expired",
            message=(
                f"Your reservation for '{self.book.title}' has expired "
                f"as it was not collected within 24 hours."
            ),
        )

    def __str__(self):
        return (
            f"Reservation: {self.member} → '{self.book.title}' "
            f"[{self.status}]"
        )

    class Meta:
        # Prevent a member from reserving the same book twice (while active)
        unique_together = [("member", "book", "status")]
        ordering = ["requested_on"]


# ─────────────────────────────────────────────
# 5.  NOTIFICATION  (alert log)
# ─────────────────────────────────────────────
class Notification(models.Model):
    """
    Stores every alert sent (or queued to send) to a member.
    Decouple delivery (email/SMS/push) from model logic — a Celery
    task or Django signal reads unsent rows and dispatches them.
    """

    TYPE_CHOICES = [
        ("due_reminder",        "Due-date reminder (2 days prior)"),
        ("overdue_alert",       "Overdue alert"),
        ("reservation_ready",   "Reservation ready (book returned)"),
        ("reservation_expired", "Reservation expired (24 hr lapsed)"),
        ("general",             "General"),
    ]

    member            = models.ForeignKey(
        Member, on_delete=models.CASCADE,
        related_name="notifications"
    )
    book              = models.ForeignKey(
        Book, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=30, choices=TYPE_CHOICES, default="general"
    )
    message   = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent    = models.BooleanField(
        default=False,
        help_text="Flipped to True once the email/SMS has been dispatched."
    )
    is_read    = models.BooleanField(
        default=False,
        help_text="Flipped to True when the member reads it in the UI."
    )

    def __str__(self):
        return f"[{self.notification_type}] → {self.member} | {self.created_at:%d %b %Y}"

    class Meta:
        ordering = ["-created_at"]
