# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 09 12 10 00 00 ADD CUSTOMER COMPLAINTS
# Database migration and schema management component.
# ==============================================

"""add customer complaints

Revision ID: c3a5f018d7e2
Revises: 9a92b84b5b11
Create Date: 2026-09-12 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3a5f018d7e2"
down_revision: Union[str, Sequence[str], None] = "9a92b84b5b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=30), server_default="open", nullable=False
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_complaints_restaurant_status",
        "complaints",
        ["restaurant_id", "status"],
    )
    op.create_index("idx_complaints_user", "complaints", ["user_id"])
    op.create_index("idx_complaints_order", "complaints", ["order_id"])


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    op.drop_index("idx_complaints_order", table_name="complaints")
    op.drop_index("idx_complaints_user", table_name="complaints")
    op.drop_index("idx_complaints_restaurant_status", table_name="complaints")
    op.drop_table("complaints")
