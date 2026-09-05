"""add radiology reporting fields: performed_by, equipment_id, report_template_id, critical finding flags

Revision ID: g5enterprisedata08
Revises: g5enterprisedata07
Create Date: 2026-09-04 00:00:00.000000

These columns existed on the RadiologyOrder model in one of the two
branches merged into this codebase but had no corresponding migration in
either branch's history (report_templates itself is created by
g5enterprisedata06). Added here so the migration chain matches the
merged models exactly.

Note: `equipment_id` references `equipment.id` (app/models/facility.py),
but no migration in this project's history creates that table - that gap
predates this merge and is not introduced by it. The FK is declared to
match the model; running this migration against a fresh database will
require adding an `equipment`-table migration first.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5enterprisedata08'
down_revision: Union[str, None] = 'g5enterprisedata07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('radiology_orders', sa.Column('performed_by', sa.Integer(), nullable=True))
    op.add_column('radiology_orders', sa.Column('equipment_id', sa.Integer(), nullable=True))
    op.add_column('radiology_orders', sa.Column('report_template_id', sa.Integer(), nullable=True))
    op.add_column('radiology_orders', sa.Column('is_critical_finding', sa.Boolean(), nullable=True))
    op.add_column('radiology_orders', sa.Column('critical_finding_notes', sa.Text(), nullable=True))
    op.add_column('radiology_orders', sa.Column('critical_finding_flagged_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('radiology_orders', sa.Column('critical_finding_acknowledged_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_radiology_orders_performed_by_users', 'radiology_orders', 'users', ['performed_by'], ['id'])
    op.create_foreign_key('fk_radiology_orders_report_template_id_report_templates', 'radiology_orders', 'report_templates', ['report_template_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_radiology_orders_report_template_id_report_templates', 'radiology_orders', type_='foreignkey')
    op.drop_constraint('fk_radiology_orders_performed_by_users', 'radiology_orders', type_='foreignkey')
    op.drop_column('radiology_orders', 'critical_finding_acknowledged_at')
    op.drop_column('radiology_orders', 'critical_finding_flagged_at')
    op.drop_column('radiology_orders', 'critical_finding_notes')
    op.drop_column('radiology_orders', 'is_critical_finding')
    op.drop_column('radiology_orders', 'report_template_id')
    op.drop_column('radiology_orders', 'equipment_id')
    op.drop_column('radiology_orders', 'performed_by')
