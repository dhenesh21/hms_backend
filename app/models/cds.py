from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, JSON)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class CDSRuleType(str, enum.Enum):
    DRUG_INTERACTION = "drug_interaction"      # two drug name-fragments that shouldn't co-occur
    DUPLICATE_THERAPY = "duplicate_therapy"     # same drug class ordered twice
    MAX_DOSE = "max_dose"                       # keyword-based dose ceiling warning
    AGE_RESTRICTION = "age_restriction"         # drug not advised below/above an age
    GENERAL_ALERT = "general_alert"             # free-form condition-triggered reminder


class CDSSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CDSRule(Base):
    """
    Configurable rule table — deliberately NOT a hardcoded drug-interaction
    database (that needs a licensed source like FDB/RxNorm, out of scope here).
    Instead, hospital pharmacy/clinical staff maintain simple keyword-pair rules
    that get checked at CPOE order time. This is a real but intentionally modest
    CDS: string-match against two drug-name fragments, not pharmacological
    reasoning. Flagged in the roadmap so it's never mistaken for a licensed
    interaction database.
    """
    __tablename__ = "cds_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(200), nullable=False)
    rule_type = Column(Enum(CDSRuleType), nullable=False)
    severity = Column(Enum(CDSSeverity), default=CDSSeverity.WARNING)

    trigger_keyword = Column(String(200), nullable=False)     # matched against the new order's item_name
    conflict_keyword = Column(String(200), nullable=True)     # matched against other active orders (interaction/duplicate)
    min_age = Column(Integer, nullable=True)                  # for age_restriction
    max_age = Column(Integer, nullable=True)

    message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CDSAlertLog(Base):
    """Every alert actually fired at order time — an audit trail of what was
    shown to the ordering doctor, and whether they overrode it."""
    __tablename__ = "cds_alert_logs"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("cds_rules.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    clinical_order_id = Column(Integer, ForeignKey("clinical_orders.id"), nullable=True)

    severity = Column(Enum(CDSSeverity), nullable=False)
    message = Column(Text, nullable=False)
    was_overridden = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    overridden_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
