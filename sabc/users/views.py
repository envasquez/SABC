# -*- coding: utf-8 -*-
# Using pylint at a file level, since it does not like django models (objects.foo())
# pylint: disable=no-member
"""User/Angler views"""
from __future__ import unicode_literals

from random import randint

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect

from names import get_first_name, get_last_name

from . import (
    CLUB_GUEST,
    CLUB_MEMBER,
    CLUB_OFFICER,
    CLUB_PRESIDENT,
    CLUB_VICE_PRESIDENT,
    CLUB_SECRETARY,
    CLUB_TREASURER,
    CLUB_SOCIAL_MEDIA,
    CLUB_TOURNAMENT_DIRECTOR,
    CLUB_ASSISTANT_TOURNAMENT_DIRECTOR,
)

from .forms import UserRegisterForm, UserUpdateForm, AnglerUpdateForm
from .models import Angler
from .tables import OfficerTable, MemberTable, GuestTable


def about(request):
    """About page"""
    return render(request, "users/about.html", {"title": "SABC - About"})


def bylaws(request):
    """Bylaws page"""
    return render(request, "users/bylaws.html", {"title": "SABC - Bylaws"})


def gallery(request):
    """Gallery page"""
    return render(request, "users/gallery.html", {"title": "SABC - Gallery"})


def calendar(request):
    """Calendar page"""
    return render(request, "users/calendar.html", {"title": "SABC - Calendar"})


def register(request):
    """User registration/validation"""
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            clean_username = form.cleaned_data.get("username")
            messages.success(request, f"Account created for {clean_username}, you can now login")
            return redirect("login")
    else:
        form = UserRegisterForm()

    context = {"title": "SABC - Registration", "form": form, "form_name": "Member Registration"}

    return render(request, "users/register.html", context)


@login_required
def profile(request):
    """Angler/Account settings"""
    angler = Angler.objects.get(user=request.user)
    if request.method == "POST":
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = AnglerUpdateForm(request.POST, request.FILES, instance=request.user.angler)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Your profile has been updated!")
            return redirect("profile")
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = AnglerUpdateForm(instance=request.user.angler)

    context = {"title": "Angler Profile", "u_form": u_form, "p_form": p_form}

    return render(request, "users/profile.html", context)


@login_required
def list_officers(request):
    """Officers roster page"""
    table = OfficerTable(Angler.objects.filter(type="officer"))
    return render(
        request,
        "users/roster_list.html",
        {
            "title": "SABC - Officers",
            "roster_name": "Current Officers",
            "table": table,
        },
    )


@login_required
def list_members(request):
    """Members roster page"""
    table = MemberTable(Angler.objects.filter(type__in=["member", "officer"]))
    table.order_by = "date_joined"
    return render(
        request,
        "users/roster_list.html",
        {
            "title": "SABC - Members",
            "roster_name": f"Active Members",
            "table": table,
        },
    )


@login_required
def list_guests(request):
    """Members roster page"""
    table = GuestTable(
        Angler.objects.filter(type="guest").exclude(user__first_name="").exclude(user__last_name="")
    )
    return render(
        request,
        "users/roster_list.html",
        {
            "title": "SABC - Past Guests",
            "roster_name": "Past Guests",
            "table": table,
        },
    )


#
# Site-admin Functions
#
def create_angler(member_type=CLUB_GUEST, officer_type=None):
    """Creates an angler"""
    first_name = get_first_name()
    last_name = get_last_name()
    email = f"{first_name}.{last_name}@gmail.com"
    user = User.objects.create(
        username=first_name[0].lower() + last_name.lower(),
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    angler = Angler.objects.get(user=user)
    if officer_type:
        angler.officer_type = officer_type
    angler.phone_number = f"+{randint(10000000000, 99999999999)}"
    angler.type = member_type
    angler.private_info = (True, False)[randint(0, 1)]
    angler.save()


@login_required
def gen_officers(request):
    """Creates One of every officer type"""
    officers = [
        CLUB_PRESIDENT,
        CLUB_VICE_PRESIDENT,
        CLUB_SECRETARY,
        CLUB_TREASURER,
        CLUB_TOURNAMENT_DIRECTOR,
        CLUB_SOCIAL_MEDIA,
        CLUB_ASSISTANT_TOURNAMENT_DIRECTOR,
    ]
    for officer_type in officers:
        try:
            Angler.objects.get(officer_type=officer_type)
        except Angler.DoesNotExist:
            create_angler(member_type=CLUB_OFFICER, officer_type=officer_type)

    return list_officers(request)


@login_required
def gen_member(request):
    """Creates member angler"""
    create_angler(member_type=CLUB_MEMBER)
    return list_members(request)


@login_required
def gen_guest(request):
    """Creates guest angler"""
    create_angler(member_type=CLUB_GUEST)
    return list_guests(request)
