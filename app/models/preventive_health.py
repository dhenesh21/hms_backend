from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, Date, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class CheckupBookingStatus(str, enum.Enum):
    BOOKED = "booked"
    SAMPLES_COLLECTED = "samples_collected"
    IN_PROGRESS = "in_progress"
    REPORT_READY = "report_ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class HealthCheckupBooking(Base):
    """
    Preventive health check-up booking (items 192-194). Deliberately does NOT
    duplicate pricing/inclusions — those already live on the existing
    `BillingPackage` (billing_packages table); this just tracks the scheduling
    and clinical-completion workflow of redeeming one for an actual check-up
    visit, and ties the resulting reports/consult back to the patient.
    """
    __tablename__ = "health_checkup_bookings"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    package_id = Column(Integer, ForeignKey("billing_packages.id"), nullable=False)

    booked_date = Column(Date, server_default=func.current_date())
    scheduled_date = Column(Date, nullable=False)
    status = Column(Enum(CheckupBookingStatus), default=CheckupBookingStatus.BOOKED)

    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
    lab_order_id = Column(Integer, ForeignKey("lab_orders.id"), nullable=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=True)

    findings_summary = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
