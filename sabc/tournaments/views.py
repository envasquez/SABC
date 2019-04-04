# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from django.contrib import messages
from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, \
    TemplateView
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin

from .forms import TournamentForm, ResultForm, TeamForm
from .models import Tournament, Result, PaperResult, Team

#
# Tournaments
#
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

    def test_func(self): # Don't delete tournaments that are not over
        return not self.get_object().complete

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj.__dict__.get('name', 'UNKNOWN'))
        return super(TournamentDeleteView, self).delete(request, *args, **kwargs)


#
# Results
#
class ResultCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Result
    form_class = ResultForm
    success_message = 'Results Successfully Added: %s'

    def get_initial(self, *args, **kwargs):
        initial = super(ResultCreateView, self).get_initial(**kwargs)
        initial['tournament'] = self.kwargs.get('pk')
        return initial

    def save(self, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj)

    def test_func(self):
        return self.request.user.profile.type == 'officer'


#
# Teams
#
class TeamCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm

    def get_initial(self, *args, **kwargs):
        initial = super(TeamCreateView, self).get_initial(**kwargs)
        initial['tournament'] = self.kwargs.get('pk')
        return initial

    def test_func(self):
        if self.request.user.profile.type != 'officer':
            return False

    def get_success_message(self, *args, **kwargs):
        obj = self.get_object()
        return '%s added to %s' % (
            obj.__str__(),
            Tournament.objects.get(id=self.kwargs.get('pk')).name)

    def get_queryset(self):
        qs = super(TeamCreateView, self).get_queryset()
        return qs.filter(tournament=self.kwargs.get('pk'))


class TeamListView(SuccessMessageMixin, LoginRequiredMixin, ListView):
    model = Team
    form_class = TeamForm
    paginate_by = 10
    template_name = 'tournaments/team_list.html'
    context_object_name = 'teams'

    def get_initial(self, *args, **kwargs):
        initial = super(TeamListView, self).get_initial(**kwargs)
        initial['tournament'] = self.kwargs.get('pk')
        return initial

    def get_queryset(self):
        qs = super(TeamListView, self).get_queryset()
        return qs.filter(tournament=self.kwargs.get('pk'))

    def test_func(self):
        return self.request.user.profile.type == 'officer'


class TeamDetailView(SuccessMessageMixin, LoginRequiredMixin, DetailView):
    model = Team
    form_class = TeamForm
    context_object_name = 'team'

    def get_initial(self, *args, **kwargs):
        initial = super(TeamListView, self).get_initial(**kwargs)
        initial['tournament'] = self.kwargs.get('pk')
        return initial

    def get_queryset(self):
        qs = super(TeamDetailView, self).get_queryset()
        return qs.filter(tournament=self.kwargs.get('pk'))

    def test_func(self):
        return self.request.user.profile.type == 'officer'


# class TeamUpdateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
#     model = Tournament
#     form_class = TeamForm
#     success_message = '%s Successfully Updated!'

#     def get_initial(self, *args, **kwargs):
#         initial = super(TeamUpdateView, self).get_initial(**kwargs)
#         initial['tournament'] = self.kwargs.get('pk')
#         return initial

#     def test_func(self):
#         return self.request.user.profile.type == 'officer'

#     def save(self, *args, **kwargs):
#         obj = self.get_object()
#         messages.success(self.request, self.success_message % obj.__dict__.get('name', 'UNKNOWN'))