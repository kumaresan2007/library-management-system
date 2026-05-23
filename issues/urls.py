from django.urls import path

from . import views

app_name = "issues"

urlpatterns = [
    path("request/<int:book_id>/", views.request_issue, name="request_issue"),
    path("mine/", views.my_issues, name="my_issues"),
    path("return/", views.return_menu, name="return_menu"),
    path("return/<int:issue_id>/", views.return_book_view, name="return_book"),
    path("fines/", views.fine_list, name="fine_list"),
    path("how-issue/", views.issue_book_page, name="issue_book_page"),
    path("admin/pending/", views.admin_pending, name="admin_pending"),
    path("admin/pending/<int:issue_id>/approve/", views.admin_approve, name="admin_approve"),
    path("admin/pending/<int:issue_id>/reject/", views.admin_reject, name="admin_reject"),
    path("admin/issued/", views.admin_issued, name="admin_issued"),
    path("admin/overdue/", views.admin_overdue, name="admin_overdue"),
]
