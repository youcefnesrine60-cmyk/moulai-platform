# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Expand tenant foundation E1 in the main history; no data backfill.

Revision ID: e1a92b200001
Revises: c413b7918a20
Creation is authorized; execution requires separate target-specific approval.
"""

from alembic.operations import Operations

from alembic import op
from migration_support.tenant_e1 import (
    downgrade_e1,
    upgrade_e1,
)

revision: str = "e1a92b200001"
down_revision: str = "c413b7918a20"
branch_labels: None = None
depends_on: None = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """Apply only the frozen, explicitly scoped E1 contract."""
    upgrade_e1(operations=Operations(op.get_context()))


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """Refuse rollback once any tenant data or reference has been retained."""
    downgrade_e1(operations=Operations(op.get_context()))
