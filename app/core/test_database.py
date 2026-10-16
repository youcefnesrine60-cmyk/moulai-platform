# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Validate isolated Neon test targets before opening a database connection."""

# ==============================================
# IMPORTS AND TARGET CONTRACT
# ==============================================

import re
import ssl
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import (
    Connection,
    make_url,
)
from sqlalchemy.exc import ArgumentError

TEST_DATABASE_NAME = "neondb_test"
_ENDPOINT_ID = re.compile(r"ep-[a-z0-9]+(?:-[a-z0-9]+)*")
_ROUTING_OPTIONS = frozenset(
    {
        "host",
        "hostaddr",
        "port",
        "database",
        "dbname",
        "user",
        "password",
        "dsn",
        "service",
        "options",
    }
)


# ==============================================
# FAIL-CLOSED TEST TARGET VALIDATION
# ==============================================


class UnsafeTestDatabaseError(RuntimeError):
    """Report a safe configuration error without exposing connection details."""


def validated_test_database_url(
    *,
    test_database_url: str,
    test_endpoint_id: str | None,
    protected_endpoint_id: str | None,
) -> str:
    """Require the declared development endpoint and exclude the protected one.

    Endpoint IDs must come from the approved Neon branch configuration. A
    different database name on the production endpoint is insufficient isolation.
    This validation does not independently attest a branch-to-endpoint mapping.
    Errors deliberately omit URLs, usernames, passwords, and query values.
    """
    if (
        not isinstance(test_endpoint_id, str)
        or not _ENDPOINT_ID.fullmatch(test_endpoint_id)
        or test_endpoint_id.endswith("-pooler")
    ):
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_ENDPOINT_ID must identify the verified development endpoint"
        )
    if (
        not isinstance(protected_endpoint_id, str)
        or not _ENDPOINT_ID.fullmatch(protected_endpoint_id)
        or protected_endpoint_id.endswith("-pooler")
    ):
        raise UnsafeTestDatabaseError(
            "PROTECTED_DATABASE_ENDPOINT_ID must identify the protected production endpoint"
        )
    if test_endpoint_id == protected_endpoint_id:
        raise UnsafeTestDatabaseError(
            "The development endpoint must differ from the protected production endpoint"
        )
    try:
        url = make_url(test_database_url)
    except (ArgumentError, TypeError, ValueError):
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_URL is not a valid SQLAlchemy URL"
        ) from None
    if url.drivername != "postgresql+asyncpg" or url.database != TEST_DATABASE_NAME:
        raise UnsafeTestDatabaseError(
            "Tests require postgresql+asyncpg and the neondb_test database"
        )
    hostname = (url.host or "").lower()
    endpoint = hostname.split(".", 1)[0].removesuffix("-pooler")
    if not hostname.endswith(".neon.tech") or endpoint != test_endpoint_id:
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_URL does not match the verified development endpoint"
        )
    if _ROUTING_OPTIONS.intersection(key.lower() for key in url.query):
        raise UnsafeTestDatabaseError(
            "Connection-routing query options are forbidden for isolated tests"
        )
    if any(
        value in {"disable", "allow", "prefer"}
        for key, value in url.query.items()
        if key in {"ssl", "sslmode"}
    ):
        raise UnsafeTestDatabaseError("Isolated Neon tests must not weaken TLS")
    return test_database_url


# ==============================================
# EXPECTED BRANCH CONFIGURATION
# ==============================================


def validate_test_branch_configuration(
    *, branch_id: str | None, project_id: str | None, protected_branch_id: str | None
) -> None:
    """Require explicit operator-confirmed branch IDs and reject the protected one."""
    if not isinstance(branch_id, str) or not re.fullmatch(
        r"br-[a-z0-9]+(?:-[a-z0-9]+)*", branch_id
    ):
        raise UnsafeTestDatabaseError("TEST_DATABASE_BRANCH_ID is missing or invalid")
    if not isinstance(protected_branch_id, str) or not re.fullmatch(
        r"br-[a-z0-9]+(?:-[a-z0-9]+)*", protected_branch_id
    ):
        raise UnsafeTestDatabaseError(
            "PROTECTED_DATABASE_BRANCH_ID is missing or invalid"
        )
    if branch_id == protected_branch_id:
        raise UnsafeTestDatabaseError(
            "The protected production branch cannot be a test target"
        )
    if not isinstance(project_id, str) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", project_id
    ):
        raise UnsafeTestDatabaseError("TEST_DATABASE_PROJECT_ID is missing or invalid")


# ==============================================
# VERIFIED TLS AND BOUNDED TEST CONNECTIONS
# ==============================================


def isolated_connection_arguments() -> dict[str, Any]:
    """Require trusted CA and hostname checks rather than asyncpg's TLS preference."""
    return {
        "ssl": ssl.create_default_context(),
        "timeout": 30,
        "command_timeout": 180,
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
        "server_settings": {
            "search_path": "public",
            "lock_timeout": "15000",
            "timezone": "UTC",
        },
    }


# ==============================================
# LIVE POSTGRESQL IDENTITY (READ-ONLY DATABASE HELPER)
# ==============================================


def read_test_database_identity(
    connection: Connection,
    *,
    endpoint_id: str | None,
    branch_id: str | None,
    project_id: str | None,
    protected_branch_id: str | None,
) -> dict[str, str]:
    """Verify immutable branch/project IDs and compare the configured endpoint.

    Neon declares these settings PGC_POSTMASTER in pgxn/neon/libpagestore.c
    and writes their values from ComputeSpec in compute_tools/src/config.rs.
    Branch/project must be postmaster settings. Some observed servers expose
    endpoint_id as superuser; it is only supplementary evidence and must match
    the configuration-file/reset value without a pending restart. Verified TLS
    and immutable branch/project identities remain mandatory for every caller.
    Session, client, default and user overrides and missing identities fail closed.
    """
    validate_test_branch_configuration(
        branch_id=branch_id,
        project_id=project_id,
        protected_branch_id=protected_branch_id,
    )
    database = connection.execute(text("SELECT current_database()")).scalar_one()
    if database != TEST_DATABASE_NAME:
        raise UnsafeTestDatabaseError(
            "The test connection reached an unexpected database"
        )
    expected = {
        "neon.endpoint_id": endpoint_id,
        "neon.branch_id": branch_id,
        "neon.project_id": project_id,
    }
    rows = (
        connection.execute(
            text(
                "SELECT name, setting, context, vartype, source, reset_val, pending_restart FROM pg_catalog.pg_settings WHERE name IN ('neon.endpoint_id', 'neon.branch_id', 'neon.project_id')"
            )
        )
        .mappings()
        .all()
    )
    actual = {row["name"]: row for row in rows}
    if set(actual) != set(expected) or any(
        not expected[name]
        or row["context"]
        not in (
            {"postmaster", "superuser"}
            if name == "neon.endpoint_id"
            else {"postmaster"}
        )
        or row["vartype"] != "string"
        or row["source"] != "configuration file"
        or row["setting"] != expected[name]
        or row["reset_val"] != expected[name]
        or row["pending_restart"] is not False
        for name, row in actual.items()
    ):
        raise UnsafeTestDatabaseError(
            "The server did not attest the expected development project, branch and endpoint"
        )
    return {
        "database": database,
        "endpoint_id": str(endpoint_id),
        "branch_id": str(branch_id),
        "project_id": str(project_id),
        "identity_source": "neon_configuration_and_postmaster_branch_project",
        "endpoint_context": actual["neon.endpoint_id"]["context"],
    }
