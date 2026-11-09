# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# O4 BILLING COUNTRY AND ENROLLMENT MIGRATION
# Extend O3 without rewriting its recorded source transfer or preceding migrations.
# ==============================================

"""Local preparation only until consumers, restore rehearsal and review cutover pass."""

from alembic import op
from migration_support.billing_country_o4 import downgrade as revert
from migration_support.billing_country_o4 import upgrade as apply

revision = "o420261108"
down_revision = "o320261108"
branch_labels = None
depends_on = None

# ==============================================
# ADDITIVE FORWARD OPERATIONS
# Use only the explicitly supplied Alembic transaction.
# ==============================================


def upgrade() -> None:
    """Persist the approved workflow without seeding tariffs or personal permissions."""
    apply(connection=op.get_bind())


# ==============================================
# RETAINED HISTORY RECOVERY
# Do not collapse evidence or country history automatically.
# ==============================================


def downgrade() -> None:
    """Refuse destructive downgrade of retained administrative evidence."""
    revert()
