# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# D1B MODULE PERMISSION MIGRATION
# Keep the accepted D1a history intact while adding an explicit cancellation grant.
# ==============================================

"""No automatic grant and no destructive financial-history downgrade."""

from alembic import op
from migration_support.dining_d1b import upgrade_dining_d1b

revision = "d1b20261103"
down_revision = "d1a20261102"
branch_labels = None
depends_on = None


# ==============================================
# EXPLICIT ADDITIVE UPGRADE
# Alembic owns the transaction and records the real new revision.
# ==============================================


def upgrade() -> None:
    """Apply the scoped capability extension, with no stamp substitution."""
    upgrade_dining_d1b(connection=op.get_bind())


# ==============================================
# RETAIN ASSIGNED AUTHORITY FOR REVIEW
# A downgrade cannot silently discard grants or invalidate audit history.
# ==============================================


def downgrade() -> None:
    """Require a separately reviewed permission reconciliation before rollback."""
    raise RuntimeError("dining_d1b_downgrade_requires_review")
