# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required

from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from tournaments.models import Tournament


class TournamentListView(ListView):
    model = Tournament
    ordering = ['-date']
    template_name = 'users/index.html'
    context_object_name = 'tournaments'

class TournamentDetailView(DetailView):
    model = Tournament



def about(request):
    """About page"""
    return render(request, 'users/about.html', {'title': 'SABC - About'})


def bilaws(request):
    """Bi Laws page"""
    return render(request, 'users/bilaws.html', {'title': 'SABC - Bi Laws'})


def gallery(request):
    """Gallery page"""
    return render(request, 'users/gallery.html', {'title': 'SABC - Gallery'})


def calendar(request):
    """Calendar page"""
    return render(request, 'users/calendar.html', {'title': 'SABC - Calendar'})


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
    return render(request, 'users/register.html', {'title':'SABC - Registration', 'form': form})


@login_required
def profile(request):
    """Profile/Account settings"""
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'users/profile.html', {'title': 'Angler Profile', 'u_form': u_form, 'p_form': p_form})