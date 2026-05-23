"""Role-based access helpers for views."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def admin_only(view_func):
    """Allow only users with admin privileges."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not (getattr(u, "is_admin", False) or getattr(u, "role", None) == "admin"):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_required(view_func):
    """Alias for admin_only (matches project spec wording)."""

    return admin_only(view_func)


def student_only(view_func):
    """Allow only students (not admin-only pages)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if getattr(u, "role", None) != "student":
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped
