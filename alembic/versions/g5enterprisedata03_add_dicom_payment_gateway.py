"""add group5 enterprise data batch C-international (DICOM metadata, payment gateway plumbing)

Revision ID: g5enterprisedata03
Revises: g5enterprisedata02
Create Date: 2026-08-27 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5enterprisedata03'
down_revision: Union[str, None] = 'g5enterprisedata02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # DICOM metadata/worklist (international standard, items 247/248) and
    # Payment Gateway transaction tracking (item 252 plumbing) — the two
    # Batch C items that turned out to be buildable once reframed around
    # international standards instead of a named vendor. Same hand-written
    # approach as every prior migration; every column and enum
    # cross-checked against source models. NOT YET RUN against a live DB.
    op.create_table('dicom_studies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('study_instance_uid', sa.String(length=100), nullable=False, unique=True),
    sa.Column('radiology_order_id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('accession_number', sa.String(length=50), nullable=True),
    sa.Column('study_date', sa.Date(), nullable=True),
    sa.Column('study_time', sa.Time(), nullable=True),
    sa.Column('study_description', sa.String(length=300), nullable=True),
    sa.Column('referring_physician', sa.String(length=200), nullable=True),
    sa.Column('modality', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['radiology_order_id'], ['radiology_orders.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('dicom_series',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('series_instance_uid', sa.String(length=100), nullable=False, unique=True),
    sa.Column('study_id', sa.Integer(), nullable=False),
    sa.Column('series_number', sa.Integer(), nullable=True),
    sa.Column('modality', sa.String(length=20), nullable=True),
    sa.Column('body_part_examined', sa.String(length=100), nullable=True),
    sa.Column('series_description', sa.String(length=300), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['study_id'], ['dicom_studies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('dicom_instances',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sop_instance_uid', sa.String(length=100), nullable=False, unique=True),
    sa.Column('series_id', sa.Integer(), nullable=False),
    sa.Column('radiology_image_id', sa.Integer(), nullable=True),
    sa.Column('instance_number', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['series_id'], ['dicom_series.id'], ),
    sa.ForeignKeyConstraint(['radiology_image_id'], ['radiology_images.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('modality_worklist_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('radiology_order_id', sa.Integer(), nullable=False),
    sa.Column('accession_number', sa.String(length=50), nullable=False, unique=True),
    sa.Column('scheduled_station_ae_title', sa.String(length=50), nullable=True),
    sa.Column('scheduled_procedure_step_start_date', sa.Date(), nullable=True),
    sa.Column('scheduled_procedure_step_start_time', sa.Time(), nullable=True),
    sa.Column('modality', sa.String(length=20), nullable=True),
    sa.Column('requested_procedure_description', sa.String(length=300), nullable=True),
    sa.Column('status', sa.Enum('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'DISCONTINUED', name='workliststatus'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['radiology_order_id'], ['radiology_orders.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('payment_gateway_transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('bill_id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('gateway_name', sa.String(length=50), nullable=False),
    sa.Column('gateway_session_id', sa.String(length=300), nullable=True),
    sa.Column('gateway_transaction_id', sa.String(length=300), nullable=True),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('currency', sa.String(length=10), nullable=True),
    sa.Column('status', sa.Enum('INITIATED', 'PENDING', 'SUCCESS', 'FAILED', 'REFUNDED', name='gatewaytxnstatus'), nullable=True),
    sa.Column('failure_reason', sa.Text(), nullable=True),
    sa.Column('raw_webhook_payload', sa.JSON(), nullable=True),
    sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('payment_gateway_transactions')
    op.drop_table('modality_worklist_items')
    op.drop_table('dicom_instances')
    op.drop_table('dicom_series')
    op.drop_table('dicom_studies')
