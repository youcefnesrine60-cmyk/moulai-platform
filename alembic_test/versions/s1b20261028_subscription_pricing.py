# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION PRICING TEST MIGRATION
# Declare S1 on the isolated legacy test lineage without changing the E1 branch.
# ==============================================

"""S1 on the disposable legacy baseline; does not reopen the E1/K10 branch."""

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

revision = "s1b20261028"
down_revision = "dce91870b4a2"
branch_labels = ("subscription_s1",)
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
