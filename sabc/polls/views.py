# -*- coding: utf-8 -*-
import calendar
import datetime
from typing import Type

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Model
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import CreateView, ListView, View
from tournaments.models.lakes import Lake

from .forms import LakePollForm
from .models import LakePoll, LakeVote


class LakePollListView(
    ListView, LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin
):
    model = LakePoll
    ordering = ["-end_date"]
    paginate_by = 0
    context_object_name = "polls"


class LakePollCreateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, CreateView
):
    model = LakePoll
    form_class = LakePollForm
    success_message = "Voting Poll successfully created!"

    def test_func(self):
        return self.request.user.is_staff

    def get_initial(self):
        initial = super().get_initial()
        today = datetime.date.today()
        month_name = calendar.month_name[today.month + 1]
        initial["name"] = f"Lake Poll for: {month_name} {today.year}"
        initial["choices"] = Lake.objects.all()
        initial["description"] = f"Cast your vote for {month_name}'s Tournament Lake!"
        return initial


class LakePollView(View, LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin):
    model: Type[LakePoll] = LakePoll

    def get_results(self, poll: LakePoll):
        results = [["Lake", "Votes"]]
        for choice in poll.choices.all():
            count = LakeVote.objects.filter(poll=poll, choice=choice).count()
            if count:
                results.append([str(choice).title(), count])
        return results

    def get(self, request, pid):
        try:
            poll = LakePoll.objects.get(id=pid)
            voted = LakeVote.objects.filter(
                poll=poll, angler=request.user.angler
            ).exists()
            results = self.get_results(poll=poll)
            context = {
                "poll": poll,
                "voted": voted,
                "results": results,
                "no_results": results == [["Lake", "Votes"]],
            }
        except AttributeError:
            return redirect("login")
        return render(request, template_name="polls/poll.html", context=context)

    def post(self, request, pid):
        lake = request.POST.get("lake", "")
        poll = LakePoll.objects.get(id=pid)
        voted = LakeVote.objects.filter(poll=poll, angler=request.user.angler).exists()
        try:
            choice = Lake.objects.get(id=lake)
            if voted:
                messages.error(
                    self.request, f"ERROR: {request.user.angler} has already voted!"
                )
                return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
        except Model.DoesNotExist as err:
            msg = "" if lake else "Please select a lake!"
            messages.error(self.request, f"ERROR: {err} {msg}")
        LakeVote.objects.create(poll=poll, choice=choice, angler=request.user.angler)
        return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
