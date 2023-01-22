# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from ..forms import ResultForm, TeamForm
from ..models.results import Result, TeamResult
from ..models.tournaments import Tournament, set_places  # , set_points


class ResultCreateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView):
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

    def form_valid(self, form):
        tid = self.kwargs.get("pk")
        duplicate = form.instance.angler in [r.angler for r in Result.objects.filter(tournament=tid)]
        if duplicate:  # Don't add duplicate records!
            result: Result = Result.objects.get(tournament=tid, angler=form.instance.angler)
            messages.error(self.request, message=f"ERROR Result exists! {result}")
            return super().form_invalid(form)

        set_places(tid=tid)
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


class ResultUpdateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Result
    form_class = ResultForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tournament"] = Result.objects.get(pk=self.kwargs.get("pk")).tournament
        return context

    def test_func(self):
        return self.request.user.is_staff

    def get_success_url(self):
        return reverse_lazy("tournament-details", kwargs={"pk": self.get_object().tournament.id})


class ResultDeleteView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):  # type: ignore
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
        return self.request.user.is_staff

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


class TeamResultDeleteView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):  # type: ignore
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
        return self.request.user.is_staff

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(self.request, f"{self.get_object()} Deleted!")
        return reverse_lazy("tournament-details", kwargs={"pk": self.get_object().tournament.id})
