"""add group3 supply chain and finance (accounts, inventory, medical coding) plus appointment token uniqueness

Revision ID: g5enterprisedata04
Revises: g5enterprisedata03
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5enterprisedata04'
down_revision: Union[str, None] = 'g5enterprisedata03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Group 3 (Supply Chain + Finance) tables — built by a separate
    # contributor in parallel with Group 4/5, merged in this session.
    # No migration existed for these in the incoming branch (same gap as
    # everything else in this project until a migration was written), so
    # generated + cross-verified here the same way as every other
    # migration in this project. Also adds the doctor/date/token uniqueness
    # constraint that appointment.py picked up during the same merge
    # (prevents double-booking the same token number for a doctor on the
    # same day under concurrent requests).
    op.create_table('accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_code', sa.String(length=20), nullable=False, unique=True),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('account_type', sa.Enum('ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE', name='accounttype'), nullable=False),
    sa.Column('is_cash', sa.Boolean(), nullable=True),
    sa.Column('is_bank', sa.Boolean(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('opening_balance', sa.Float(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('journal_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entry_number', sa.String(length=20), nullable=False, unique=True),
    sa.Column('entry_date', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('narration', sa.Text(), nullable=False),
    sa.Column('reference', sa.String(length=200), nullable=True),
    sa.Column('cost_center', sa.String(length=100), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('gl_postings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_type', sa.Enum('BILL', 'PAYMENT', 'PURCHASE_ORDER', name='glpostingsourcetype'), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('journal_entry_id', sa.Integer(), nullable=False),
    sa.Column('posted_by', sa.Integer(), nullable=True),
    sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['journal_entry_id'], ['journal_entries.id'], ),
    sa.ForeignKeyConstraint(['posted_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('journal_lines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entry_id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('debit', sa.Float(), nullable=True),
    sa.Column('credit', sa.Float(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['entry_id'], ['journal_entries.id'], ),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('inventory_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item_code', sa.String(length=30), nullable=False, unique=True),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('category', sa.Enum('CONSUMABLE', 'ASSET', 'STATIONERY', 'GENERAL', name='itemcategory'), nullable=True),
    sa.Column('unit', sa.String(length=30), nullable=True),
    sa.Column('reorder_level', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('inventory_vendors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('contact_person', sa.String(length=200), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('email', sa.String(length=200), nullable=True),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('inventory_purchase_orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('po_number', sa.String(length=20), nullable=False, unique=True),
    sa.Column('vendor_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'SENT', 'PARTIALLY_RECEIVED', 'RECEIVED', 'CANCELLED', name='postatus'), nullable=True),
    sa.Column('order_date', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('expected_delivery_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['vendor_id'], ['inventory_vendors.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('inventory_po_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('po_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('quantity_ordered', sa.Integer(), nullable=False),
    sa.Column('quantity_received', sa.Integer(), nullable=True),
    sa.Column('unit_price', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['po_id'], ['inventory_purchase_orders.id'], ),
    sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('inventory_grn',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('grn_number', sa.String(length=20), nullable=False, unique=True),
    sa.Column('po_id', sa.Integer(), nullable=False),
    sa.Column('received_date', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.Column('received_by', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['po_id'], ['inventory_purchase_orders.id'], ),
    sa.ForeignKeyConstraint(['received_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('inventory_grn_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('grn_id', sa.Integer(), nullable=False),
    sa.Column('po_item_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('quantity_received', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['grn_id'], ['inventory_grn.id'], ),
    sa.ForeignKeyConstraint(['po_item_id'], ['inventory_po_items.id'], ),
    sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('inventory_stock',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('location', sa.String(length=100), nullable=True),
    sa.Column('quantity_available', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('inventory_movements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('movement_type', sa.Enum('ISSUE', 'TRANSFER', 'RETURN', 'ADJUSTMENT', name='movementtype'), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('from_location', sa.String(length=100), nullable=True),
    sa.Column('to_location', sa.String(length=100), nullable=True),
    sa.Column('department', sa.String(length=100), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('moved_by', sa.Integer(), nullable=True),
    sa.Column('moved_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ),
    sa.ForeignKeyConstraint(['moved_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('medical_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code_system', sa.Enum('ICD10', 'CPT', name='medicalcodingcodesystem'), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('is_active', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('patient_coding',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('bill_id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('code_id', sa.Integer(), nullable=False),
    sa.Column('code_type', sa.Enum('DIAGNOSIS', 'PROCEDURE', name='codetype'), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('coded_by', sa.Integer(), nullable=True),
    sa.Column('coded_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['code_id'], ['medical_codes.id'], ),
    sa.ForeignKeyConstraint(['coded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_unique_constraint(
        "uq_doctor_date_token", "appointments", ["doctor_id", "appointment_date", "token_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_doctor_date_token", "appointments", type_="unique")
    op.drop_table('patient_coding')
    op.drop_table('medical_codes')
    op.drop_table('inventory_movements')
    op.drop_table('inventory_stock')
    op.drop_table('inventory_grn_items')
    op.drop_table('inventory_grn')
    op.drop_table('inventory_po_items')
    op.drop_table('inventory_purchase_orders')
    op.drop_table('inventory_vendors')
    op.drop_table('inventory_items')
    op.drop_table('journal_lines')
    op.drop_table('gl_postings')
    op.drop_table('journal_entries')
    op.drop_table('accounts')
