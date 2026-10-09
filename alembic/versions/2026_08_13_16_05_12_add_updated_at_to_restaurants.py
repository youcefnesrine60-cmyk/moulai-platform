# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 08 13 16 05 12 ADD UPDATED AT TO RESTAURANTS
# Database migration and schema management component.
# ==============================================

"""add_updated_at_to_restaurants

Revision ID: 1452679b0eb0
Revises: 83fe3deff863
Create Date: 2026-08-13 16:05:12.103510

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "1452679b0eb0"
down_revision: Union[str, Sequence[str], None] = "83fe3deff863"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """
    إضافة عمود updated_at إلى جدول restaurants.
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    #  التحقق من وجود العمود
    columns = [col["name"] for col in inspector.get_columns("restaurants")]

    if "updated_at" not in columns:
        #  إضافة العمود مع تحديث تلقائي
        op.add_column(
            "restaurants",
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=True,
                server_default=sa.text("now()"),
                comment="تاريخ ووقت آخر تحديث",
            ),
        )
        print("[OK] Added updated_at column to restaurants")
    else:
        print("[INFO] updated_at column already exists in restaurants")


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """
    حذف عمود updated_at من جدول restaurants.
    """
    op.drop_column("restaurants", "updated_at")
