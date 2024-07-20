# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.db.models import (
    CharField,
    DecimalField,
    Model,
    SmallIntegerField,
    TextField,
)

RULE_INFO = """
1. All Federal, State and local laws must be observed. Illegal acts may result in disqualification.
2. Protests must be presented to a club officer within 30 minutes of the weigh-in.
3. Team members must fish from the same boat. SABC rules do allow a third contestant in a boat during “Individual” type tournaments. (A guest must fish with a paid member)
4. Only artificial baits may be used. (Exception – pork rind may be used.)
5. Only legal-sized Black, Smallmouth, or Spotted Bass are eligible for weigh-in. (Exception --Spotted/ Guadalupe Bass must be 12 inches in length.) Members are responsible for knowing individual lake rules.
6. Fish must be measured on a flat board with a perpendicular end. Fish must be placed flat on the board, with mouth closed and jammed against perpendicular end. You may manipulate tail to determine maximum length. (Tip of tail must touch the line for 14 inches, etc.). Any fish at weigh-in short of legal limit makes team/individual subject to disqualification. If you are unsure of a fish’s measurement, ask a club officer to check the fish prior to presentation at weigh-in.
7. Tournament Lake is off limits for Fishing 12 hours prior to tournament start time.
8. There is a five (5) fish limit per person. Each person may weigh-in only those five fish that they caught. No exchange of fish between team members. Keep your fish separated or mark when caught.
Exceptions:
    (a) Two-day tournaments--5 fish per day, and/or
    (b) Local lake law allows less than five fish stringers.
    (c) Summer 3 fish limits to prevent fish mortality
9. No trolling with gas engine will be allowed.
10. Weigh-ins will be held lakeside when possible for live release of fish.
11. Fish should not be presented at weigh-in in a net! Fish must be presented in a water holding bag.
12. Any team or individual may be disqualified for a violation of rules or un-sportsman like conduct, by a vote of the club officers present.
13. Start time: You may not make your first cast until the designated start time.
14. Team may consist of 1 member, but he may weigh-in only 5 fish--against the other teams with 10 fish.
"""
WEIGH_IN_INFO = """
1. Tournament anglers must be inside of the buoys, where weigh-in is to be held by the end time of the tournament. If an angler or a team is not at an idle speed, inside the buoys by the end time of the tournament they will be disqualified.
2. The weigh-in will begin 15min after the end time of the tournament. This time is for people to trailer their boats and for the weigh-in committee to get set up to receive fish. For fish care reasons please wait for scales to officially open before placing your fish in a weigh in bag.
3. Hard Luck Clause: If a Team experiences mechanical issues or any issues outside their power, they can call an Officer before the end of the Tournament for a grace period or assistance. The team’s creel will be weighed in once they can get back to weigh-in site.
"""

PAYOUT_INFO = """Moneys paid to winners will be based on total weight of combined stringers of both team members.
Individual stringer weights are recorded to determine the points awarded for the year-end awards.
"""
BIG_BASS_INFO = """
Big Bass Pot is paid to the heaviest bass caught at the tournament OVER 5lbs.

If fishing a Slot Limit Lake or a Paper Tournament and no bass is brought in over the slot limit,
this pot will be carried over to the next tournament.

- ONLY MEMBERS in good standing are eligible for Big Bass Award.
"""
PAYMENT_INFO = """
Entry fee shall be due no later than weigh-in. No checks, cash only and possibly Venmo/Zello/Ca$hApp.
Fee is due if you fish at any time during the tournament.

1. Teams/ Club Members fishing tournament waters, during tournament hours, will be responsible for
entry fees whether you show up for weigh-in or not as you will be considered fishing the tournament.

2. If you have an adult guest fishing in the boat they will be considered fishing the tournament and will
pay the tournament fee. A guest can fish up to two tournaments within the same calendar year
without having to become an SABC member. After that, they will be required to pay the annual
$20 annual membership fee prior to fishing any more club tournaments within the same year.

3. If special provisions or requests are required by a member they must be brought up before the
tournament and voted on and approved by at least three officers
"""


class RuleSet(Model):
    year = SmallIntegerField(default=datetime.date.today().year)
    name = CharField(
        default=f"SABC Default Rules {datetime.date.today().year}", max_length=100
    )
    rules = TextField(default=RULE_INFO)
    payout = TextField(default=PAYOUT_INFO)
    weigh_in = TextField(default=WEIGH_IN_INFO)
    entry_fee = TextField(default=PAYMENT_INFO)
    limit_num = SmallIntegerField(default=5)
    dead_fish_penalty = DecimalField(
        default=Decimal("0.25"), max_digits=5, decimal_places=2
    )
    max_points = SmallIntegerField(default=100)
    big_bass_breakdown = TextField(default=BIG_BASS_INFO)
    zeroes_points_offset = SmallIntegerField(default=2)
    buy_ins_points_offset = SmallIntegerField(default=4)
    disqualified_points_offset = SmallIntegerField(default=3)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"RuleSet-{self.id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
