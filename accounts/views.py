"""Home, registration, email-OTP login, logout, role-based redirects."""

import random
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import TemplateView

from .decorators import admin_only
from .forms import EmailForm, OTPForm, StudentRegistrationForm
from .utils import send_otp_email


def handler403(request, exception=None):
    """Custom 403 page for PermissionDenied."""
    return render(request, "403.html", status=403)


def home(request):
    """Public landing page with library intro and quick links."""
    # Temporary SMTP test trigger (only in DEBUG):
    # http://127.0.0.1:8000/?test_email=1&to=your_email@gmail.com
    if getattr(settings, "DEBUG", False) and request.GET.get("test_email") == "1":
        to = request.GET.get("to") or getattr(settings, "EMAIL_HOST_USER", "")
        if to:
            send_otp_email(to, "123456")
    return render(request, "accounts/home.html")


def register(request):
    """Register user, send OTP to email, and require verification."""
    if request.user.is_authenticated:
        return redirect("accounts:post_login_redirect")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if not form.is_valid():
            for errs in form.errors.values():
                for e in errs:
                    messages.error(request, e)
            return render(request, "accounts/register.html", {"form": form})

        user = form.save(commit=False)
        if get_user_model().objects.filter(email=user.email).exists():
            messages.error(request, "Email already exists")
            return redirect("accounts:register")

        otp = str(random.randint(100000, 999999))
        user.is_verified = False
        user.otp = otp
        user.otp_created_at = timezone.now()
        user.save()

        send_otp_email(user.email, otp)
        request.session["verify_user_id"] = user.id
        return redirect("accounts:verify_register")
    else:
        form = StudentRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def verify_register_otp(request):
    user_id = request.session.get("verify_user_id")
    if not user_id:
        messages.error(request, "Session expired. Please register again.")
        return redirect("accounts:register")

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.pop("verify_user_id", None)
        messages.error(request, "Session expired. Please register again.")
        return redirect("accounts:register")

    if request.method == "POST":
        form = OTPForm(request.POST)
        if not form.is_valid():
            for errs in form.errors.values():
                for e in errs:
                    messages.error(request, e)
            return redirect("accounts:verify_register")

        otp = form.cleaned_data["otp"]
        if otp == (user.otp or ""):
            if user.otp_created_at and (timezone.now() - user.otp_created_at) < timedelta(minutes=5):
                user.is_verified = True
                user.otp = None
                user.otp_created_at = None
                user.save(update_fields=["is_verified", "otp", "otp_created_at"])

                request.session.pop("verify_user_id", None)
                login(request, user)
                return redirect("accounts:post_login_redirect")
            messages.error(request, "OTP expired")
        else:
            messages.error(request, "Invalid OTP")

    form = OTPForm()
    return render(request, "accounts/verify_register.html", {"form": form, "email": user.email})


def login_request(request):
    """Email-only OTP login (no password, no phone)."""
    if request.user.is_authenticated:
        return redirect("accounts:post_login_redirect")

    if request.method == "POST":
        form = EmailForm(request.POST)
        if not form.is_valid():
            for errs in form.errors.values():
                for e in errs:
                    messages.error(request, e)
            return render(request, "accounts/login.html", {"form": form})

        email = form.cleaned_data["email"]
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Invalid email")
            return redirect("accounts:login")

        # If user registered but hasn't verified yet, resend verification OTP
        if not getattr(user, "is_verified", False):
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.otp_created_at = timezone.now()
            user.save(update_fields=["otp", "otp_created_at"])

            send_otp_email(email, otp)
            request.session["verify_user_id"] = user.id
            messages.info(request, "Account not verified. OTP sent again.")
            return redirect("accounts:verify_register")

        otp = str(random.randint(100000, 999999))
        user.otp = otp
        user.otp_created_at = timezone.now()
        user.save(update_fields=["otp", "otp_created_at"])

        send_otp_email(email, otp)
        request.session["login_user_id"] = user.id
        return redirect("accounts:verify_login")

    form = EmailForm()
    return render(request, "accounts/login.html", {"form": form})


def verify_login_otp(request):
    user_id = request.session.get("login_user_id")
    if not user_id:
        messages.error(request, "Session expired. Please login again.")
        return redirect("accounts:login")

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id, is_verified=True)
    except User.DoesNotExist:
        request.session.pop("login_user_id", None)
        messages.error(request, "Session expired. Please login again.")
        return redirect("accounts:login")

    if request.method == "POST":
        form = OTPForm(request.POST)
        if not form.is_valid():
            for errs in form.errors.values():
                for e in errs:
                    messages.error(request, e)
            return redirect("accounts:verify_login")

        otp = form.cleaned_data["otp"]
        if otp == (user.otp or ""):
            if user.otp_created_at and (timezone.now() - user.otp_created_at) < timedelta(minutes=5):
                user.otp = None
                user.otp_created_at = None
                user.save(update_fields=["otp", "otp_created_at"])

                request.session.pop("login_user_id", None)
                login(request, user)
                return redirect("accounts:post_login_redirect")
            messages.error(request, "OTP expired")
        else:
            messages.error(request, "Invalid OTP")

    form = OTPForm()
    return render(request, "accounts/verify_login.html", {"form": form, "email": user.email})


def post_login_redirect(request):
    """Route admins and students to their dashboards after login."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if getattr(request.user, "is_admin", False) or request.user.role == "admin":
        return redirect("accounts:admin_dashboard")
    return redirect("accounts:student_dashboard")


def admin_login(request):
    """
    Admin-only 2-step authentication:
    Step 1: email + password
    Step 2: OTP to email
    """
    if request.user.is_authenticated:
        return redirect("accounts:post_login_redirect")

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        User = get_user_model()
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Invalid email or password")
            return redirect("accounts:admin_login")
        # Primary auth path for email-username model
        user = authenticate(request, username=email, password=password)
        # Backward-compatible fallback for earlier username-based auth setups
        if user is None:
            user = authenticate(request, username=user_obj.username, password=password)
        if settings.DEBUG:
            print("EMAIL:", email)
            print("USER:", user)

        # Security check: allow only staff/admin accounts into this flow
        if user is None:
            messages.error(request, "Invalid email or password")
            return redirect("accounts:admin_login")
        if not user.is_staff:
            messages.error(request, "You are not an admin")
            return redirect("accounts:admin_login")
        if not user.is_active:
            messages.error(request, "This account is inactive")
            return redirect("accounts:admin_login")
        if not (getattr(user, "is_admin", False) or getattr(user, "role", None) == "admin"):
            messages.error(request, "You are not an admin")
            return redirect("accounts:admin_login")

        otp = str(random.randint(100000, 999999))
        user.otp = otp
        user.otp_created_at = timezone.now()
        user.save(update_fields=["otp", "otp_created_at"])

        send_otp_email(user.email, otp)
        request.session["admin_otp_user_id"] = user.id
        return redirect("accounts:verify_admin_otp")

    return render(request, "accounts/admin_login.html")


def verify_admin_otp(request):
    """Step 2: verify OTP for admin login."""
    user_id = request.session.get("admin_otp_user_id")
    if not user_id:
        return redirect("accounts:admin_login")

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.pop("admin_otp_user_id", None)
        return redirect("accounts:admin_login")

    # Security check: only allow staff/admin accounts through
    if not user.is_staff or not (getattr(user, "is_admin", False) or getattr(user, "role", None) == "admin"):
        request.session.pop("admin_otp_user_id", None)
        messages.error(request, "Unauthorized")
        return redirect("accounts:admin_login")

    if request.method == "POST":
        entered_otp = (request.POST.get("otp") or "").strip()

        if entered_otp and entered_otp == (user.otp or ""):
            if user.otp_created_at and (timezone.now() - user.otp_created_at) < timedelta(minutes=5):
                login(request, user)
                user.otp = None
                user.otp_created_at = None
                user.save(update_fields=["otp", "otp_created_at"])
                request.session.pop("admin_otp_user_id", None)
                return redirect("accounts:admin_dashboard")
            messages.error(request, "OTP expired")
        else:
            messages.error(request, "Invalid OTP")

    return render(request, "accounts/verify_admin_otp.html", {"email": user.email})


def logout_view(request):
    """Log out the current user and send them to login."""
    logout(request)
    return redirect("accounts:login")


class AdminDashboardView(TemplateView):
    """Admin home: KPI cards, charts, quick actions."""

    template_name = "accounts/admin_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not (
            getattr(request.user, "is_admin", False) or request.user.role == "admin"
        ):
            return redirect_to_login(request.get_full_path())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from books.models import Book
        from django.contrib.auth import get_user_model
        from issues.models import Issue
        from reservations.models import Reservation

        ctx = super().get_context_data(**kwargs)
        User = get_user_model()
        today = timezone.localdate()

        agg = Book.objects.aggregate(total_copies=Sum("total_copies"), avail=Sum("available_copies"))
        ctx["book_titles"] = Book.objects.count()
        ctx["total_copies"] = agg["total_copies"] or 0
        ctx["available_copies_sum"] = agg["avail"] or 0
        ctx["student_count"] = User.objects.filter(role="student").count()
        ctx["pending_issues"] = Issue.objects.filter(status=Issue.STATUS_PENDING).count()
        ctx["active_issues"] = Issue.objects.filter(status=Issue.STATUS_ACTIVE).count()
        ctx["overdue_issues"] = Issue.objects.filter(
            status=Issue.STATUS_ACTIVE, due_date__lt=today
        ).count()
        ctx["waiting_reservations"] = Reservation.objects.filter(
            status=Reservation.STATUS_PENDING
        ).count()
        ctx["category_counts"] = list(
            Book.objects.values("category").annotate(n=Count("id")).order_by("-n")[:12]
        )
        return ctx


@admin_only
def admin_students(request):
    """Admin: list registered students (read-only directory)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    students = User.objects.filter(role="student").order_by("name")
    return render(request, "accounts/admin_students.html", {"students": students})


@admin_only
def student_list(request):
    """Admin: student listing page at /accounts/students/."""
    User = get_user_model()
    field_names = {f.name for f in User._meta.get_fields()}
    if "is_student" in field_names:
        students = User.objects.filter(is_student=True).order_by("name", "id")
    else:
        students = User.objects.filter(role="student").order_by("name", "id")
    return render(request, "accounts/students.html", {"students": students})


@admin_only
def library_status(request):
    """Operational view for issued, overdue, and pending reservations."""
    from issues.models import Issue
    from reservations.models import Reservation

    today = timezone.localdate()
    issue_field_names = {f.name for f in Issue._meta.get_fields()}
    if "returned" in issue_field_names:
        issued_books = Issue.objects.filter(returned=False).select_related("user", "book")
    else:
        issued_books = Issue.objects.filter(status=Issue.STATUS_ACTIVE).select_related("user", "book")

    overdue_books = issued_books.filter(due_date__lt=today)
    pending_reservations = Reservation.objects.filter(
        status__iexact=Reservation.STATUS_PENDING
    ).select_related("user", "book")

    return render(
        request,
        "accounts/library_status.html",
        {
            "issued_books": issued_books,
            "overdue_books": overdue_books,
            "pending_reservations": pending_reservations,
            "today": today,
        },
    )


class StudentDashboardView(TemplateView):
    """Student home: quick stats and shortcuts."""

    template_name = "accounts/student_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != "student":
            return redirect_to_login(request.get_full_path())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from issues.models import Issue

        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        today = timezone.localdate()
        ctx["my_active"] = Issue.objects.filter(user=u, status=Issue.STATUS_ACTIVE).count()
        ctx["my_pending"] = Issue.objects.filter(user=u, status=Issue.STATUS_PENDING).count()
        ctx["my_overdue"] = Issue.objects.filter(
            user=u, status=Issue.STATUS_ACTIVE, due_date__lt=today
        ).count()
        return ctx
