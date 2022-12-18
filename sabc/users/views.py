# -*- coding: utf-8 -*-
import datetime

from decimal import Decimal

from humanize import number

from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect
from django.views.generic import UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required

from tournaments.views import get_aoy_results
from tournaments.models import Result

from .forms import UserRegisterForm, AnglerRegisterForm, AnglerUserMultiUpdateForm
from .models import Angler
from .tables import OfficerTable, MemberTable, GuestTable


def about(request):
    return render(request, "users/about.html", {"title": "SABC - About"})


def bylaws(request):
    return render(request, "users/bylaws.html", {"title": "SABC - Bylaws"})


def calendar(request):
    return render(request, "users/calendar.html", {"title": "SABC - Calendar"})


@login_required
def roster(request):
    o_table = OfficerTable(Angler.officers.get())
    m_table = MemberTable(Angler.members.get_active_members())
    guests = (
        Angler.objects.filter(~Q(user__username="test_guest"), type="guest")
        .exclude(user__first_name="")
        .exclude(user__last_name="")
    )
    g_table = GuestTable(guests) if guests else None
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


def register(request):
    """User registration/validation"""
    if request.method == "POST":
        u_form = UserRegisterForm(request.POST)
        a_form = AnglerRegisterForm(request.POST)
        if u_form.is_valid():
            u_form.save()
            messages.success(
                request,
                f"Account created for {u_form.cleaned_data.get('username')}, you can now login",
            )
            return redirect("login")
    else:
        u_form = UserRegisterForm()
        a_form = AnglerRegisterForm()

    context = {
        "title": "Angler Registration",
        "u_form": u_form,
        "a_form": a_form,
        "form_name": "Angler Registration",
    }

    return render(request, "users/register.html", context)


class AnglerEditView(UpdateView, LoginRequiredMixin, SuccessMessageMixin):
    model = Angler
    form_class = AnglerUserMultiUpdateForm
    template_name = "users/edit_profile.html"
    context_object_name = "angler"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(instance={"user": self.object.user, "angler": self.object})
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial["dataset_request"] = Angler.objects.get(user=self.request.user)
        return initial

    def get_queryset(self):
        return super().get_queryset().filter(user=self.kwargs.get("pk"))

    def get_success_url(self):
        return reverse_lazy("profile", kwargs={"pk": self.kwargs.get("pk")})


class AnglerDetailView(DetailView):
    model = Angler
    template_name = "users/profile.html"
    context_object_name = "angler"

    def get_object(self):
        return self.request.user

    def get_num_wins(self, year=None):
        year = year or datetime.date.today().year
        return Result.objects.filter(
            tournament__year=year, angler__user=self.get_object(), place_finish=1
        ).count()

    def get_biggest_bass(self, year=None):
        year = year or datetime.date.today().year
        big_bass = Result.objects.filter(
            tournament__year=year, angler__user=self.get_object(), big_bass_weight__gte=Decimal("5")
        )
        if big_bass:
            biggest_bass = max(big_bass)
            return f"{biggest_bass:.2f}"
        return "0.00"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["year"] = datetime.date.today().year
        results = get_aoy_results(context["year"], self.get_object().get_full_name())
        context["wins"] = self.get_num_wins()
        context["points"] = results["total_points"]
        context["num_fish"] = results["total_fish"]
        context["total_wt"] = results["total_weight"]
        context["big_bass"] = self.get_biggest_bass()
        context["num_events"] = results["events"]

        context["can_edit"] = False
        if self.get_object().id == self.kwargs.get("pk"):
            context["can_edit"] = True
        return context
