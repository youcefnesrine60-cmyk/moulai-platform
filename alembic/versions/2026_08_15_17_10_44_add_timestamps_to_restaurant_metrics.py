# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 08 15 17 10 44 ADD TIMESTAMPS TO RESTAURANT METRICS
# Database migration and schema management component.
# ==============================================

"""add_timestamps_to_restaurant_metrics

Revision ID: a9a5aec4604b
Revises: 888e43fc4f9b
Create Date: 2026-08-15 17:10:44.702056

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "a9a5aec4604b"
down_revision: Union[str, Sequence[str], None] = "888e43fc4f9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """
    إضافة أعمدة created_at و updated_at إلى جدول restaurant_metrics.
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    columns = [col["name"] for col in inspector.get_columns("restaurant_metrics")]

    # ✅ إضافة created_at
    if "created_at" not in columns:
        op.add_column(
            "restaurant_metrics",
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True,
                server_default=sa.text("now()"),
                comment="تاريخ الإنشاء",
            ),
        )
        print("[OK] Added created_at to restaurant_metrics")
    else:
        print("[INFO] created_at already exists in restaurant_metrics")

    # ✅ إضافة updated_at
    if "updated_at" not in columns:
        op.add_column(
            "restaurant_metrics",
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=True,
                server_default=sa.text("now()"),
                comment="تاريخ آخر تحديث",
            ),
        )
        print("[OK] Added updated_at to restaurant_metrics")
    else:
        print("[INFO] updated_at already exists in restaurant_metrics")


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """
    حذف أعمدة created_at و updated_at من جدول restaurant_metrics.
    """
    op.drop_column("restaurant_metrics", "created_at")
    op.drop_column("restaurant_metrics", "updated_at")
