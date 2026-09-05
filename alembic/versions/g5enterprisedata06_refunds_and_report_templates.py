"""add refund workflow and report templates (items 146-149, 90)

Revision ID: g5enterprisedata06
Revises: g5enterprisedata05
Create Date: 2026-08-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5enterprisedata06'
down_revision: Union[str, None] = 'g5enterprisedata05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Refund request/approval/reversal workflow (items 146-149) and
    # standardized standardized report templates for lab/radiology reporting
    # (item 90). Same hand-written-from-models approach as every migration
    # in this project; every column and enum cross-checked against source
    # models. NOT YET RUN against a live database.
    op.create_table('refund_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('refund_number', sa.String(length=20), nullable=False, unique=True),
    sa.Column('original_payment_id', sa.Integer(), nullable=False),
    sa.Column('bill_id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('REQUESTED', 'APPROVED', 'REJECTED', 'REVERSED', name='refundstatus'), nullable=True),
    sa.Column('refund_payment_id', sa.Integer(), nullable=True),
    sa.Column('requested_by', sa.Integer(), nullable=False),
    sa.Column('approved_by', sa.Integer(), nullable=True),
    sa.Column('reversed_by', sa.Integer(), nullable=True),
    sa.Column('reversal_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reversed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['original_payment_id'], ['payments.id'], ),
    sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ),
    sa.ForeignKeyConstraint(['refund_payment_id'], ['payments.id'], ),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['reversed_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('report_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('department', sa.Enum('RADIOLOGY', 'LAB', name='reportdepartment'), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=False),
    sa.Column('template_name', sa.String(length=200), nullable=False),
    sa.Column('findings_template', sa.Text(), nullable=False),
    sa.Column('impression_template', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('report_templates')
    op.drop_table('refund_requests')
