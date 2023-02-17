# -*- coding: utf-8 -*-
import datetime

import pytest

from ..models.events import Events, get_next_event


@pytest.mark.django_db
def test_get_next_event() -> None:
    event_1_date: datetime.date = datetime.date(year=2023, month=2, day=6)
    Events.objects.create(type="meeting", date=event_1_date)
    event_2_date: datetime.date = datetime.date(year=2023, month=3, day=6)
    next_mtg: Events = Events.objects.create(type="meeting", date=event_2_date)
    next_event = get_next_event(event_type="meeting", today=datetime.date.today())

    assert next_mtg == next_event
    assert next_mtg.date.day == next_event.date.day
    assert next_mtg.date.month == next_event.date.month
    assert next_mtg.date.year == next_event.date.year
