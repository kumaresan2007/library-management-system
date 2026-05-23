from django.contrib import admin

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "book", "status", "reservation_date", "notified_at")
    list_filter = ("status",)
