"""User Forms"""
# Using file level pylint disable because of Django form objects
# pylint: disable=too-few-public-methods
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from phonenumber_field.modelfields import PhoneNumberField

from .models import Angler


class UserRegisterForm(UserCreationForm):
    """UserRegistrationForm"""

    email = forms.EmailField()
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)

    class Meta:
        """UserRegisterForm metadata"""

        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name",
        )


class GuestRegisterForm(UserCreationForm):
    """UserRegistrationForm"""

    email = forms.EmailField()
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)

    class Meta:
        """UserRegisterForm metadata"""

        model = User
        fields = ("email", "first_name", "last_name")


class UserUpdateForm(forms.ModelForm):
    """User update form"""

    email = forms.EmailField()

    class Meta:
        """UserRegisterForm metadata"""

        model = User
        fields = ("username", "email")


class AnglerUpdateForm(forms.ModelForm):
    """Angler update form"""

    phone_number = PhoneNumberField(blank=True)

    class Meta:
        """AnglerUpdateForm metadata"""

        model = Angler
        fields = ("phone_number", "image", "private_info")


class CsvImportForm(forms.Form):
    csv_upload = forms.FileField()
