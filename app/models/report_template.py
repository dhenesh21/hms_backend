from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class ReportDepartment(str, enum.Enum):
    RADIOLOGY = "radiology"
    LAB = "lab"


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True, index=True)
    department = Column(Enum(ReportDepartment), nullable=False)
    category = Column(String(100), nullable=False)
    template_name = Column(String(200), nullable=False)

    findings_template = Column(Text, nullable=False)
    impression_template = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
