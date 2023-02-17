# -*- coding: utf-8 -*-
from decimal import Decimal
from typing import Type

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.shortcuts import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView
from users.models import Angler

from ..forms import ResultForm, ResultUpdateForm, TeamForm
from ..models.results import Result, TeamResult
from ..models.tournaments import Tournament


class ResultCreateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView
):
    model: Type[Result] = Result
    form_class: Type[ResultForm] = ResultForm

    def get_initial(self) -> dict:
        initial: dict = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def get_context_data(self, **kwargs: dict) -> dict:
        context: dict = super().get_context_data(**kwargs)
        context["tournament"] = Tournament.objects.get(pk=self.kwargs.get("pk"))
        return context

    def get_form_kwargs(self) -> dict:
        kwargs: dict = super().get_form_kwargs()
        tid: int = kwargs["initial"]["tournament"]
        exists: list = [r.angler for r in Result.objects.filter(tournament=tid)]
        kwargs["angler"] = Angler.objects.filter(
            user__id__in=[a.user.id for a in Angler.objects.all() if a not in exists]
        )
        return kwargs

    def form_valid(self, form) -> HttpResponse:
        valid: bool
        msg: str
        valid, msg = valid_result(result=form.instance)
        if not valid:
            messages.error(self.request, msg)
            return self.form_invalid(form)
        messages.success(self.request, f"Result ADDED for: {form.instance}!")
        return super().form_valid(form)


class ResultUpdateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    model: Type[Result] = Result
    form_class: Type[ResultUpdateForm] = ResultUpdateForm

    def get_context_data(self, **kwargs: dict) -> dict:
        context: dict = super().get_context_data(**kwargs)
        context["tournament"] = Result.objects.get(pk=self.kwargs.get("pk")).tournament
        return context

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def get_success_url(self) -> str:
        return reverse_lazy(
            "tournament-details", kwargs={"pk": self.get_object().tournament.id}
        )

    def form_valid(self, form) -> HttpResponse:
        valid: bool
        msg: str
        valid, msg = valid_result(result=form.instance, new_result=False)
        if not valid:
            messages.error(self.request, msg)
            return self.form_invalid(form)
        messages.success(self.request, f"Result EDITED for: {form.instance}!")
        return super().form_valid(form)


class ResultDeleteView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):  # type: ignore
    model: Type[Result] = Result

    def get_context_data(self, **kwargs) -> dict:
        context: dict = super().get_context_data(**kwargs)
        context["tournament"] = Result.objects.get(pk=self.kwargs.get("pk")).tournament
        return context

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self) -> str:
        messages.success(self.request, f"{self.get_object()} Deleted!")
        return reverse_lazy(
            "tournament-details", kwargs={"pk": self.get_object().tournament.id}
        )


class TeamCreateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView
):
    model: Type[TeamResult] = TeamResult
    form_class: Type[TeamForm] = TeamForm
    template_name: str = "tournaments/team_form.html"

    def get_initial(self) -> dict:
        initial: dict = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def get_form_kwargs(self) -> dict:
        kwargs: dict = super().get_form_kwargs()
        tid: int = kwargs["initial"]["tournament"]
        all_results: list[Result] = list(
            Result.objects.filter(tournament=tid, buy_in=False)
        )
        team_results: list[Result] = [
            t.result_1 for t in TeamResult.objects.filter(tournament=tid)
        ]
        team_results += [
            t.result_2 for t in TeamResult.objects.filter(tournament=tid) if t.result_2
        ]

        results: QuerySet[Result] = Result.objects.filter(
            id__in=[r.id for r in all_results if r not in team_results]
        )
        kwargs["result_1"] = results
        kwargs["result_2"] = results
        return kwargs

    def get_context_data(self, **kwargs: dict) -> dict:
        context: dict = super().get_context_data(**kwargs)
        context["tournament"] = Tournament.objects.get(pk=self.kwargs.get("pk"))
        return context

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def form_valid(self, form) -> HttpResponse:
        tid: int = self.get_initial()["tournament"]
        results: QuerySet[TeamResult] = TeamResult.objects.filter(tournament=tid)
        anglers: list[Result] = [r.result_1.angler for r in results] + [
            r.result_2.angler for r in results if r.result_2
        ]
        err: str = "Team Result for %s already exists!"
        if form.instance.result_1.angler in anglers:
            messages.error(self.request, err % form.instance.result_1.angler)
            return self.form_invalid(form)
        if form.instance.result_2:
            if form.instance.result_2.angler in anglers:
                messages.error(self.request, err % form.instance.result_2.angler)
                return self.form_invalid(form)
            if form.instance.result_2.angler == form.instance.result_1.angler:
                messages.error(self.request, "Angler 2 cannot be the same as Angler 1!")
                return self.form_invalid(form)
        msg: str = f"{form.instance.result_1.angler}"
        msg += (
            f"& {form.instance.result_2.angler}"
            if form.instance.result_2
            else " - solo"
        )
        messages.success(self.request, f"Team added: {msg}")
        return super().form_valid(form)


class TeamResultDeleteView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):  # type: ignore
    model: Type[TeamResult] = TeamResult

    def get_initial(self) -> dict:
        initial: dict = super().get_initial()
        initial["tournament"] = self.kwargs.get("pk")
        return initial

    def get_context_data(self, **kwargs: dict) -> dict:
        context: dict = super().get_context_data(**kwargs)
        context["tournament"] = TeamResult.objects.get(
            pk=self.kwargs.get("pk")
        ).tournament
        return context

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self) -> str:
        messages.success(self.request, f"{self.get_object()} Deleted!")
        return reverse_lazy(
            "tournament-details", kwargs={"pk": self.get_object().tournament.id}
        )


def valid_result(result, new_result: bool = True) -> tuple[bool, str]:
    msg: str = ""
    if new_result:
        if result.angler in [
            r.angler for r in Result.objects.filter(tournament=result.tournament.id)
        ]:
            msg = f"ERROR Result exists for {result.angler} ... edit instead?"
    if result.num_fish == 0 and result.total_weight > Decimal("0"):
        msg = f"ERROR Can't have weight: {result.total_weight}lbs with {result.num_fish} fish weighed!"
    elif result.num_fish > result.tournament.rules.limit_num:
        msg = (
            f"ERROR: Number of Fish exceeds limit: {result.tournament.rules.limit_num}"
        )
    return (True, msg) if msg == "" else (False, msg)
