from core.models.base import BaseModel, ConfigDict, Decimal, Optional


class TournamentResultBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    angler_id: int
    angler_name: str
    total_weight: Decimal
    num_fish: int
    big_bass_weight: Decimal = Decimal("0")
    buy_in: bool = False
    disqualified: bool = False
    member: bool = True


class TournamentResult(TournamentResultBase):
    id: Optional[int] = None
    calculated_place: Optional[int] = None
    calculated_points: Optional[int] = None


class TournamentStats(BaseModel):
    total_anglers: int = 0
    total_fish: int = 0
    total_weight: Decimal = Decimal("0")
    limits: int = 0
    zeros: int = 0
    buy_ins: int = 0
    biggest_bass: Decimal = Decimal("0")
    heavy_stringer: Decimal = Decimal("0")


class TeamResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    place_finish: int
    angler1_name: str
    angler2_name: Optional[str] = None
    total_fish: int
    total_weight: Decimal
    angler1_member: bool
    angler2_member: bool = False
    id: int
    team_size: int = 2
