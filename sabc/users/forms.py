"""User Forms"""
# pylint: disable=import-error
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import Angler


class UserRegisterForm(UserCreationForm):
    """UserRegistrationForm"""
    email = forms.EmailField()
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)

    class Meta:
        """UserRegisterForm metadata"""
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'first_name', 'last_name']


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        """UserRegisterForm metadata"""
        model = User
        fields = ['username', 'email']


class AnglerUpdateForm(forms.ModelForm):
    class Meta:
        model = Angler
        fields = ['phone_number', 'image', 'private_info']