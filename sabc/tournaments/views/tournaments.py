# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from ..forms import TournamentForm
from ..models.events import get_next_event
from ..models.payouts import PayOutMultipliers
from ..models.results import Result, TeamResult
from ..models.rules import RuleSet
from ..models.tournaments import (
    Tournament,
    get_big_bass_winner,
    get_payouts,
    set_places,
    set_points,
)
from ..tables import (
    BuyInTable,
    DQTable,
    EditableBuyInTable,
    EditableDQTable,
    EditableResultTable,
    EditableTeamResultTable,
    PayoutSummary,
    ResultTable,
    TeamResultTable,
    TournamentSummaryTable,
)

class TournamentCreateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Tournament
    form_class = TournamentForm
    success_message = "Tournament successfully created!"

    def get_initial(self):
        initial = super().get_initial()
        initial["rules"] = RuleSet.objects.filter(year=datetime.date.today().year).first()
        initial["payout_multiplier"] = PayOutMultipliers.objects.filter(year=datetime.date.today().year).first()
        initial["event"] = get_next_event(event_type="tournament")
        return initial

    def test_func(self):
        return self.request.user.is_staff


class TournamentListView(ListView):
    model = Tournament
    ordering = ["-event__date"]  # Newest tournament first
    paginate_by = 3
    template_name = "users/index.html"
    context_object_name = "tournaments"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["index_html"] = True
        context["next_meeting"] = get_next_event(event_type="meeting")
        context["next_tournament"] = get_next_event(event_type="tournament")
        return context


class TournamentDetailView(DetailView):
    model = Tournament
    context_object_name = "tournament"

    def get_payout_table(self, tid):
        payouts = get_payouts(tid=tid)
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
        bb_result = get_big_bass_winner(tid=tid)
        heavy_stringer = "--"
        hs_result = Result.objects.filter(tournament=tid, place_finish=1)
        if hs_result:
            heavy_stringer = f"{hs_result.first().total_weight}lbs"

        total_fish = 0
        total_weight = Decimal("0")
        for result in Result.objects.filter(tournament=tid, num_fish__gt=0):
            total_fish += result.num_fish
            total_weight += result.total_weight

        big_bass: str = "--"
        if bb_result:
            big_bass = f"{bb_result.big_bass_weight: .2f}lbs"
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
        tid = self.kwargs.get("pk")
        tmnt = Tournament.objects.get(pk=tid)
        set_places(tid=tid)
        if tmnt.points_count:
            set_points(tid=tid)

        team_results = TeamResult.objects.filter(tournament=tid).order_by("place_finish")
        context["team_results"] = TeamResultTable(team_results)
        context["editable_team_results"] = EditableTeamResultTable(team_results)

        indv_results = Result.objects.filter(tournament=tid, buy_in=False, disqualified=False).order_by("place_finish")
        context["results"] = ResultTable(indv_results)
        context["editable_results"] = EditableResultTable(indv_results)

        buy_ins = Result.objects.filter(tournament=tmnt, buy_in=True)
        context["buy_ins"] = BuyInTable(buy_ins)
        context["render_buy_ins"] = buy_ins.count()
        context["editable_buy_ins"] = EditableBuyInTable(buy_ins)

        dqs = Result.objects.filter(tournament=tmnt, disqualified=True)
        context["dqs"] = DQTable(dqs)
        context["render_dqs"] = dqs.count()
        context["editable_dqs"] = EditableDQTable(dqs)

        context["payouts"] = self.get_payout_table(tid=tid)
        context["catch_stats"] = self.get_stats_table(tid=tid) if indv_results else TournamentSummaryTable([])
        return context


class TournamentUpdateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Tournament
    form_class = TournamentForm

    def test_func(self):
        return self.request.user.is_staff

    def get_success_url(self):
        return reverse_lazy("tournament-details", kwargs={"pk": self.kwargs.get("pk")})


class TournamentDeleteView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):  # type: ignore
    model = Tournament

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(self.request, f"{self.get_object().name} Deleted!")
        return reverse_lazy("sabc-home")

    def delete(self, request, *args, **kwargs):
        messages.success(request, self.success_message)
        return super().delete(request, *args, **kwargs)
