# -*- coding: utf-8 -*-
""" Test Plan for Payouts

- Test that payout calculations are accurate for all payout modifiers
- Test that big bass carry-over is True if a bass over 5lbs is caught by a member (False otherwise)
-
"""
# from typing import Any

# from decimal import Decimal

# from unittest import TestCase

# # from . import create_angler, RESULTS_NO_TIE
# from ..models.lakes import Lake, Ramp
# from ..models.payouts import PayOutMultipliers
# from ..models.results import Result
# from ..models.tournament import Tournament


# class TestPayouts(TestCase):
#     def test_get_payouts(self) -> None:
#         """Tests the get_payouts function: funds are calculated properly"""
#         pom: PayOutMultipliers = PayOutMultipliers.objects.create()
#         lake: Lake = Lake.objects.create(name="Test Lake")
#         ramp: Ramp = Ramp.objects.create(lake=lake, name="Test Ramp")
#         tmnt: dict[str, Any] = {"lake": lake, "ramp": ramp, "payout_multiplier": pom}
#         tournament = Tournament.objects.create(**tmnt)
#         for data in RESULTS_NO_TIE.values():
#             angler = create_angler(data["first_name"], data["last_name"], "member")
#             if data.get("buy_in"):
#                 Result.objects.create(tournament=tournament, angler=angler, buy_in=True)
#                 continue
#             Result.objects.create(
#                 tournament=tournament,
#                 angler=angler,
#                 num_fish=data.get("num_fish", 0),
#                 total_weight=data.get("total_weight", 0),
#                 num_fish_dead=data.get("num_fish_dead", 0),
#                 big_bass_weight=data.get("big_bass_weight", Decimal("0")),
#             )
#         Tournament.results.reconcile_indiv_results(tournament)
#         payouts = Tournament.results.get_payouts(tournament)
#         yes_bb = Result.objects.filter(tournament=tournament, big_bass_weight__gte=5.0).count() > 0
#         self.assertEqual(payouts["club"], Decimal("45"))
#         self.assertEqual(payouts["total"], Decimal("375"))
#         self.assertEqual(payouts["place_1"], Decimal("105"))
#         self.assertEqual(payouts["place_2"], Decimal("75"))
#         self.assertEqual(payouts["place_3"], Decimal("60"))
#         self.assertEqual(payouts["charity"], Decimal("30"))
#         self.assertEqual(payouts["bb_carry_over"], not yes_bb)
