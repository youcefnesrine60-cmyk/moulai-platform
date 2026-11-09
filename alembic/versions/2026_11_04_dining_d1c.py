# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# D1C EXPLICIT FINANCIAL PERMISSION MIGRATION
# Keep applied D1a/D1b migrations intact; financial powers require separate owner grants.
# ==============================================

"""No automatic grant and no destructive financial-history downgrade."""

# isort: split
# ==============================================
# MIGRATION DEPENDENCIES
# Delegate DDL to the versioned helper while retaining Alembic transaction ownership.
# ==============================================

from alembic import op
from migration_support.dining_d1c import upgrade_dining_d1c

# ==============================================
# MAIN GRAPH LINK
# Existing installations advance from their unchanged D1b revision.
# ==============================================

revision = "d1c20261104"
down_revision = "d1b20261103"
branch_labels = None
depends_on = None


# ==============================================
# EXPLICIT ADDITIVE UPGRADE
# Alembic owns the transaction and records the real new revision.
# ==============================================


def upgrade() -> None:
    """Apply the scoped capability extension, with no stamp substitution."""
    upgrade_dining_d1c(connection=op.get_bind())


# ==============================================
# RETAIN ASSIGNED AUTHORITY FOR REVIEW
# A downgrade cannot silently discard grants or invalidate audit history.
# ==============================================


def downgrade() -> None:
    """Require a separately reviewed permission reconciliation before rollback."""
    raise RuntimeError("dining_d1c_downgrade_requires_review")
