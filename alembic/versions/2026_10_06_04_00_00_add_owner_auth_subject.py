# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / VERSIONS / 2026 10 06 04 00 00 ADD OWNER AUTH SUBJECT
# Database migration and schema management component.
# ==============================================

"""add owner identity-provider subject

Revision ID: 6bf21d4a8c30
Revises: c3a5f018d7e2
Create Date: 2026-10-06 04:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "6bf21d4a8c30"
down_revision: Union[str, Sequence[str], None] = "c3a5f018d7e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    op.add_column(
        "owners",
        sa.Column("auth_subject", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_owners_auth_subject",
        "owners",
        ["auth_subject"],
        unique=True,
    )


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    op.drop_index("ix_owners_auth_subject", table_name="owners")
    op.drop_column("owners", "auth_subject")
