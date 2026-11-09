# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# D1C EXPLICIT FINANCIAL POWERS
# Add independent financial grants without granting them through a service role.
# ==============================================

"""Preserve old grants and history; installations must explicitly assign new powers."""

# isort: split
# ==============================================
# SQL MIGRATION DEPENDENCIES
# Accept only the connection owned by the already-controlled Alembic transaction.
# ==============================================

from sqlalchemy import text
from sqlalchemy.engine import Connection

# ==============================================
# VERSIONED CAPABILITY CONTRACT
# Extend the allowed vocabulary without inferring any member's effective grants.
# ==============================================

D1C_REVISION = "d1c20261104"
FINANCIAL_CAPABILITIES = (
    "finance.read",
    "invoices.create",
    "invoices.finalize",
    "advances.allocate",
)
CAPABILITY_CHECK = "capability IN ('read','service','clean','collect','assistant','reservations.cancel_before_arrival','finance.read','invoices.create','invoices.finalize','advances.allocate')"

# ==============================================
# ADD PERMISSION VOCABULARY ONLY
# The exact parent and transaction owner protect already-applied migration history.
# ==============================================


def upgrade_dining_d1c(*, connection: Connection) -> None:
    """Expand the existing check; never infer a grant from service or collection."""
    if (
        connection.scalar(text("SELECT version_num FROM public.alembic_version"))
        != "d1b20261103"
    ):
        raise RuntimeError("dining_d1c_requires_exact_parent")
    connection.execute(
        text("ALTER TABLE public.dining_grants DROP CONSTRAINT ck_dining_capability")
    )
    connection.execute(
        text(
            "ALTER TABLE public.dining_grants ADD CONSTRAINT ck_dining_capability CHECK ("
            + CAPABILITY_CHECK
            + ")"
        )
    )
