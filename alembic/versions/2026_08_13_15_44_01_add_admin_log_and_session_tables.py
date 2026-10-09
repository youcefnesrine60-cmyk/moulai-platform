# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 08 13 15 44 01 ADD ADMIN LOG AND SESSION TABLES
# Database migration and schema management component.
# ==============================================

"""add_admin_log_and_session_tables

Revision ID: 83fe3deff863
Revises: 4c3017ab0067
Create Date: 2026-08-13 15:44:01.483127

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "83fe3deff863"
down_revision: Union[str, Sequence[str], None] = "4c3017ab0067"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """
    إنشاء جداول AdminLog و AdminSession.
    """
    #  إنشاء جدول admin_logs
    op.create_table(
        "admin_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
    )

    #  إنشاء جدول admin_sessions
    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("session_token", sa.String(255), unique=True, nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("last_activity", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
    )

    #  إضافة فهارس
    op.create_index("idx_admin_logs_admin_id", "admin_logs", ["admin_id"])
    op.create_index("idx_admin_logs_action", "admin_logs", ["action"])
    op.create_index("idx_admin_sessions_admin_id", "admin_sessions", ["admin_id"])
    op.create_index(
        "idx_admin_sessions_session_token", "admin_sessions", ["session_token"]
    )


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """
    حذف جداول AdminLog و AdminSession (للتراجع).
    """
    #  حذف الفهارس (ترتيب عكسي)
    op.drop_index("idx_admin_sessions_session_token", table_name="admin_sessions")
    op.drop_index("idx_admin_sessions_admin_id", table_name="admin_sessions")
    op.drop_index("idx_admin_logs_action", table_name="admin_logs")
    op.drop_index("idx_admin_logs_admin_id", table_name="admin_logs")

    #  حذف الجداول (ترتيب عكسي - حذف الجداول التي تعتمد على غيرها أولاً)
    op.drop_table("admin_sessions")
    op.drop_table("admin_logs")
