"""
Custom user model for the app.

Refactor note:
- Phone number + SMS OTP are fully removed.
- Authentication flows use email-based OTP in views.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Application user — extends AbstractUser.

    We keep the built-in `username` field for display/uniqueness, and use `email`
    as the identifier for OTP authentication in our views.
    """

    email = models.EmailField("email address", unique=True)
    name = models.CharField(max_length=150, blank=True)
    role = models.CharField(
        max_length=10,
        choices=[("admin", "Admin"), ("student", "Student")],
        default="student",
    )
    is_admin = models.BooleanField(default=False)

    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def is_library_admin(self):
        return self.role == "admin" or getattr(self, "is_admin", False)
