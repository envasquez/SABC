# -*- coding: utf-8 -*-

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
    model = Tournament
    ordering = ["-date"]  # Newest tournament first
    paginate_by = 3
    template_name = "users/index.html"
    context_object_name = "tournaments"


class ExtraContext:
    extra_context = {}

    def get_context_data(self):
        context = super().get_context_data()
        tmnt = Tournament.objects.get(id=self.get_object().id)
        if tmnt.points:
            Tournament.results.set_points(tournament=tmnt)
        self.extra_context["results"] = ResultTable(
            Result.objects.filter(tournament=tmnt).order_by("place_finish")
        )
        self.extra_context["team_results"] = TeamResultTable(
            TeamResult.objects.filter(tournament=tmnt).order_by("place_finish")
        )
        self.extra_context["payouts"] = {}
        for key, val in Tournament.results.get_payouts(tmnt).items():
            self.extra_context["payouts"][key] = val

        self.extra_context["bb_winner"] = Tournament.results.get_big_bass_winner(tournament=tmnt)
        context.update(self.extra_context)

        return context


class TournamentDetailView(ExtraContext, DetailView):
    model = Tournament
    context_object_name = "tournament"


class TournamentCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Tournament
    form_class = TournamentForm
    success_message = "Tournament Successfully Created!"

    def test_func(self):
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )


class TournamentUpdateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    model = Tournament
    form_class = TournamentForm
    success_message = "Tournament Successfully Updated!"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user.angler
        return super().form_valid(form)

    def test_func(self):
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )


class TournamentDeleteView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView
):
    model = Tournament
    success_message = "Tournament [ %s ] Successfully Deleted!"
    success_url = "/"

    def test_func(self):
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj.__dict__.get("name", "UNKNOWN"))
        return super().delete(request, *args, **kwargs)


#
# Results
#
class ResultCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Result
    form_class = ResultForm

    def get_initial(self):
        initial = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def test_func(self):
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )

    def form_valid(self, form):
        tid = self.kwargs.get("pk")
        duplicate = form.instance.angler in [
            r.angler for r in Result.objects.filter(tournament=tid)
        ]
        if duplicate:
            result = Result.objects.get(tournament=tid, angler=form.instance.angler)
            messages.error(self.request, message=f"ERROR Result exists! {result}")
            return super().form_invalid(form)
        Tournament.results.set_points(Tournament.objects.get(id=tid))
        msg = f"{form.instance.angler} Buy-in"
        if not form.instance.buy_in:
            msg = " ".join(
                [
                    f"{form.instance.angler} {form.instance.num_fish} fish",
                    f"{form.instance.total_weight}lbs",
                    f"{form.instance.big_bass_weight}lb BB",
                ]
            )
        messages.success(self.request, f"Result added: {msg}")
        return super().form_valid(form)


#
# Teams
#
class TeamCreateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = TeamResult
    form_class = TeamForm
    template_name = "tournaments/team_form.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")

        return initial

    def test_func(self):
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )

    def get_queryset(self):
        q_set = super().get_queryset()
        return q_set.filter(tournament=self.kwargs.get("pk"))


class TeamListView(SuccessMessageMixin, LoginRequiredMixin, ListView):
    model = TeamResult
    form_class = TeamForm
    paginate_by = 10
    template_name = "tournaments/team_list.html"
    context_object_name = "teams"

    def get_initial(self):
        initial = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def get_queryset(self):
        q_set = super().get_queryset()
        return q_set.filter(tournament=self.kwargs.get("pk"))

    def test_func(self):
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )


class TeamDetailView(SuccessMessageMixin, LoginRequiredMixin, DetailView):
    model = TeamResult
    form_class = TeamForm
    template_name = "tournaments/team_detail.html"
    context_object_name = "team"

    def get_initial(self):
        initial = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def get_queryset(self):
        q_set = super().get_queryset()
        return q_set.filter(tournament=self.kwargs.get("pk"))

    def test_func(self):
        return any(
            [
                self.request.user.angler.officer_type in OFFICERS,
                self.request.user.is_staff,
            ]
        )


class TeamUpdateView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Tournament
    form_class = TeamForm
    success_message = "%s Successfully Updated!"

    def get_initial(self):
        initial = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")

        return initial

    def test_func(self):
        return self.request.user.angler.type == "officer"

    def save(self):
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj.__dict__.get("name", "UNKNOWN"))
