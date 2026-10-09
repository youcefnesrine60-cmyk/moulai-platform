# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 08 12 02 22 08 ADD USER RELATIONSHIP TO ORDERS
# Database migration and schema management component.
# ==============================================

"""add_user_relationship_to_orders

Revision ID: 2d999b8ed18f
Revises: 17b6b58772b7
Create Date: 2026-08-12 02:22:08.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision: str = "2d999b8ed18f"
down_revision: Union[str, None] = "17b6b58772b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """
    Add user relationship to orders.

    1. Add customer_name and customer_phone to users
    2. Add user_id to orders
    3. Migrate data from orders to users
    4. Add foreign key
    5. Drop old columns from orders
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    # ==========================================
    #  Add columns to users
    # ==========================================

    user_columns = [col["name"] for col in inspector.get_columns("users")]

    if "customer_name" not in user_columns:
        op.add_column(
            "users", sa.Column("customer_name", sa.String(255), nullable=True)
        )
        print("[OK] Added customer_name to users")

    if "customer_phone" not in user_columns:
        op.add_column(
            "users", sa.Column("customer_phone", sa.String(20), nullable=True)
        )
        print("[OK] Added customer_phone to users")

    # ==========================================
    #  Add user_id to orders (FIRST!)
    # ==========================================

    order_columns = [col["name"] for col in inspector.get_columns("orders")]

    if "user_id" not in order_columns:
        op.add_column("orders", sa.Column("user_id", sa.Integer(), nullable=True))
        print("[OK] Added user_id to orders")

    # ==========================================
    #  Migrate data from orders to users
    # ==========================================

    # Only run if both customer_name and customer_phone exist in orders
    if "customer_name" in order_columns and "customer_phone" in order_columns:
        #  Now user_id exists, so this will work
        op.execute(text("""
            UPDATE users u
            SET 
                customer_name = o.customer_name,
                customer_phone = o.customer_phone
            FROM orders o
            WHERE o.user_id = u.id
            AND (u.customer_name IS NULL OR u.customer_phone IS NULL)
        """))
        print("[OK] Migrated customer data from orders to users")

    # ==========================================
    #  Add foreign key
    # ==========================================

    # Check if foreign key already exists
    fk_exists = False
    for constraint in inspector.get_foreign_keys("orders"):
        if constraint["name"] == "fk_orders_user":
            fk_exists = True
            break

    if not fk_exists:
        op.create_foreign_key(
            "fk_orders_user",
            "orders",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        print("[OK] Added foreign key from orders to users")

    # ==========================================
    #  Drop old columns from orders
    # ==========================================

    if "customer_name" in order_columns:
        op.drop_column("orders", "customer_name")
        print("[OK] Dropped customer_name from orders")

    if "customer_phone" in order_columns:
        op.drop_column("orders", "customer_phone")
        print("[OK] Dropped customer_phone from orders")


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """
    Rollback changes.
    """
    # Restore columns to orders
    op.add_column("orders", sa.Column("customer_name", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("customer_phone", sa.String(20), nullable=True))

    # Restore data from users to orders
    op.execute(text("""
        UPDATE orders o
        SET 
            customer_name = u.customer_name,
            customer_phone = u.customer_phone
        FROM users u
        WHERE o.user_id = u.id
    """))

    # Drop foreign key
    op.drop_constraint("fk_orders_user", "orders", type_="foreignkey")

    # Drop user_id column
    op.drop_column("orders", "user_id")

    # Drop columns from users
    op.drop_column("users", "customer_name")
    op.drop_column("users", "customer_phone")
