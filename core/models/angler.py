from core.models.base import BaseModel, ConfigDict, Decimal, EmailStr, Optional, datetime


class AnglerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    email: EmailStr
    member: bool = True
    is_admin: bool = False
    phone: Optional[str] = None


class Angler(AnglerBase):
    id: int
    password_hash: Optional[str] = None
    year_joined: Optional[int] = None
    created_at: Optional[datetime] = None


class AOYStanding(BaseModel):
    name: str
    total_points: int
    total_fish: int
    total_weight: Decimal
    tournaments_fished: int
