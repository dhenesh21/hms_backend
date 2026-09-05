"""add MFA (TOTP) fields to users table

Revision ID: g5enterprisedata09
Revises: g5enterprisedata08
Create Date: 2026-09-04 00:00:00.000000

Same situation as g5enterprisedata08: mfa_secret/mfa_enabled exist on the
User model but had no corresponding migration in either merged branch's
history.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5enterprisedata09'
down_revision: Union[str, None] = 'g5enterprisedata08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('mfa_secret', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'mfa_secret')
