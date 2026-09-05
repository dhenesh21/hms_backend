from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, Text, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class BloodGroup(str, enum.Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"


class MaritalStatus(str, enum.Enum):
    SINGLE = "single"
    MARRIED = "married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    uhid = Column(String(20), unique=True, index=True, nullable=False)  # Unique Hospital ID
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    blood_group = Column(Enum(BloodGroup))
    marital_status = Column(Enum(MaritalStatus))

    # Contact
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))
    country = Column(String(100), default="India")

    # Emergency contact
    emergency_contact_name = Column(String(200))
    emergency_contact_phone = Column(String(20))
    emergency_contact_relation = Column(String(50))

    # Medical info
    allergies = Column(Text)
    chronic_conditions = Column(Text)
    current_medications = Column(Text)
    height_cm = Column(Float)
    weight_kg = Column(Float)

    # Insurance
    insurance_provider = Column(String(200))
    insurance_policy_number = Column(String(100))
    insurance_validity = Column(Date)

    # Identity
    aadhar_number = Column(String(12))
    pan_number = Column(String(10))
    photo_url = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True)
    registered_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    admissions = relationship("Admission", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    opd_visits = relationship("OPDVisit", back_populates="patient")
