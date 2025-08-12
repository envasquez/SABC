# -*- coding: utf-8 -*-
import calendar
import datetime
from typing import Type

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
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
    paginate_by = 5  # Pagination similar to tournaments
    context_object_name = "polls"

    def test_func(self):
        """Ensure user is authenticated and has an angler profile with membership."""
        if not self.request.user.is_authenticated:
            return False
        try:
            return (
                hasattr(self.request.user, "angler") and self.request.user.angler.member
            )
        except AttributeError:
            return False

    def get_context_data(self, **kwargs):
        """Add poll results data for each poll."""
        context = super().get_context_data(**kwargs)
        
        # Get total member count
        from users.models import Angler
        total_members = Angler.objects.filter(member=True).count()
        
        # Add results for each poll
        for poll in context['polls']:
            results = {}
            max_votes = 0
            for choice in poll.choices.all():
                count = LakeVote.objects.filter(poll=poll, choice=choice).count()
                # Only include lakes that have votes
                if count > 0:
                    results[choice.name] = count
                    if count > max_votes:
                        max_votes = count
            
            poll.results = results
            poll.max_votes = max_votes
            poll.has_votes = max_votes > 0
            
            # Get total votes for this poll
            poll.total_votes = LakeVote.objects.filter(poll=poll).count()
            poll.total_members = total_members
            poll.participation_rate = (poll.total_votes / total_members * 100) if total_members > 0 else 0
            
            # Check if current user has voted
            if self.request.user.is_authenticated and hasattr(self.request.user, 'angler'):
                poll.user_voted = LakeVote.objects.filter(
                    poll=poll, 
                    angler=self.request.user.angler
                ).exists()
            else:
                poll.user_voted = False
                
        return context


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

    def test_func(self):
        """Ensure user is authenticated and has an angler profile with membership."""
        if not self.request.user.is_authenticated:
            return False
        try:
            return (
                hasattr(self.request.user, "angler") and self.request.user.angler.member
            )
        except AttributeError:
            return False

    def get_results(self, poll: LakePoll):
        results = [["Lake", "Votes"]]
        for choice in poll.choices.all():
            count = LakeVote.objects.filter(poll=poll, choice=choice).count()
            # Only include lakes that have received votes
            if count > 0:
                results.append([str(choice).title(), count])
        return results

    def get(self, request, pid):
        """Display poll with voting form or results."""
        try:
            poll = LakePoll.objects.get(id=pid)
        except LakePoll.DoesNotExist:
            messages.error(request, "Poll not found.")
            return redirect("polls")

        # User is guaranteed to have angler profile due to test_func
        voted = LakeVote.objects.filter(poll=poll, angler=request.user.angler).exists()
        results = self.get_results(poll=poll)
        
        # Get voting statistics
        from users.models import Angler
        total_members = Angler.objects.filter(member=True).count()
        total_votes = LakeVote.objects.filter(poll=poll).count()
        participation_rate = (total_votes / total_members * 100) if total_members > 0 else 0
        
        context = {
            "poll": poll,
            "voted": voted,
            "results": results,
            "no_results": results == [["Lake", "Votes"]],
            "total_votes": total_votes,
            "total_members": total_members,
            "participation_rate": participation_rate,
        }
        return render(request, template_name="polls/poll.html", context=context)

    def post(self, request, pid):
        """Handle vote submission with proper validation."""
        try:
            poll = LakePoll.objects.get(id=pid)
        except LakePoll.DoesNotExist:
            messages.error(request, "Poll not found.")
            return redirect("polls")

        # Check if poll is still active
        if not poll.is_active():
            messages.error(request, "This poll is no longer accepting votes.")
            return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))

        # User is guaranteed to have angler profile due to test_func
        angler = request.user.angler

        # Check if user has already voted
        if LakeVote.objects.filter(poll=poll, angler=angler).exists():
            messages.error(request, f"ERROR: {angler} has already voted!")
            return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))

        # Validate lake selection
        lake_id = request.POST.get("lake", "")
        if not lake_id:
            messages.error(request, "Please select a lake!")
            return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))

        try:
            choice = Lake.objects.get(id=lake_id)
            # Verify the lake is one of the poll choices
            if choice not in poll.choices.all():
                messages.error(request, "Invalid lake selection.")
                return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
        except Lake.DoesNotExist:
            messages.error(request, "Invalid lake selection.")
            return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
        except ValueError:
            messages.error(request, "Invalid lake selection.")
            return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))

        # Create the vote
        LakeVote.objects.create(poll=poll, choice=choice, angler=angler)
        messages.success(request, f"Vote successfully cast for {choice}!")
        return HttpResponseRedirect(reverse("poll", kwargs={"pid": pid}))
