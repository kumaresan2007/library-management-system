"""Book catalog: copies, category, optional cover image."""
from django.db import models


class Book(models.Model):
    """A library book with inventory (total vs available copies)."""

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    category = models.CharField(max_length=100, db_index=True)
    isbn = models.CharField(max_length=20, unique=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    cover_image = models.ImageField(upload_to="book_covers/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.isbn})"

    def save(self, *args, **kwargs):
        # Keep available within [0, total_copies]
        if self.available_copies > self.total_copies:
            self.available_copies = self.total_copies
        super().save(*args, **kwargs)
