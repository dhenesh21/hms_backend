from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ReportType(str, enum.Enum):
    OPD_SUMMARY = "opd_summary"
    IPD_SUMMARY = "ipd_summary"
    REVENUE = "revenue"
    COLLECTION = "collection"
    OUTSTANDING = "outstanding"
    PHARMACY_SALES = "pharmacy_sales"
    LAB_SUMMARY = "lab_summary"
    RADIOLOGY_SUMMARY = "radiology_summary"
    PATIENT_REGISTER = "patient_register"
    DOCTOR_WISE = "doctor_wise"
    DEPARTMENT_WISE = "department_wise"
    INSURANCE_CLAIMS = "insurance_claims"
    BED_OCCUPANCY = "bed_occupancy"
    DISCHARGE_SUMMARY = "discharge_summary"
    MIS = "mis_dashboard"


class ReportFormat(str, enum.Enum):
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"


class SavedReport(Base):
    __tablename__ = "saved_reports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    parameters = Column(JSON, default=dict)   # date range, filters etc
    format = Column(Enum(ReportFormat), default=ReportFormat.JSON)
    file_path = Column(String(500))
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    generated_by = Column(Integer, ForeignKey("users.id"))
    file_size_kb = Column(Integer)
    is_active = Column(Boolean, default=True)


class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    frequency = Column(String(20), nullable=False)  # daily, weekly, monthly
    send_to_emails = Column(JSON, default=list)
    parameters = Column(JSON, default=dict)
    last_run = Column(DateTime(timezone=True))
    next_run = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
