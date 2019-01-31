# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.shortcuts import render
from django.contrib.auth.forms import UserCreationForm


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
    """Allows a user to register with the site"""
    return render(request, 'register.html', {'title': 'User Registration', 'form': UserCreationForm()})