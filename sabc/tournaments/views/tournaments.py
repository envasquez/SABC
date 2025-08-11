# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from sabc.decorators import user_rate_limit

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


@method_decorator(
    user_rate_limit(requests=5, window=300), name="post"
)  # 5 tournament creations per 5 minutes
class TournamentCreateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView
):
    model = Tournament
    form_class = TournamentForm
    success_message = "Tournament successfully created!"

    def get_initial(self):
        today = datetime.date.today()
        initial = super().get_initial()
        initial["rules"] = RuleSet.objects.filter(year=today.year).first()
        initial["payout_multiplier"] = PayOutMultipliers.objects.filter(
            year=today.year
        ).first()

        event = get_next_event(event_type="tournament")
        initial["event"] = event
        initial["name"] = (
            f"{event.month} {event.year} Event #{event.date.month}" if event else None
        )
        return initial

    def test_func(self):
        return self.request.user.is_staff


class TournamentListView(ListView):
    model = Tournament
    ordering = ["-event__date"]  # Newest tournament first
    paginate_by = 3
    template_name = "users/index.html"
    context_object_name = "tournaments"

    def get_context_data(self, **kwargs: dict):
        context = super().get_context_data(**kwargs)
        context["index_html"] = True
        next_meeting = get_next_event(event_type="meeting")
        context["next_meeting"] = next_meeting.as_html() if next_meeting else "N/A"
        next_tournament = get_next_event(event_type="tournament")
        context["next_tournament"] = (
            next_tournament.as_html() if next_tournament else "N/A"
        )
        return context


class TournamentDetailView(DetailView):
    model = Tournament
    context_object_name = "tournament"

    def get_payout_table(self, tid):
        payouts = get_payouts(tid=tid)
        for key, val in payouts.items():
            payouts[key] = f"${val:.2f}"
        return PayoutSummary([payouts])

    def get_stats_table(self, tid, tournament=None, all_results=None):
        if tournament is None:
            tournament = Tournament.objects.get(pk=tid)
        if not tournament.complete:
            return TournamentSummaryTable([])

        # Use provided results or fetch them efficiently
        if all_results is None:
            all_results = list(
                Result.objects.filter(tournament=tid).select_related("angler__user")
            )

        # Calculate stats from in-memory data
        limits = sum(1 for r in all_results if r.num_fish == 5)
        zeroes = sum(1 for r in all_results if r.num_fish == 0 and not r.buy_in)
        buy_ins = sum(1 for r in all_results if r.buy_in)
        anglers = sum(1 for r in all_results if not r.buy_in)

        # Find big bass winner
        bb_result = None
        max_bass_weight = Decimal("0")
        for result in all_results:
            if result.big_bass_weight > max_bass_weight:
                max_bass_weight = result.big_bass_weight
                bb_result = result

        big_bass = "--"
        if bb_result and bb_result.big_bass_weight >= Decimal("5"):
            big_bass = f"{bb_result.big_bass_weight: .2f}lbs"

        # Find heavy stringer (place_finish = 1)
        heavy_stringer = "--"
        hs_result = next((r for r in all_results if r.place_finish == 1), None)
        if hs_result:
            heavy_stringer = f"{hs_result.total_weight}lbs"

        # Calculate totals
        total_fish = sum(r.num_fish for r in all_results if r.num_fish > 0)
        total_weight = sum(r.total_weight for r in all_results if r.num_fish > 0)

        data = {
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tid = self.kwargs.get("pk")

        # Use prefetch_related for efficient data loading
        tmnt = (
            Tournament.objects.select_related(
                "lake", "event", "rules", "payout_multiplier"
            )
            .prefetch_related(
                "result_set__angler__user",
                "teamresult_set__result_1__angler__user",
                "teamresult_set__result_2__angler__user",
            )
            .get(pk=tid)
        )

        set_places(tid=tid)
        if tmnt.points_count:
            set_points(tid=tid)

        # Get all results in one query and filter in Python to reduce DB hits
        all_results = list(tmnt.result_set.select_related("angler__user").all())

        # Filter results efficiently
        team_results = list(
            tmnt.teamresult_set.select_related(
                "result_1__angler__user", "result_2__angler__user"
            ).order_by("place_finish", "-total_weight", "-num_fish")
        )

        indv_results = [r for r in all_results if not r.buy_in and not r.disqualified]
        indv_results.sort(
            key=lambda x: (x.place_finish or 999, -x.total_weight, -x.num_fish)
        )

        buy_ins = [r for r in all_results if r.buy_in]
        dqs = [r for r in all_results if r.disqualified]

        # Create table objects
        context["team_results"] = TeamResultTable(team_results)
        context["editable_team_results"] = EditableTeamResultTable(team_results)
        context["results"] = ResultTable(indv_results)
        context["editable_results"] = EditableResultTable(indv_results)
        context["buy_ins"] = BuyInTable(buy_ins)
        context["render_buy_ins"] = len(buy_ins)
        context["editable_buy_ins"] = EditableBuyInTable(buy_ins)
        context["dqs"] = DQTable(dqs)
        context["render_dqs"] = len(dqs)
        context["editable_dqs"] = EditableDQTable(dqs)

        context["payouts"] = self.get_payout_table(tid=tid)
        context["catch_stats"] = (
            self.get_stats_table(tid=tid, tournament=tmnt, all_results=all_results)
            if indv_results
            else TournamentSummaryTable([])
        )

        # Set primary results based on tournament type
        context["is_team_tournament"] = tmnt.team
        context["render_team_results"] = len(team_results) > 0

        return context


class TournamentUpdateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    model = Tournament
    form_class = TournamentForm

    def test_func(self):
        return self.request.user.is_staff

    def get_success_url(self):
        return reverse_lazy("tournament-details", kwargs={"pk": self.kwargs.get("pk")})


class TournamentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Tournament

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self):
        return reverse_lazy("sabc-home")

    def form_valid(self, form):
        tournament_name = self.get_object().name
        response = super().form_valid(form)
        messages.success(self.request, f"{tournament_name} Deleted!")
        return response
