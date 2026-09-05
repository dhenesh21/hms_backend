import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Date, Enum, Text
from datetime import datetime
from app.core.database import Base


class BloodGroup(str, enum.Enum):
    A_POS = "A+"; A_NEG = "A-"; B_POS = "B+"; B_NEG = "B-"
    AB_POS = "AB+"; AB_NEG = "AB-"; O_POS = "O+"; O_NEG = "O-"


class DonorStatus(str, enum.Enum):
    ACTIVE = "active"; DEFERRED = "deferred"; INELIGIBLE = "ineligible"


class BloodRequestStatus(str, enum.Enum):
    PENDING = "pending"; APPROVED = "approved"; ISSUED = "issued"
    RETURNED = "returned"; REJECTED = "rejected"


class BloodDonor(Base):
    __tablename__ = "blood_donors"
    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(String(20), unique=True, index=True)
    name = Column(String(100), nullable=False)
    blood_group = Column(Enum(BloodGroup), nullable=False)
    age = Column(Integer)
    gender = Column(String(10))
    phone = Column(String(15))
    email = Column(String(100))
    address = Column(Text)
    last_donation_date = Column(Date, nullable=True)
    total_donations = Column(Integer, default=0)
    status = Column(Enum(DonorStatus), default=DonorStatus.ACTIVE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BloodStock(Base):
    __tablename__ = "blood_stock"
    id = Column(Integer, primary_key=True, index=True)
    blood_group = Column(Enum(BloodGroup), nullable=False, unique=True)
    units_available = Column(Float, default=0)
    units_reserved = Column(Float, default=0)
    minimum_stock = Column(Integer, default=2)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BloodDonation(Base):
    __tablename__ = "blood_donations"
    id = Column(Integer, primary_key=True, index=True)
    donation_number = Column(String(20), unique=True)
    donor_id = Column(Integer, ForeignKey("blood_donors.id"))
    blood_group = Column(Enum(BloodGroup), nullable=False)
    units = Column(Float, default=1.0)
    donation_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    bag_number = Column(String(20))
    collected_by = Column(String(100))
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BloodRequest(Base):
    __tablename__ = "blood_requests"
    id = Column(Integer, primary_key=True, index=True)
    request_number = Column(String(20), unique=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    blood_group = Column(Enum(BloodGroup), nullable=False)
    units_requested = Column(Float, nullable=False)
    units_issued = Column(Float, default=0)
    reason = Column(String(200))
    doctor_name = Column(String(100))
    priority = Column(String(20), default="routine")
    status = Column(Enum(BloodRequestStatus), default=BloodRequestStatus.PENDING)
    requested_date = Column(DateTime, default=datetime.utcnow)
    issued_date = Column(DateTime, nullable=True)
    notes = Column(Text)
