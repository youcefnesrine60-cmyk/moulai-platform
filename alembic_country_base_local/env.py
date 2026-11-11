# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DISPOSABLE O3 MIGRATION ENVIRONMENT
# Accept only the new country-base rehearsal database on its dedicated loopback port.
# ==============================================

"""No URL lookup, application settings, offline SQL mode, stamp or remote target."""

from sqlalchemy import text
from sqlalchemy.engine import Connection

from alembic import context

connection = context.config.attributes.get("connection")
marker = context.config.attributes.get("country_base_marker")
if (
    context.is_offline_mode()
    or not isinstance(connection, Connection)
    or not connection.in_transaction()
    or not isinstance(marker, str)
    or len(marker) != 32
    or context.get_revision_argument()
    not in {"o220261108", "o320261108", "o420261108", "o520261111"}
):
    raise RuntimeError("country_base_migration_not_attested")
row = connection.execute(
    text(
        "SELECT current_database(),current_user,inet_server_port(),shobj_description(oid,'pg_database') "
        "FROM pg_database WHERE datname=current_database()"
    )
).one()
expected = (
    (
        "moulai_integrated",
        "moulai_integrated",
        55434,
        "moulai-restored-operational:" + marker,
    )
    if context.config.attributes.get("restored_operational") is True
    else (
        "moulai_base_rehearsal",
        "moulai_base_rehearsal",
        55434,
        "moulai-country-base:" + marker,
    )
)
if tuple(row) != expected:
    raise RuntimeError("country_base_migration_target_mismatch")
context.configure(connection=connection, transactional_ddl=True)
with context.begin_transaction():
    context.run_migrations()
