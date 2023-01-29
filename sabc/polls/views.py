# -*- coding: utf-8 -*-
from typing import Type

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Model
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView, View
from tournaments.models.lakes import Lake

from .models import LakePoll, LakeVote


class LakePollListView(ListView, LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin):
    model: Type[LakePoll] = LakePoll
    context_object_name: str = "polls"


class LakePollView(View, LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin):
    model: Type[LakePoll] = LakePoll

    def get_results(self, poll: LakePoll) -> list[list]:
        results: list = [["Lake", "Votes"]]
        for choice in poll.choices.all():
            count: int = LakeVote.objects.filter(poll=poll, choice=choice).count()
            if count:
                results.append([str(choice).title(), count])
        return results

    def get(self, request: HttpRequest, pid: int) -> HttpResponse:
        poll: LakePoll = LakePoll.objects.get(id=pid)
        voted: bool = LakeVote.objects.filter(poll=poll, angler=request.user.angler).exists()
        context: dict = {"poll": poll, "results": self.get_results(poll=poll), "voted": voted}
        return render(request, template_name="polls/poll.html", context=context)

    def post(self, request, pid: int) -> HttpResponseRedirect:
        lake: str = request.POST.get("lake", "")
        poll: LakePoll = LakePoll.objects.get(id=pid)
        voted: bool = LakeVote.objects.filter(poll=poll, angler=request.user.angler).exists()
        try:
            choice: Lake = Lake.objects.get(id=lake)
            if voted:
                messages.error(self.request, f"ERROR: {request.user.angler} has already voted!")
                return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
        except Model.DoesNotExist as err:
            msg: str = "" if lake else "Please select a lake!"
            messages.error(self.request, f"ERROR: {err} {msg}")
        LakeVote.objects.create(poll=poll, choice=choice, angler=request.user.angler)
        return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
