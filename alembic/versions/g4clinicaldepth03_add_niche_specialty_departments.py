"""add niche specialty clinical departments

Revision ID: g4clinicaldepth03
Revises: g4clinicaldepth02
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g4clinicaldepth03'
down_revision: Union[str, None] = 'g4clinicaldepth02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dialysis, Mental Health/Psychiatry, Fertility/IVF, Oncology, Transplant —
    # the 5 niche specialty departments (Batch 3 items 69, 73, 74, 75, 76).
    # Same hand-written-from-models approach as g4clinicaldepth01/02 (no
    # network access to run alembic autogenerate against a live DB); every
    # column and enum cross-checked against the source models — see
    # GROUP4_ROADMAP.md. NOT YET RUN against a live database.
    op.create_table('dialysis_patient_profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False, unique=True),
    sa.Column('nephrologist_id', sa.Integer(), nullable=False),
    sa.Column('modality', sa.Enum('HEMODIALYSIS', 'PERITONEAL_DIALYSIS', 'CRRT', name='dialysismodality'), nullable=True),
    sa.Column('access_type', sa.Enum('AV_FISTULA', 'AV_GRAFT', 'CENTRAL_CATHETER', 'PERITONEAL_CATHETER', name='dialysisaccesstype'), nullable=False),
    sa.Column('access_site', sa.String(length=100), nullable=True),
    sa.Column('dry_weight_kg', sa.Float(), nullable=True),
    sa.Column('frequency_per_week', sa.Integer(), nullable=True),
    sa.Column('primary_renal_diagnosis', sa.String(length=300), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['nephrologist_id'], ['doctor_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('dialysis_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.Enum('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'INTERRUPTED', name='dialysissessionstatus'), nullable=True),
    sa.Column('machine_id', sa.String(length=50), nullable=True),
    sa.Column('technician_id', sa.Integer(), nullable=True),
    sa.Column('pre_weight_kg', sa.Float(), nullable=True),
    sa.Column('post_weight_kg', sa.Float(), nullable=True),
    sa.Column('fluid_removed_ml', sa.Integer(), nullable=True),
    sa.Column('duration_minutes', sa.Integer(), nullable=True),
    sa.Column('pre_bp_systolic', sa.Integer(), nullable=True),
    sa.Column('pre_bp_diastolic', sa.Integer(), nullable=True),
    sa.Column('post_bp_systolic', sa.Integer(), nullable=True),
    sa.Column('post_bp_diastolic', sa.Integer(), nullable=True),
    sa.Column('complications', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['profile_id'], ['dialysis_patient_profiles.id'], ),
    sa.ForeignKeyConstraint(['technician_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('psychiatric_assessments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('psychiatrist_id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=50), nullable=True),
    sa.Column('source_id', sa.Integer(), nullable=True),
    sa.Column('presenting_complaint', sa.Text(), nullable=False),
    sa.Column('mental_status_exam', sa.Text(), nullable=True),
    sa.Column('risk_self_harm', sa.Enum('NONE', 'LOW', 'MODERATE', 'HIGH', 'IMMINENT', name='risklevel'), nullable=True),
    sa.Column('risk_to_others', sa.Enum('NONE', 'LOW', 'MODERATE', 'HIGH', 'IMMINENT', name='risklevel'), nullable=True),
    sa.Column('provisional_diagnosis', sa.String(length=300), nullable=True),
    sa.Column('icd_code', sa.String(length=20), nullable=True),
    sa.Column('safety_plan_created', sa.Boolean(), nullable=True),
    sa.Column('family_involved', sa.Boolean(), nullable=True),
    sa.Column('assessed_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['psychiatrist_id'], ['doctor_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('mental_health_care_plans',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('assessment_id', sa.Integer(), nullable=True),
    sa.Column('psychiatrist_id', sa.Integer(), nullable=False),
    sa.Column('diagnosis', sa.String(length=300), nullable=False),
    sa.Column('treatment_modalities', sa.JSON(), nullable=True),
    sa.Column('goals', sa.JSON(), nullable=True),
    sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'DISCONTINUED', name='mentalhealthplanstatus'), nullable=True),
    sa.Column('next_review_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['assessment_id'], ['psychiatric_assessments.id'], ),
    sa.ForeignKeyConstraint(['psychiatrist_id'], ['doctor_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('therapy_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('care_plan_id', sa.Integer(), nullable=False),
    sa.Column('therapist_id', sa.Integer(), nullable=True),
    sa.Column('session_type', sa.String(length=100), nullable=True),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('attended', sa.Boolean(), nullable=True),
    sa.Column('session_notes', sa.Text(), nullable=True),
    sa.Column('risk_reassessed', sa.Enum('NONE', 'LOW', 'MODERATE', 'HIGH', 'IMMINENT', name='risklevel'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['care_plan_id'], ['mental_health_care_plans.id'], ),
    sa.ForeignKeyConstraint(['therapist_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('fertility_patient_profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False, unique=True),
    sa.Column('fertility_specialist_id', sa.Integer(), nullable=False),
    sa.Column('partner_patient_id', sa.Integer(), nullable=True),
    sa.Column('partner_name', sa.String(length=200), nullable=True),
    sa.Column('diagnosis', sa.String(length=300), nullable=True),
    sa.Column('amh_level', sa.Float(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['fertility_specialist_id'], ['doctor_profiles.id'], ),
    sa.ForeignKeyConstraint(['partner_patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('fertility_cycles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('treatment_type', sa.Enum('IUI', 'IVF', 'ICSI', 'FET', 'OVULATION_INDUCTION', 'FERTILITY_PRESERVATION', name='treatmenttype'), nullable=False),
    sa.Column('status', sa.Enum('PLANNED', 'STIMULATION', 'RETRIEVAL', 'TRANSFER', 'LUTEAL_SUPPORT', 'PREGNANCY_TEST_DUE', 'SUCCESSFUL', 'UNSUCCESSFUL', 'CANCELLED', name='fertilitycyclestatus'), nullable=True),
    sa.Column('cycle_start_date', sa.Date(), nullable=True),
    sa.Column('stimulation_protocol', sa.String(length=200), nullable=True),
    sa.Column('eggs_retrieved', sa.Integer(), nullable=True),
    sa.Column('embryos_created', sa.Integer(), nullable=True),
    sa.Column('embryos_transferred', sa.Integer(), nullable=True),
    sa.Column('embryos_frozen', sa.Integer(), nullable=True),
    sa.Column('transfer_date', sa.Date(), nullable=True),
    sa.Column('pregnancy_test_date', sa.Date(), nullable=True),
    sa.Column('pregnancy_test_result', sa.String(length=20), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['profile_id'], ['fertility_patient_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('fertility_monitoring_visits',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cycle_id', sa.Integer(), nullable=False),
    sa.Column('visit_date', sa.Date(), nullable=True, server_default=sa.text('(CURRENT_DATE)')),
    sa.Column('day_of_cycle', sa.Integer(), nullable=True),
    sa.Column('follicle_counts', sa.JSON(), nullable=True),
    sa.Column('endometrial_thickness_mm', sa.Float(), nullable=True),
    sa.Column('estradiol_level', sa.Float(), nullable=True),
    sa.Column('lh_level', sa.Float(), nullable=True),
    sa.Column('medication_adjustment', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['cycle_id'], ['fertility_cycles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('oncology_cases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('oncologist_id', sa.Integer(), nullable=False),
    sa.Column('primary_site', sa.String(length=200), nullable=False),
    sa.Column('histology', sa.String(length=300), nullable=True),
    sa.Column('stage', sa.Enum('STAGE_0', 'STAGE_I', 'STAGE_II', 'STAGE_III', 'STAGE_IV', 'UNKNOWN', name='cancerstage'), nullable=True),
    sa.Column('diagnosis_date', sa.Date(), nullable=True),
    sa.Column('treatment_intent', sa.Enum('CURATIVE', 'PALLIATIVE', 'ADJUVANT', 'NEOADJUVANT', name='treatmentintent'), nullable=True),
    sa.Column('tumor_board_reviewed', sa.Boolean(), nullable=True),
    sa.Column('tumor_board_notes', sa.Text(), nullable=True),
    sa.Column('chemo_protocol_name', sa.String(length=200), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['oncologist_id'], ['doctor_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('chemo_cycles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('cycle_number', sa.Integer(), nullable=False),
    sa.Column('scheduled_date', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('SCHEDULED', 'ADMINISTERED', 'DELAYED', 'SKIPPED', name='chemocyclestatus'), nullable=True),
    sa.Column('drugs_administered', sa.JSON(), nullable=True),
    sa.Column('body_surface_area', sa.String(length=20), nullable=True),
    sa.Column('pre_cycle_labs_reviewed', sa.Boolean(), nullable=True),
    sa.Column('toxicity_grade', sa.Integer(), nullable=True),
    sa.Column('adverse_events', sa.Text(), nullable=True),
    sa.Column('delay_reason', sa.Text(), nullable=True),
    sa.Column('administered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['case_id'], ['oncology_cases.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('oncology_follow_ups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('visit_date', sa.Date(), nullable=True, server_default=sa.text('(CURRENT_DATE)')),
    sa.Column('response_assessment', sa.String(length=100), nullable=True),
    sa.Column('imaging_reviewed', sa.Boolean(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('next_follow_up_date', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['case_id'], ['oncology_cases.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('transplant_candidates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('transplant_surgeon_id', sa.Integer(), nullable=False),
    sa.Column('organ_needed', sa.Enum('KIDNEY', 'LIVER', 'HEART', 'LUNG', 'PANCREAS', 'CORNEA', 'BONE_MARROW', name='organtype'), nullable=False),
    sa.Column('blood_group', sa.String(length=5), nullable=True),
    sa.Column('listed_date', sa.Date(), nullable=True, server_default=sa.text('(CURRENT_DATE)')),
    sa.Column('urgency_score', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('ACTIVE', 'ON_HOLD', 'TRANSPLANTED', 'REMOVED', 'DECEASED', name='waitliststatus'), nullable=True),
    sa.Column('workup_complete', sa.Boolean(), nullable=True),
    sa.Column('hla_typing_done', sa.Boolean(), nullable=True),
    sa.Column('ethics_committee_cleared', sa.Boolean(), nullable=True),
    sa.Column('removed_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['transplant_surgeon_id'], ['doctor_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('transplant_cases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('candidate_id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('transplant_surgeon_id', sa.Integer(), nullable=False),
    sa.Column('organ', sa.Enum('KIDNEY', 'LIVER', 'HEART', 'LUNG', 'PANCREAS', 'CORNEA', 'BONE_MARROW', name='organtype'), nullable=False),
    sa.Column('donor_type', sa.Enum('LIVING_RELATED', 'LIVING_UNRELATED', 'DECEASED', name='donortype'), nullable=False),
    sa.Column('donor_patient_id', sa.Integer(), nullable=True),
    sa.Column('donor_relation', sa.String(length=100), nullable=True),
    sa.Column('surgery_date', sa.Date(), nullable=True),
    sa.Column('ot_surgery_id', sa.Integer(), nullable=True),
    sa.Column('cross_match_result', sa.String(length=50), nullable=True),
    sa.Column('immunosuppression_protocol', sa.Text(), nullable=True),
    sa.Column('outcome', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['candidate_id'], ['transplant_candidates.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['transplant_surgeon_id'], ['doctor_profiles.id'], ),
    sa.ForeignKeyConstraint(['donor_patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['ot_surgery_id'], ['surgeries.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('transplant_follow_ups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_id', sa.Integer(), nullable=False),
    sa.Column('visit_date', sa.Date(), nullable=True, server_default=sa.text('(CURRENT_DATE)')),
    sa.Column('days_post_transplant', sa.Integer(), nullable=True),
    sa.Column('graft_function_status', sa.String(length=100), nullable=True),
    sa.Column('rejection_signs', sa.Boolean(), nullable=True),
    sa.Column('immunosuppression_levels', sa.JSON(), nullable=True),
    sa.Column('medication_adjustment', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['case_id'], ['transplant_cases.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('transplant_follow_ups')
    op.drop_table('transplant_cases')
    op.drop_table('transplant_candidates')
    op.drop_table('oncology_follow_ups')
    op.drop_table('chemo_cycles')
    op.drop_table('oncology_cases')
    op.drop_table('fertility_monitoring_visits')
    op.drop_table('fertility_cycles')
    op.drop_table('fertility_patient_profiles')
    op.drop_table('therapy_sessions')
    op.drop_table('mental_health_care_plans')
    op.drop_table('psychiatric_assessments')
    op.drop_table('dialysis_sessions')
    op.drop_table('dialysis_patient_profiles')
