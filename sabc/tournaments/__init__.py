# -*- coding: utf-8 -*-
from __future__ import unicode_literals

TOURNAMENT_TYPES = [("team", "TEAM"), ("individual", "INDIVIDUAL")]
LAKES = [
    ("tbd", "TBD"),
    ("lbj", "LBJ"),
    ("travis", "TRAVIS"),
    ("belton", "BELTON"),
    ("decker", "DECKER"),
    ("canyon", "CANYON"),
    ("medina", "MEDINA"),
    ("austin", "AUSTIN"),
    ("bastrop", "BASTROP"),
    ("fayette", "FAYETTE"),
    ("buchanan", "BUCHANAN"),
    ("palestine", "PALESTINE"),
    ("lady-bird", "LADY-BIRD"),
    ("stillhouse", "STILLHOUSE"),
    ("marble-falls", "MARBLE-FALLS"),
    ("richland-chambers", "RICHLAND-CHAMBERS"),
]
STATES = [
    ("AK", "Alaska"),
    ("AL", "Alabama"),
    ("AR", "Arkansas"),
    ("AS", "American Samoa"),
    ("AZ", "Arizona"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DC", "District of Columbia"),
    ("DE", "Delaware"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("GU", "Guam"),
    ("HI", "Hawaii"),
    ("IA", "Iowa"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("MA", "Massachusetts"),
    ("MD", "Maryland"),
    ("ME", "Maine"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MO", "Missouri"),
    ("MP", "Northern Mariana Islands"),
    ("MS", "Mississippi"),
    ("MT", "Montana"),
    ("NA", "National"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("NE", "Nebraska"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NV", "Nevada"),
    ("NY", "New York"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("PR", "Puerto Rico"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VA", "Virginia"),
    ("VI", "Virgin Islands"),
    ("VT", "Vermont"),
    ("WA", "Washington"),
    ("WI", "Wisconsin"),
    ("WV", "West Virginia"),
    ("WY", "Wyoming"),
]

PAPER_LENGTH_TO_WT = {
    12.0: 1.13,
    13.0: 1.25,
    13.5: 1.38,
    14.0: 1.50,
    14.5: 1.75,
    15.0: 2.00,
    15.5: 2.25,
    16.0: 2.50,
    16.5: 2.75,
    17.0: 3.00,
    17.5: 3.25,
    18.0: 3.50,
    18.5: 3.75,
    19.0: 4.00,
    19.5: 4.25,
    20.0: 4.50,
    20.5: 4.75,
    21.0: 5.00,
    21.5: 5.25,
    22.0: 5.50,
    22.5: 5.75,
    23.0: 6.00,
    23.5: 6.25,
    24.0: 6.50,
    24.5: 6.75,
    25.0: 7.00,
    25.5: 7.25,
    26.0: 7.50,
}

# pylint: disable=line-too-long
DEFAULT_RULES = """1. All Federal, State and local laws must be observed. Illegal acts may result in disqualification.

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

9. No trolling with gas engine will be allowed.

10. Weigh-ins will be held lakeside when possible for live release of fish.

11. Fish should not be presented at weigh-in in a net! Fish must be presented in a water holding bag.

12. Any team or individual may be disqualified for a violation of rules or un-sportsman like conduct, by a vote of the club officers present.

13. Start time: You may not make your first cast until the designated start time.

14. Team may consist of 1 member, but he may weigh-in only 5 fish--against the other teams with 10 fish.
"""
DEFAULT_PAYOUT = """Moneys paid to winners will be based on total weight of combined stringers of both team members.
Individual stringer weights are recorded to determine the points awarded for the year-end awards.
"""
DEFAULT_WEIGH_IN = """1. Tournament anglers must be inside of the buoys, where weigh-in is to be held by the end time of the tournament. If an angler or a team is not at an idle speed, inside the buoys by the end time of the tournament they will be disqualified.

2. The weigh-in will begin 15min after the end time of the tournament. This time is for people to trailer their boats and for the weigh-in committee to get set up to receive fish. For fish care reasons please wait for scales to officially open before placing your fish in a weigh in bag.

3. Hard Luck Clause: If a Team experiences mechanical issues or any issues outside their power, they can call an Officer before the end of the Tournament for a grace period or assistance. The team’s creel will be weighed in once they can get back to weigh-in site.
"""
DEFAULT_ENTRY_FEE = """
Entry fee shall be $20.00 per member, due no later than weigh-in. No checks, cash only. Fee is
due if you fish at any time during the tournament.

1. Teams/ Club Members fishing tournament waters, during tournament hours, will be responsible for
entry fees whether you show up for weigh-in or not as you will be considered fishing the tournament.

2. If you have an adult guest fishing in the boat they will be considered fishing the tournament and will
pay the tournament fee. A guest can fish up to two tournaments within the same calendar year
without having to become an SABC member. After that, they will be required to pay the annual
$20 annual membership fee prior to fishing any more club tournaments within the same year.

3. If special provisions or requests are required by a member they must be brought up before the
tournament and voted on and approved by at least three officers
"""
DEFAULT_FEE_BREAKDOWN = """Breakdown of $20.00 Entry Fee:
- $13.00 to the Tournament Pot 1st $6.00, 2nd $4.00, 3rd $3.00
- $2.00 to the Tournament Big Bass Pot OVER 5 lbs.
- $3.00 will go towards Clubs Funds
- $2.00 Club Charity – Charity give back will be decided by a vote of club members present at the December club meeting.
"""
DEFAULT_DEAD_FISH_PENALTY = 0.25
DEFAULT_BIG_BASS_BREAKDOWN = """Big Bass Pot is paid to the heaviest bass caught at the tournament OVER 5lbs. If fishing a Slot Limit Lake or a Paper Tournament and no bass is brought in over the slot limit, this pot will be carried over to the next tournament.

- ONLY MEMBERS in good standing are eligible for Big Bass Award.
"""
