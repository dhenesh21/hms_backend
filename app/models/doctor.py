from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    # Item 171 — the checklist asked for a "unified" Doctor/Staff table, but
    # doctor_profiles and staff_profiles already have ~150 other tables
    # across this codebase with direct FK references to one or the other
    # (CPOE orders, appointments, payroll, leave, the salary structures and
    # shift assignments just built for item 173/176, etc). Physically
    # merging the two tables would mean migrating every one of those FKs -
    # high risk for a checklist item whose actual need is "see a doctor's
    # employment data alongside their clinical profile," not "restructure
    # the schema." This nullable link achieves that without touching any
    # existing reference: a doctor who is also a paid employee (most of
    # them) links here to their StaffProfile for payroll/leave/attendance;
    # a visiting/consulting doctor who isn't on staff payroll simply has
    # this null. See routers/organization.py's /unified-staff endpoints
    # for the combined read view this enables.
    staff_profile_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=True, unique=True)
    registration_number = Column(String(50), unique=True, nullable=False)
    specialization = Column(String(200), nullable=False)
    sub_specialization = Column(String(200))
    qualification = Column(String(500))
    experience_years = Column(Integer, default=0)
    consultation_fee = Column(Float, default=0.0)
    bio = Column(Text)
    languages_spoken = Column(JSON, default=list)
    available_days = Column(JSON, default=list)  # ["Monday", "Tuesday", ...]
    consultation_duration_minutes = Column(Integer, default=15)
    is_available = Column(Boolean, default=True)
    photo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="doctor_profile")
    appointments = relationship("Appointment", back_populates="doctor")
    opd_visits = relationship("OPDVisit", back_populates="doctor")
    duty_roster = relationship("DutyRoster", back_populates="doctor")


class DutyRoster(Base):
    __tablename__ = "duty_rosters"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)
    day_of_week = Column(String(20), nullable=False)
    start_time = Column(String(10), nullable=False)  # "09:00"
    end_time = Column(String(10), nullable=False)    # "17:00"
    max_patients = Column(Integer, default=20)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    doctor = relationship("DoctorProfile", back_populates="duty_roster")
