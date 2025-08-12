# -*- coding: utf-8 -*-
import datetime

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
from ..models.tournaments import Tournament, set_places, set_points
from ..services.tournament_service import TournamentService
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
    """Create new tournaments with rate limiting and staff-only access."""

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
    """Display paginated list of tournaments with upcoming event information."""

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
        
        # Add poll data for upcoming tournaments
        from polls.models import LakePoll, LakeVote
        
        for tournament in context['tournaments']:
            if not tournament.complete and not tournament.lake:
                # Find active poll for this tournament's month
                month_year = tournament.event.date.strftime("%B %Y")
                
                # Try to find a poll that matches this tournament's timeframe
                matching_polls = LakePoll.objects.filter(
                    name__icontains=month_year[:3],  # Match month abbreviation
                    complete=False
                ).first()
                
                if not matching_polls:
                    # Try to find any active poll
                    matching_polls = LakePoll.objects.filter(
                        complete=False,
                        end_date__gte=datetime.date.today()
                    ).first()
                
                if matching_polls:
                    # Get poll results
                    poll_results = {}
                    for choice in matching_polls.choices.all():
                        count = LakeVote.objects.filter(poll=matching_polls, choice=choice).count()
                        if count > 0:  # Only include lakes with votes
                            poll_results[choice.name] = count
                    
                    tournament.poll_results = poll_results
                    tournament.has_poll = bool(poll_results)
                    tournament.poll_name = matching_polls.name
                else:
                    tournament.has_poll = False
                    tournament.poll_results = {}
        
        return context


class TournamentDetailView(DetailView):
    """
    Display detailed view of a tournament including results, statistics, and payouts.

    Business logic has been extracted to TournamentService for better maintainability.
    """

    model = Tournament
    context_object_name = "tournament"

    def get_context_data(self, **kwargs):
        """Prepare context data using service layer for business logic."""
        context = super().get_context_data(**kwargs)
        tid = self.kwargs.get("pk")

        # Use service to get optimized tournament data
        tmnt = TournamentService.get_optimized_tournament_data(tid)

        # Update tournament places and points
        set_places(tid=tid)
        if tmnt.points_count:
            set_points(tid=tid)

        # Get all results in one query
        all_results = list(tmnt.result_set.select_related("angler__user").all())

        # Use service to filter and sort results
        indv_results, buy_ins, dqs = TournamentService.filter_and_sort_results(
            all_results
        )

        # Get team results using service
        team_results = TournamentService.get_team_results_data(tmnt)

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

        # Use service for payouts and statistics
        formatted_payouts = TournamentService.get_formatted_payouts(tid)
        context["payouts"] = PayoutSummary([formatted_payouts])

        tournament_stats = TournamentService.calculate_tournament_statistics(
            tmnt, all_results
        )
        context["catch_stats"] = (
            TournamentSummaryTable([tournament_stats])
            if indv_results and tournament_stats
            else TournamentSummaryTable([])
        )

        # Set primary results based on tournament type
        context["is_team_tournament"] = tmnt.team
        context["render_team_results"] = len(team_results) > 0

        return context


class TournamentUpdateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    """Update existing tournaments with staff-only access."""

    model = Tournament
    form_class = TournamentForm

    def test_func(self):
        return self.request.user.is_staff

    def get_success_url(self):
        return reverse_lazy("tournament-details", kwargs={"pk": self.kwargs.get("pk")})


class TournamentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete tournaments with confirmation and staff-only access."""

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
