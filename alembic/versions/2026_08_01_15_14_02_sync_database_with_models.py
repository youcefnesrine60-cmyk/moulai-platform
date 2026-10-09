# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 08 01 15 14 02 SYNC DATABASE WITH MODELS
# Database migration and schema management component.
# ==============================================

"""sync_database_with_models

Revision ID: 17b6b58772b7
Revises:
Create Date: 2026-08-01 15:14:02.032701

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "17b6b58772b7"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """
    مزامنة قاعدة البيانات مع النماذج.
    ✅ يتجاهل الجداول الموجودة
    ✅ يضيف الجداول المفقودة فقط
    ✅ يضيف الأعمدة المفقودة فقط
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # ==========================================
    # 📊 قائمة الجداول المطلوبة حسب النماذج
    # ==========================================
    required_tables = {
        # ✅ الجداول الأساسية
        "admins",
        "branches",
        "categories",
        "features",
        "option_groups",
        "owners",
        "payments",
        "plan_features",
        "product_options",
        "products",
        "promotions",
        "registration_requests",
        "restaurant_branches",
        "restaurant_groups",
        "restaurant_metrics",
        "restaurant_order_counters",
        "restaurants",
        "subscription_feature_requests",
        "subscription_features",
        "subscription_plans",
        "subscriptions",
        "users",
        "orders",
        "order_items",
        "order_item_options",
        "order_payments",
        "order_status_history",
        "branch_pricing",
        "feature_pricing",
        "feature_usage_counters",
        "feature_usage_limits",
        "loyalty_discounts",
        "multi_restaurant_discounts",
        # 🆕 الجداول الجديدة (غير موجودة)
        "agents",
        "channels",
        "conversations",
        "messages",
    }

    # ==========================================
    # 1️⃣ إنشاء الجداول المفقودة فقط
    # ==========================================

    tables_to_create = required_tables - existing_tables

    if tables_to_create:
        print(
            f"[INFO] Creating {len(tables_to_create)} missing tables: {tables_to_create}"
        )

        # 🆕 جداول الوكيل الذكي
        if "agents" in tables_to_create:
            op.create_table(
                "agents",
                sa.Column("id", sa.Integer(), primary_key=True, index=True),
                sa.Column("restaurant_id", sa.Integer(), nullable=False),
                sa.Column(
                    "name",
                    sa.String(100),
                    nullable=False,
                    server_default="My Assistant",
                ),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column(
                    "language", sa.String(10), nullable=True, server_default="ar"
                ),
                sa.Column(
                    "tone", sa.String(50), nullable=True, server_default="professional"
                ),
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("true"),
                ),
                sa.Column("config", sa.JSON(), nullable=True),
                sa.Column("ai_config", sa.JSON(), nullable=True),
                sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
                sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
                sa.ForeignKeyConstraint(
                    ["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"
                ),
            )
            print("[OK] Created table: agents")

        if "channels" in tables_to_create:
            op.create_table(
                "channels",
                sa.Column("id", sa.Integer(), primary_key=True, index=True),
                sa.Column("agent_id", sa.Integer(), nullable=False),
                sa.Column("type", sa.String(50), nullable=False),
                sa.Column("name", sa.String(100), nullable=False),
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("true"),
                ),
                sa.Column("config", sa.JSON(), nullable=True),
                sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
                sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
                sa.ForeignKeyConstraint(
                    ["agent_id"], ["agents.id"], ondelete="CASCADE"
                ),
            )
            print("[OK] Created table: channels")

        if "conversations" in tables_to_create:
            op.create_table(
                "conversations",
                sa.Column("id", sa.Integer(), primary_key=True, index=True),
                sa.Column("agent_id", sa.Integer(), nullable=False),
                sa.Column("channel_id", sa.Integer(), nullable=False),
                sa.Column("user_id", sa.String(255), nullable=False),
                sa.Column("user_name", sa.String(255), nullable=True),
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("true"),
                ),
                sa.Column("context", sa.JSON(), nullable=True),
                sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
                sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
                sa.ForeignKeyConstraint(
                    ["agent_id"], ["agents.id"], ondelete="CASCADE"
                ),
                sa.ForeignKeyConstraint(
                    ["channel_id"], ["channels.id"], ondelete="CASCADE"
                ),
            )
            print("[OK] Created table: conversations")

        if "messages" in tables_to_create:
            op.create_table(
                "messages",
                sa.Column("id", sa.Integer(), primary_key=True, index=True),
                sa.Column("conversation_id", sa.Integer(), nullable=False),
                sa.Column("role", sa.String(20), nullable=False),
                sa.Column("content", sa.Text(), nullable=False),
                sa.Column("intent", sa.String(100), nullable=True),
                sa.Column("confidence", sa.Float(), nullable=True),
                sa.Column("entities", sa.JSON(), nullable=True),
                sa.Column("meta_data", sa.JSON(), nullable=True),
                sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
                sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
                sa.ForeignKeyConstraint(
                    ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
                ),
            )
            print("[OK] Created table: messages")
    else:
        print("[INFO] All required tables already exist.")

    # ==========================================
    # 2️⃣ إضافة الأعمدة المفقودة في الجداول الموجودة
    # ==========================================

    # ✅ إضافة عمود consent في جدول users
    if "users" in existing_tables:
        columns = [col["name"] for col in inspector.get_columns("users")]
        if "consent" not in columns:
            op.add_column(
                "users",
                sa.Column(
                    "consent",
                    sa.Boolean(),
                    nullable=True,
                    server_default=sa.text("false"),
                ),
            )
            print("[OK] Added column 'consent' to users table")

        # ✅ التأكد من وجود القيد الفريد على chat_id
        constraints = [c["name"] for c in inspector.get_unique_constraints("users")]
        if "users_chat_id_key" not in constraints:
            op.create_unique_constraint("users_chat_id_key", "users", ["chat_id"])
            print("[OK] Added unique constraint on chat_id in users table")

    # ✅ إضافة عمود group_id في جدول restaurants (إذا لم يكن موجوداً)
    if "restaurants" in existing_tables:
        columns = [col["name"] for col in inspector.get_columns("restaurants")]
        if "group_id" not in columns:
            op.add_column(
                "restaurants", sa.Column("group_id", sa.Integer(), nullable=True)
            )
            op.create_foreign_key(
                "fk_restaurant_group",
                "restaurants",
                "restaurant_groups",
                ["group_id"],
                ["id"],
                ondelete="SET NULL",
            )
            print("[OK] Added column 'group_id' to restaurants table")

    print("\n[DONE] Database synchronization completed successfully!")


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """
    التراجع عن التغييرات (للتراجع فقط).
    """
    # حذف الجداول الجديدة (ترتيب عكسي)
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("channels")
    op.drop_table("agents")

    # حذف الأعمدة المضافة
    op.drop_column("restaurants", "group_id")
    op.drop_column("users", "consent")
    op.drop_constraint("users_chat_id_key", "users", type_="unique")
