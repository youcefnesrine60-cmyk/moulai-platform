# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# O5 DISTINCT SAAS DOCUMENT CIRCUIT
# Extend O4 additively without rewriting any applied migration or granting personal authority.
# ==============================================

"""Persist immutable local documentary evidence separately from restaurant QR links."""

from alembic import op
from migration_support.saas_documents_o5 import downgrade as revert
from migration_support.saas_documents_o5 import upgrade as apply

revision = "o520261111"
down_revision = "o420261108"
branch_labels = None
depends_on = None

# ==============================================
# EXPLICIT FORWARD CONNECTION
# Alembic retains ownership of transaction and revision bookkeeping.
# ==============================================


def upgrade() -> None:
    """Create only the documentary tables, indexes and history protections."""
    apply(connection=op.get_bind())


# ==============================================
# RETAINED ORIGINALS
# Never erase financial documentary evidence through a routine downgrade.
# ==============================================


def downgrade() -> None:
    """Require the reviewed recovery procedure for retained history."""
    revert()
