"""Email-only OTP authentication forms (no phone/SMS)."""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class StudentRegistrationForm(UserCreationForm):
    """
    Registration form used by the registration page.
    Phone fields are fully removed.
    """

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "autocomplete": "username"})
        self.fields["email"].widget.attrs.update({"class": "form-control", "autocomplete": "email"})
        for key in ("password1", "password2"):
            self.fields[key].widget.attrs.update({"class": "form-control", "autocomplete": "new-password"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "student"
        # Keep `name` populated for existing templates/emails.
        user.name = user.name or user.username
        if commit:
            user.save()
        return user


class EmailForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}))


class OTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-center fs-4",
                "style": "letter-spacing: 0.25em;",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
                "maxlength": "6",
            }
        ),
    )

    def clean_otp(self):
        otp = (self.cleaned_data.get("otp") or "").strip()
        if not otp.isdigit() or len(otp) != 6:
            raise forms.ValidationError("Enter the 6-digit numeric code.")
        return otp
