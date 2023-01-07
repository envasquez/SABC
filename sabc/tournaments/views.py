# -*- coding: utf-8 -*-
import datetime

from decimal import Decimal

from django.urls import reverse_lazy
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

from users.models import Officers

from . import NEXT_MEETING, NEXT_TOURNAMENT

from .forms import TournamentForm, ResultForm, TeamForm
from .tables import (
    Aoy as AoyTable,
    BigBass,
    ResultTable,
    PayoutSummary,
    HeavyStringer,
    TeamResultTable,
    EditableResultTable,
    TournamentSummaryTable,
    EditableTeamResultTable,
)
from .models import Tournament, Result, TeamResult, PayOutMultipliers


class TournamentListView(ListView):
    model = Tournament
    ordering = ["-date"]  # Newest tournament first
    paginate_by = 3
    template_name = "users/index.html"
    context_object_name = "tournaments"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["index_html"] = True
        context["next_meeting"] = NEXT_MEETING
        context["next_tournament"] = NEXT_TOURNAMENT
        return context


class ExtraTournamentContext:
    extra_context = {}

    def get_payout_table(self, tid):
        payouts = Tournament.results.get_payouts(tid)
        for key, val in payouts.items():
            payouts[key] = f"${val:.2f}"

        return PayoutSummary([payouts])

    def get_stats_table(self, tid):
        tournament = Tournament.objects.get(pk=tid)
        if not tournament.complete:
            return TournamentSummaryTable([])

        limits = Result.objects.filter(tournament=tid, num_fish=5).count()
        zeroes = Result.objects.filter(tournament=tid, num_fish=0, buy_in=False).count()
        buy_ins = Result.objects.filter(tournament=tid, buy_in=True).count()
        bb_result = Tournament.results.get_big_bass_winner(tournament=tid)
        hs_result = Result.objects.filter(tournament=tid, place_finish=1)[0]
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

        return TournamentSummaryTable([data])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        tmnt = Tournament.objects.get(pk=self.kwargs.get("pk"))
        results = Result.objects.filter(tournament=tmnt).order_by("place_finish")
        team_results = TeamResult.objects.filter(tournament=tmnt).order_by("place_finish")

        Tournament.results.set_points(tournament=tmnt)
        self.extra_context["payouts"] = self.get_payout_table(tmnt)
        self.extra_context["results"] = ResultTable(results)
        self.extra_context["catch_stats"] = (
            self.get_stats_table(tmnt.id) if results else TournamentSummaryTable([])
        )
        self.extra_context["team_results"] = TeamResultTable(team_results)
        self.extra_context["editable_results"] = EditableResultTable(results)
        self.extra_context["editable_team_results"] = EditableTeamResultTable(team_results)

        context.update(self.extra_context)
        return context


class TournamentDetailView(ExtraTournamentContext, DetailView):
    model = Tournament
    context_object_name = "tournament"


class TournamentCreateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView
):
    model = Tournament
    form_class = TournamentForm
    success_message = "Tournament successfully created!"

    def get_initial(self):
        initial = super().get_initial()
        initial["payout_multiplier"] = PayOutMultipliers.objects.get(
            year=datetime.date.today().year
        )
        return initial

    def test_func(self):
        is_officer = Officers.objects.filter(
            year=datetime.date.today().year, angler=self.request.user.angler
        ).count()
        return is_officer != 0 or self.request.user.is_staff


class TournamentUpdateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    model = Tournament
    form_class = TournamentForm
    success_message = "Tournament successfully updated!"

    def test_func(self):
        is_officer = Officers.objects.filter(
            year=datetime.date.today().year, angler=self.request.user.angler
        ).count()
        return is_officer != 0 or self.request.user.is_staff


class TournamentDeleteView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView
):
    model = Tournament

    def test_func(self):
        is_officer = Officers.objects.filter(
            year=datetime.date.today().year, angler=self.request.user.angler
        ).count()
        return is_officer != 0 or self.request.user.is_staff

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(self.request, f"{self.get_object().name} Deleted!")
        return reverse_lazy("sabc-home")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, self.success_message % obj.name)
        return super().delete(request, *args, **kwargs)


class ResultCreateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Result
    form_class = ResultForm

    def get_initial(self):
        initial = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def test_func(self):
        is_officer = Officers.objects.filter(
            year=datetime.date.today().year, angler=self.request.user.angler
        ).count()
        return is_officer != 0 or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tournament"] = Tournament.objects.get(pk=self.kwargs.get("pk"))
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

        Tournament.results.set_points(Tournament.objects.get(pk=tid))
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


class ResultDeleteView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tournament"] = Result.objects.get(pk=self.kwargs.get("pk")).tournament
        return context

    def test_func(self):
        is_officer = Officers.objects.filter(
            year=datetime.date.today().year, angler=self.request.user.angler
        ).count()
        return is_officer != 0 or self.request.user.is_staff

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(self.request, f"{self.get_object()} Deleted!")
        return reverse_lazy("tournament-details", kwargs={"pk": self.get_object().tournament.id})


class TeamCreateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = TeamResult
    form_class = TeamForm
    template_name = "tournaments/team_form.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tournament"] = Tournament.objects.get(pk=self.kwargs.get("pk"))
        return context

    def test_func(self):
        is_officer = Officers.objects.filter(
            year=datetime.date.today().year, angler=self.request.user.angler
        ).count()
        return is_officer != 0 or self.request.user.is_staff

    def form_valid(self, form):
        tid = self.get_initial()["tournament"]
        results = TeamResult.objects.filter(tournament=tid)
        anglers = [r.result_1.angler for r in results] + [r.result_2.angler for r in results]
        err = "Team Result for %s already exists!"
        if form.instance.result_1.angler in anglers:
            messages.error(self.request, err % form.instance.result_1.angler)
            return self.form_invalid(form)
        if form.instance.result_2:
            if form.instance.result_2.angler in anglers:
                messages.error(self.request, err % form.instance.result_2.angler)
                return self.form_invalid(form)

        msg = f"{form.instance.result_1.angler}"
        msg += f"& {form.instance.result_2.angler}" if form.instance.result_2 else " - solo"
        messages.success(self.request, f"Team added: {msg}")
        return super().form_valid(form)


class TeamResultDeleteView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView
):
    model = TeamResult

    def get_initial(self):
        initial = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tournament"] = TeamResult.objects.get(pk=self.kwargs.get("pk")).tournament
        return context

    def test_func(self):
        is_officer = Officers.objects.filter(
            year=datetime.date.today().year, angler=self.request.user.angler
        ).count()
        return is_officer != 0 or self.request.user.is_staff

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(self.request, f"{self.get_object()} Deleted!")
        return reverse_lazy("tournament-details", kwargs={"pk": self.get_object().tournament.id})


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
        stats = {
            "angler": angler.user.get_full_name(),
            "total_points": sum(r.points for r in all_results if r.angler == angler),
            "total_weight": sum(r.total_weight for r in all_results if r.angler == angler),
            "total_fish": sum(r.num_fish for r in all_results if r.angler == angler),
            "events": sum(1 for r in all_results if r.angler == angler),
        }
        results.append(stats)
    return results


def get_heavy_stringer(year=datetime.date.today().year):
    result = (
        Result.objects.filter(
            tournament__year=year, angler__user__is_active=True, total_weight__gt=Decimal("0")
        )
        .order_by("-total_weight")
        .first()
    )
    if not result:
        return []
    return [
        {
            "angler": result.angler,
            "weight": result.total_weight,
            "fish": result.num_fish,
            "tournament": result.tournament,
        },
    ]


def get_big_bass(year=datetime.date.today().year):
    result = (
        Result.objects.filter(
            tournament__year=year, angler__user__is_active=True, big_bass_weight__gte=Decimal("5.0")
        )
        .order_by("-big_bass_weight")
        .first()
    )
    if not result:
        return []
    return [
        {
            "angler": result.angler,
            "weight": result.big_bass_weight,
            "tournament": result.tournament,
        },
    ]
