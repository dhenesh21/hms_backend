from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, Float)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ConsultationStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    WAITING = "waiting"          # patient joined, doctor not yet
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class VirtualConsultation(Base):
    """
    Telemedicine / e-Consult session (items 188-190). Deliberately vendor-agnostic:
    `meeting_link`/`meeting_provider` are free-form so any video vendor (Twilio,
    Agora, Daily, Jitsi, a plain Zoom link) can populate them — no vendor SDK
    integration is built here, that's a separate decision documented in the roadmap.
    `is_second_opinion` covers item 191 without needing a whole separate model:
    a second-opinion request is a virtual consult with a different doctor, flagged.
    """
    __tablename__ = "virtual_consultations"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)

    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(ConsultationStatus), default=ConsultationStatus.SCHEDULED)

    meeting_provider = Column(String(50), nullable=True)   # e.g. "twilio", "agora", "external_link"
    meeting_link = Column(String(500), nullable=True)
    meeting_id_external = Column(String(200), nullable=True)

    is_second_opinion = Column(Boolean, default=False)
    referring_doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=True)  # set when second opinion
    reason_for_consult = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    consultation_notes = Column(Text, nullable=True)
    prescription_issued = Column(Boolean, default=False)
    follow_up_advised = Column(Boolean, default=False)
    cancellation_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
