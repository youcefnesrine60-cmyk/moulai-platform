# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT LOCAL MAIN MIGRATION LAUNCHER
# Refuse permanent destinations before applying bootstrap and the main S1a chain.
# ==============================================

"""Reconstruct only a marked, disposable local database; never read .env."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND DEDICATED TARGET SETTINGS
# Receive the connection through one named process variable, with no DATABASE_URL fallback.
# ==============================================

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import asyncpg
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.run_local_postgres_tests import apply_local_migrations
from test_support.local_postgres import (
    LOCAL_MAIN_REVISION,
    LocalPostgresNetworkGuard,
    LocalPostgresSettings,
    read_local_test_identity,
)

# ==============================================
# ONE TRANSACTION ON AN ATTESTED EMPTY DATABASE
# Require explicit opt-in; failures roll back DDL rather than repairing existing schemas.
# ==============================================


async def reconstruct(
    *, configuration: LocalPostgresSettings, apply: bool
) -> dict[str, object]:
    """Inspect or reconstruct the exact local database; return nonsensitive evidence."""
    engine = create_async_engine(
        configuration.URL.get_secret_value(),
        echo=False,
        hide_parameters=True,
        connect_args={"ssl": False, "timeout": 20, "command_timeout": 90},
    )
    try:
        async with engine.begin() as connection:
            if not apply:
                await connection.execute(text("SET TRANSACTION READ ONLY"))
            await connection.run_sync(
                lambda sync: read_local_test_identity(sync, configuration=configuration)
            )
            if apply:
                await connection.run_sync(
                    lambda sync: apply_local_migrations(
                        sync, configuration=configuration
                    )
                )
            count = (
                await connection.execute(
                    text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
                )
            ).scalar_one()
            revision = (
                (
                    await connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    )
                ).scalar_one()
                if apply
                else None
            )
            if apply and (revision != LOCAL_MAIN_REVISION or count != 61):
                raise RuntimeError("main_migration_final_catalogue_mismatch")
        return {
            "mode": "applied_and_committed" if apply else "identity_checked_only",
            "host": "127.0.0.1",
            "database": "moulai_pytest",
            "revision": revision,
            "public_tables": count,
        }
    finally:
        await engine.dispose()


# ==============================================
# FAIL-CLOSED COMMAND LINE
# The only accepted URL is an isolated loopback target with a fresh instance marker.
# ==============================================


def main() -> int:
    """Run a checked inspection by default, or one explicit empty-local reconstruction."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--confirm-empty-local", action="store_true")
    options = parser.parse_args()
    try:
        configuration = LocalPostgresSettings(
            URL=os.environ.get("MOULAI_MAIN_LOCAL_URL", ""),
            INSTANCE_ID=options.instance_id,
            PROFILE="main",
            SERVER_PORT=55432,
        )
        guard = LocalPostgresNetworkGuard()
        sys.addaudithook(guard)
        result = asyncio.run(
            reconstruct(configuration=configuration, apply=options.confirm_empty_local)
        )
        if guard.denied:
            raise RuntimeError("main_migration_network_boundary_violation")
    except (
        OSError,
        RuntimeError,
        ValueError,
        SQLAlchemyError,
        asyncpg.PostgresError,
    ) as error:
        # Driver exceptions can include parameters; expose the class only.
        print(json.dumps({"status": "STOPPED", "error_type": type(error).__name__}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
