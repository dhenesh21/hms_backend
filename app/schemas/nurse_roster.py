from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from app.models.nurse_roster import ShiftType


class NurseAssignmentCreate(BaseModel):
    nurse_id: int
    ward_id: int
    assignment_date: date
    shift: ShiftType
    is_charge_nurse: bool = False


class NurseAssignmentResponse(BaseModel):
    id: int
    nurse_id: int
    ward_id: int
    assignment_date: date
    shift: ShiftType
    is_charge_nurse: bool

    class Config:
        from_attributes = True
