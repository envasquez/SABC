# -*- coding: utf-8 -*-
from decimal import Decimal

from django.db.models import SmallIntegerField, DecimalField, TextField, Model, BooleanField

from . import CURRENT_YEAR


class PayOutMultipliers(Model):
    class Meta:
        verbose_name_plural = "payout multipliers"

    year = SmallIntegerField(default=CURRENT_YEAR)
    club = DecimalField(default=Decimal("3"), max_digits=4, decimal_places=2)
    place_1 = DecimalField(default=Decimal("7"), max_digits=4, decimal_places=2)
    place_2 = DecimalField(default=Decimal("5"), max_digits=4, decimal_places=2)
    place_3 = DecimalField(default=Decimal("4"), max_digits=4, decimal_places=2)
    charity = DecimalField(default=Decimal("2"), max_digits=4, decimal_places=2)
    big_bass = DecimalField(default=Decimal("4"), max_digits=4, decimal_places=2)
    entry_fee = DecimalField(default=Decimal("25"), max_digits=5, decimal_places=2)
    paid_places = SmallIntegerField(default=3)
    per_boat_fee = DecimalField(default=Decimal("50"), max_digits=5, decimal_places=2)
    fee_breakdown = TextField(default="")

    def __str__(self):
        return f"POM: {self.year} Entry Fee: {self.entry_fee}"

    def get_fee_breakdown(self):
        tmnt_pot = sum([self.place_1, self.place_2, self.place_3])
        return "\n".join(
            [
                "Breakdown of the Entry Fee:",
                f"${tmnt_pot:.2f} to the Tournament Pot",
                f"1st ${self.place_1:.2f}, 2nd ${self.place_2:.2f}, 3rd ${self.place_3:.2f}",
                f"${self.big_bass:.2f} to the Tournament Big Bass Pot OVER 5 lbs.",
                f"${self.club:.2f} will go towards Clubs Funds",
                f"${self.charity:.2f} Charity of the clubs choosing",
            ]
        )

    def save(self, *args, **kwargs):
        total = sum(
            [self.club, self.charity, self.place_1, self.place_2, self.place_3, self.big_bass]
        )
        if total != self.entry_fee:
            raise ValueError(
                f"Fee breakdown: {total} does not add up to entry fee: {self.entry_fee}"
            )
        self.per_boat_fee = self.entry_fee * 2
        self.fee_breakdown = self.fee_breakdown or self.get_fee_breakdown()
        super().save(*args, **kwargs)


class TournamentPayOut(Model):
    class Meta:
        verbose_name_plural = "tournament payouts"

    club = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    offset = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    place_1 = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    place_2 = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    place_3 = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    charity = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    big_bass = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    big_bass_paid = BooleanField(default=False)
