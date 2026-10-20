# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Pinned local-only entry point for the unchanged compatibility schema."""

from sqlalchemy.engine import Connection

from alembic import context
from test_support.local_postgres import (
    LOCAL_REVISION,
    LocalPostgresSettings,
    read_local_test_identity,
)

# ==============================================
# EXECUTE ONLY A CHECKED CONNECTION AT THE EXACT PROFILE REVISION
# ==============================================


def run_local_migrations() -> None:
    """Admit only the unchanged baseline on a pinned disposable local instance."""
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
    expected_revision = LOCAL_REVISION
    if context.get_revision_argument() != expected_revision:
        raise RuntimeError("local_migration_profile_revision_mismatch")
    read_local_test_identity(connection, configuration=configuration)
    context.configure(connection=connection, transactional_ddl=True)
    with context.begin_transaction():
        context.run_migrations()


run_local_migrations()
