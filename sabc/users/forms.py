# -*- coding: utf-8 -*-
from django.forms import CharField, EmailField, FileField, ModelForm, Form
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from betterforms.multiform import MultiModelForm
from phonenumber_field.formfields import PhoneNumberField

from .models import Angler


class UserRegisterForm(UserCreationForm):
    email = EmailField()
    first_name = CharField(max_length=100)
    last_name = CharField(max_length=100)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name",
        )


class UserUpdateForm(ModelForm):
    email = EmailField()

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")


class AnglerRegisterForm(ModelForm):
    phone_number = PhoneNumberField()

    class Meta:
        model = Angler
        fields = ("phone_number", "image")


class AnglerUpdateForm(ModelForm):
    phone_number = PhoneNumberField()

    class Meta:
        model = Angler
        fields = ("phone_number", "image")


class AnglerUserMultiUpdateForm(MultiModelForm):
    form_classes = {
        "user": UserUpdateForm,
        "angler": AnglerUpdateForm,
    }


class CsvImportForm(Form):
    csv_upload = FileField()
