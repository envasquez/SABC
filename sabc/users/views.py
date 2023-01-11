# -*- coding: utf-8 -*-
from typing import Any, Type, Optional

import datetime

from decimal import Decimal

from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy
from django.db.models import QuerySet
from django.shortcuts import render, redirect
from django.views.generic import CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required

from tournaments.models.results import Result

from .forms import AnglerUserMultiRegisterForm, AnglerUserMultiUpdateForm
from .models import Angler, Officers
from .tables import OfficerTable, MemberTable, GuestTable


def about(request: Type[HttpRequest]) -> Type[HttpResponse]:
    return render(request, "users/about.html", {"title": "SABC - About"})


def bylaws(request: Type[HttpRequest]) -> Type[HttpResponse]:
    return render(request, "users/bylaws.html", {"title": "SABC - Bylaws"})


def calendar(request: Type[HttpRequest]) -> Type[HttpResponse]:
    return render(request, "users/calendar.html", {"title": "SABC - Calendar"})


@login_required
def roster(request: Type[HttpRequest]) -> Type[HttpResponse]:
    guests: Type[QuerySet] = Angler.objects.filter(type="guest")
    g_table: Type[GuestTable] = GuestTable(guests) if guests else GuestTable([])
    m_table: Type[MemberTable] = MemberTable(Angler.members.get_active_members())
    o_table: Type[OfficerTable] = OfficerTable(
        Officers.objects.filter(year=datetime.date.today().year)
    )
    context: dict = {
        "title": "Members",
        "roster_name": f"{datetime.date.today().year} Members",
        "o_table": o_table,
        "m_table": m_table,
        "g_table": g_table,
    }
    return render(request, "users/roster_list.html", context=context)


class AnglerRegistrationView(CreateView, SuccessMessageMixin):
    model: Type[Angler] = Angler
    form_class: Type[AnglerUserMultiRegisterForm] = AnglerUserMultiRegisterForm
    template_name: str = "users/register.html"

    def form_valid(self, form: dict) -> Type[HttpResponse]:
        user = form["user"].save()
        angler = form["angler"].save(commit=False)
        angler.user = user
        angler.save()
        return redirect("login")


class AnglerEditView(UpdateView, LoginRequiredMixin, SuccessMessageMixin):
    model: Type[Angler] = Angler
    form_class: Type[AnglerUserMultiUpdateForm] = AnglerUserMultiUpdateForm
    template_name: str = "users/edit_profile.html"

    def get_form_kwargs(self) -> Optional[dict[Any, Any]]:
        kwargs: dict = super().get_form_kwargs()
        return kwargs.update(instance={"user": self.object.user, "angler": self.object})

    def get_initial(self) -> dict:
        initial: dict = super().get_initial()
        initial["dataset_request"] = Angler.objects.get(user=self.request.user)
        return initial

    def get_queryset(self) -> Type[QuerySet]:
        return super().get_queryset().filter(user=self.kwargs.get("pk"))

    def get_success_url(self):
        return reverse_lazy("profile", kwargs={"pk": self.kwargs.get("pk")})


class AnglerDetailView(DetailView):
    model = Type[Angler]
    template_name = "users/profile.html"

    def get_object(self):
        return self.request.user

    def get_biggest_bass(self, year: int = 0) -> str:
        year = year or datetime.date.today().year
        bb_result: Type[QuerySet] = (
            Result.objects.filter(
                tournament__year=year,
                angler__user=self.get_object(),
                big_bass_weight__gte=Decimal("5"),
            )
            .order_by("-big_bass_weight")
            .first()
        )
        if bb_result:
            return f"{bb_result.big_bass_weight:.2f}"
        return "0.00"

    def get_stats(self, year: int = 0) -> dict[Any, Any]:
        year = year or datetime.date.today().year
        angler: Type[Angler] = Angler.objects.get(user=self.get_object().id)
        results: Type[QuerySet] = Result.objects.filter(angler=angler, tournament__year=year)
        return {
            "wins": sum(1 for r in results),
            "angler": angler.user.get_full_name(),
            "events": results.count(),
            "total_fish": sum(r.num_fish for r in results),
            "total_points": sum(r.points for r in results),
            "total_weight": sum(r.total_weight for r in results),
        }

    def get_context_data(self, **kwargs: dict[Any, Any]) -> dict[Any, Any]:
        context: dict = super().get_context_data(**kwargs)
        context["year"] = datetime.date.today().year
        results: dict = self.get_stats(context["year"])
        context["wins"] = results.get("wins")
        context["points"] = results.get("total_points", 0)
        context["num_fish"] = results.get("total_fish", 0)
        context["total_wt"] = results.get("total_weight", Decimal("0"))
        context["big_bass"] = self.get_biggest_bass()
        context["num_events"] = results.get("events", 0)

        context["officer_pos"] = None
        officer = Officers.objects.filter(angler__user=self.request.user)
        if officer:
            context["officer_pos"] = officer.position.title()

        context["can_edit"] = False
        if self.get_object().id == self.kwargs.get("pk"):
            context["can_edit"] = True
        return context
