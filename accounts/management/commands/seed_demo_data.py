from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from books.models import Book


STUDENTS = [
    ("STU1001", "Arjun Kumar", "arjun@example.com"),
    ("STU1002", "Priya S", "priya@example.com"),
    ("STU1003", "Rahul M", "rahul@example.com"),
    ("STU1004", "Divya R", "divya@example.com"),
    ("STU1005", "Karthik V", "karthik@example.com"),
]

BOOKS = [
    ("Clean Code", "Robert C Martin", "Computer Science", "BK1001", 5),
    ("Python Crash Course", "Eric Matthes", "Programming", "BK1002", 3),
    ("Django for Beginners", "William S Vincent", "Web Development", "BK1003", 4),
    ("Data Structures in Python", "Narasimha Karumanchi", "Computer Science", "BK1004", 2),
    ("Artificial Intelligence Basics", "Tom Taulli", "Artificial Intelligence", "BK1005", 3),
    ("Operating Systems Concepts", "Abraham Silberschatz", "Computer Science", "BK1006", 2),
    ("Database System Design", "Carlos Coronel", "Database", "BK1007", 4),
    ("Machine Learning Basics", "Peter Flach", "Machine Learning", "BK1008", 3),
    ("Networking Essentials", "Jeff T. Parker", "Networking", "BK1009", 2),
    ("Web Development with Django", "A N Mehul", "Web Development", "BK1010", 5),
]


class Command(BaseCommand):
    help = "Seed demo students and books in an idempotent way."

    def handle(self, *args, **options):
        User = get_user_model()

        students_created = 0
        students_updated = 0
        for student_id, name, email in STUDENTS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": student_id,
                    "name": name,
                    "role": "student",
                    "is_verified": True,
                    "is_active": True,
                },
            )
            changed = False
            if user.username != student_id:
                user.username = student_id
                changed = True
            if user.name != name:
                user.name = name
                changed = True
            if user.role != "student":
                user.role = "student"
                changed = True
            if not user.is_verified:
                user.is_verified = True
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if not user.check_password("student123"):
                user.set_password("student123")
                changed = True
            if changed:
                user.save()
            if created:
                students_created += 1
            elif changed:
                students_updated += 1

        books_created = 0
        books_updated = 0
        for title, author, category, isbn, copies in BOOKS:
            book, created = Book.objects.get_or_create(
                isbn=isbn,
                defaults={
                    "title": title,
                    "author": author,
                    "category": category,
                    "total_copies": copies,
                    "available_copies": copies,
                },
            )
            changed = False
            if book.title != title:
                book.title = title
                changed = True
            if book.author != author:
                book.author = author
                changed = True
            if book.category != category:
                book.category = category
                changed = True
            if book.total_copies != copies:
                delta = copies - book.total_copies
                book.total_copies = copies
                # Preserve "issued" copies while adjusting capacity.
                book.available_copies = max(0, min(copies, book.available_copies + delta))
                changed = True
            if changed:
                book.save()
            if created:
                books_created += 1
            elif changed:
                books_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data seeded. Students: +{students_created} new, {students_updated} updated | "
                f"Books: +{books_created} new, {books_updated} updated"
            )
        )

