# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 09 11 16 12 10 ADD PLAN ID TO BRANCH PRICING AND
# Database migration and schema management component.
# ==============================================

"""add_plan_id_to_branch_pricing_and_foreign_keys_to_discounts

Revision ID: 9a92b84b5b11
Revises: 084c58bd26bf
Create Date: 2026-09-11 16:12:10.116753

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "9a92b84b5b11"
down_revision: Union[str, Sequence[str], None] = "084c58bd26bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """
    إضافة التعديلات التالية:
    1. إضافة plan_id إلى branch_pricing
    2. إضافة owner_id إلى loyalty_discounts
    3. إضافة restaurant_id إلى promotions
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    # ==========================================
    # 1️⃣ إضافة plan_id إلى branch_pricing
    # ==========================================

    if inspector.has_table("branch_pricing"):
        columns = [col["name"] for col in inspector.get_columns("branch_pricing")]

        if "plan_id" not in columns:
            op.add_column(
                "branch_pricing",
                sa.Column(
                    "plan_id",
                    sa.Integer(),
                    nullable=True,
                    comment="معرف خطة الاشتراك (اختياري)",
                ),
            )

            op.create_foreign_key(
                "fk_branch_pricing_plan",
                "branch_pricing",
                "subscription_plans",
                ["plan_id"],
                ["id"],
                ondelete="CASCADE",
            )
            print("[OK] Added plan_id to branch_pricing")
        else:
            print("[INFO] plan_id already exists in branch_pricing")

    # ==========================================
    # 2️⃣ إضافة owner_id إلى loyalty_discounts
    # ==========================================

    if inspector.has_table("loyalty_discounts"):
        columns = [col["name"] for col in inspector.get_columns("loyalty_discounts")]

        if "owner_id" not in columns:
            op.add_column(
                "loyalty_discounts",
                sa.Column(
                    "owner_id",
                    sa.Integer(),
                    nullable=True,
                    comment="معرف المالك (اختياري)",
                ),
            )

            op.create_foreign_key(
                "fk_loyalty_discounts_owner",
                "loyalty_discounts",
                "owners",
                ["owner_id"],
                ["id"],
                ondelete="CASCADE",
            )
            print("[OK] Added owner_id to loyalty_discounts")
        else:
            print("[INFO] owner_id already exists in loyalty_discounts")

    # ==========================================
    # 3️⃣ إضافة restaurant_id إلى promotions
    # ==========================================

    if inspector.has_table("promotions"):
        columns = [col["name"] for col in inspector.get_columns("promotions")]

        if "restaurant_id" not in columns:
            op.add_column(
                "promotions",
                sa.Column(
                    "restaurant_id",
                    sa.Integer(),
                    nullable=True,
                    comment="معرف المطعم (اختياري)",
                ),
            )

            op.create_foreign_key(
                "fk_promotions_restaurant",
                "promotions",
                "restaurants",
                ["restaurant_id"],
                ["id"],
                ondelete="CASCADE",
            )
            print("[OK] Added restaurant_id to promotions")
        else:
            print("[INFO] restaurant_id already exists in promotions")


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """
    التراجع عن التعديلات.
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    # حذف restaurant_id من promotions
    if inspector.has_table("promotions"):
        columns = [col["name"] for col in inspector.get_columns("promotions")]
        if "restaurant_id" in columns:
            op.drop_constraint(
                "fk_promotions_restaurant", "promotions", type_="foreignkey"
            )
            op.drop_column("promotions", "restaurant_id")

    # حذف owner_id من loyalty_discounts
    if inspector.has_table("loyalty_discounts"):
        columns = [col["name"] for col in inspector.get_columns("loyalty_discounts")]
        if "owner_id" in columns:
            op.drop_constraint(
                "fk_loyalty_discounts_owner", "loyalty_discounts", type_="foreignkey"
            )
            op.drop_column("loyalty_discounts", "owner_id")

    # حذف plan_id من branch_pricing
    if inspector.has_table("branch_pricing"):
        columns = [col["name"] for col in inspector.get_columns("branch_pricing")]
        if "plan_id" in columns:
            op.drop_constraint(
                "fk_branch_pricing_plan", "branch_pricing", type_="foreignkey"
            )
            op.drop_column("branch_pricing", "plan_id")
