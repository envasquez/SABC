# # -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, UpdateView
from tournaments.models.results import Result

from sabc.decorators import rate_limit, user_rate_limit

from .forms import (
    AnglerRegisterForm,
    AnglerUpdateForm,
    UserRegisterForm,
    UserUpdateForm,
)
from .models import Angler, Officers

User = get_user_model()


def about(request):
    return render(request, "users/about.html", {"title": "SABC - About"})


def bylaws(request):
    return render(request, "users/bylaws.html", {"title": "SABC - Bylaws"})


def calendar(request):
    import calendar as cal
    import datetime

    from tournaments.models.calendar_events import CalendarEvent
    from tournaments.models.tournaments import Tournament

    # Get year from request or use default
    current_year = datetime.date.today().year

    requested_year = request.GET.get("year")
    if requested_year:
        try:
            display_year = int(requested_year)
        except (ValueError, TypeError):
            display_year = current_year
    else:
        # Check if current year has tournaments, otherwise use demo year
        current_year_tournaments = Tournament.objects.filter(
            event__year=current_year
        ).count()
        display_year = current_year

    # Get all events for the year with optimized queries
    tournaments = (
        Tournament.objects.select_related("lake", "event")
        .filter(event__year=display_year)
        .only(
            "id",
            "name",
            "complete",
            "lake__name",
            "event__date",
            "event__start",
            "event__finish",
        )
    )
    calendar_events = CalendarEvent.objects.filter(date__year=display_year).only(
        "date", "title", "description", "category"
    )

    # Create a lookup of events by date
    events_by_date = {}
    today = datetime.date.today()

    # Add tournaments
    for tournament in tournaments:
        date_key = tournament.event.date.strftime("%Y-%m-%d")
        if date_key not in events_by_date:
            events_by_date[date_key] = []
        events_by_date[date_key].append(
            {
                "type": "tournament",
                "title": tournament.name,
                "description": f"Tournament at {tournament.lake or 'TBD'}",
            }
        )
        # Also add meeting
        events_by_date[date_key].append(
            {
                "type": "meeting",
                "title": "Club Meeting",
                "description": "Club meeting after tournament",
            }
        )

    # Add calendar events
    for event in calendar_events:
        date_key = event.date.strftime("%Y-%m-%d")
        if date_key not in events_by_date:
            events_by_date[date_key] = []
        events_by_date[date_key].append(
            {
                "type": event.category,
                "title": event.title,
                "description": event.description or event.title,
            }
        )

    # Generate 12 months of calendar data
    months_data = []
    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    for month_num in range(1, 13):
        # Get calendar for this month
        month_cal = cal.monthcalendar(display_year, month_num)

        days = []

        # Add days from the calendar grid
        for week in month_cal:
            for day in week:
                if day == 0:
                    # Previous/next month day - just show empty for simplicity
                    days.append(
                        {
                            "number": "",
                            "other_month": True,
                            "is_today": False,
                            "event_type": None,
                            "tooltip": None,
                        }
                    )
                else:
                    # Current month day
                    day_date = datetime.date(display_year, month_num, day)
                    date_key = day_date.strftime("%Y-%m-%d")

                    # Check for events on this day
                    day_events = events_by_date.get(date_key, [])
                    event_type = None
                    tooltip = None

                    if day_events:
                        # Prioritize event types: tournament > holiday > external > meeting
                        if any(e["type"] == "tournament" for e in day_events):
                            event_type = "tournament"
                        elif any(e["type"] == "holiday" for e in day_events):
                            event_type = "holiday"
                        elif any(e["type"] == "external" for e in day_events):
                            event_type = "external"
                        elif any(e["type"] == "meeting" for e in day_events):
                            event_type = "meeting"

                        # Create tooltip with all events
                        tooltip = " | ".join([e["title"] for e in day_events])

                    days.append(
                        {
                            "number": day,
                            "other_month": False,
                            "is_today": day_date == today,
                            "event_type": event_type,
                            "tooltip": tooltip,
                        }
                    )

        months_data.append({"name": month_names[month_num - 1], "days": days})

    context = {
        "title": "SABC - Calendar",
        "display_year": display_year,
        "current_year": current_year,
        "months_data": months_data,
    }

    return render(request, "users/calendar.html", context)


def calendar_image(request):
    """Generate and serve calendar as an image"""
    import datetime

    from django.http import HttpResponse
    from tournaments.models.tournaments import Tournament

    from .calendar_image import calendar_image_to_bytes, generate_calendar_image

    # Get year from request or use default
    current_year = datetime.date.today().year

    requested_year = request.GET.get("year")
    if requested_year:
        try:
            display_year = int(requested_year)
        except (ValueError, TypeError):
            display_year = current_year
    else:
        # Check if current year has tournaments, otherwise use demo year
        current_year_tournaments = Tournament.objects.filter(
            event__year=current_year
        ).count()
        display_year = current_year

    # Get only tournaments for the year
    tournaments = Tournament.objects.filter(event__year=display_year)

    # Create a lookup of tournament events by date
    events_by_date = {}

    # Add only tournaments
    for tournament in tournaments:
        date_key = tournament.event.date.strftime("%Y-%m-%d")
        if date_key not in events_by_date:
            events_by_date[date_key] = []
        events_by_date[date_key].append(
            {
                "type": "tournament",
                "title": tournament.name,
                "description": f"Tournament at {tournament.lake or 'TBD'}",
            }
        )

    # Generate the calendar image
    img = generate_calendar_image(display_year, events_by_date)
    img_bytes = calendar_image_to_bytes(img)

    # Return as HTTP response
    response = HttpResponse(img_bytes, content_type="image/png")
    response["Cache-Control"] = "max-age=3600"  # Cache for 1 hour
    return response


@login_required
def roster(request):
    # Filter officers with complete names
    officers = Officers.objects.select_related('angler__user').filter(
        year=datetime.date.today().year
    ).exclude(
        angler__user__first_name="", angler__user__last_name=""
    )

    # Filter members with complete names
    members = Angler.members.get_active_members().select_related('user').exclude(
        user__first_name="", user__last_name=""
    )

    # Filter guests with complete names
    guests = (
        Angler.objects.select_related('user').filter(member=False)
        .exclude(user__first_name="", user__last_name="")
        .exclude(user__username="sabc")
    )
    
    return render(
        request,
        "users/roster_list.html",
        {
            "title": "Members",
            "roster_name": f"{datetime.date.today().year} Members",
            "officers": officers,
            "members": members,
            "guests": guests,
        },
    )


@method_decorator(
    rate_limit(requests=3, window=600), name="post"
)  # 3 registrations per 10 minutes
class AnglerRegistrationView(CreateView, SuccessMessageMixin):
    model = Angler
    template_name = "users/register.html"

    def get(self, request, *args, **kwargs):
        user_form = UserRegisterForm()
        angler_form = AnglerRegisterForm()
        return render(
            request,
            self.template_name,
            {"u_form": user_form, "form": angler_form},
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
            {"u_form": user_form, "form": angler_form},
        )


@method_decorator(
    user_rate_limit(requests=10, window=300), name="post"
)  # 10 profile updates per 5 minutes
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
            {"form": {"user": user_form, "angler": angler_form}, "object": self.object},
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user_form = UserUpdateForm(request.POST, instance=self.object.user)
        angler_form = AnglerUpdateForm(request.POST, request.FILES, instance=self.object)

        if user_form.is_valid() and angler_form.is_valid():
            user_form.save()
            angler_form.save()
            return redirect(self.get_success_url())

        return render(
            request,
            self.template_name,
            {"form": {"user": user_form, "angler": angler_form}, "object": self.object},
        )

    def get_success_url(self):
        return reverse_lazy("profile", kwargs={"pk": self.kwargs.get("pk")})


class AnglerDetailView(DetailView):
    model = Angler
    template_name = "users/profile.html"

    def get_object(self, queryset=None):
        user_pk = self.kwargs.get("pk")
        return Angler.objects.get(user_id=user_pk)

    def get_biggest_bass(self, year=0):
        year = year or datetime.date.today().year
        angler = self.get_object()
        big_bass = [
            r.big_bass_weight
            for r in Result.objects.filter(
                tournament__event__year=year,
                angler=angler,
                big_bass_weight__gte=Decimal("5"),
            )
        ]
        if big_bass:
            biggest_bass = max(big_bass)
            return f"{biggest_bass:.2f}"
        return "0.00"

    def get_stats(self, year=0):
        year = year or datetime.date.today().year
        angler = self.get_object()
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
        angler = self.get_object()
        officer = Officers.objects.filter(
            angler=angler,
            year=datetime.date.today().year,
        )
        if officer:
            context["officer_pos"] = officer.first().position.title()

        context["can_edit"] = False
        if angler.user.id == self.request.user.id:
            context["can_edit"] = True
        return context
