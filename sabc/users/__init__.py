"""User defines for SABC """
CLUBS = (("SABC", "South Austin Bass Club"),)

CLUB_GUEST = "guest"
CLUB_MEMBER = "member"
CLUB_OFFICER = "officer"
MEMBER_CHOICES = (
    (CLUB_GUEST, "guest"),
    (CLUB_MEMBER, "member"),
    (CLUB_OFFICER, "officer"),
)

CLUB_PRESIDENT = "president"
CLUB_VICE_PRESIDENT = "vice-president"
CLUB_SECRETARY = "secretary"
CLUB_TREASURER = "treasurer"
CLUB_SOCIAL_MEDIA = "social-media"
CLUB_TOURNAMENT_DIRECTOR = "tournament-director"
CLUB_ASSISTANT_TOURNAMENT_DIRECTOR = "assistant-tournament-director"

CLUB_OFFICERS_TYPES = (
    (CLUB_PRESIDENT, "president"),
    (CLUB_VICE_PRESIDENT, "vice-president"),
    (CLUB_SECRETARY, "secretary"),
    (CLUB_TREASURER, "treasurer"),
    (CLUB_SOCIAL_MEDIA, "social-media"),
    (CLUB_TOURNAMENT_DIRECTOR, "tournament-director"),
    (CLUB_ASSISTANT_TOURNAMENT_DIRECTOR, "assistant-tournament-director"),
)
