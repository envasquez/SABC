# -*- coding: utf-8 -*-
"""Tournament definitions and enums"""
from __future__ import unicode_literals

from decimal import Decimal
from datetime import datetime, date
from calendar import monthcalendar

LAKES = [
    ("tbd", "TBD"),
    ("lbj", "LBJ"),
    ("travis", "TRAVIS"),
    ("belton", "BELTON"),
    ("decker", "DECKER"),
    ("canyon", "CANYON"),
    ("medina", "MEDINA"),
    ("austin", "AUSTIN"),
    ("oh-ivie", "OH-IVIE"),
    ("bastrop", "BASTROP"),
    ("fayette", "FAYETTE"),
    ("buchanan", "BUCHANAN"),
    ("palestine", "PALESTINE"),
    ("lady-bird", "LADY-BIRD"),
    ("stillhouse", "STILLHOUSE"),
    ("marble-falls", "MARBLE-FALLS"),
    ("richland-chambers", "RICHLAND-CHAMBERS"),
]


# pylint: disable=line-too-long
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

PAYOUT = """Moneys paid to winners will be based on total weight of combined stringers of both team members.
Individual stringer weights are recorded to determine the points awarded for the year-end awards.
"""

WEIGH_IN = """
1. Tournament anglers must be inside of the buoys, where weigh-in is to be held by the end time of the tournament. If an angler or a team is not at an idle speed, inside the buoys by the end time of the tournament they will be disqualified.
2. The weigh-in will begin 15min after the end time of the tournament. This time is for people to trailer their boats and for the weigh-in committee to get set up to receive fish. For fish care reasons please wait for scales to officially open before placing your fish in a weigh in bag.
3. Hard Luck Clause: If a Team experiences mechanical issues or any issues outside their power, they can call an Officer before the end of the Tournament for a grace period or assistance. The team’s creel will be weighed in once they can get back to weigh-in site.
"""

PAYMENT = """
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
FEE_BREAKDOWN = """Breakdown of $20.00 Entry Fee:
- $13.00 to the Tournament Pot 1st $6.00, 2nd $4.00, 3rd $3.00
- $2.00 to the Tournament Big Bass Pot OVER 5 lbs.
- $3.00 will go towards Clubs Funds
- $2.00 Club Charity – Charity give back will be decided by a vote of club members present at the December club meeting.
"""
ENTRY_FEE_DOLLARS = Decimal("20.00")
DEAD_FISH_PENALTY = Decimal("0.25")
BIG_BASS_BREAKDOWN = """
Big Bass Pot is paid to the heaviest bass caught at the tournament OVER 5lbs.

If fishing a Slot Limit Lake or a Paper Tournament and no bass is brought in over the slot limit,
this pot will be carried over to the next tournament.

- ONLY MEMBERS in good standing are eligible for Big Bass Award.
"""

DEFAULT_END_TIME = datetime.time(datetime.strptime("3:00 pm", "%I:%M %p"))
DEFAULT_START_TIME = datetime.time(datetime.strptime("6:00 am", "%I:%M %p"))
DEFAULT_PAID_PLACES = 3
DEFAULT_FACEBOOK_URL = "https://www.facebook.com/SouthAustinBassClub"
DEFAULT_INSTAGRAM_URL = "https://www.instagram.com/south_austin_bass_club"


# TPW Length-weight Conversion Table for Texas Largemouth Bass
# https://tpwd.texas.gov/fishboat/fish/recreational/catchrelease/bass_length_weight.phtml
#
# Inches	Fractions
#  	       0	 1/8	 1/4	 3/8	 1/2	 5/8	 3/4	 7/8
# 10	0.48	0.50	0.52	0.54	0.56	0.58	0.61	0.63
# 11	0.66	0.68	0.71	0.73	0.76	0.79	0.81	0.84
# 12	0.87	0.90	0.93	0.97	1.00	1.03	1.07	1.10
# 13	1.14	1.17	1.21	1.25	1.29	1.32	1.37	1.41
# 14	1.45	1.49	1.54	1.58	1.63	1.67	1.72	1.77
# 15	1.82	1.87	1.92	1.97	2.02	2.08	2.13	2.19
# 16	2.25	2.31	2.36	2.42	2.49	2.55	2.61	2.68
# 17	2.74	2.81	2.88	2.95	3.02	3.09	3.16	3.23
# 18	3.31	3.39	3.46	3.54	3.62	3.70	3.78	3.87
# 19	3.95	4.04	4.13	4.22	4.31	4.40	4.49	4.58
# 20	4.68	4.78	4.87	4.97	5.08	5.18	5.28	5.39
# 21	5.49	5.60	5.71	5.82	5.94	6.05	6.17	6.28
# 22	6.40	6.52	6.64	6.77	6.89	7.02	7.15	7.28
# 23	7.41	7.54	7.68	7.81	7.95	8.09	8.23	8.38
# 24	8.52	8.67	8.82	8.97	9.12	9.27	9.43	9.59
# 25	9.75	9.91	10.07	10.23	10.40	10.57	10.74	10.91
# 26	11.09	11.26	11.44	11.62	11.80	11.99	12.17	12.36
# 27	12.55	12.74	12.94	13.13	13.33	13.53	13.73	13.94
# 28	14.15	14.35	14.56	14.78	14.99	15.21	15.43	15.65
# 29	15.87	16.10	16.33	16.56	16.79	17.03	17.26	17.50
LENGTH_TO_WEIGHT = {
    #     0    1/8    1/4   3/8   1/2   5/8   3/4   7/8
    # 10: [0.48, 0.50, 0.52, 0.54, 0.56, 0.58, 0.61, 0.63],
    # 11: [0.66, 0.68, 0.71, 0.73, 0.76, 0.79, 0.81, 0.84],
    12: [0.87, 0.90, 0.93, 0.97, 1.00, 1.03, 1.07, 1.10],
    13: [1.14, 1.17, 1.21, 1.25, 1.29, 1.32, 1.37, 1.41],
    14: [1.45, 1.49, 1.54, 1.58, 1.63, 1.67, 1.72, 1.77],
    15: [1.82, 1.87, 1.92, 1.97, 2.02, 2.08, 2.13, 2.19],
    16: [2.25, 2.31, 2.36, 2.42, 2.49, 2.55, 2.61, 2.68],
    17: [2.74, 2.81, 2.88, 2.95, 3.02, 3.09, 3.16, 3.23],
    18: [3.31, 3.39, 3.46, 3.54, 3.62, 3.70, 3.78, 3.87],
    19: [3.95, 4.04, 4.13, 4.22, 4.31, 4.40, 4.49, 4.58],
    20: [4.68, 4.78, 4.87, 4.97, 5.08, 5.18, 5.28, 5.39],
    21: [5.49, 5.60, 5.71, 5.82, 5.94, 6.05, 6.17, 6.28],
    22: [6.40, 6.52, 6.64, 6.77, 6.89, 7.02, 7.15, 7.28],
    23: [7.41, 7.54, 7.68, 7.81, 7.95, 8.09, 8.23, 8.38],
    24: [8.52, 8.67, 8.82, 8.97, 9.12, 9.27, 9.43, 9.59],
    25: [9.75, 9.91, 10.07, 10.23, 10.40, 10.57, 10.74, 10.91],
    26: [11.09, 11.26, 11.44, 11.62, 11.80, 11.99, 12.17, 12.36],
    27: [12.55, 12.74, 12.94, 13.13, 13.33, 13.53, 13.73, 13.94],
    28: [14.15, 14.35, 14.56, 14.78, 14.99, 15.21, 15.43, 15.65],
    29: [15.87, 16.10, 16.33, 16.56, 16.79, 17.03, 17.26, 17.50],
}


def get_weight_from_length(length):
    """Returns the weight of a fish, given its length

    if the length is below 10 inches: 0.00 (lbs) is returned
    if the length is greater than 29 inches: 18.00 (lbs) is returned

    Fractional inch measurements for reference:
      0 = 0.00
    1/8 = 0.125
    1/4 = 0.25
    3/8 = 0.375
    1/2 = 0.50
    5/8 = 0.625
    3/4 = 0.75
    7/8 = 0.875
    """
    length = float(length)  # Endure we're always dealing with floats
    inches, fraction = str(length).split(".")

    inches = int(inches)
    fraction = float(f"0.{fraction}")
    if inches > 29:
        return 18.00

    fractions = {0.00: 0, 0.125: 1, 0.25: 2, 0.375: 3, 0.50: 4, 0.625: 5, 0.75: 6, 0.875: 7}
    if inches in LENGTH_TO_WEIGHT:
        return LENGTH_TO_WEIGHT[inches][fractions[fraction]]

    return 0.00


def get_length_from_weight(weight):
    """Given a fishes weight, return its length

    if the weight is less than 0.48 pounds: 10.00 (inches) is returned
    if the weight is greater than 17.50 pounds: 30.00 (inches) is returned

    Fractional inch measurements for reference:
    0: 0.00   0
    1: 0.125 1/8
    2: 0.25  1/4
    3: 0.375 3/8
    4: 0.50  1/2
    5: 0.625 5/8
    6: 0.75  3/4
    7: 0.875 7/8
    """
    weight = float(weight)  # Ensure we're always dealing with a float
    if weight > 17.50:
        return 30.0

    fractions = {0: 0.00, 1: 0.125, 2: 0.25, 3: 0.375, 4: 0.50, 5: 0.625, 6: 0.75, 7: 0.875}
    index, inches = 0, 0
    for inch, weights in LENGTH_TO_WEIGHT.items():
        # Find inch range for the weight
        if all([weight >= min(weights), weight <= max(weights)]):
            inches = inch
            # Get the closes fractional weight
            closest = min(weights, key=lambda w: abs(w - weight))
            index = weights.index(closest)
            break

    return inches + fractions[index]


def get_last_sunday(month=None):
    """Returns the date of the last Sunday of the month passed in.

    If no month is passed in, then the current (when called) month is used.

    Args:
        month (int) The month to get the last Sunday from.
    Raises:
        ValueError if the month is less than 0 for greater than 12 or not an int.
    """
    if month is None:
        month = date.today().month
    sunday = max(week[-1] for week in monthcalendar(date.today().year, month))
    sunday = sunday if sunday >= 10 else f"0{sunday}"
    return f"{date.today().year}-{month}-{sunday}"
