"""add items 93,101-103,107,142-143,173,176,280,289,291 (pharmacy/billing/hr/privacy hardening)

Revision ID: g5enterprisedata05
Revises: g5enterprisedata04
Create Date: 2026-08-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5enterprisedata05'
down_revision: Union[str, None] = 'g5enterprisedata04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Batch 2 harden pass - Drug Return/Transfer/Stock Adjustment (101-103),
    # Package Line Items (142-143), Salary Structure + Shift Assignment
    # (176, 173), Medical Record Access Audit + Privacy Flags (291, 289).
    # Same hand-written-from-models approach as every migration in this
    # project; every column and enum cross-checked. NOT YET RUN against a
    # live database.

    # item 93 - new columns on the existing drug_master table
    op.add_column('drug_master', sa.Column('known_interactions', sa.Text(), nullable=True))
    op.add_column('drug_master', sa.Column('contraindications', sa.Text(), nullable=True))
    op.add_column('drug_master', sa.Column('pregnancy_category', sa.String(length=10), nullable=True))

    op.create_table('drug_returns',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('return_number', sa.String(length=20), nullable=False, unique=True),
    sa.Column('direction', sa.Enum('TO_SUPPLIER', 'FROM_PATIENT', name='returndirection'), nullable=False),
    sa.Column('status', sa.Enum('REQUESTED', 'APPROVED', 'COMPLETED', 'REJECTED', name='returnstatus'), nullable=True),
    sa.Column('drug_id', sa.Integer(), nullable=False),
    sa.Column('stock_id', sa.Integer(), nullable=True),
    sa.Column('dispense_item_id', sa.Integer(), nullable=True),
    sa.Column('supplier_id', sa.Integer(), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('requested_by', sa.Integer(), nullable=False),
    sa.Column('approved_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['drug_id'], ['drug_master.id'], ),
    sa.ForeignKeyConstraint(['stock_id'], ['drug_stock.id'], ),
    sa.ForeignKeyConstraint(['dispense_item_id'], ['dispense_items.id'], ),
    sa.ForeignKeyConstraint(['supplier_id'], ['pharmacy_suppliers.id'], ),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('drug_transfers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('transfer_number', sa.String(length=20), nullable=False, unique=True),
    sa.Column('stock_id', sa.Integer(), nullable=False),
    sa.Column('from_location', sa.String(length=100), nullable=True),
    sa.Column('to_location', sa.String(length=100), nullable=False),
    sa.Column('from_branch_id', sa.Integer(), nullable=True),
    sa.Column('to_branch_id', sa.Integer(), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('transferred_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['stock_id'], ['drug_stock.id'], ),
    sa.ForeignKeyConstraint(['from_branch_id'], ['branches.id'], ),
    sa.ForeignKeyConstraint(['to_branch_id'], ['branches.id'], ),
    sa.ForeignKeyConstraint(['transferred_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('stock_adjustments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('stock_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.Enum('DAMAGE', 'WASTAGE', 'THEFT_LOSS', 'EXPIRY_WRITE_OFF', 'STOCK_COUNT_CORRECTION', name='adjustmentreason'), nullable=False),
    sa.Column('quantity_before', sa.Integer(), nullable=False),
    sa.Column('quantity_after', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('adjusted_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['stock_id'], ['drug_stock.id'], ),
    sa.ForeignKeyConstraint(['adjusted_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('package_line_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('package_id', sa.Integer(), nullable=False),
    sa.Column('service_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=True),
    sa.Column('package_price', sa.Float(), nullable=False),
    sa.Column('standalone_price', sa.Float(), nullable=True),
    sa.Column('is_optional', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['package_id'], ['billing_packages.id'], ),
    sa.ForeignKeyConstraint(['service_id'], ['service_master.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('salary_structures',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('staff_id', sa.Integer(), nullable=False, unique=True),
    sa.Column('basic', sa.Float(), nullable=False),
    sa.Column('effective_from', sa.Date(), nullable=True, server_default=sa.text('(CURRENT_DATE)')),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['staff_id'], ['staff_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('salary_components',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('structure_id', sa.Integer(), nullable=False),
    sa.Column('component_name', sa.String(length=100), nullable=False),
    sa.Column('is_earning', sa.Boolean(), nullable=True),
    sa.Column('calc_type', sa.Enum('FIXED', 'PERCENT_OF_BASIC', 'PERCENT_OF_GROSS', name='componentcalctype'), nullable=True),
    sa.Column('value', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['structure_id'], ['salary_structures.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('shift_assignments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('staff_id', sa.Integer(), nullable=False),
    sa.Column('shift_date', sa.Date(), nullable=False),
    sa.Column('shift_name', sa.String(length=50), nullable=False),
    sa.Column('start_time', sa.String(length=5), nullable=False),
    sa.Column('end_time', sa.String(length=5), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['staff_id'], ['staff_profiles.id'], ),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('medical_record_access_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('accessed_by', sa.Integer(), nullable=False),
    sa.Column('resource_type', sa.String(length=100), nullable=False),
    sa.Column('resource_id', sa.String(length=50), nullable=True),
    sa.Column('access_reason', sa.String(length=200), nullable=True),
    sa.Column('was_restricted_record', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['accessed_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('patient_privacy_flags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False, unique=True),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('flagged_by', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['flagged_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('patient_privacy_flags')
    op.drop_table('medical_record_access_logs')
    op.drop_table('shift_assignments')
    op.drop_table('salary_components')
    op.drop_table('salary_structures')
    op.drop_table('package_line_items')
    op.drop_table('stock_adjustments')
    op.drop_table('drug_transfers')
    op.drop_table('drug_returns')
    op.drop_column('drug_master', 'pregnancy_category')
    op.drop_column('drug_master', 'contraindications')
    op.drop_column('drug_master', 'known_interactions')
