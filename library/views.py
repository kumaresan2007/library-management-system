from django.shortcuts import render

"""
views.py — Digital Library Management System (DLMS)
=====================================================
Covers all core backend operations your friend's frontend will call:

  POST /members/add/          → AddMemberView
  POST /books/add/            → AddBookView
  POST /books/issue/          → IssueBookView
  POST /books/return/<id>/    → ReturnBookView
  POST /books/reserve/        → ReserveBookView
  GET  /books/availability/   → BookAvailabilityView
  GET  /members/<id>/history/ → MemberHistoryView

All views are class-based and return JSON so they work cleanly as a
REST backend (pair with Django REST Framework for production).
"""

import json
from django.http  import JsonResponse
from django.views import View
from django.utils import timezone
from django.db    import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators      import method_decorator

from .models import Member, Book, BookIssue, Reservation, Notification



def index(request):
    return JsonResponse({"message": "Welcome to the Digital Library API"})
# ── Helper: parse JSON body ──────────────────────────────────────────────────
def parse_body(request):
    """Safely decode the JSON request body; return {} on failure."""
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


# ── Decorator: skip CSRF for API endpoints (use token auth in production) ───
csrf_exempt_cbv = method_decorator(csrf_exempt, name="dispatch")


# ─────────────────────────────────────────────
# 1.  ADD MEMBER
#     POST /members/add/
# ─────────────────────────────────────────────
@csrf_exempt_cbv
class AddMemberView(View):
    """
    Register a new library member.

    Expected JSON body:
    {
      "username":        "priya_s",
      "password":        "SecurePass@123",
      "first_name":      "Priya",
      "last_name":       "Subramanian",
      "email":           "priya@example.com",
      "phone_number":    "9876543210",
      "membership_id":   "LIB-00101",
      "membership_expiry": "2026-12-31"   ← optional; omit for lifetime
    }
    """

    def post(self, request):
        data = parse_body(request)

        # ── Validate required fields ─────────────────────────────
        required = ["username", "password", "first_name",
                    "last_name", "email", "membership_id"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return JsonResponse(
                {"error": f"Missing required fields: {', '.join(missing)}"},
                status=400
            )

        # ── Check for duplicates ──────────────────────────────────
        if Member.objects.filter(username=data["username"]).exists():
            return JsonResponse({"error": "Username already taken."}, status=409)
        if Member.objects.filter(membership_id=data["membership_id"]).exists():
            return JsonResponse({"error": "Membership ID already in use."}, status=409)

        # ── Create member (use create_user so password is hashed) ─
        member = Member.objects.create_user(
            username      = data["username"],
            password      = data["password"],
            first_name    = data["first_name"],
            last_name     = data["last_name"],
            email         = data["email"],
            phone_number  = data.get("phone_number", ""),
            membership_id = data["membership_id"],
            membership_expiry = data.get("membership_expiry") or None,
        )

        return JsonResponse({
            "message":       "Member registered successfully.",
            "member_id":     member.id,
            "membership_id": member.membership_id,
        }, status=201)


# ─────────────────────────────────────────────
# 2.  ADD BOOK
#     POST /books/add/
# ─────────────────────────────────────────────
@csrf_exempt_cbv
class AddBookView(View):
    """
    Add a new book (or increase stock of an existing ISBN).

    Expected JSON body:
    {
      "title":          "The Pragmatic Programmer",
      "author":         "David Thomas",
      "isbn":           "9780135957059",
      "publisher":      "Addison-Wesley",   ← optional
      "genre":          "Technology",       ← optional
      "total_copies":   3                   ← defaults to 1
    }
    """

    def post(self, request):
        data = parse_body(request)

        required = ["title", "author", "isbn"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return JsonResponse(
                {"error": f"Missing required fields: {', '.join(missing)}"},
                status=400
            )

        total_copies = int(data.get("total_copies", 1))

        # ── If ISBN already exists, just increase stock ───────────
        book, created = Book.objects.get_or_create(
            isbn=data["isbn"],
            defaults={
                "title":           data["title"],
                "author":          data["author"],
                "publisher":       data.get("publisher", ""),
                "genre":           data.get("genre", ""),
                "total_copies":    total_copies,
                "available_copies": total_copies,
                "is_available":    total_copies > 0,
            }
        )

        if not created:
            # Book exists — add more copies
            book.total_copies     += total_copies
            book.available_copies += total_copies
            book.update_availability()   # syncs is_available flag
            return JsonResponse({
                "message":          f"Added {total_copies} more copies.",
                "book_id":          book.id,
                "total_copies":     book.total_copies,
                "available_copies": book.available_copies,
            }, status=200)

        return JsonResponse({
            "message":  "Book added to catalogue.",
            "book_id":  book.id,
            "title":    book.title,
            "is_available": book.is_available,
        }, status=201)


# ─────────────────────────────────────────────
# 3.  ISSUE BOOK  (borrow)
#     POST /books/issue/
# ─────────────────────────────────────────────
@csrf_exempt_cbv
class IssueBookView(View):
    """
    Issue a book to a member.

    Expected JSON body:
    { "member_id": 5, "book_id": 12 }

    • Checks member eligibility and book availability.
    • Uses a DB transaction so availability counters stay consistent.
    • If the member had an active reservation for this book, it is
      marked as fulfilled.
    """

    def post(self, request):
        data = parse_body(request)

        try:
            member = Member.objects.get(pk=data["member_id"])
            book   = Book.objects.get(pk=data["book_id"])
        except (Member.DoesNotExist, Book.DoesNotExist, KeyError):
            return JsonResponse({"error": "Invalid member_id or book_id."}, status=404)

        # ── Eligibility checks ────────────────────────────────────
        if not member.can_borrow():
            return JsonResponse(
                {"error": "Member cannot borrow: membership expired or borrow limit reached."},
                status=403
            )
        if not book.is_available:
            return JsonResponse(
                {"error": "No copies available. You can reserve this book."},
                status=409
            )

        # ── Atomic transaction: create issue + update counters ────
        with transaction.atomic():
            issue = BookIssue.objects.create(member=member, book=book)

            # Decrement available copies
            book.available_copies -= 1
            book.update_availability()

            # Increment member's borrow counter
            member.books_borrowed_count += 1
            member.save(update_fields=["books_borrowed_count"])

            # Fulfil any active reservation for this member+book
            Reservation.objects.filter(
                member=member, book=book, status="reserved"
            ).update(status="fulfilled")

        return JsonResponse({
            "message":   "Book issued successfully.",
            "issue_id":  issue.id,
            "due_date":  str(issue.due_date),
        }, status=201)


# ─────────────────────────────────────────────
# 4.  RETURN BOOK
#     POST /books/return/<issue_id>/
# ─────────────────────────────────────────────
@csrf_exempt_cbv
class ReturnBookView(View):
    """
    Process a book return.
    BookIssue.mark_returned() handles:
      • Stamping returned_on / status
      • Incrementing available_copies
      • Promoting the first reservation (if any) → 24-hr window opens
      • Decrementing member borrow counter
    """

    def post(self, request, issue_id):
        try:
            issue = BookIssue.objects.get(pk=issue_id, status="active")
        except BookIssue.DoesNotExist:
            return JsonResponse(
                {"error": "Active issue record not found."}, status=404
            )

        issue.mark_returned()   # all cascade logic lives in the model

        return JsonResponse({
            "message":      "Book returned successfully.",
            "book_title":   issue.book.title,
            "returned_on":  str(issue.returned_on),
        })


# ─────────────────────────────────────────────
# 5.  RESERVE BOOK
#     POST /books/reserve/
# ─────────────────────────────────────────────
@csrf_exempt_cbv
class ReserveBookView(View):
    """
    Place a reservation for a currently borrowed book.

    Expected JSON body:
    { "member_id": 5, "book_id": 12 }

    • Prevents duplicate reservations from the same member.
    • Returns the member's queue position.
    """

    def post(self, request):
        data = parse_body(request)

        try:
            member = Member.objects.get(pk=data["member_id"])
            book   = Book.objects.get(pk=data["book_id"])
        except (Member.DoesNotExist, Book.DoesNotExist, KeyError):
            return JsonResponse({"error": "Invalid member_id or book_id."}, status=404)

        # ── Don't reserve if copies are already available ─────────
        if book.is_available:
            return JsonResponse(
                {"error": "Book is available right now — no reservation needed!"},
                status=400
            )

        # ── Prevent duplicate active reservations ─────────────────
        already = Reservation.objects.filter(
            member=member, book=book,
            status__in=["waiting", "reserved"]
        ).exists()
        if already:
            return JsonResponse(
                {"error": "You already have an active reservation for this book."},
                status=409
            )

        reservation = Reservation.objects.create(member=member, book=book)

        # Calculate queue position (how many are ahead of this member)
        queue_position = Reservation.objects.filter(
            book=book, status="waiting",
            requested_on__lt=reservation.requested_on
        ).count() + 1

        return JsonResponse({
            "message":        "Reservation placed successfully.",
            "reservation_id": reservation.id,
            "queue_position": queue_position,
        }, status=201)


# ─────────────────────────────────────────────
# 6.  BOOK AVAILABILITY  (real-time)
#     GET /books/availability/?search=django
# ─────────────────────────────────────────────
class BookAvailabilityView(View):
    """
    Real-time availability listing.
    Optionally filter by ?search=<title|author|isbn>
    Returns: title, author, is_available, available_copies,
             next_due_date (if all copies borrowed).
    """

    def get(self, request):
        search = request.GET.get("search", "").strip()
        books  = Book.objects.all()

        if search:
            books = books.filter(
                title__icontains=search
            ) | books.filter(
                author__icontains=search
            ) | books.filter(
                isbn__icontains=search
            )

        result = []
        for book in books.distinct():
            entry = {
                "book_id":          book.id,
                "title":            book.title,
                "author":           book.author,
                "isbn":             book.isbn,
                "is_available":     book.is_available,
                "available_copies": book.available_copies,
                "total_copies":     book.total_copies,
                "waitlist_count":   book.reservations.filter(
                                        status="waiting").count(),
            }
            # Append soonest due_date so patrons know when to expect return
            if not book.is_available:
                soonest = (
                    BookIssue.objects
                    .filter(book=book, status="active")
                    .order_by("due_date")
                    .values_list("due_date", flat=True)
                    .first()
                )
                entry["next_due_date"] = str(soonest) if soonest else None

            result.append(entry)

        return JsonResponse({"books": result})


# ─────────────────────────────────────────────
# 7.  MEMBER BORROW HISTORY
#     GET /members/<member_id>/history/
# ─────────────────────────────────────────────
class MemberHistoryView(View):
    """
    Return a member's full borrow history and active reservations.
    Useful for the member dashboard.
    """

    def get(self, request, member_id):
        try:
            member = Member.objects.get(pk=member_id)
        except Member.DoesNotExist:
            return JsonResponse({"error": "Member not found."}, status=404)

        issues = BookIssue.objects.filter(member=member).select_related("book")
        reservations = Reservation.objects.filter(
            member=member
        ).select_related("book")

        history = [{
            "issue_id":    i.id,
            "book":        i.book.title,
            "issued_on":   str(i.issued_on.date()),
            "due_date":    str(i.due_date),
            "returned_on": str(i.returned_on.date()) if i.returned_on else None,
            "status":      i.status,
            "is_overdue":  i.is_overdue(),
        } for i in issues]

        waitlist = [{
            "reservation_id": r.id,
            "book":           r.book.title,
            "requested_on":   str(r.requested_on.date()),
            "status":         r.status,
            "claim_deadline": str(r.claim_deadline) if r.claim_deadline else None,
        } for r in reservations]

        return JsonResponse({
            "member":       str(member),
            "borrow_history": history,
            "reservations":   waitlist,
        })
