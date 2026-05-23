"""Root URL configuration; serves media in development."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import RedirectView
from django.urls import include, path

from accounts.views import library_status
from reservations.views import reserve_book

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="accounts:home", permanent=False)),
    path("admin/library-status/", library_status, name="library_status"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("books/", include("books.urls")),
    path("issues/", include("issues.urls")),
    path("reservations/", include("reservations.urls")),
    path("reserve/<int:book_id>/", reserve_book, name="reserve_book"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "accounts.views.handler403"
