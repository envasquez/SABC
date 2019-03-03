# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin

from .forms import TournamentForm
from .models import Tournament


class TournamentListView(ListView):
    model = Tournament
    ordering = ['-date'] # Newest tournament first
    paginate_by = 3
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
        messages.success(self.request, self.success_message % obj.__dict__.get('name', 'UNKNOWN'))

        return super(TournamentDeleteView, self).delete(request, *args, **kwargs)