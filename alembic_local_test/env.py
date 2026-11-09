# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ISOLATED ALEMBIC ENVIRONMENT
# Run migrations only through the explicitly checked disposable PostgreSQL connection.
# ==============================================

"""Pinned local-only entry point for the compatibility or tenant-E1 profile."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from sqlalchemy.engine import Connection

from alembic import context
from test_support.local_postgres import (
    LOCAL_DINING_REVISION,
    LOCAL_E1_REVISION,
    LOCAL_MAIN_REVISION,
    LOCAL_REVISION,
    LOCAL_S1_REVISION,
    LocalPostgresSettings,
    read_local_test_identity,
)

# ==============================================
# EXECUTE ONLY A CHECKED CONNECTION AT THE EXACT PROFILE REVISION
# Admit only the selected legacy or K10 E1 target on a pinned local instance.
# ==============================================


def run_local_migrations() -> None:
    """Admit only the selected legacy or K10 E1 target on a pinned local instance."""
    config = context.config
    connection = config.attributes.get("connection")
    configuration = config.attributes.get("local_configuration")
    if (
        context.is_offline_mode()
        or not isinstance(connection, Connection)
        or not isinstance(configuration, LocalPostgresSettings)
        or not connection.in_transaction()
    ):
        raise RuntimeError("local_migration_requires_pinned_approved_target")
    expected_revision = {
        "dining": LOCAL_DINING_REVISION,
        "k10": LOCAL_E1_REVISION,
        "subscription": LOCAL_S1_REVISION,
        "main": LOCAL_MAIN_REVISION,
    }.get(configuration.PROFILE, LOCAL_REVISION)
    if context.get_revision_argument() != expected_revision:
        raise RuntimeError("local_migration_profile_revision_mismatch")
    read_local_test_identity(connection, configuration=configuration)
    context.configure(connection=connection, transactional_ddl=True)
    with context.begin_transaction():
        context.run_migrations()


run_local_migrations()
