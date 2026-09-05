"""add doctor-staff profile link (item 171)

Revision ID: g5enterprisedata07
Revises: g5enterprisedata06
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5enterprisedata07'
down_revision: Union[str, None] = 'g5enterprisedata06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Item 171 - safe additive link between doctor_profiles and
    # staff_profiles rather than a destructive table merge (see
    # DoctorProfile's docstring in models/doctor.py for why). Nullable and
    # unique: a doctor links to at most one staff record, and a staff
    # record is claimed by at most one doctor.
    op.add_column(
        'doctor_profiles',
        sa.Column('staff_profile_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_doctor_profiles_staff_profile_id', 'doctor_profiles',
        'staff_profiles', ['staff_profile_id'], ['id']
    )
    op.create_unique_constraint(
        'uq_doctor_profiles_staff_profile_id', 'doctor_profiles', ['staff_profile_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_doctor_profiles_staff_profile_id', 'doctor_profiles', type_='unique')
    op.drop_constraint('fk_doctor_profiles_staff_profile_id', 'doctor_profiles', type_='foreignkey')
    op.drop_column('doctor_profiles', 'staff_profile_id')
