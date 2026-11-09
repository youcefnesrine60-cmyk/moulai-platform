# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# O3 PREPARED COUNTRY BASE MIGRATION
# Require an explicit application cutover after the last reviewed local O2 revision.
# ==============================================

"""Prepared only: legacy price readers must be replaced before activating O3.

This revision is not applied to the retained review instance or any Neon database.
"""

from alembic import op
from migration_support.country_base_o3 import downgrade as revert
from migration_support.country_base_o3 import upgrade as apply

revision = "o320261108"
down_revision = "o220261108"
branch_labels = None
depends_on = None

# ==============================================
# AUTHORITATIVE STORAGE REPLACEMENT
# The supplied Alembic transaction owns both the transfer and removal of the old source.
# ==============================================


def upgrade() -> None:
    """Execute only through the caller's explicit migration connection."""
    apply(connection=op.get_bind())


# ==============================================
# LOSSLESS HISTORY GUARD
# Refuse an automatic downgrade that would discard country-specific decisions.
# ==============================================


def downgrade() -> None:
    """Require an independently reviewed recovery procedure instead of collapsing history."""
    revert()
