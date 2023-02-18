# -*- coding: utf-8 -*-
from typing import Type

from betterforms.multiform import MultiModelForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.forms import CharField, EmailField, FileField, Form, ModelForm
from phonenumber_field.formfields import PhoneNumberField

from .models import Angler

User = get_user_model()


class UserRegisterForm(UserCreationForm):
    email: EmailField = EmailField(max_length=512)
    first_name: CharField = CharField(max_length=25)
    last_name: CharField = CharField(max_length=30)

    class Meta:
        model: Type[User] = User  # type: ignore
        fields: tuple[str, ...] = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )


class AnglerRegisterForm(ModelForm):
    phone_number: PhoneNumberField = PhoneNumberField()

    class Meta:
        model: Type[Angler] = Angler
        fields: tuple[str] = ("phone_number",)


class AnglerUserMultiRegisterForm(MultiModelForm):
    form_classes: dict = {"user": UserRegisterForm, "angler": AnglerRegisterForm}


class UserUpdateForm(ModelForm):
    email: EmailField = EmailField()

    class Meta:
        model: Type[User] = User  # type: ignore
        fields: tuple[str, ...] = ("username", "first_name", "last_name", "email")


class AnglerUpdateForm(ModelForm):
    phone_number: PhoneNumberField = PhoneNumberField()

    class Meta:
        model: Type[Angler] = Angler
        fields: tuple[str] = ("phone_number",)


class AnglerUserMultiUpdateForm(MultiModelForm):
    form_classes: dict = {"user": UserUpdateForm, "angler": AnglerUpdateForm}


class CsvImportForm(Form):
    csv_upload: FileField = FileField()
