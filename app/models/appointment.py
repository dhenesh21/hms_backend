from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Date, Time, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentType(str, enum.Enum):
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    PROCEDURE = "procedure"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    appointment_number = Column(String(20), unique=True, index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(String(10), nullable=False)
    appointment_type = Column(Enum(AppointmentType), default=AppointmentType.CONSULTATION)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    reason = Column(Text)
    notes = Column(Text)
    token_number = Column(Integer)
    booked_by = Column(Integer, ForeignKey("users.id"))
    cancelled_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Prevents two appointments from getting the same token number for
        # the same doctor on the same day - without this, concurrent
        # bookings could silently collide since token_number itself had
        # no DB-level constraint at all. Trade-off: a cancelled
        # appointment's token number is not freed up for reuse, but that's
        # a fair price for a real, DB-enforced guarantee (a "skip
        # cancelled" version would need a partial/filtered unique index,
        # which isn't portably supported across SQLite and Postgres).
        UniqueConstraint("doctor_id", "appointment_date", "token_number", name="uq_doctor_date_token"),
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("DoctorProfile", back_populates="appointments")
    opd_visit = relationship("OPDVisit", back_populates="appointment", uselist=False)
