# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from random import randint

from names import get_first_name, get_last_name

from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from . import (
    CLUB_GUEST,
    CLUB_MEMBER,
    CLUB_OFFICER,
    SITE_ADMIN,
    CLUB_PRESIDENT,
    CLUB_VICE_PRESIDENT,
    CLUB_SECRETARY,
    CLUB_TREASURER,
    CLUB_TOURNAMENT_DIRECTOR,
    CLUB_SOCIAL_MEDIA,
    CLUB_ASSISTANT_TOURNAMENT_DIRECTOR,
)

from .models import Angler

from .forms import UserRegisterForm, UserUpdateForm, AnglerUpdateForm


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
            messages.success(
                request,
                "Account created for %s, you can now login"
                % form.cleaned_data.get("username"),
            )
            return redirect("login")
    else:
        form = UserRegisterForm()

    return render(
        request, "users/register.html", {"title": "SABC - Registration", "form": form}
    )


@login_required
def profile(request):
    """Angler/Account settings"""
    profile = Angler.objects.get_or_create(user=request.user)
    if request.method == "POST":
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = AnglerUpdateForm(
            request.POST, request.FILES, instance=request.user.angler
        )
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Your profile has been updated!")

            return redirect("profile")
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = AnglerUpdateForm(instance=request.user.angler)

    return render(
        request,
        "users/profile.html",
        {"title": "Angler Profile", "u_form": u_form, "p_form": p_form},
    )


@login_required
def roster(request):
    """Roster page"""
    guests = Angler.objects.filter(type="guest")
    members = Angler.objects.filter(type="member")
    officers = Angler.objects.filter(type="officer")

    return render(
        request,
        "users/roster.html",
        {
            "title": "SABC - Roster",
            "guests": guests,
            "members": members,
            "officers": officers,
        },
    )


def create_angler(member_type=CLUB_GUEST, officer_type=SITE_ADMIN):
    """Creates an angler"""
    first_name = get_first_name()
    last_name = get_last_name()
    email = f"{first_name}.{last_name}@gmail.com"
    u = User.objects.create(
        username=first_name[0].lower() + last_name.lower(),
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    a = Angler.objects.get(user=u)
    a.phone_number = "+12345678901"
    a.type = member_type
    a.officer_type = officer_type
    a.private_info = (True, False)[randint(0, 1)]
    a.save()


@login_required
def generate_all_officers(request):
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
        create_angler(member_type=CLUB_OFFICER, officer_type=officer_type)

    return roster(request)


@login_required
def generate_member(request):
    """Creates member angler"""
    create_angler(member_type=CLUB_MEMBER)
    return roster(request)


@login_required
def generate_guest(request):
    """Creates a guest angler"""
    create_angler(member_type=CLUB_GUEST)
    return roster(request)
