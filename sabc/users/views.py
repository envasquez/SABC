# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required

from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm

from .models import Profile

from tournaments.forms import TournamentForm
from tournaments.models import Tournament


class TournamentListView(ListView):
    model = Tournament
    ordering = ['-date'] # Newest tournament first
    template_name = 'users/index.html'
    context_object_name = 'tournaments'


class TournamentDetailView(DetailView):
    model = Tournament


class TournamentCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Tournament
    form_class = TournamentForm
    success_message = 'Tournament Successfully Created!'

    def form_valid(self, form):
        form.instance.created_by = self.request.user.profile

        return super(CreateView, self).form_valid(form)

    def test_func(self):
        return self.request.user.profile.type == 'officer'

class TournamentUpdateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Tournament
    form_class = TournamentForm
    success_message = 'Tournament Successfully Updated!'

    def form_valid(self, form):
        form.instance.updated_by = self.request.user.profile

        return super(UpdateView, self).form_valid(form)

    def test_func(self):
        return self.request.user.profile.type == 'officer'


class TournamentDeleteView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Tournament
    success_message = 'Tournament [ %s ] Successfully Deleted!'
    success_url = '/'

    def test_func(self):
        return not self.get_object().complete

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj.__dict__.get('name', ''))

        return super(TournamentDeleteView, self).delete(request, *args, **kwargs)


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
    profile = Profile.objects.get_or_create(user=request.user)
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