# -*- coding: utf-8 -*-
# Using a file level pylint disable because of Django objects
# pylint: disable=unused-argument
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
from .tables import ResultTable, TeamResultTable
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


class ExtraContext:
    """Additional tournament data - namely results for a completed tournament"""

    extra_context = {}

    def get_context_data(self, **kwargs):
        """Override of get_context_data

        Args:
            kwargs (dict): Keyword arguments

        Returns:
            context (dict): Updated tournament context
        """
        context = super().get_context_data(**kwargs)
        #
        # Get the tournament results if any
        #
        tmnt = Tournament.objects.get(id=self.get_object().id)
        Tournament.results.set_places(tournament=tmnt)
        if tmnt.points:
            Tournament.results.set_points(tournament=tmnt)
        self.extra_context["results"] = ResultTable(
            Result.objects.filter(tournament=tmnt).order_by("place_finish")
        )
        self.extra_context["team_results"] = TeamResultTable(
            TeamResult.objects.filter(tournament=tmnt).order_by("place_finish")
        )
        #
        # Add the Tournament payout info
        #
        self.extra_context["payouts"] = {}
        for key, val in Tournament.results.get_payouts(tmnt).items():
            self.extra_context["payouts"][key] = val

        self.extra_context["bb_winner"] = Tournament.results.get_big_bass_winner(tournament=tmnt)
        context.update(self.extra_context)

        return context


class TournamentDetailView(ExtraContext, DetailView):
    """Tournament detail view"""

    model = Tournament
    context_object_name = "tournament"


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
    success_message = "Results Added for: %s"

    def get_initial(self, *args, **kwargs):
        """Get initial result"""
        initial = super().get_initial(**kwargs)
        initial["tournament"] = self.kwargs.get("pk")

        return initial

    def save(self, *args, **kwargs):
        """Save a result - Trigger a re-setting of places and points when a result is saved"""
        tmnt = Tournament.objects.get(self.get_initial(*args, **kwargs)["tournament"])
        Tournament.results.set_places(tournament=tmnt)
        if tmnt.points:
            Tournament.results.set_points(tournament=tmnt)

        messages.success(self.request, self.success_message % self.get_object())

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
    template_name = "tournaments/team_detail.html"
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


class TeamUpdateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    """Team update View"""

    model = Tournament
    form_class = TeamForm
    success_message = "%s Successfully Updated!"

    def get_initial(self, *args, **kwargs):
        """Get an intial TeamUpdateView state for a tournament"""
        initial = super().get_initial(**kwargs)
        initial["tournament"] = self.kwargs.get("pk")

        return initial

    def test_func(self):
        """Test that only officers can update team info"""
        return self.request.user.angler.type == "officer"

    def save(self, *args, **kwargs):
        """Save a team record"""
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj.__dict__.get("name", "UNKNOWN"))
