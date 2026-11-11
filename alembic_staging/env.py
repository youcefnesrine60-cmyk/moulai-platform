# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ISOLATED STAGING MIGRATION BOUNDARY
# Execute unchanged main revisions only through a supplied attested transaction.
# ==============================================

"""No environment URL lookup, stamp, application startup or default branch."""

# isort: split
# ==============================================
# EXPLICIT CONNECTION AND ATTESTOR
# The remote rehearsal and its local restoration have distinct identity checks.
# ==============================================

from sqlalchemy.engine import Connection

from alembic import context
from app.staging.target import StagingTarget

connection = context.config.attributes.get("connection")
target = context.config.attributes.get("staging_target")
if (
    context.is_offline_mode()
    or not isinstance(connection, Connection)
    or not connection.in_transaction()
    or not isinstance(target, StagingTarget)
    or context.get_revision_argument()
    not in {"s1a20261028", "o420261108", "o520261111"}
):
    raise RuntimeError("staging_migration_not_attested")
target.attest(connection=connection, migration=True)
context.configure(connection=connection, transactional_ddl=True)
with context.begin_transaction():
    context.run_migrations()
