# -*- coding: utf-8 -*-
import datetime

from decimal import Decimal

from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic import CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required

from tournaments.models import Result

from .forms import AnglerUserMultiRegisterForm, AnglerUserMultiUpdateForm
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
        Angler.objects.filter(type="guest").exclude(user__first_name="").exclude(user__last_name="")
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


class AnglerRegistrationView(CreateView, SuccessMessageMixin):
    model = Angler
    form_class = AnglerUserMultiRegisterForm
    template_name = "users/register.html"

    def form_valid(self, form):
        user = form["user"].save()
        angler = form["angler"].save(commit=False)
        angler.user = user
        angler.save()

        return redirect("login")


class AnglerEditView(UpdateView, LoginRequiredMixin, SuccessMessageMixin):
    model = Angler
    form_class = AnglerUserMultiUpdateForm
    template_name = "users/edit_profile.html"

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

    def get_object(self):
        return self.request.user

    def get_biggest_bass(self, year=None):
        year = year or datetime.date.today().year
        big_bass = Result.objects.filter(
            tournament__year=year, angler__user=self.get_object(), big_bass_weight__gte=Decimal("5")
        )
        if big_bass:
            biggest_bass = max(big_bass)
            return f"{biggest_bass:.2f}"
        return "0.00"

    def get_stats(self, year=None):
        year = year or datetime.date.today().year
        angler = Angler.objects.get(user=self.get_object().id)
        results = Result.objects.filter(angler=angler, tournament__year=year)
        return {
            "wins": sum(1 for r in results),
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

        context["can_edit"] = False
        if self.get_object().id == self.kwargs.get("pk"):
            context["can_edit"] = True
        return context
