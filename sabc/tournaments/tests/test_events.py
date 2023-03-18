# -*- coding: utf-8 -*-
import datetime

import pytest

from ..models.events import Events, get_next_event


@pytest.mark.django_db
def test_get_next_event() -> None:
    now = datetime.datetime.now()
    for month in range(1, 13):
        event_date: datetime.date = datetime.date(year=now.year, month=month, day=3)
        Events.objects.create(type="meeting", date=event_date)

    next_event = get_next_event(event_type="meeting", today=datetime.date.today())
    assert next_event.date.month >= now.month
