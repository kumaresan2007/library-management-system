from django.urls import path

from . import views

app_name = "reservations"

urlpatterns = [
    path("book/<int:book_id>/", views.reserve_book, name="reserve_book"),
    path("mine/", views.my_reservations, name="my_reservations"),
    path("<int:pk>/cancel/", views.cancel_reservation, name="cancel_reservation"),
    path("admin/", views.admin_reservations, name="admin_reservations"),
]
