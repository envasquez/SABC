# -*- coding: utf-8 -*-
from typing import List, Type

from django.urls import reverse
from django.http import HttpResponseRedirect, HttpRequest
from django.contrib import messages
from django.db.models import Model, QuerySet
from django.shortcuts import render
from django.views.generic import View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin

from tournaments.models.lakes import Lake

from .models import LakePoll, LakeVote


class LakePollListView(ListView, LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin):
    model: Type[LakePoll] = LakePoll
    context_object_name: str = "polls"


class LakePollView(View, LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin):
    model: Type[LakePoll] = LakePoll

    def get_random_results(self, poll: Type[LakePoll]) -> List[List]:
        import random

        lakes: List[str] = ["travis", "lbj", "bastrop", "buchanan"]
        results: list = [["Lake", "Votes"]]
        for choice in poll.choices.all():
            if choice.name in lakes:
                results.append([choice.name.title(), random.randint(1, 15)])
        return results

    def get_results(self, poll: Type[LakePoll]) -> List[List]:
        results: list = [["Lake", "Votes"]]
        for choice in poll.choices.all():
            count: int = LakeVote.objects.filter(poll=poll, choice=choice).count()
            if count:
                results.append([choice.title(), count])
        return results

    def get(self, request: Type[HttpRequest], pid: int) -> Type[HttpRequest]:
        poll: Type[QuerySet] = LakePoll.objects.get(id=pid)
        voted: bool = LakeVote.objects.filter(poll=poll, angler=request.user.angler).exists()
        context: dict = {
            "poll": poll,
            "results": self.get_random_results(poll=poll),  # TODO: REMOVE THIS AFTER 2nd DEMO!
            "voted": voted,
        }
        return render(request, template_name="polls/poll.html", context=context)

    def post(self, request: Type[HttpRequest], pid: int) -> Type[HttpResponseRedirect]:
        poll: Type[LakePoll] = LakePoll.objects.get(id=pid)
        lake: str = request.POST.get("lake")
        voted: bool = LakeVote.objects.filter(poll=poll, angler=request.user.angler).exists()
        try:
            choice: Type[Lake] = Lake.objects.get(id=lake)
            if voted:
                messages.error(self.request, f"ERROR: {request.user.angler} has already voted!")
                return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
        except Model.DoesNotExist as err:
            msg: str = "" if lake else "Please select a lake!"
            messages.error(self.request, f"ERROR: {err} {msg}")
        LakeVote.objects.create(poll=poll, choice=choice, angler=request.user.angler)
        return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
