"""Issue / return workflows, fines, admin queues."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.decorators import admin_only, student_only
from books.models import Book
from library_system.notifications import notify_user

from .models import Fine, Issue
from .services import approve_issue, reject_issue, return_book


@login_required
@student_only
@require_http_methods(["GET", "POST"])
def request_issue(request, book_id):
    """Student submits an issue request (pending until admin approves)."""
    book = get_object_or_404(Book, pk=book_id)
    if request.method == "POST":
        if book.available_copies < 1:
            messages.warning(
                request,
                "No copies available. Use reservation instead.",
            )
            return redirect("books:book_detail", pk=book.pk)
        exists = Issue.objects.filter(
            user=request.user,
            book=book,
            status__in=[Issue.STATUS_PENDING, Issue.STATUS_ACTIVE],
        ).exists()
        if exists:
            messages.info(request, "You already have a pending request or active loan for this book.")
            return redirect("books:book_detail", pk=book.pk)
        Issue.objects.create(user=request.user, book=book, status=Issue.STATUS_PENDING)
        messages.success(request, "Request submitted. Awaiting librarian approval.")
        return redirect("issues:my_issues")
    return render(request, "issues/request_issue.html", {"book": book})


@login_required
@student_only
def my_issues(request):
    """Student: pending, active, and returned issues."""
    issues = Issue.objects.filter(user=request.user).select_related("book")
    today = timezone.localdate()
    for row in issues:
        if (
            row.status == Issue.STATUS_ACTIVE
            and row.due_date
            and not row.reminder_due_sent
            and (row.due_date - today).days <= 2
        ):
            notify_user(
                request.user,
                "Book return reminder",
                (
                    f"Hello {request.user.name},\n\n"
                    f'Friendly reminder: "{row.book.title}" is due on {row.due_date}.\n\n'
                    "Please return/renew on time to avoid fines."
                ),
            )
            row.reminder_due_sent = True
            row.save(update_fields=["reminder_due_sent"])
    return render(request, "issues/my_issues.html", {"issues": issues})


@login_required
@student_only
def return_menu(request):
    """List active loans so the student can open the return confirmation page."""
    active = Issue.objects.filter(user=request.user, status=Issue.STATUS_ACTIVE).select_related(
        "book"
    )
    return render(request, "issues/return_menu.html", {"active": active})


@login_required
@student_only
@require_http_methods(["GET", "POST"])
def return_book_view(request, issue_id):
    """Student confirms return (updates DB + fines + waitlist)."""
    issue = get_object_or_404(Issue, pk=issue_id, user=request.user)
    if request.method == "POST":
        try:
            return_book(issue)
            messages.success(request, "Book returned. Thank you!")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("issues:my_issues")
    return render(request, "issues/return_book.html", {"issue": issue})


@login_required
@student_only
def fine_list(request):
    """Student: list fines and running overdue estimates for active loans."""
    fines = Fine.objects.filter(user=request.user).select_related("issue", "issue__book")
    active = (
        Issue.objects.filter(user=request.user, status=Issue.STATUS_ACTIVE)
        .select_related("book")
    )
    return render(
        request,
        "issues/fine_list.html",
        {"fines": fines, "active_issues": active},
    )


@login_required
@admin_only
def admin_pending(request):
    """Admin: approve or reject pending issue requests."""
    pending = Issue.objects.filter(status=Issue.STATUS_PENDING).select_related("user", "book")
    return render(request, "issues/admin_pending.html", {"pending": pending})


@login_required
@admin_only
@require_http_methods(["POST"])
def admin_approve(request, issue_id):
    issue = get_object_or_404(Issue, pk=issue_id, status=Issue.STATUS_PENDING)
    try:
        approve_issue(issue)
        messages.success(request, "Issue approved and book checked out.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect("issues:admin_pending")


@login_required
@admin_only
@require_http_methods(["POST"])
def admin_reject(request, issue_id):
    issue = get_object_or_404(Issue, pk=issue_id, status=Issue.STATUS_PENDING)
    reject_issue(issue)
    messages.info(request, "Request rejected.")
    return redirect("issues:admin_pending")


@login_required
@admin_only
def admin_issued(request):
    """Admin: currently issued books."""
    rows = Issue.objects.filter(status=Issue.STATUS_ACTIVE).select_related("user", "book")
    return render(request, "issues/admin_issued.html", {"rows": rows})


@login_required
@admin_only
def admin_overdue(request):
    """Admin: active loans past due date."""
    from django.utils import timezone

    today = timezone.localdate()
    rows = Issue.objects.filter(status=Issue.STATUS_ACTIVE, due_date__lt=today).select_related(
        "user", "book"
    )
    return render(request, "issues/admin_overdue.html", {"rows": rows, "today": today})


@login_required
def issue_book_page(request):
    """
    Landing page explaining the issue workflow (linked from nav).
    Content-only; real actions are on book detail / my issues.
    """
    return render(request, "issues/issue_book.html")
