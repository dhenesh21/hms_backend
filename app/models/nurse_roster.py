from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum, Date
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ShiftType(str, enum.Enum):
    MORNING = "morning"
    EVENING = "evening"
    NIGHT = "night"


class NurseWardAssignment(Base):
    """
    Closes a gap flagged during Nurse Portal (item 186): previously there was
    no ward-to-nurse roster anywhere in this codebase, so any nurse could view
    any ward's worklist. This is a simple per-shift, per-date roster — a nurse
    is "on" a ward for a given date+shift. Nurse Portal endpoints can now scope
    "my ward" to wards where a NurseWardAssignment exists for that nurse today.
    """
    __tablename__ = "nurse_ward_assignments"

    id = Column(Integer, primary_key=True, index=True)
    nurse_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    assignment_date = Column(Date, server_default=func.current_date(), nullable=False)
    shift = Column(Enum(ShiftType), nullable=False)
    is_charge_nurse = Column(Boolean, default=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
