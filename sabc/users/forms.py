"""User Forms"""

from django.forms import CharField, EmailField, FileField, ModelForm, Form
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from phonenumber_field.formfields import PhoneNumberField

from .models import Angler


class UserRegisterForm(UserCreationForm):
    """UserRegistrationForm for registering new Users"""

    email = EmailField()
    first_name = CharField(max_length=100)
    last_name = CharField(max_length=100)

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


class AnglerRegisterForm(ModelForm):
    """AnglerRegisterForm for registering new Anglers"""

    class Meta:
        """Model and field designations for Anglers registering"""

        model = Angler
        fields = ("phone_number", "image")


class UserUpdateForm(ModelForm):
    """User update form"""

    email = EmailField()

    class Meta:
        """UserRegisterForm metadata"""

        model = User
        fields = ("username", "email")


class AnglerUpdateForm(ModelForm):
    """Angler update form"""

    phone_number = PhoneNumberField()

    class Meta:
        """AnglerUpdateForm metadata"""

        model = Angler
        fields = ("phone_number", "image")


class CsvImportForm(Form):
    csv_upload = FileField()
