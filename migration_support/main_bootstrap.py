# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# VERSIONED HISTORICAL MAIN BOOTSTRAP
# Establish explicit prerequisites on an empty, identity-checked local database.
# ==============================================

"""Apply frozen historical DDL before the unchanged main Alembic history."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND CONTRACT IDENTITY
# Keep the bootstrap independent of application settings and current ORM metadata.
# ==============================================

import hashlib
import json
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

from test_support.local_postgres import (
    LocalPostgresSettings,
    read_local_test_identity,
)

CONTRACT_PATH = Path(__file__).with_name("main_bootstrap_v1.json")
CONTRACT_SHA256 = "846eceda2218c4f2b7d43242669d95c21c5ab2cf7319fe779b34e2a25407071d"
LOGGER = logging.getLogger(__name__)


# ==============================================
# IMMUTABLE DDL ADMISSION
# Reject changed or malformed contracts before executing any schema statement.
# ==============================================


def load_bootstrap_statements() -> tuple[str, ...]:
    """Return reviewed DDL only when the exact frozen artifact is present."""
    raw = CONTRACT_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONTRACT_SHA256:
        raise RuntimeError("main_bootstrap_contract_hash_mismatch")
    contract = json.loads(raw)
    statements = contract["statements"]
    if contract["version"] != "main-bootstrap-v1" or not statements:
        raise RuntimeError("main_bootstrap_contract_invalid")
    return tuple(statements)


# ==============================================
# TRANSACTIONAL EMPTY-DATABASE BOOTSTRAP
# Never adopt existing tables or write migration history; Alembic owns its revision.
# ==============================================


def apply_main_bootstrap(
    connection: Connection, *, configuration: LocalPostgresSettings
) -> None:
    """Prepare the main prerequisites; refuse nonlocal, nonempty or unowned targets.

    The caller owns the transaction and its commit. No application configuration,
    personal permissions, commercial feature prices or Alembic version is created.
    """
    if configuration.PROFILE != "main" or not connection.in_transaction():
        raise RuntimeError("main_bootstrap_requires_explicit_transaction_and_profile")
    read_local_test_identity(connection, configuration=configuration)
    statements = load_bootstrap_statements()
    objects = connection.execute(
        text(
            "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f')"
        )
    ).scalar_one()
    if objects:
        raise RuntimeError("main_bootstrap_requires_empty_database")
    for statement in statements:
        connection.exec_driver_sql(statement)
    LOGGER.info(
        "Historical main bootstrap prepared in transaction: statements=%d",
        len(statements),
    )
