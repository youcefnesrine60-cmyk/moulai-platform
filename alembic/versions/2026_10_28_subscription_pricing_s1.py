# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION PRICING MAIN MIGRATION
# Declare the prepared main-chain S1 revision with its guarded downgrade policy.
# ==============================================

"""Shared pricing configuration and immutable subscription snapshots.

Prepared only: do not apply to a permanent database without separate approval.
Existing invoice amounts and missing historical periods are never backfilled.
"""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from alembic import op
from migration_support.subscription_s1 import downgrade as revert
from migration_support.subscription_s1 import upgrade as apply

# ==============================================
# REVISION METADATA
# Connect this prepared revision to its existing Alembic lineage.
# ==============================================

revision = "s1a20261028"
down_revision = "e1a92b200001"
branch_labels = None
depends_on = None


# ==============================================
# UPGRADE
# Apply the prepared S1 operations using the connection explicitly supplied by the
# caller.
# ==============================================


def upgrade() -> None:
    """Apply the prepared S1 operations using the connection explicitly supplied by the caller."""

    apply(connection=op.get_bind())


# ==============================================
# DOWNGRADE
# Delegate to the preservation guard that refuses an unplanned history downgrade.
# ==============================================


def downgrade() -> None:
    """Delegate to the preservation guard that refuses an unplanned history downgrade."""

    revert(connection=op.get_bind())
