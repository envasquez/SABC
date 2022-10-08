# -*- coding: utf-8 -*-
# Using a file level pylint disable because of Django objects
# pylint: disable=no-member, unused-argument
"""Tournament Views"""
from __future__ import unicode_literals


from django.contrib import messages
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin

from .forms import TournamentForm, ResultForm, TeamForm
from .models import Tournament, Result, TeamResult

OFFICERS = [
    "president",
    "vice-president",
    "secretary",
    "treasurer",
    "social-media",
    "tournament-director",
    "assistant-tournament-director",
]

#
# Tournaments
#
class TournamentListView(ListView):
    """Tournament list view"""

    model = Tournament
    ordering = ["-date"]  # Newest tournament first
    paginate_by = 3
    template_name = "users/index.html"
    context_object_name = "tournaments"


class TournamentDetailView(DetailView):
    """Tournament detail view"""

    model = Tournament


class TournamentCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    """Tournament create view"""

    model = Tournament
    form_class = TournamentForm
    success_message = "Tournament Successfully Created!"

    def form_valid(self, form):
        """Form validator"""
        # pylint: disable=useless-super-delegation
        return super().form_valid(form)

    def test_func(self):
        """Test function for values"""
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )


class TournamentUpdateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    """Tournament update view"""

    model = Tournament
    form_class = TournamentForm
    success_message = "Tournament Successfully Updated!"

    def form_valid(self, form):
        """Form validator"""
        form.instance.updated_by = self.request.user.angler
        return super().form_valid(form)

    def test_func(self):
        """Test function for values"""
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )


class TournamentDeleteView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView
):
    """Tournament delete view"""

    model = Tournament
    success_message = "Tournament [ %s ] Successfully Deleted!"
    success_url = "/"

    def test_func(self):  # Don't delete tournaments that are not over
        """Test function for values"""
        return not self.get_object().complete

    def delete(self, request, *args, **kwargs):
        """Execute a deletion"""
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj.__dict__.get("name", "UNKNOWN"))
        return super().delete(request, *args, **kwargs)


#
# Results
#
class ResultCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    """Result creation view"""

    model = Result
    form_class = ResultForm
    success_message = "Results Successfully Added for: %s"

    def get_initial(self, *args, **kwargs):
        """Get initial result"""
        initial = super().get_initial(**kwargs)
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def save(self, *args, **kwargs):
        """Save a result"""
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj.angler)

    def test_func(self):
        """Test function for values"""
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )


#
# Teams
#
class TeamCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    """Team creation view"""

    model = TeamResult
    form_class = TeamForm
    template_name = "tournaments/team_form.html"

    def get_initial(self, *args, **kwargs):
        """Get intital team create view"""
        initial = super().get_initial(**kwargs)
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def test_func(self):
        """Test function for values"""
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )

    def get_success_message(self, *args, **kwargs):
        """Get success message"""
        obj = self.get_object()
        tournament_name = Tournament.objects.get(id=self.kwargs.get("pk")).name
        return f"{str(obj)} added to {tournament_name}"

    def get_queryset(self):
        """Get query set"""
        q_set = super().get_queryset()
        return q_set.filter(tournament=self.kwargs.get("pk"))


class TeamListView(SuccessMessageMixin, LoginRequiredMixin, ListView):
    """Team list view"""

    model = TeamResult
    form_class = TeamForm
    paginate_by = 10
    template_name = "tournaments/team_list.html"
    context_object_name = "teams"

    def get_initial(self, *args, **kwargs):
        """Get intitial view"""
        initial = super().get_initial(**kwargs)
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def get_queryset(self):
        """Get team queryset"""
        q_set = super().get_queryset()
        return q_set.filter(tournament=self.kwargs.get("pk"))

    def test_func(self):
        """Test function for values"""
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )


class TeamDetailView(SuccessMessageMixin, LoginRequiredMixin, DetailView):
    """Team detail view"""

    model = TeamResult
    form_class = TeamForm
    context_object_name = "team"

    def get_initial(self, *args, **kwargs):
        """Get initial team"""
        initial = super().get_initial(**kwargs)
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def get_queryset(self):
        """Gets a queryset from a tournament object"""
        q_set = super().get_queryset()
        return q_set.filter(tournament=self.kwargs.get("pk"))

    def test_func(self):
        """Test function for values"""
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )


# class TeamUpdateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
#     model = Tournament
#     form_class = TeamForm
#     success_message = '%s Successfully Updated!'

#     def get_initial(self, *args, **kwargs):
#         initial = super(TeamUpdateView, self).get_initial(**kwargs)
#         initial['tournament'] = self.kwargs.get('pk')
#         return initial

#     def test_func(self):
#         return self.request.user.angler.type == 'officer'

#     def save(self, *args, **kwargs):
#         obj = self.get_object()
#         messages.success(self.request, self.success_message % obj.__dict__.get('name', 'UNKNOWN'))
