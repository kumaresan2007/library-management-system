from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("username", "email", "name", "role", "is_verified", "is_staff", "is_active")
    search_fields = ("username", "email", "name")
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Personal", {"fields": ("name", "role", "is_verified")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "name", "role", "is_verified", "password1", "password2"),
            },
        ),
    )
