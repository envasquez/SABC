"""User Forms"""
# pylint: disable=import-error
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class UserRegisterForm(UserCreationForm):
    """UserRegistrationForm"""
    email = forms.EmailField()

    class Meta:
        """UserRegisterForm metadata"""
        model = User
        fields = ['username', 'email', 'password1', 'password2']
