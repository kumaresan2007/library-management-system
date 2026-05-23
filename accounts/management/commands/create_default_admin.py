from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create default admin user"

    def handle(self, *args, **kwargs):
        email = "kumaresan24102000@gmail.com"
        password = "password@123"
        User = get_user_model()

        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                username="admin",
                email=email,
                password=password,
            )
            User.objects.filter(email=email).update(
                is_admin=True,
                role="admin",
                is_verified=True,
                is_active=True,
            )
            self.stdout.write(self.style.SUCCESS("Admin user created"))
        else:
            user = User.objects.get(email=email)
            changed = False
            if not user.check_password(password):
                user.set_password(password)
                changed = True
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if not getattr(user, "is_admin", False):
                user.is_admin = True
                changed = True
            if getattr(user, "role", None) != "admin":
                user.role = "admin"
                changed = True
            if not getattr(user, "is_verified", False):
                user.is_verified = True
                changed = True
            if changed:
                user.save()
                self.stdout.write(self.style.SUCCESS("Admin already existed; details updated"))
            else:
                self.stdout.write("Admin already exists")

