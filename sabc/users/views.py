# # -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, UpdateView
from tournaments.models.results import Result

from .forms import (
    AnglerRegisterForm,
    AnglerUpdateForm,
    UserRegisterForm,
    UserUpdateForm,
)
from .models import Angler, Officers
from .tables import GuestTable, MemberTable, OfficerTable

User = get_user_model()


def about(request):
    return render(request, "users/about.html", {"title": "SABC - About"})


def bylaws(request):
    return render(request, "users/bylaws.html", {"title": "SABC - Bylaws"})


def calendar(request):
    return render(request, "users/calendar.html", {"title": "SABC - Calendar"})


@login_required
def roster(request):
    o_table = OfficerTable(Officers.objects.filter(year=datetime.date.today().year))
    m_table = MemberTable(Angler.members.get_active_members())
    guests = (
        Angler.objects.filter(member=False)
        .exclude(user__first_name="")
        .exclude(user__last_name="")
        .exclude(user__username="sabc")
    )
    g_table = GuestTable(guests) if guests else GuestTable([])
    return render(
        request,
        "users/roster_list.html",
        {
            "title": "Members",
            "roster_name": f"{datetime.date.today().year} Members",
            "o_table": o_table,
            "m_table": m_table,
            "g_table": g_table,
        },
    )


class AnglerRegistrationView(CreateView, SuccessMessageMixin):
    model = Angler
    template_name = "users/register.html"

    def get(self, request, *args, **kwargs):
        user_form = UserRegisterForm()
        angler_form = AnglerRegisterForm()
        return render(
            request,
            self.template_name,
            {"user_form": user_form, "angler_form": angler_form},
        )

    def post(self, request, *args, **kwargs):
        user_form = UserRegisterForm(request.POST)
        angler_form = AnglerRegisterForm(request.POST)

        if user_form.is_valid() and angler_form.is_valid():
            user = user_form.save()
            angler = angler_form.save(commit=False)
            angler.user = user
            angler.save()
            return redirect("login")

        return render(
            request,
            self.template_name,
            {"user_form": user_form, "angler_form": angler_form},
        )


class AnglerUpdateView(UpdateView, LoginRequiredMixin, SuccessMessageMixin):
    model = Angler
    template_name = "users/edit_profile.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        user_form = UserUpdateForm(instance=self.object.user)
        angler_form = AnglerUpdateForm(instance=self.object)
        return render(
            request,
            self.template_name,
            {"user_form": user_form, "angler_form": angler_form, "object": self.object},
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user_form = UserUpdateForm(request.POST, instance=self.object.user)
        angler_form = AnglerUpdateForm(request.POST, instance=self.object)

        if user_form.is_valid() and angler_form.is_valid():
            user_form.save()
            angler_form.save()
            return redirect(self.get_success_url())

        return render(
            request,
            self.template_name,
            {"user_form": user_form, "angler_form": angler_form, "object": self.object},
        )

    def get_success_url(self):
        return reverse_lazy("profile", kwargs={"pk": self.kwargs.get("pk")})


class AnglerDetailView(DetailView):
    model = Angler
    template_name = "users/profile.html"

    def get_object(self, queryset=None):
        return self.request.user

    def get_biggest_bass(self, year=0):
        year = year or datetime.date.today().year
        big_bass = [
            r.big_bass_weight
            for r in Result.objects.filter(
                tournament__event__year=year,
                angler__user=self.get_object(),
                big_bass_weight__gte=Decimal("5"),
            )
        ]
        if big_bass:
            biggest_bass = max(big_bass)
            return f"{biggest_bass:.2f}"
        return "0.00"

    def get_stats(self, year=0):
        year = year or datetime.date.today().year
        angler = Angler.objects.get(user=self.get_object().id)
        results = Result.objects.filter(angler=angler, tournament__event__year=year)
        return {
            "wins": sum(1 for r in results if r.place_finish == 1),
            "angler": angler.user.get_full_name(),
            "events": results.count(),
            "total_fish": sum(r.num_fish for r in results),
            "total_points": sum(r.points for r in results),
            "total_weight": sum(r.total_weight for r in results),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["year"] = datetime.date.today().year
        results = self.get_stats(context["year"])
        context["wins"] = results.get("wins")
        context["points"] = results.get("total_points", 0)
        context["num_fish"] = results.get("total_fish", 0)
        context["total_wt"] = results.get("total_weight", Decimal("0"))
        context["big_bass"] = self.get_biggest_bass()
        context["num_events"] = results.get("events", 0)

        context["officer_pos"] = None
        officer = Officers.objects.filter(
            angler__user=self.request.user,
            year=datetime.date.today().year,
        )
        if officer:
            context["officer_pos"] = officer.first().position.title()

        context["can_edit"] = False
        if self.get_object().id == self.kwargs.get("pk"):
            context["can_edit"] = True
        return context
