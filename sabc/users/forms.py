# -*- coding: utf-8 -*-
from betterforms.multiform import MultiModelForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

# from django.contrib.auth.models import User
from django.forms import CharField, EmailField, FileField, Form, ModelForm
from phonenumber_field.formfields import PhoneNumberField

from .models import Angler

User = get_user_model()


class UserRegisterForm(UserCreationForm):
    email = EmailField(max_length=512)
    first_name = CharField(max_length=25)
    last_name = CharField(max_length=30)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")


class AnglerRegisterForm(ModelForm):
    phone_number = PhoneNumberField()

    class Meta:
        model = Angler
        fields = ("phone_number", "image")


class AnglerUserMultiRegisterForm(MultiModelForm):
    form_classes = {"user": UserRegisterForm, "angler": AnglerRegisterForm}


class UserUpdateForm(ModelForm):
    email = EmailField()

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")


class AnglerUpdateForm(ModelForm):
    phone_number = PhoneNumberField()

    class Meta:
        model = Angler
        fields = ("phone_number", "image")


class AnglerUserMultiUpdateForm(MultiModelForm):
    form_classes = {"user": UserUpdateForm, "angler": AnglerUpdateForm}


class CsvImportForm(Form):
    csv_upload = FileField()
