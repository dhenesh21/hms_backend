"""add group5 enterprise data batch B (FHIR, HL7, consent exchange, SSO)

Revision ID: g5enterprisedata02
Revises: g5enterprisedata01
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5enterprisedata02'
down_revision: Union[str, None] = 'g5enterprisedata01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Group 5 Batch B — FHIR access audit, Consent-based Data Exchange,
    # Identity Provider/SSO (items 245-246 need no new tables, they are
    # pure read-facades/generators over existing data; 254 and 258 do).
    # Same hand-written-from-models approach as every prior migration in
    # this project; every column and enum cross-checked against source
    # models. NOT YET RUN against a live database.
    op.create_table('fhir_access_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('accessed_by', sa.Integer(), nullable=False),
    sa.Column('resource_type', sa.String(length=50), nullable=False),
    sa.Column('resource_id', sa.String(length=50), nullable=True),
    sa.Column('patient_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['accessed_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('data_exchange_authorizations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('authorized_facility_id', sa.Integer(), nullable=True),
    sa.Column('authorized_provider_id', sa.Integer(), nullable=True),
    sa.Column('authorized_party_name_freetext', sa.String(length=300), nullable=True),
    sa.Column('data_categories', sa.JSON(), nullable=True),
    sa.Column('purpose', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('ACTIVE', 'EXPIRED', 'REVOKED', name='exchangeauthstatus'), nullable=True),
    sa.Column('consented_by_name', sa.String(length=200), nullable=True),
    sa.Column('signature_data', sa.Text(), nullable=True),
    sa.Column('granted_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['authorized_facility_id'], ['facility_registry_entries.id'], ),
    sa.ForeignKeyConstraint(['authorized_provider_id'], ['provider_registry_entries.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('data_exchange_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('authorization_id', sa.Integer(), nullable=False),
    sa.Column('accessed_by_user_id', sa.Integer(), nullable=True),
    sa.Column('data_category', sa.Enum('DEMOGRAPHICS', 'DIAGNOSES', 'MEDICATIONS', 'LAB_RESULTS', 'IMAGING', 'ALLERGIES', 'FULL_RECORD', name='datacategory'), nullable=False),
    sa.Column('record_count', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['authorization_id'], ['data_exchange_authorizations.id'], ),
    sa.ForeignKeyConstraint(['accessed_by_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('oidc_provider_configs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('provider_name', sa.String(length=100), nullable=False),
    sa.Column('issuer', sa.String(length=500), nullable=False),
    sa.Column('client_id', sa.String(length=300), nullable=False),
    sa.Column('client_secret', sa.String(length=500), nullable=False),
    sa.Column('authorization_endpoint', sa.String(length=500), nullable=False),
    sa.Column('token_endpoint', sa.String(length=500), nullable=False),
    sa.Column('userinfo_endpoint', sa.String(length=500), nullable=True),
    sa.Column('redirect_uri', sa.String(length=500), nullable=False),
    sa.Column('scopes', sa.String(length=300), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('sso_identity_links',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('provider_id', sa.Integer(), nullable=False),
    sa.Column('external_subject_id', sa.String(length=300), nullable=False),
    sa.Column('linked_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['provider_id'], ['oidc_provider_configs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('sso_identity_links')
    op.drop_table('oidc_provider_configs')
    op.drop_table('data_exchange_logs')
    op.drop_table('data_exchange_authorizations')
    op.drop_table('fhir_access_logs')
