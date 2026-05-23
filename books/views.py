"""Book catalog: list, search, detail; admin CRUD."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import admin_only

from issues.models import Issue
from reservations.models import Reservation

from .forms import BookForm
from .models import Book


def book_list(request):
    """Paginated book list with optional category filter."""
    qs = Book.objects.all().order_by("title")
    category = request.GET.get("category", "").strip()
    if category:
        qs = qs.filter(category__iexact=category)
    categories = (
        Book.objects.values_list("category", flat=True).distinct().order_by("category")
    )
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))

    # For books with 0 available copies, show the earliest due date from active issues.
    # (If a due date is missing, we can't predict an availability date.)
    book_ids = [b.id for b in page.object_list if b.available_copies == 0]
    next_available_by_book_id = {}
    if book_ids:
        rows = (
            Issue.objects.filter(
                book_id__in=book_ids,
                status=Issue.STATUS_ACTIVE,
                due_date__isnull=False,
            )
            .values("book_id")
            .annotate(next_due=Min("due_date"))
        )
        next_available_by_book_id = {r["book_id"]: r["next_due"] for r in rows}

    for b in page.object_list:
        b.next_available_date = next_available_by_book_id.get(b.id)
        b.pending_reservations_count = 0
        if b.available_copies > 0:
            b.availability_label = f"Available ({b.available_copies} copies)"
        else:
            b.availability_label = "Not Available"

    reservations_by_book = {}
    if page.object_list:
        rows = (
            Reservation.objects.filter(
                book_id__in=[b.id for b in page.object_list],
                status=Reservation.STATUS_PENDING,
            )
            .values("book_id")
            .annotate(n=Count("id"))
        )
        reservations_by_book = {r["book_id"]: r["n"] for r in rows}

    for b in page.object_list:
        b.pending_reservations_count = reservations_by_book.get(b.id, 0)

    return render(
        request,
        "books/book_list.html",
        {
            "page_obj": page,
            "categories": categories,
            "current_category": category,
            "next_available_by_book_id": next_available_by_book_id,
        },
    )


def book_search(request):
    """Search by title, author, ISBN, or category."""
    q = request.GET.get("q", "").strip()
    results = Book.objects.none()
    if q:
        results = Book.objects.filter(
            Q(title__icontains=q)
            | Q(author__icontains=q)
            | Q(isbn__icontains=q)
            | Q(category__icontains=q)
        ).order_by("title")[:50]
    return render(request, "books/book_search.html", {"q": q, "results": results})


def book_detail(request, pk):
    """Single book with cover and actions (request/reserve) for logged-in students."""
    book = get_object_or_404(Book, pk=pk)
    return render(request, "books/book_detail.html", {"book": book})


@login_required
@admin_only
@require_http_methods(["GET", "POST"])
def book_add(request):
    """Admin: create a new book row."""
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Book added.")
            return redirect("books:book_list")
    else:
        form = BookForm()
    return render(request, "books/book_form.html", {"form": form, "title": "Add book"})


@login_required
@admin_only
@require_http_methods(["GET", "POST"])
def book_edit(request, pk):
    """Admin: update book metadata and copy counts."""
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, "Book updated.")
            return redirect("books:book_detail", pk=book.pk)
    else:
        form = BookForm(instance=book)
    return render(
        request,
        "books/book_form.html",
        {"form": form, "title": "Edit book", "book": book},
    )


@login_required
@admin_only
@require_http_methods(["POST"])
def book_delete(request, pk):
    """Admin: remove a book (cascades to issues if configured — be careful)."""
    book = get_object_or_404(Book, pk=pk)
    book.delete()
    messages.success(request, "Book removed.")
    return redirect("books:book_list")
