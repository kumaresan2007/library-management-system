from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("verify-register/", views.verify_register_otp, name="verify_register"),
    path("login/", views.login_request, name="login"),
    path("verify-login/", views.verify_login_otp, name="verify_login"),
    path("admin-login/", views.admin_login, name="admin_login"),
    path("verify-admin-otp/", views.verify_admin_otp, name="verify_admin_otp"),
    path("logout/", views.logout_view, name="logout"),
    path("redirect/", views.post_login_redirect, name="post_login_redirect"),
    path("dashboard/admin/", views.AdminDashboardView.as_view(), name="admin_dashboard"),
    path("admin-dashboard/", views.AdminDashboardView.as_view(), name="admin_dashboard_short"),
    path("dashboard/student/", views.StudentDashboardView.as_view(), name="student_dashboard"),
    path("admin/students/", views.admin_students, name="admin_students"),
    path("students/", views.student_list, name="student_list"),
]
