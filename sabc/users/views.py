# -*- coding: utf-8 -*-
# Using pylint at a file level, since it does not like django models (objects.foo())

import datetime

from random import randint

from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect

from . import (
    CLUB_GUEST,
    CLUB_MEMBER,
    CLUB_OFFICER,
    CLUB_PRESIDENT,
    CLUB_VICE_PRESIDENT,
    CLUB_SECRETARY,
    CLUB_TREASURER,
    CLUB_TECHNOLOGY,
    CLUB_TOURNAMENT_DIRECTOR,
    CLUB_ASSISTANT_TOURNAMENT_DIRECTOR,
)
from .forms import UserRegisterForm, AnglerRegisterForm, UserUpdateForm, AnglerUpdateForm
from .models import Angler
from .tables import OfficerTable, MemberTable, GuestTable


def about(request):
    """About page"""
    return render(request, "users/about.html", {"title": "SABC - About"})


def bylaws(request):
    """Bylaws page"""
    return render(request, "users/bylaws.html", {"title": "SABC - Bylaws"})


def calendar(request):
    """Calendar page"""
    return render(request, "users/calendar.html", {"title": "SABC - Calendar"})


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


@login_required
def profile(request):
    """Angler/Account settings"""
    if request.method == "POST":
        u_form = UserUpdateForm(request.POST, instance=request.user)
        a_form = AnglerUpdateForm(request.POST, request.FILES, instance=request.user.angler)
        if u_form.is_valid():
            u_form.save()
            a_form.save()
            messages.success(request, "Your profile has been updated!")
            return redirect("profile")
    else:
        u_form = UserUpdateForm(instance=request.user)
        a_form = AnglerUpdateForm(instance=request.user.angler)

    context = {"title": "Angler Profile", "u_form": u_form, "a_form": a_form}

    return render(request, "users/profile.html", context)


@login_required
def roster(request):
    """Officers roster page"""
    o_table = OfficerTable(Angler.officers.get())
    m_table = MemberTable(Angler.members.get_active_members())
    g_table = GuestTable(
        Angler.objects.filter(~Q(user__username="test_guest"), type="guest")
        .exclude(user__first_name="")
        .exclude(user__last_name="")
    )
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


#
# Site-admin Functions
#
# def create_angler(member_type=CLUB_GUEST, officer_type=None):
#     """Creates an angler with random data (for testing)"""
#     first_name = get_first_name()
#     last_name = get_last_name()
#     email = f"{first_name}.{last_name}@gmail.com"
#     user = User.objects.create(
#         username=first_name[0].lower() + last_name.lower(),
#         first_name=first_name,
#         last_name=last_name,
#         email=email,
#     )
#     angler = Angler.objects.get(user=user)
#     if officer_type:
#         angler.officer_type = officer_type
#     angler.phone_number = f"+{randint(10000000000, 99999999999)}"
#     angler.type = member_type
#     angler.private_info = (True, False)[randint(0, 1)]
#     angler.save()
# @login_required
# def gen_officers(request):
#     """Creates One of every officer type"""
#     officers = [
#         CLUB_PRESIDENT,
#         CLUB_VICE_PRESIDENT,
#         CLUB_SECRETARY,
#         CLUB_TREASURER,
#         CLUB_TECHNOLOGY,
#         CLUB_TOURNAMENT_DIRECTOR,
#         CLUB_ASSISTANT_TOURNAMENT_DIRECTOR,
#     ]
#     for officer_type in officers:
#         try:
#             Angler.objects.get(officer_type=officer_type)
#         except Angler.DoesNotExist:
#             create_angler(member_type=CLUB_OFFICER, officer_type=officer_type)
#     return list_officers(request)
# @login_required
# def gen_member(request):
#     """Creates member angler"""
#     create_angler(member_type=CLUB_MEMBER)
#     return list_members(request)
# @login_required
# def gen_guest(request):
#     """Creates guest angler"""
#     create_angler(member_type=CLUB_GUEST)
#     return list_guests(request)
