# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, UpdateView
from users.models import Angler

from sabc.decorators import user_rate_limit

from ..forms import ResultForm, ResultUpdateForm, TeamForm
from ..models.results import Result, TeamResult
from ..models.tournaments import Tournament
from ..services.tournament_service import (
    ResultValidationService,
    TeamResultService,
)


@method_decorator(
    user_rate_limit(requests=15, window=300), name="post"
)  # 15 result creations per 5 minutes
class ResultCreateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView
):
    """
    Create new tournament results with validation via service layer.

    Business logic validation has been extracted to ResultValidationService
    for better separation of concerns and testability.
    """

    model = Result
    form_class = ResultForm

    def get_initial(self):
        initial = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tournament"] = Tournament.objects.get(pk=self.kwargs.get("pk"))
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        tid = kwargs["initial"]["tournament"]
        exists = [r.angler for r in Result.objects.filter(tournament=tid)]
        kwargs["angler"] = Angler.objects.filter(
            user__id__in=[a.user.id for a in Angler.objects.all() if a not in exists]
        )
        return kwargs

    def form_valid(self, form):
        """Validate result using service layer before saving."""
        is_valid, error_message = ResultValidationService.validate_result(
            form.instance, is_new_result=True
        )
        if not is_valid:
            messages.error(self.request, error_message)
            return self.form_invalid(form)
        messages.success(self.request, f"Result ADDED for: {form.instance}!")
        return super().form_valid(form)


class ResultUpdateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    """Update existing tournament results with validation via service layer."""

    model = Result
    form_class = ResultUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tournament"] = Result.objects.get(pk=self.kwargs.get("pk")).tournament
        return context

    def test_func(self):
        return self.request.user.is_staff

    def get_success_url(self):
        return reverse_lazy(
            "tournament-details", kwargs={"pk": self.get_object().tournament.id}
        )

    def form_valid(self, form):
        """Validate result update using service layer before saving."""
        is_valid, error_message = ResultValidationService.validate_result(
            form.instance, is_new_result=False
        )
        if not is_valid:
            messages.error(self.request, error_message)
            return self.form_invalid(form)
        messages.success(self.request, f"Result EDITED for: {form.instance}!")
        return super().form_valid(form)


class ResultDeleteView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView
):
    model = Result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tournament"] = Result.objects.get(pk=self.kwargs.get("pk")).tournament
        return context

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(self.request, f"{self.get_object()} Deleted!")
        return reverse_lazy(
            "tournament-details", kwargs={"pk": self.get_object().tournament.id}
        )


class TeamCreateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView
):
    """
    Create team tournament results with validation via service layer.

    Business logic for team validation has been extracted to TeamResultService
    for better maintainability and testability.
    """

    model = TeamResult
    form_class = TeamForm
    template_name = "tournaments/team_form.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def get_form_kwargs(self):
        """Get available results for team formation using service layer."""
        kwargs = super().get_form_kwargs()
        tid = kwargs["initial"]["tournament"]

        # Use service to get available results
        available_results = TeamResultService.get_available_results_for_teams(tid)
        results_queryset = Result.objects.filter(
            id__in=[r.id for r in available_results]
        )

        kwargs["result_1"] = results_queryset
        kwargs["result_2"] = results_queryset
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tournament"] = Tournament.objects.get(pk=self.kwargs.get("pk"))
        return context

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        """Validate team formation using service layer before saving."""
        tid = self.get_initial()["tournament"]

        # Use service to validate team formation
        is_valid, error_message = TeamResultService.validate_team_formation(
            tid, form.instance.result_1, form.instance.result_2
        )

        if not is_valid:
            messages.error(self.request, error_message)
            return self.form_invalid(form)

        # Use service to format success message
        success_message = TeamResultService.format_team_message(
            form.instance.result_1, form.instance.result_2
        )
        messages.success(self.request, success_message)
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
        context["tournament"] = TeamResult.objects.get(
            pk=self.kwargs.get("pk")
        ).tournament
        return context

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(self.request, f"{self.get_object()} Deleted!")
        return reverse_lazy(
            "tournament-details", kwargs={"pk": self.get_object().tournament.id}
        )
