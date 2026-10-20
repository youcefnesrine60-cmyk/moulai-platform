# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Expand tenant foundation E1 in the independent isolated-test history.

Revision ID: e1b92b200001
Revises: dce91870b4a2
Creation is authorized; execution requires separate target-specific approval.
"""

from alembic.operations import Operations

from alembic import op
from migration_support.tenant_e1 import (
    downgrade_e1,
    upgrade_e1,
)

revision: str = "e1b92b200001"
down_revision: str = "dce91870b4a2"
branch_labels: None = None
depends_on: None = None


# ==============================================
# UPGRADE
# ==============================================


def upgrade() -> None:
    """Apply the same frozen contract without merging migration histories."""
    upgrade_e1(operations=Operations(op.get_context()))


# ==============================================
# DOWNGRADE
# ==============================================


def downgrade() -> None:
    """Remove unused E1 objects only after the shared fail-closed checks."""
    downgrade_e1(operations=Operations(op.get_context()))
