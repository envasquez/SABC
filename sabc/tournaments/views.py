# -*- coding: utf-8 -*-
import datetime

from decimal import Decimal

from django.contrib import messages
from django.shortcuts import render
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required

from .forms import TournamentForm, ResultForm, TeamForm
from .tables import (
    Aoy as AoyTable,
    BigBass,
    ResultTable,
    PayoutSummary,
    HeavyStringer,
    TeamResultTable,
    TournamentSummary,
)
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

    def get_payout_table(self, tid):
        payouts = Tournament.results.get_payouts(tid)
        for key, val in payouts.items():
            payouts[key] = f"${val:.2f}"

        return PayoutSummary([payouts])

    def get_stats_table(self, tid):
        limits = Result.objects.filter(tournament=tid, num_fish=5).count()
        zeroes = Result.objects.filter(tournament=tid, num_fish=0, buy_in=False).count()
        buy_ins = Result.objects.filter(tournament=tid, buy_in=True).count()
        bb_result = Tournament.results.get_big_bass_winner(tournament=tid)
        hs_result = Result.objects.get(tournament=tid, place_finish=1)
        heavy_stringer = f"{hs_result.angler} {hs_result.total_weight}lbs"

        total_fish, total_weight = 0, Decimal("0")
        for result in Result.objects.filter(tournament=tid, num_fish__gt=0):
            total_fish += result.num_fish
            total_weight += result.total_weight

        big_bass = "--"
        if bb_result:
            big_bass = f"{bb_result.angler} {bb_result.big_bass_weight: .2f}lbs"
        data = {
            "limits": limits,
            "zeros": zeroes,
            "buy_ins": buy_ins,
            "total_fish": total_fish,
            "total_weight": f"{total_weight: .2f}lbs",
            "big_bass": big_bass,
            "heavy_stringer": heavy_stringer,
        }

        return TournamentSummary([data])

    def get_context_data(self, **kwargs):
        tmnt = Tournament.objects.get(id=self.get_object().id)
        results = Result.objects.filter(tournament=tmnt).order_by("place_finish")
        team_results = TeamResult.objects.filter(tournament=tmnt).order_by("place_finish")
        context = super().get_context_data(**kwargs)

        Tournament.results.set_points(tournament=tmnt)
        self.extra_context["results"] = ResultTable(results)
        self.extra_context["team_results"] = TeamResultTable(team_results)
        self.extra_context["payouts"] = self.get_payout_table(tmnt)
        self.extra_context["catch_stats"] = TournamentSummary([])
        if results:
            self.extra_context["catch_stats"] = self.get_stats_table(tmnt)
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tournament"] = Tournament.objects.get(id=self.kwargs.get("pk"))

        return context

    def form_valid(self, form):
        tid = self.kwargs.get("pk")
        duplicate = form.instance.angler in [
            r.angler for r in Result.objects.filter(tournament=tid)
        ]
        if duplicate:  # Don't add duplicate records!
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


@login_required
def annual_awards(request):
    aoy_tbl = AoyTable(get_aoy_results())
    aoy_tbl.order_by = "-total_points"
    hvy_tbl = HeavyStringer(get_heavy_stringer())
    bb_tbl = BigBass(get_big_bass())
    return render(
        request,
        "tournaments/annual_awards.html",
        {
            "title": "Statistics",
            "aoy_tbl": aoy_tbl,
            "hvy_tbl": hvy_tbl,
            "bb_tbl": bb_tbl,
            "year": datetime.date.today().year,
        },
    )


def get_aoy_results(year=datetime.date.today().year):
    all_results = Result.objects.filter(
        tournament__year=year,
        angler__user__is_active=True,
    )
    anglers = []
    for result in all_results:
        if result.angler not in anglers:
            anglers.append(result.angler)

    results = []
    for angler in anglers:
        total_pts = sum(r.points for r in all_results if r.angler == angler)
        total_weight = sum(r.total_weight for r in all_results if r.angler == angler)
        total_fish = sum(r.num_fish for r in all_results if r.angler == angler)
        total_results = sum(1 for r in all_results if r.angler == angler)
        results.append(
            {
                "angler": angler.user.get_full_name(),
                "total_points": total_pts,
                "total_weight": total_weight,
                "total_fish": total_fish,
                "events": total_results,
            }
        )

    return results


def get_heavy_stringer(year=datetime.date.today().year):
    result = (
        Result.objects.filter(
            tournament__year=year, angler__user__is_active=True, total_weight__gt=Decimal("0")
        )
        .order_by("-total_weight")
        .first()
    )

    return [
        {
            "angler": result.angler,
            "weight": result.total_weight,
            "fish": result.num_fish,
            "tournament": result.tournament,
        }
    ]


def get_big_bass(year=datetime.date.today().year):
    result = (
        Result.objects.filter(
            tournament__year=year, angler__user__is_active=True, big_bass_weight__gte=Decimal("5.0")
        )
        .order_by("-big_bass_weight")
        .first()
    )
    return [
        {"angler": result.angler, "weight": result.big_bass_weight, "tournament": result.tournament}
    ]
