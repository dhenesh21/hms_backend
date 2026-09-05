from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ClaimStatus(str, enum.Enum):
    DRAFT = "draft"
    PREAUTH_REQUESTED = "preauth_requested"
    PREAUTH_APPROVED = "preauth_approved"
    PREAUTH_REJECTED = "preauth_rejected"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PARTIAL_APPROVED = "partial_approved"
    REJECTED = "rejected"
    SETTLED = "settled"
    APPEALED = "appealed"


class InsuranceCompany(Base):
    __tablename__ = "insurance_companies"

    id = Column(Integer, primary_key=True, index=True)
    company_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(300), nullable=False)
    tpa_name = Column(String(200))
    contact_person = Column(String(200))
    phone = Column(String(20))
    email = Column(String(200))
    address = Column(Text)
    claim_submission_email = Column(String(200))
    portal_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    policies = relationship("InsurancePolicy", back_populates="company")


class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id = Column(Integer, primary_key=True, index=True)
    policy_number = Column(String(100), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("insurance_companies.id"), nullable=False)
    tpa_id = Column(String(100))
    policy_holder_name = Column(String(200), nullable=False)
    relation_to_patient = Column(String(50))  # self, spouse, parent, child
    sum_insured = Column(Float, nullable=False)
    policy_start_date = Column(Date, nullable=False)
    policy_end_date = Column(Date, nullable=False)
    room_rent_limit = Column(Float)           # per day limit
    icu_limit = Column(Float)
    copay_percent = Column(Float, default=0.0)
    deductible_amount = Column(Float, default=0.0)
    pre_existing_covered = Column(Boolean, default=False)
    waiting_period_days = Column(Integer, default=30)
    network_hospital = Column(Boolean, default=True)
    card_number = Column(String(100))
    group_policy = Column(Boolean, default=False)
    employer_name = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient")
    company = relationship("InsuranceCompany", back_populates="policies")
    claims = relationship("InsuranceClaim", back_populates="policy")


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_number = Column(String(30), unique=True, nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("insurance_policies.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ipd_admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=True)
    status = Column(Enum(ClaimStatus), default=ClaimStatus.DRAFT)

    # Pre-authorization
    preauth_number = Column(String(100))
    preauth_requested_at = Column(DateTime(timezone=True))
    preauth_approved_at = Column(DateTime(timezone=True))
    preauth_approved_amount = Column(Float)
    preauth_validity_date = Column(Date)
    preauth_notes = Column(Text)

    # Diagnosis & Treatment
    admission_diagnosis = Column(Text)
    icd_codes = Column(JSON, default=list)
    procedure_codes = Column(JSON, default=list)
    treating_doctor = Column(String(200))

    # Claim amounts
    claimed_amount = Column(Float, default=0.0)
    approved_amount = Column(Float, default=0.0)
    rejected_amount = Column(Float, default=0.0)
    deductible_applied = Column(Float, default=0.0)
    copay_amount = Column(Float, default=0.0)
    non_payable_amount = Column(Float, default=0.0)

    # Submission
    submitted_at = Column(DateTime(timezone=True))
    submission_reference = Column(String(200))
    documents_submitted = Column(JSON, default=list)

    # Settlement
    settled_at = Column(DateTime(timezone=True))
    settlement_reference = Column(String(200))
    payment_mode = Column(String(50))
    rejection_reason = Column(Text)
    non_payable_reason = Column(Text)

    # Appeal
    appealed_at = Column(DateTime(timezone=True))
    appeal_reason = Column(Text)
    appeal_status = Column(String(50))

    remarks = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    policy = relationship("InsurancePolicy", back_populates="claims")
    patient = relationship("Patient")
    documents = relationship("ClaimDocument", back_populates="claim")


class ClaimDocument(Base):
    __tablename__ = "claim_documents"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("insurance_claims.id"), nullable=False)
    document_type = Column(String(100), nullable=False)
    document_name = Column(String(300), nullable=False)
    file_path = Column(String(500))
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    claim = relationship("InsuranceClaim", back_populates="documents")
