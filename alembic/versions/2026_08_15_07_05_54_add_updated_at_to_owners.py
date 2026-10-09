# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 08 15 07 05 54 ADD UPDATED AT TO OWNERS
# Database migration and schema management component.
# ==============================================

"""add_updated_at_to_owners

Revision ID: fd29befe8baf
Revises: 1452679b0eb0
Create Date: 2026-08-15 07:05:54.208238

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "fd29befe8baf"
down_revision: Union[str, Sequence[str], None] = "1452679b0eb0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """
    إضافة عمود updated_at إلى جدول owners.
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    # ✅ التحقق من وجود العمود
    columns = [col["name"] for col in inspector.get_columns("owners")]

    if "updated_at" not in columns:
        # ✅ إضافة العمود مع تحديث تلقائي
        op.add_column(
            "owners",
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=True,
                server_default=sa.text("now()"),
                comment="تاريخ ووقت آخر تحديث",
            ),
        )
        print("[OK] Added updated_at column to owners")
    else:
        print("[INFO] updated_at column already exists in owners")


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """
    حذف عمود updated_at من جدول owners.
    """
    op.drop_column("owners", "updated_at")
