# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal
from typing import Type

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from ..forms import TournamentForm
from ..models.events import Events, get_next_event
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
    model: Type[Tournament] = Tournament
    form_class: Type[TournamentForm] = TournamentForm
    success_message: str = "Tournament successfully created!"

    def get_initial(self) -> dict:
        today: datetime.date = datetime.date.today()
        initial: dict = super().get_initial()
        initial["rules"] = RuleSet.objects.filter(year=today.year).first()
        initial["payout_multiplier"] = PayOutMultipliers.objects.filter(year=today.year).first()

        event: Events | None = get_next_event(event_type="tournament", today=today)
        initial["event"] = event
        initial["name"] = f"{event.month} {event.year} Event #{event.date.month}" if event else None
        return initial

    def test_func(self):
        return self.request.user.is_staff


class TournamentListView(ListView):
    model: Type[Tournament] = Tournament
    ordering: list = ["-event__date"]  # Newest tournament first
    paginate_by: int = 3
    template_name: str = "users/index.html"
    context_object_name: str = "tournaments"

    def get_context_data(self, **kwargs: dict) -> dict:
        context: dict = super().get_context_data(**kwargs)
        context["index_html"] = True
        today: datetime.date = datetime.date.today()
        next_meeting: Events | None = get_next_event(event_type="meeting", today=today)
        context["next_meeting"] = next_meeting.as_html() if next_meeting else "N/A"
        next_tournament: Events | None = get_next_event(event_type="tournament", today=today)
        context["next_tournament"] = next_tournament.as_html() if next_tournament else "N/A"
        return context


class TournamentDetailView(DetailView):
    model: Type[Tournament] = Tournament
    context_object_name: str = "tournament"

    def get_payout_table(self, tid: int) -> PayoutSummary:
        payouts: dict = get_payouts(tid=tid)
        for key, val in payouts.items():
            payouts[key] = f"${val:.2f}"
        return PayoutSummary([payouts])

    def get_stats_table(self, tid: int) -> TournamentSummaryTable:
        tournament: Tournament = Tournament.objects.get(pk=tid)
        if not tournament.complete:
            return TournamentSummaryTable([])

        limits: int = Result.objects.filter(tournament=tid, num_fish=5).count()
        zeroes: int = Result.objects.filter(tournament=tid, num_fish=0, buy_in=False).count()
        buy_ins: int = Result.objects.filter(tournament=tid, buy_in=True).count()
        anglers: int = Result.objects.filter(tournament=tid, buy_in=False).count()

        bb_result: Result | None = get_big_bass_winner(tid=tid)
        big_bass: str = "--"
        if bb_result:
            big_bass = f"{bb_result.big_bass_weight: .2f}lbs"

        heavy_stringer: str = "--"
        hs_result: Result | None = Result.objects.filter(tournament=tid, place_finish=1).first()
        if hs_result:
            heavy_stringer = f"{hs_result.total_weight}lbs"

        total_fish: int = 0
        total_weight: Decimal = Decimal("0")
        for result in Result.objects.filter(tournament=tid, num_fish__gt=0):
            total_fish += result.num_fish
            total_weight += result.total_weight

        data: dict = {
            "limits": limits,
            "zeros": zeroes,
            "anglers": anglers,
            "buy_ins": buy_ins,
            "total_fish": total_fish,
            "total_weight": f"{total_weight: .2f}lbs",
            "big_bass": big_bass,
            "heavy_stringer": heavy_stringer,
        }

        return TournamentSummaryTable([data])

    def get_context_data(self, **kwargs: dict) -> dict:
        context: dict = super().get_context_data(**kwargs)
        tid: int = self.kwargs.get("pk")
        tmnt: Tournament = Tournament.objects.get(pk=tid)
        set_places(tid=tid)
        if tmnt.points_count:
            set_points(tid=tid)

        team_results: QuerySet[TeamResult] = TeamResult.objects.filter(tournament=tid).order_by(
            "place_finish", "-total_weight", "-num_fish"
        )
        context["team_results"] = TeamResultTable(team_results)
        context["editable_team_results"] = EditableTeamResultTable(team_results)

        indv_results: QuerySet[Result] = Result.objects.filter(
            tournament=tid, buy_in=False, disqualified=False
        ).order_by("place_finish", "-total_weight", "-num_fish")
        context["results"] = ResultTable(indv_results)
        context["editable_results"] = EditableResultTable(indv_results)

        buy_ins: QuerySet[Result] = Result.objects.filter(tournament=tmnt, buy_in=True)
        context["buy_ins"] = BuyInTable(buy_ins)
        context["render_buy_ins"] = buy_ins.count()
        context["editable_buy_ins"] = EditableBuyInTable(buy_ins)

        dqs: QuerySet[Result] = Result.objects.filter(tournament=tmnt, disqualified=True)
        context["dqs"] = DQTable(dqs)
        context["render_dqs"] = dqs.count()
        context["editable_dqs"] = EditableDQTable(dqs)

        context["payouts"] = self.get_payout_table(tid=tid)
        context["catch_stats"] = self.get_stats_table(tid=tid) if indv_results else TournamentSummaryTable([])
        return context


class TournamentUpdateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model: Type[Tournament] = Tournament
    form_class: Type[TournamentForm] = TournamentForm

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def get_success_url(self) -> str:
        return reverse_lazy("tournament-details", kwargs={"pk": self.kwargs.get("pk")})


class TournamentDeleteView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):  # type: ignore
    model: Type[Tournament] = Tournament

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def get_queryset(self) -> QuerySet[Tournament]:
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self) -> str:
        messages.success(self.request, f"{self.get_object().name} Deleted!")
        return reverse_lazy("sabc-home")

    def delete(self, request: HttpRequest, *args: list, **kwargs: dict) -> HttpResponse:
        messages.success(request, self.success_message)
        return super().delete(request, *args, **kwargs)
