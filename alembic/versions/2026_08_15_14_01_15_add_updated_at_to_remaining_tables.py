# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 08 15 14 01 15 ADD UPDATED AT TO REMAINING TABLES
# Database migration and schema management component.
# ==============================================

"""add_updated_at_to_remaining_tables

Revision ID: 888e43fc4f9b
Revises: dc626cfd1aaf
Create Date: 2026-08-15 14:01:15.138806

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "888e43fc4f9b"
down_revision: Union[str, Sequence[str], None] = "dc626cfd1aaf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """
    إضافة عمود updated_at إلى الجداول المتبقية (مع التحقق من الوجود).
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    # ==========================================
    # 📊 الجداول التي تحتاج إلى updated_at
    # ==========================================

    tables_to_update = [
        "branches",
        "payments",
        "orders",
        "products",
        "categories",
        "option_groups",
        "product_options",
        "order_items",
        "order_item_options",
        "order_payments",
        "order_status_history",
        "subscription_plans",
        "features",
        "plan_features",
        "subscription_features",
        "subscription_feature_requests",
        "feature_pricing",
        "feature_usage_limits",
        "feature_usage_counters",
        "branch_pricing",
        "loyalty_discounts",
        "multi_restaurant_discounts",
        "promotions",
        "registration_requests",
        "restaurant_groups",
        "restaurant_branches",
        "restaurant_metrics",
        "restaurant_order_counters",
        "admins",
        "agents",
        "channels",
        "conversations",
        "messages",
    ]

    # ==========================================
    # 🔄 إضافة العمود مع التحقق من الوجود
    # ==========================================

    for table_name in tables_to_update:
        # ✅ التحقق من وجود الجدول
        if not inspector.has_table(table_name):
            print(f"[INFO] Table '{table_name}' does not exist, skipping")
            continue

        # ✅ التحقق من وجود العمود
        columns = [col["name"] for col in inspector.get_columns(table_name)]

        if "updated_at" not in columns:
            # ✅ إضافة العمود
            op.add_column(
                table_name,
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=True,
                    server_default=sa.text("now()"),
                    comment="تاريخ ووقت آخر تحديث",
                ),
            )
            print(f"[OK] Added 'updated_at' to '{table_name}'")
        else:
            print(f"[INFO] 'updated_at' already exists in '{table_name}', skipping")


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """
    حذف عمود updated_at من الجداول المضافة (مع التحقق من الوجود).
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    tables_to_update = [
        "branches",
        "payments",
        "orders",
        "products",
        "categories",
        "option_groups",
        "product_options",
        "order_items",
        "order_item_options",
        "order_payments",
        "order_status_history",
        "subscription_plans",
        "features",
        "plan_features",
        "subscription_features",
        "subscription_feature_requests",
        "feature_pricing",
        "feature_usage_limits",
        "feature_usage_counters",
        "branch_pricing",
        "loyalty_discounts",
        "multi_restaurant_discounts",
        "promotions",
        "registration_requests",
        "restaurant_groups",
        "restaurant_branches",
        "restaurant_metrics",
        "restaurant_order_counters",
        "admins",
        "agents",
        "channels",
        "conversations",
        "messages",
    ]

    for table_name in tables_to_update:
        if not inspector.has_table(table_name):
            continue

        columns = [col["name"] for col in inspector.get_columns(table_name)]

        if "updated_at" in columns:
            op.drop_column(table_name, "updated_at")
            print(f"[OK] Dropped 'updated_at' from '{table_name}'")
