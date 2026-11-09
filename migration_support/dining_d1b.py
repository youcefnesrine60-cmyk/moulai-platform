# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# D1B EXPLICIT CANCELLATION AUTHORITY
# Extend the module grant vocabulary without changing the frozen D1a migration.
# ==============================================

"""Add only the owner-assigned pre-arrival cancellation capability."""

from sqlalchemy import text
from sqlalchemy.engine import Connection

D1B_REVISION = "d1b20261103"
CANCEL_CAPABILITY = "reservations.cancel_before_arrival"
CAPABILITY_CHECK = "capability IN ('read','service','clean','collect','assistant','reservations.cancel_before_arrival')"


# ==============================================
# UPGRADE FROM THE EXACT REVIEWED PARENT
# Preserve all existing grants and retain the assistant human-capability ceiling.
# ==============================================


def upgrade_dining_d1b(*, connection: Connection) -> None:
    """Expand one column/check atomically; never seed a personal permission."""
    if (
        connection.scalar(text("SELECT version_num FROM public.alembic_version"))
        != "d1a20261102"
    ):
        raise RuntimeError("dining_d1b_requires_exact_parent")
    connection.execute(
        text(
            "ALTER TABLE public.dining_grants ALTER COLUMN capability TYPE varchar(64)"
        )
    )
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
