# -*- coding: utf-8 -*-
import datetime

import pytest

from ..models.events import Events, get_next_event


@pytest.mark.django_db
def test_get_next_event() -> None:
    now = datetime.datetime.now()
    event_1_date: datetime.date = datetime.date(
        year=now.year, month=now.month, day=now.day + 1
    )
    next_mtg: Events = Events.objects.create(type="meeting", date=event_1_date)
    event_2_date: datetime.date = datetime.date(
        year=now.year, month=now.month + 1, day=now.day
    )
    Events.objects.create(type="meeting", date=event_2_date)
    next_event = get_next_event(event_type="meeting", today=datetime.date.today())

    assert next_mtg == next_event
    assert next_mtg.date.day == next_event.date.day
    assert next_mtg.date.month == next_event.date.month
    assert next_mtg.date.year == next_event.date.year
