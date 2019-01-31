# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.contrib import messages
from django.shortcuts import render, redirect

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


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created for %s!' % form.cleaned_data.get('username'))
            return redirect('sabc-home')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})