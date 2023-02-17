# -*- coding: utf-8 -*-
from typing import Any, Type

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from ..forms import EventForm
from ..models.events import Events
from ..models.tournaments import Tournament


class EventUpdateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    model: Type[Events] = Events
    form_class: Type[EventForm] = EventForm

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def get_success_url(self) -> Any:
        tmnt: Tournament = Tournament.objects.get(event__id=self.kwargs.get("pk"))
        return reverse_lazy("tournament-details", kwargs={"pk": tmnt.id})
