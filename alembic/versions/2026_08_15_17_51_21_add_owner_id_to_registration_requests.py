# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 08 15 17 51 21 ADD OWNER ID TO REGISTRATION REQUESTS
# Database migration and schema management component.
# ==============================================

"""add_owner_id_to_registration_requests

Revision ID: 43d4b74c965c
Revises: a9a5aec4604b
Create Date: 2026-08-15 17:51:21.749025

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "43d4b74c965c"
down_revision: Union[str, Sequence[str], None] = "a9a5aec4604b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """
    إضافة عمود owner_id إلى جدول registration_requests.
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    # ✅ التحقق من وجود الجدول
    if not inspector.has_table("registration_requests"):
        print("[INFO] Table registration_requests does not exist, skipping")
        return

    # ✅ التحقق من وجود العمود
    columns = [col["name"] for col in inspector.get_columns("registration_requests")]

    if "owner_id" not in columns:
        # ✅ إضافة العمود
        op.add_column(
            "registration_requests",
            sa.Column(
                "owner_id",
                sa.Integer(),
                nullable=True,
                comment="معرف المالك المرتبط (بعد الموافقة)",
            ),
        )
        print("[OK] Added owner_id column to registration_requests")

        # ✅ إضافة المفتاح الخارجي
        op.create_foreign_key(
            "fk_registration_requests_owner",
            "registration_requests",
            "owners",
            ["owner_id"],
            ["id"],
            ondelete="SET NULL",
        )
        print("[OK] Added foreign key from registration_requests to owners")
    else:
        print("[INFO] owner_id column already exists in registration_requests")


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """
    حذف عمود owner_id من جدول registration_requests.
    """
    # ✅ حذف المفتاح الخارجي
    op.drop_constraint(
        "fk_registration_requests_owner", "registration_requests", type_="foreignkey"
    )

    # ✅ حذف العمود
    op.drop_column("registration_requests", "owner_id")

    print("[OK] Removed owner_id column from registration_requests")
