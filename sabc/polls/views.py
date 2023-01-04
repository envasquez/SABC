# -*- coding: utf-8 -*-
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import render
from django.views.generic import View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin

from tournaments.models import Lake

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
            results.append([choice.name, LakeVote.objects.filter(poll=poll, choice=choice).count()])
            if count:
                results.append([choice.name, count])
        return results

    def get(self, request, pid):
        poll = LakePoll.objects.get(id=pid)
        voted = LakeVote.objects.filter(poll=poll, angler=request.user.angler).exists()
        return render(
            request,
            template_name="polls/poll.html",
            context={"poll": poll, "results": self.get_results(poll=poll), "voted": voted},
        )

    def post(self, request, pid):
        poll = LakePoll.objects.get(id=pid)
        lake = request.POST.get("lake")
        try:
            choice = Lake.objects.get(id=lake)
            LakeVote.objects.create(poll=poll, choice=choice, angler=request.user.angler)
        except Exception as err:
            msg = "" if lake else "Please select a lake!"
            messages.error(self.request, f"ERROR:{err} {msg}")
            return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
        return render(
            request,
            template_name="polls/poll.html",
            context={
                "poll": poll,
                "voted": LakeVote.objects.filter(poll=poll, angler=request.user.angler).exists(),
                "results": self.get_results(poll=poll),
                "success_message": f"Voted for: {str(choice).title()} successfully!",
            },
        )
