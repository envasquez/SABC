# # -*- coding: utf-8 -*-
""" Test Plan for conversion functions

- Test that weight to length and lenght to weight conversions are accurate
"""

from .. import get_length_from_weight, get_weight_from_length
from . import LENGTH_TO_WEIGHT, WEIGHT_TO_LENGTH


def test_get_weight_by_length():
    for length, expected_weight in LENGTH_TO_WEIGHT:
        assert expected_weight == get_weight_from_length(length)

    for weight, expected_length in WEIGHT_TO_LENGTH:
        assert expected_length == get_length_from_weight(weight)
