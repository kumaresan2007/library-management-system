"""Admin book create/edit forms."""
from django import forms

from .models import Book


class BookForm(forms.ModelForm):
    """Form for adding or updating books (used by admin dashboard)."""

    class Meta:
        model = Book
        fields = (
            "title",
            "author",
            "category",
            "isbn",
            "total_copies",
            "available_copies",
            "cover_image",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "author": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "isbn": forms.TextInput(attrs={"class": "form-control"}),
            "total_copies": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "available_copies": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "cover_image": forms.FileInput(attrs={"class": "form-control"}),
        }
