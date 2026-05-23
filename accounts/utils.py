from django.conf import settings
from django.core.mail import send_mail


def send_otp_email(email, otp):
    subject = "Your OTP Code"
    message = f"Your OTP is {otp}. It is valid for 5 minutes."
    print(f"[EMAIL OTP] Sending OTP {otp} to {email}")
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        print("Email sent successfully")
    except Exception as e:
        print("Email failed:", str(e))

