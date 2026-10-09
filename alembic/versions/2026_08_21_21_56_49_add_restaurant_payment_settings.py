# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 08 21 21 56 49 ADD RESTAURANT PAYMENT SETTINGS
# Database migration and schema management component.
# ==============================================

"""add_restaurant_payment_settings

Revision ID: 084c58bd26bf
Revises: 43d4b74c965c
Create Date: 2026-08-21 21:56:49.670357

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "084c58bd26bf"
down_revision: Union[str, Sequence[str], None] = "43d4b74c965c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """
    إضافة جدول restaurant_payment_settings.
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    # ✅ التحقق من وجود الجدول
    if inspector.has_table("restaurant_payment_settings"):
        print("[INFO] Table restaurant_payment_settings already exists")
        return

    # ✅ إنشاء الجدول
    op.create_table(
        "restaurant_payment_settings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("restaurant_id", sa.Integer(), nullable=False, unique=True),
        sa.Column(
            "allow_cash", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "allow_card", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "allow_ccp", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "allow_baridimob",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "allow_stripe",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "allow_paypal",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("restaurant_id", name="uq_restaurant_payment_settings"),
    )

    # ✅ إضافة فهارس
    op.create_index(
        "idx_restaurant_payment_settings_restaurant",
        "restaurant_payment_settings",
        ["restaurant_id"],
    )

    print("[OK] Created table restaurant_payment_settings")


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """
    حذف جدول restaurant_payment_settings.
    """
    op.drop_table("restaurant_payment_settings")
    print("[OK] Dropped table restaurant_payment_settings")
