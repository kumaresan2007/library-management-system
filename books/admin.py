from django.contrib import admin

from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "category", "isbn", "total_copies", "available_copies")
    list_filter = ("category",)
    search_fields = ("title", "author", "isbn")
