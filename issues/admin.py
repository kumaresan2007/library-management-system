from django.contrib import admin

from .models import Fine, Issue


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "book", "status", "issue_date", "due_date", "return_date")
    list_filter = ("status",)
    raw_id_fields = ("user", "book")


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "issue", "amount", "status")
    list_filter = ("status",)
