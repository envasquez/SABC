# -*- coding: utf-8 -*-
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.db.models import Model
from django.shortcuts import render
from django.views.generic import View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin

from tournaments.models.lakes import Lake

from .models import LakePoll, LakeVote


class LakePollListView(ListView, LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin):
    model = LakePoll
    context_object_name = "polls"


class LakePollView(View, LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin):
    model = LakePoll

    def get_results(self, poll):
        results = [["Lake", "Votes"]]
        for choice in poll.choices.all():
            count = LakeVote.objects.filter(poll=poll, choice=choice).count()
            if count:
                results.append([choice.name, count])
        return results

    def get(self, request, pid):
        poll = LakePoll.objects.get(id=pid)
        voted = LakeVote.objects.filter(poll=poll, angler=request.user.angler).exists()
        return render(
            request,
            template_name="polls/poll.html",
            context={
                "poll": poll,
                "results": self.get_results(poll=poll),
                "voted": voted,
            },
        )

    def post(self, request, pid):
        poll = LakePoll.objects.get(id=pid)
        lake = request.POST.get("lake")
        voted = LakeVote.objects.filter(poll=poll, angler=request.user.angler).exists()
        try:
            choice = Lake.objects.get(id=lake)
            if voted:
                messages.error(self.request, f"ERROR: {request.user.angler} has already voted!")
                return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
        except Model.DoesNotExist as err:
            msg = "" if lake else "Please select a lake!"
            messages.error(self.request, f"ERROR: {err} {msg}")
        LakeVote.objects.create(poll=poll, choice=choice, angler=request.user.angler)
        return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
