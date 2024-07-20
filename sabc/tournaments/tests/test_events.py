# -*- coding: utf-8 -*-
import datetime

import pytest

from ..models.events import Events, get_next_event


@pytest.mark.django_db
def test_get_next_event():
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    if month == 12:
        year += 1
        month = 1
    event_date = datetime.date(year=year, month=month, day=now.day + 1)
    Events.objects.create(type="meeting", date=event_date)

    next_event = get_next_event(event_type="meeting")
    assert next_event is not None
