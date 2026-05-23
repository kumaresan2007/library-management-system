"""Load demo catalog books (idempotent — skips existing ISBNs)."""
from django.core.management.base import BaseCommand

from books.models import Book


SAMPLE = [
    ("The Alchemist", "Paulo Coelho", "Fiction", "978-0061122415", 5, 5),
    ("Atomic Habits", "James Clear", "Self-help", "978-0735211292", 5, 5),
    ("Rich Dad Poor Dad", "Robert T. Kiyosaki", "Personal Finance", "978-1612680194", 5, 5),
    ("1984", "George Orwell", "Fiction", "978-0451524935", 5, 5),
    ("Clean Code", "Robert C. Martin", "Computer Science", "978-0132350884", 5, 5),
    ("The Pragmatic Programmer", "Andrew Hunt & David Thomas", "Computer Science", "978-0201616224", 5, 5),
    ("Deep Work", "Cal Newport", "Productivity", "978-1455586691", 5, 5),
    ("Sapiens", "Yuval Noah Harari", "History", "978-0062316110", 5, 5),
    ("Think and Grow Rich", "Napoleon Hill", "Personal Finance", "978-1585424337", 5, 5),
    ("To Kill a Mockingbird", "Harper Lee", "Fiction", "978-0061120084", 5, 5),
]


class Command(BaseCommand):
    help = "Insert sample books if their ISBN is not already present."

    def handle(self, *args, **options):
        n = 0
        for title, author, cat, isbn, total, avail in SAMPLE:
            if Book.objects.filter(isbn=isbn).exists():
                continue
            Book.objects.create(
                title=title,
                author=author,
                category=cat,
                isbn=isbn,
                total_copies=total,
                available_copies=avail,
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Added {n} demo book(s)."))
