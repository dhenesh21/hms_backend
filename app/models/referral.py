import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date, Enum, Text
from datetime import datetime
from app.core.database import Base


class ReferralType(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class ReferralStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True, index=True)
    referral_number = Column(String(20), unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    referring_doctor_id = Column(Integer, ForeignKey("users.id"))
    referred_to_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    referred_to_hospital = Column(String(200), nullable=True)
    referred_to_department = Column(String(100), nullable=True)
    referral_type = Column(Enum(ReferralType), default=ReferralType.INTERNAL)
    reason = Column(Text, nullable=False)
    clinical_summary = Column(Text)
    urgency = Column(String(20), default="routine")  # routine, urgent, emergency
    status = Column(Enum(ReferralStatus), default=ReferralStatus.PENDING)
    referral_date = Column(DateTime, default=datetime.utcnow)
    appointment_date = Column(Date, nullable=True)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
