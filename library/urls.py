"""
library/urls.py
================
URL patterns for all backend API endpoints.
Connect this to the main dlms_project/urls.py (see bottom of this file).
"""

from django.urls import path
from .views import (
    AddMemberView,
    AddBookView,
    IssueBookView,
    ReturnBookView,
    ReserveBookView,
    BookAvailabilityView,
    MemberHistoryView,
)

urlpatterns = [

    # ── Member ───────────────────────────────────────────────────
    # POST → register a new member
    path("members/add/", AddMemberView.as_view(), name="add-member"),

    # GET  → full borrow history + reservations for one member
    path("members/<int:member_id>/history/", MemberHistoryView.as_view(), name="member-history"),

    # ── Book Catalogue ───────────────────────────────────────────
    # POST → add a new book (or increase stock of existing ISBN)
    path("books/add/", AddBookView.as_view(), name="add-book"),

    # GET  → real-time availability list; supports ?search=<title/author/isbn>
    path("books/availability/", BookAvailabilityView.as_view(), name="book-availability"),

    # ── Borrow / Return ──────────────────────────────────────────
    # POST → issue (borrow) a book to a member
    path("books/issue/", IssueBookView.as_view(), name="issue-book"),

    # POST → return a borrowed book (triggers reservation cascade)
    path("books/return/<int:issue_id>/", ReturnBookView.as_view(), name="return-book"),

    # ── Reservation (Waitlist) ───────────────────────────────────
    # POST → place a reservation for a currently borrowed book
    path("books/reserve/", ReserveBookView.as_view(), name="reserve-book"),
]


# ──────────────────────────────────────────────────────────────────
# IMPORTANT: Also update  dlms_project/urls.py  to include these:
#
#   from django.urls import path, include
#
#   urlpatterns = [
#       path("admin/", admin.site.urls),
#       path("api/",   include("library.urls")),  # all API routes under /api/
#   ]
#
# After this, your full URLs will be:
#   POST  /api/members/add/
#   GET   /api/members/<id>/history/
#   POST  /api/books/add/
#   GET   /api/books/availability/
#   POST  /api/books/issue/
#   POST  /api/books/return/<id>/
#   POST  /api/books/reserve/
# ──────────────────────────────────────────────────────────────────