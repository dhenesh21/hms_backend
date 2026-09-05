from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Enum,
)
from sqlalchemy.sql import func

import enum

from app.core.database import Base


class IncidentType(str, enum.Enum):
    THEFT = "theft"
    VIOLENCE = "violence"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    VANDALISM = "vandalism"
    FIRE_SAFETY = "fire_safety"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    OTHER = "other"


class IncidentSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, enum.Enum):
    REPORTED = "reported"
    UNDER_INVESTIGATION = "under_investigation"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SecurityIncident(Base):
    __tablename__ = "security_incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_number = Column(String(20), unique=True, index=True, nullable=False)

    incident_type = Column(Enum(IncidentType), default=IncidentType.OTHER)
    severity = Column(Enum(IncidentSeverity), default=IncidentSeverity.MEDIUM)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.REPORTED)

    location = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    persons_involved = Column(Text, nullable=True)
    incident_datetime = Column(DateTime(timezone=True), server_default=func.now())

    police_informed = Column(String(10), default="no")
    police_report_number = Column(String(50), nullable=True)

    investigated_by = Column(String(200), nullable=True)
    investigation_notes = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    reported_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
