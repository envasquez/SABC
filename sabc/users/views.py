# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .forms import UserRegisterForm


events = [
    {
        'name': 'Lake Travis Tournament 1 - Jan 27, 2019',
        'ramp': 'Tatum',
        'time_start': '7am',
        'time_end': '4pm'
    },
    {
        'name': 'Lake Richland Chambers 2019 Tournament 2 - Feb 23 & 24',
        'ramp': 'Cottonwood Shores',
        'time_start': '7am',
        'time_end': '3pm'
    }
]


def index(request):
    """Landing page"""
    return render(request, 'index.html', {'title': 'South Austin Bass Club', 'posts': events})


def about(request):
    """About page"""
    return render(request, 'about.html', {'title': 'SABC - About'})


def bilaws(request):
    """Bi Laws page"""
    return render(request, 'bilaws.html', {'title': 'SABC - Bi Laws'})


def gallery(request):
    """Gallery page"""
    return render(request, 'gallery.html', {'title': 'SABC - Gallery'})


def calendar(request):
    """Calendar page"""
    return render(request, 'calendar.html', {'title': 'SABC - Calendar'})


def register(request):
    """User registration/validation"""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created for %s, you can now login' % form.cleaned_data.get('username'))
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'title':'SABC - Registration', 'form': form})


@login_required
def profile(request):
    """Profile/Account settings"""
    return render(request, 'profile.html', {'title': 'Angler Profile'})