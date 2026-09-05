from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class RecoveryStatus(str, enum.Enum):
    IN_RECOVERY = "in_recovery"
    READY_FOR_DISCHARGE = "ready_for_discharge"
    DISCHARGED_TO_WARD = "discharged_to_ward"
    DISCHARGED_TO_ICU = "discharged_to_icu"


class RecoveryRoomStay(Base):
    """PACU (Post-Anesthesia Care Unit) stay — bridges OT completion to ward/ICU transfer."""
    __tablename__ = "recovery_room_stays"

    id = Column(Integer, primary_key=True, index=True)
    surgery_id = Column(Integer, ForeignKey("surgeries.id"), nullable=False, unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    admitted_at = Column(DateTime(timezone=True), server_default=func.now())
    admitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    aldrete_score = Column(Integer, nullable=True)   # standard PACU discharge scoring, 0-10
    status = Column(Enum(RecoveryStatus), default=RecoveryStatus.IN_RECOVERY)

    pain_score_on_arrival = Column(Integer, nullable=True)   # 0-10
    nausea_vomiting = Column(Boolean, default=False)
    airway_patent = Column(Boolean, default=True)
    bleeding_at_site = Column(Boolean, default=False)

    discharged_at = Column(DateTime(timezone=True), nullable=True)
    discharged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    discharge_destination = Column(String(100), nullable=True)  # ward, icu, day-care exit
    discharge_notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RecoveryRoomObservation(Base):
    """Periodic PACU observations (typically every 15 min)."""
    __tablename__ = "recovery_room_observations"

    id = Column(Integer, primary_key=True, index=True)
    recovery_stay_id = Column(Integer, ForeignKey("recovery_room_stays.id"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    heart_rate = Column(Integer, nullable=True)
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    spo2 = Column(Float, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    consciousness_level = Column(String(50), nullable=True)   # alert, drowsy, responds to voice/pain
    pain_score = Column(Integer, nullable=True)
    notes = Column(Text)
