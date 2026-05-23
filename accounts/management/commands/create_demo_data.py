import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from books.models import Book
from issues.models import Issue
from reservations.models import Reservation


class Command(BaseCommand):
    help = "Create demo students, books, issues, overdue items, and reservations."

    def handle(self, *args, **options):
        User = get_user_model()
        today = timezone.localdate()

        user_field_names = {f.name for f in User._meta.get_fields()}
        issue_field_names = {f.name for f in Issue._meta.get_fields()}

        student_emails = [f"student{i}@mail.com" for i in range(1, 21)]
        books_isbns = [f"DEMO-BOOK-{i:03d}" for i in range(1, 11)]

        students = []
        for i in range(1, 21):
            email = f"student{i}@mail.com"
            defaults = {
                "username": f"student{i}",
                "name": f"Student {i}",
                "role": "student",
                "is_verified": True,
                "is_active": True,
            }
            if "is_student" in user_field_names:
                defaults["is_student"] = True

            student, _ = User.objects.get_or_create(email=email, defaults=defaults)
            updated = False
            if student.name != defaults["name"]:
                student.name = defaults["name"]
                updated = True
            if student.role != "student":
                student.role = "student"
                updated = True
            if "is_student" in user_field_names and not getattr(student, "is_student", False):
                student.is_student = True
                updated = True
            if not student.is_verified:
                student.is_verified = True
                updated = True
            if not student.is_active:
                student.is_active = True
                updated = True
            if updated:
                student.save()
            students.append(student)

        books = []
        for i in range(1, 11):
            isbn = f"DEMO-BOOK-{i:03d}"
            defaults = {
                "title": f"Book {i}",
                "author": f"Author {i}",
                "category": "General",
                "total_copies": 5,
                "available_copies": 5,
            }
            book, _ = Book.objects.get_or_create(isbn=isbn, defaults=defaults)
            updated = False
            for key, value in defaults.items():
                if getattr(book, key) != value:
                    setattr(book, key, value)
                    updated = True
            if updated:
                book.save()
            books.append(book)

        Issue.objects.filter(user__email__in=student_emails, book__isbn__in=books_isbns).delete()
        Reservation.objects.filter(user__email__in=student_emails, book__isbn__in=books_isbns).delete()

        issue_kwargs = {}
        if "returned" in issue_field_names:
            issue_kwargs["returned"] = False
        else:
            issue_kwargs["status"] = Issue.STATUS_ACTIVE
            issue_kwargs["issue_date"] = today

        for _ in range(10):
            Issue.objects.create(
                user=random.choice(students),
                book=random.choice(books),
                due_date=today + timedelta(days=14),
                **issue_kwargs,
            )

        for _ in range(5):
            Issue.objects.create(
                user=random.choice(students),
                book=random.choice(books),
                due_date=today - timedelta(days=5),
                **issue_kwargs,
            )

        for _ in range(5):
            Reservation.objects.create(
                user=random.choice(students),
                book=random.choice(books),
                status=Reservation.STATUS_PENDING,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data created: 20 students, 10 books, 10 issued, 5 overdue, 5 pending reservations."
            )
        )
