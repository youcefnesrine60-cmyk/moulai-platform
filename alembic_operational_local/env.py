# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNED OPERATIONAL DEVELOPMENT MIGRATION BOUNDARY
# Reuse the main history on a new, identified local database without stamping.
# ==============================================

"""No URL discovery, permanent target or migration-history substitution."""

from sqlalchemy import text
from sqlalchemy.engine import Connection

from alembic import context
from app.integration.config import IntegrationConfig

connection = context.config.attributes.get("connection")
configuration = context.config.attributes.get("operational_configuration")
if (
    context.is_offline_mode()
    or not isinstance(connection, Connection)
    or not isinstance(configuration, IntegrationConfig)
    or not connection.in_transaction()
    or context.get_revision_argument() not in {"o120261108", "o220261108", "o420261108"}
):
    raise RuntimeError("operational_migration_not_attested")
row = connection.execute(
    text(
        "SELECT current_database(),current_user,inet_server_port(),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"
    )
).one()
if tuple(row) != (
    "moulai_integrated",
    "moulai_integrated",
    55433,
    "moulai-operational-local:" + configuration.instance_id,
):
    raise RuntimeError("operational_migration_target_mismatch")
context.configure(connection=connection, transactional_ddl=True)
with context.begin_transaction():
    context.run_migrations()
