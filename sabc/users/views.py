# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView
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


class TournamentCreateView(CreateView):
    model = Tournament
    fields = '__all__'
    # type = models.CharField(default=TOURNAMENT_TYPES[1][1], max_length=48, choices=TOURNAMENT_TYPES)
    # name = models.CharField(
    #     default='%s %s Tournament - %s' % (
    #         time.strftime('%B'),  # Month Name
    #         time.strftime('%Y'),  # Year
    #         time.strftime('%m')), # Tournament # for the year
    #         null=True, max_length=128)
    # date = models.DateField(null=True)
    # lake = models.CharField(blank=True, max_length=100, choices=LAKES)
    # ramp = models.CharField(blank=True, max_length=128)

    # days = models.IntegerField(default=1)
    # start = models.TimeField(blank=True, null=True)
    # finish = models.TimeField(blank=True, null=True)
    # state = models.CharField(max_length=16, choices=STATES, default='TX')
    # points = models.BooleanField(default=True)
    # entry_fee = models.IntegerField(default=20)
    # description = models.TextField(null=True, blank=True)
    # organization = models.CharField(max_length=128, default='SABC', choices=Profile.CLUBS)
    # ramp_url = models.CharField(max_length=1024, blank=True)
    # facebook_url = models.CharField(max_length=1024, blank=True)

def about(request):
    """About page"""
    return render(request, 'users/about.html', {'title': 'SABC - About'})


def bylaws(request):
    """Bylaws page"""
    return render(request, 'users/bylaws.html', {'title': 'SABC - Bylaws'})


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