# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MAIN HISTORY D1 DINING REVISION
# Add scoped tables, reservation planning and restaurant advance evidence after S1a.
# ==============================================

"""Add dining D1 without rewriting the accepted S1a or historical revisions."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT REVISION METADATA
# Keep the new main-history node separate from all test-history siblings.
# ==============================================

from alembic import op
from migration_support.dining_d1 import upgrade_dining

revision: str = "d1a20261102"
down_revision: str = "s1a20261028"
branch_labels: None = None
depends_on: None = None


# ==============================================
# ADDITIVE UPGRADE
# Alembic owns the transaction; this revision performs no independent commit.
# ==============================================


def upgrade() -> None:
    """Apply the frozen D1 contract on an exact S1a database."""
    upgrade_dining(op.get_bind())


# ==============================================
# RETAIN BOOKING AND FINANCIAL EVIDENCE
# Require a reviewed forward repair or isolated restore instead of destructive loss.
# ==============================================


def downgrade() -> None:
    """Deliberately reject automatic removal of immutable dining financial history."""
    raise RuntimeError("dining_downgrade_requires_reviewed_preservation_plan")
