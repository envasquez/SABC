# -*- coding: utf-8 -*-

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from django.forms import (
    CharField,
    EmailField,
    FileField,
    Form,
    ImageField,
    ModelForm,
    ValidationError,
)
from phonenumber_field.formfields import PhoneNumberField

from .models import Angler

User = get_user_model()


class UserRegisterForm(UserCreationForm):
    email = EmailField(max_length=512, help_text="Enter a valid email address")
    first_name = CharField(
        max_length=25,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z\s\'-]+$",
                message="First name can only contain letters, spaces, hyphens, and apostrophes",
            )
        ],
        help_text="Enter your first name (letters only)",
    )
    last_name = CharField(
        max_length=30,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z\s\'-]+$",
                message="Last name can only contain letters, spaces, hyphens, and apostrophes",
            )
        ],
        help_text="Enter your last name (letters only)",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username:
            # Username validation: alphanumeric, underscore, hyphen only
            if not re.match(r"^[a-zA-Z0-9_-]+$", username):
                raise ValidationError(
                    "Username can only contain letters, numbers, underscores, and hyphens"
                )
            if len(username) < 3:
                raise ValidationError("Username must be at least 3 characters long")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            # Check for existing email
            if User.objects.filter(email=email).exists():
                raise ValidationError("A user with this email already exists")
        return email


class AnglerRegisterForm(ModelForm):
    phone_number = PhoneNumberField()

    class Meta:
        model = Angler
        fields = ("phone_number",)


class UserUpdateForm(ModelForm):
    email = EmailField(help_text="Enter a valid email address")
    first_name = CharField(
        max_length=25,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z\s\'-]+$",
                message="First name can only contain letters, spaces, hyphens, and apostrophes",
            )
        ],
        help_text="Enter your first name (letters only)",
    )
    last_name = CharField(
        max_length=30,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z\s\'-]+$",
                message="Last name can only contain letters, spaces, hyphens, and apostrophes",
            )
        ],
        help_text="Enter your last name (letters only)",
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username:
            if not re.match(r"^[a-zA-Z0-9_-]+$", username):
                raise ValidationError(
                    "Username can only contain letters, numbers, underscores, and hyphens"
                )
            if len(username) < 3:
                raise ValidationError("Username must be at least 3 characters long")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and self.instance:
            # Check for existing email excluding current user
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError("A user with this email already exists")
        return email


class AnglerUpdateForm(ModelForm):
    phone_number = PhoneNumberField()
    image = ImageField(required=False, help_text="Upload a profile picture (max 5MB, JPG/PNG)")

    class Meta:
        model = Angler
        fields = ("phone_number", "image")

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            # Check file size (5MB max)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Image size cannot exceed 5MB")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise ValidationError("Only JPG and PNG images are allowed")
            
            # Check image dimensions (optional - prevent extremely large images)
            from PIL import Image
            try:
                img = Image.open(image)
                if img.width > 2000 or img.height > 2000:
                    raise ValidationError("Image dimensions cannot exceed 2000x2000 pixels")
            except Exception:
                raise ValidationError("Invalid image file")
                
        return image


class CsvImportForm(Form):
    csv_upload = FileField(help_text="Upload a CSV file (max 5MB)")

    def clean_csv_upload(self):
        file = self.cleaned_data.get("csv_upload")
        if file:
            # Check file size (5MB max)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 5MB")

            # Check file extension
            if not file.name.lower().endswith(".csv"):
                raise ValidationError("Only CSV files are allowed")

            # Check MIME type
            allowed_types = ["text/csv", "application/csv", "text/plain"]
            if hasattr(file, "content_type") and file.content_type not in allowed_types:
                raise ValidationError("Invalid file type. Please upload a CSV file")

        return file
