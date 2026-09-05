"""add nurse ward roster table

Revision ID: g4clinicaldepth02
Revises: g4clinicaldepth01
Create Date: 2026-08-24 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g4clinicaldepth02'
down_revision: Union[str, None] = 'g4clinicaldepth01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Closes the "no ward-to-nurse roster" gap flagged for Nurse Portal (item 186).
    # NOT YET RUN against a live database in this environment.
    op.create_table('nurse_ward_assignments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nurse_id', sa.Integer(), nullable=False),
    sa.Column('ward_id', sa.Integer(), nullable=False),
    sa.Column('assignment_date', sa.Date(), nullable=False, server_default=sa.text('(CURRENT_DATE)')),
    sa.Column('shift', sa.Enum('MORNING', 'EVENING', 'NIGHT', name='shifttype'), nullable=False),
    sa.Column('is_charge_nurse', sa.Boolean(), nullable=True),
    sa.Column('assigned_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['nurse_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['ward_id'], ['wards.id'], ),
    sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('nurse_ward_assignments')
