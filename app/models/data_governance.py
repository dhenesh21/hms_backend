from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Boolean, Enum, JSON, Date)
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class DataClassification(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"      # e.g. mental health, HIV status — extra-sensitive


class RetentionAction(str, enum.Enum):
    RETAIN = "retain"
    ARCHIVE = "archive"
    ANONYMIZE = "anonymize"
    DELETE = "delete"


class DataAssetRegistry(Base):
    """
    Item 242 (Data Governance) — a catalog of what tables/domains hold what
    kind of data, who owns them, and how sensitive they are. This is
    metadata ABOUT the schema, not a runtime enforcement engine — it doesn't
    change what any endpoint returns; it's the documentation layer a
    governance/compliance function needs (which tables have PHI, who's the
    business owner, what's the retention policy) that usually doesn't exist
    anywhere until someone writes it down. Seeding this for all ~150 tables
    in this codebase is a data-entry task for whoever owns each domain, not
    something to fabricate placeholder entries for here.
    """
    __tablename__ = "data_asset_registry"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(200), nullable=False, unique=True)
    domain = Column(String(100), nullable=True)         # e.g. "clinical", "billing", "hr"
    classification = Column(Enum(DataClassification), default=DataClassification.INTERNAL)
    contains_phi = Column(Boolean, default=False)
    business_owner = Column(String(200), nullable=True)   # role/team name, not necessarily a User row
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RetentionPolicy(Base):
    """Item 243 (Data Retention) — declared policy per data asset. Enforcement
    (an actual scheduled job that archives/deletes) is a separate concern
    (background job infra, Group 6 scope) — this is the policy declaration
    those jobs would read, not the job runner itself."""
    __tablename__ = "retention_policies"

    id = Column(Integer, primary_key=True, index=True)
    data_asset_id = Column(Integer, ForeignKey("data_asset_registry.id"), nullable=False)
    retain_for_years = Column(Integer, nullable=False)
    action_after_retention = Column(Enum(RetentionAction), default=RetentionAction.ARCHIVE)
    legal_basis = Column(String(300), nullable=True)   # e.g. "local medical records regulation, 8 years"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ArchivalJob(Base):
    """Item 244 (Data Archival) — a record of an archival run (manually
    triggered here; a scheduler wiring it to run automatically is Group 6
    infra scope, same reasoning as RetentionPolicy above)."""
    __tablename__ = "archival_jobs"

    id = Column(Integer, primary_key=True, index=True)
    data_asset_id = Column(Integer, ForeignKey("data_asset_registry.id"), nullable=False)
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    cutoff_date = Column(Date, nullable=False)      # records older than this were targeted
    records_affected = Column(Integer, nullable=True)
    status = Column(String(50), default="completed")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DataQualityRule(Base):
    """
    Item 241 (Data Quality Management) — configurable checks (not hardcoded
    per-table validation, so new rules don't need a code change), e.g.
    "patients.phone must be 10 digits" or "no ClinicalOrder older than 24h
    still in 'ordered' status". A rule's `check_query_description` is
    documentation of what a human/scheduled job should check — this session
    doesn't wire a query execution engine here (that's real SQL-injection
    surface if rules were arbitrary stored SQL executed automatically; a
    proper implementation should use parameterized, code-reviewed checks per
    rule type, not free-text SQL from a database row).
    """
    __tablename__ = "data_quality_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(200), nullable=False)
    data_asset_id = Column(Integer, ForeignKey("data_asset_registry.id"), nullable=True)
    rule_type = Column(String(50), nullable=False)   # completeness, validity, consistency, timeliness
    check_description = Column(Text, nullable=False)
    severity = Column(String(20), default="warning")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DataQualityFinding(Base):
    """A logged result of running a rule — who/what failed it, when."""
    __tablename__ = "data_quality_findings"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("data_quality_rules.id"), nullable=False)
    affected_table = Column(String(200), nullable=True)
    affected_record_id = Column(Integer, nullable=True)
    finding_details = Column(JSON, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
