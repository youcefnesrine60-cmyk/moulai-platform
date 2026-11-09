# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# D1D CONTROLLED SERVICE EXTENSIONS
# Preserve applied migrations and add explicit professional and public-link resources.
# ==============================================

"""No identity, permission, tariff or production configuration is automatically seeded."""

# isort: split
# ==============================================
# MIGRATION DEPENDENCIES
# The migration is entered only through the explicitly controlled target connection.
# ==============================================

from alembic import op
from migration_support.dining_d1d import upgrade_dining_d1d

revision = "d1d20261105"
down_revision = "d1c20261104"
branch_labels = None
depends_on = None


# ==============================================
# APPLY THE VERSIONED CONTRACT
# Alembic owns the transaction; no stamp or environment fallback is used.
# ==============================================


def upgrade() -> None:
    """Add the reviewed service resources without mutating existing financial history."""
    upgrade_dining_d1d(connection=op.get_bind())


# ==============================================
# RETAIN ISSUED DOCUMENTS AND VISITS
# A destructive rollback needs its own reviewed reconciliation of retained history.
# ==============================================


def downgrade() -> None:
    """Refuse automatic deletion of issued links, orders and professional audit evidence."""
    raise RuntimeError("dining_d1d_downgrade_requires_review")
