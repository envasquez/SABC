# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render


def index(request):
    """Landing page"""
    return render(request, 'index.html', {'title': 'South Austin Bass Club'})
