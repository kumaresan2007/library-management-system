"""Book reservations (waitlist) when no copies are available."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import admin_only, student_only
from books.models import Book
from library_system.notifications import notify_user

from .models import Reservation


@login_required
@student_only
@require_http_methods(["GET", "POST"])
def reserve_book(request, book_id):
    """Join waitlist for a book (FIFO)."""
    book = get_object_or_404(Book, pk=book_id)
    if request.method == "POST":
        if book.available_copies > 0:
            messages.info(request, "Book is currently available, no reservation needed.")
            return redirect("books:book_detail", pk=book.pk)
        if Reservation.objects.filter(
            user=request.user, book=book, status=Reservation.STATUS_PENDING
        ).exists():
            messages.info(request, "You already have an active reservation for this book.")
        else:
            try:
                Reservation.objects.create(
                    user=request.user,
                    book=book,
                    status=Reservation.STATUS_PENDING,
                )
                notify_user(
                    request.user,
                    "Reservation confirmed",
                    (
                        f"Hello {request.user.name},\n\n"
                        f'Your reservation for "{book.title}" is confirmed.\n'
                        "We will notify you when a copy is available."
                    ),
                )
                messages.success(
                    request,
                    "You are on the waitlist. We will email you when a copy is free.",
                )
            except IntegrityError:
                messages.info(request, "You already have an active reservation for this book.")
        return redirect("reservations:my_reservations")
    return render(request, "reservations/reserve_book.html", {"book": book})


@login_required
@student_only
def my_reservations(request):
    """Student reservation list."""
    rows = Reservation.objects.filter(user=request.user).select_related("book")
    return render(request, "reservations/my_reservations.html", {"rows": rows})


@login_required
@student_only
@require_http_methods(["POST"])
def cancel_reservation(request, pk):
    """Student cancels a waiting reservation."""
    r = get_object_or_404(Reservation, pk=pk, user=request.user, status=Reservation.STATUS_PENDING)
    r.status = Reservation.STATUS_CANCELLED
    r.save(update_fields=["status"])
    messages.info(request, "Reservation cancelled.")
    return redirect("reservations:my_reservations")


@login_required
@admin_only
def admin_reservations(request):
    """Admin view of all reservations (manage waitlist)."""
    rows = Reservation.objects.select_related("user", "book").order_by("-reservation_date")
    return render(request, "reservations/admin_reservations.html", {"rows": rows})
