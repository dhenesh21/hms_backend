"""add group5 enterprise data batch A (MPI, registries, terminology, governance)

Revision ID: g5enterprisedata01
Revises: g4clinicaldepth03
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5enterprisedata01'
down_revision: Union[str, None] = 'g4clinicaldepth03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Group 5 Batch A — Master Patient Index, Provider Registry, Facility
    # Registry, Terminology Repository, Data Governance/Retention/Archival/
    # Quality (items 237-244). Same hand-written-from-models approach as
    # every prior Group 4/5 migration (no DB/network access in this
    # environment); every column and enum cross-checked against source
    # models — see GROUP4_ROADMAP.md. NOT YET RUN against a live database.
    op.create_table('mpi_match_candidates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id_a', sa.Integer(), nullable=False),
    sa.Column('patient_id_b', sa.Integer(), nullable=False),
    sa.Column('match_score', sa.Float(), nullable=False),
    sa.Column('match_reasons', sa.JSON(), nullable=True),
    sa.Column('status', sa.Enum('POTENTIAL_DUPLICATE', 'CONFIRMED_DUPLICATE', 'NOT_A_MATCH', 'MERGED', name='matchstatus'), nullable=True),
    sa.Column('reviewed_by', sa.Integer(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('review_notes', sa.Text(), nullable=True),
    sa.Column('merged_into_patient_id', sa.Integer(), nullable=True),
    sa.Column('merged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['patient_id_a'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['patient_id_b'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['merged_into_patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('patient_merge_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('match_candidate_id', sa.Integer(), nullable=False),
    sa.Column('surviving_patient_id', sa.Integer(), nullable=False),
    sa.Column('merged_patient_id', sa.Integer(), nullable=False),
    sa.Column('merged_patient_old_uhid', sa.String(length=20), nullable=True),
    sa.Column('merged_by', sa.Integer(), nullable=False),
    sa.Column('merge_notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['match_candidate_id'], ['mpi_match_candidates.id'], ),
    sa.ForeignKeyConstraint(['surviving_patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['merged_patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['merged_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('provider_registry_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('provider_type', sa.Enum('INDIVIDUAL_PRACTITIONER', 'FACILITY', 'LAB', 'PHARMACY', name='providertype'), nullable=False),
    sa.Column('national_registry_id', sa.String(length=100), nullable=True, unique=True),
    sa.Column('full_name', sa.String(length=300), nullable=False),
    sa.Column('specialization', sa.String(length=200), nullable=True),
    sa.Column('registration_council', sa.String(length=200), nullable=True),
    sa.Column('registration_valid_until', sa.Date(), nullable=True),
    sa.Column('linked_doctor_profile_id', sa.Integer(), nullable=True),
    sa.Column('is_internal', sa.Boolean(), nullable=True),
    sa.Column('is_verified', sa.Boolean(), nullable=True),
    sa.Column('contact_phone', sa.String(length=20), nullable=True),
    sa.Column('contact_email', sa.String(length=255), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['linked_doctor_profile_id'], ['doctor_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('facility_registry_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('facility_type', sa.Enum('HOSPITAL', 'CLINIC', 'LAB', 'PHARMACY', 'DIAGNOSTIC_CENTER', 'BLOOD_BANK', name='facilitytype'), nullable=False),
    sa.Column('name', sa.String(length=300), nullable=False),
    sa.Column('national_facility_id', sa.String(length=100), nullable=True, unique=True),
    sa.Column('is_self', sa.Boolean(), nullable=True),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('state', sa.String(length=100), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('contact_phone', sa.String(length=20), nullable=True),
    sa.Column('contact_email', sa.String(length=255), nullable=True),
    sa.Column('is_verified', sa.Boolean(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('terminology_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code_system', sa.Enum('ICD10', 'ICD11', 'SNOMED_CT', 'LOINC', 'RXNORM', 'CPT', 'LOCAL', name='codesystem'), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('display_name', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('parent_code', sa.String(length=50), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('terminology_mappings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_code_id', sa.Integer(), nullable=False),
    sa.Column('target_code_id', sa.Integer(), nullable=False),
    sa.Column('mapping_confidence', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['source_code_id'], ['terminology_codes.id'], ),
    sa.ForeignKeyConstraint(['target_code_id'], ['terminology_codes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('data_asset_registry',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('table_name', sa.String(length=200), nullable=False, unique=True),
    sa.Column('domain', sa.String(length=100), nullable=True),
    sa.Column('classification', sa.Enum('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED', name='dataclassification'), nullable=True),
    sa.Column('contains_phi', sa.Boolean(), nullable=True),
    sa.Column('business_owner', sa.String(length=200), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('retention_policies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('data_asset_id', sa.Integer(), nullable=False),
    sa.Column('retain_for_years', sa.Integer(), nullable=False),
    sa.Column('action_after_retention', sa.Enum('RETAIN', 'ARCHIVE', 'ANONYMIZE', 'DELETE', name='retentionaction'), nullable=True),
    sa.Column('legal_basis', sa.String(length=300), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['data_asset_id'], ['data_asset_registry.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('archival_jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('data_asset_id', sa.Integer(), nullable=False),
    sa.Column('triggered_by', sa.Integer(), nullable=False),
    sa.Column('cutoff_date', sa.Date(), nullable=False),
    sa.Column('records_affected', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['data_asset_id'], ['data_asset_registry.id'], ),
    sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('data_quality_rules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('rule_name', sa.String(length=200), nullable=False),
    sa.Column('data_asset_id', sa.Integer(), nullable=True),
    sa.Column('rule_type', sa.String(length=50), nullable=False),
    sa.Column('check_description', sa.Text(), nullable=False),
    sa.Column('severity', sa.String(length=20), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['data_asset_id'], ['data_asset_registry.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('data_quality_findings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('rule_id', sa.Integer(), nullable=False),
    sa.Column('affected_table', sa.String(length=200), nullable=True),
    sa.Column('affected_record_id', sa.Integer(), nullable=True),
    sa.Column('finding_details', sa.JSON(), nullable=True),
    sa.Column('resolved', sa.Boolean(), nullable=True),
    sa.Column('resolved_by', sa.Integer(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['rule_id'], ['data_quality_rules.id'], ),
    sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('data_quality_findings')
    op.drop_table('data_quality_rules')
    op.drop_table('archival_jobs')
    op.drop_table('retention_policies')
    op.drop_table('data_asset_registry')
    op.drop_table('terminology_mappings')
    op.drop_table('terminology_codes')
    op.drop_table('facility_registry_entries')
    op.drop_table('provider_registry_entries')
    op.drop_table('patient_merge_logs')
    op.drop_table('mpi_match_candidates')
