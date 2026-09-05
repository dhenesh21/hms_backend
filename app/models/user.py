from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    RECEPTIONIST = "receptionist"
    PHARMACIST = "pharmacist"
    LAB_TECHNICIAN = "lab_technician"
    RADIOLOGIST = "radiologist"
    ACCOUNTANT = "accountant"
    HR = "hr"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)

    phone = Column(String(20))
    department = Column(String(100))
    photo_url = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # MFA (TOTP-based 2FA) - roadmap's "Auth/MFA". mfa_secret is only set
    # once the user has confirmed a working code during setup (see
    # mfa_enabled), so a half-configured secret can never lock someone
    # out or silently gate their login.
    mfa_secret = Column(String(64), nullable=True)
    mfa_enabled = Column(Boolean, default=False)

    last_login = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    doctor_profile = relationship(
        "DoctorProfile",
        back_populates="user",
        uselist=False
    )

    admin_audit_logs = relationship(
        "AuditLog",
        back_populates="user"
    )

    opd_audit_logs = relationship(
        "OpdAuditLog",
        back_populates="user"
    )

# from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
