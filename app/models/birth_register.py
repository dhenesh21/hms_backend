from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Float,
    Boolean,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class BabyGender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    AMBIGUOUS = "ambiguous"


class DeliveryType(str, enum.Enum):
    NORMAL_VAGINAL = "normal_vaginal"
    CESAREAN = "cesarean"
    ASSISTED_VAGINAL = "assisted_vaginal"  # forceps/vacuum


class BirthStatus(str, enum.Enum):
    LIVE_BIRTH = "live_birth"
    STILLBIRTH = "stillbirth"


class BirthRegister(Base):
    """
    One record per delivery/birth. Links to the mother's IPD admission
    (roadmap: "Mother Link") and can register multiple babies for the same
    delivery (twins/triplets) via the BirthBaby relationship.
    """
    __tablename__ = "birth_registers"

    id = Column(Integer, primary_key=True, index=True)
    birth_register_number = Column(String(20), unique=True, index=True, nullable=False)

    mother_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    mother_ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)

    delivery_datetime = Column(DateTime(timezone=True), server_default=func.now())
    delivery_type = Column(Enum(DeliveryType), default=DeliveryType.NORMAL_VAGINAL)
    attending_doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=True)
    attending_nurse_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    gravida = Column(Integer, nullable=True)  # number of pregnancies
    para = Column(Integer, nullable=True)     # number of births
    complications = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    registered_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    babies = relationship("BirthBaby", back_populates="birth_register")


class BirthBaby(Base):
    """
    Baby details for one birth register entry - roadmap's "Baby Details".
    A birth_register can have multiple babies (twins/triplets share the
    same delivery event but each gets their own record + certificate).
    """
    __tablename__ = "birth_babies"

    id = Column(Integer, primary_key=True, index=True)
    birth_register_id = Column(Integer, ForeignKey("birth_registers.id"), nullable=False)

    # The baby usually doesn't have their own UHID/patient record right at
    # birth - this can be linked later once formally registered as a patient.
    baby_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)

    baby_name = Column(String(200), nullable=True)  # often "Baby of <mother name>" initially
    gender = Column(Enum(BabyGender), nullable=False)
    birth_status = Column(Enum(BirthStatus), default=BirthStatus.LIVE_BIRTH)
    birth_weight_grams = Column(Float, nullable=True)
    birth_length_cm = Column(Float, nullable=True)
    apgar_score_1min = Column(Integer, nullable=True)
    apgar_score_5min = Column(Integer, nullable=True)

    birth_defects_notes = Column(Text, nullable=True)
    resuscitation_required = Column(Boolean, default=False)

    # Birth certificate tracking (roadmap: "Birth Certificate")
    certificate_number = Column(String(50), nullable=True)
    certificate_issued = Column(Boolean, default=False)
    certificate_issued_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    birth_register = relationship("BirthRegister", back_populates="babies")
