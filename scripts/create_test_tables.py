# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MAINTENANCE SCRIPT - TEST DATABASE BOOTSTRAP
# Inspect and migrate the isolated test schema safely.
# ==============================================

"""Bootstrap the isolated test database through its dedicated Alembic history.

The script never derives a database name from ``DATABASE_URL`` and never uses
``Base.metadata.create_all()``. Existing schemas and data are never reset.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_NAME = "neondb_test"
TEST_ALEMBIC_CONFIG = PROJECT_ROOT / "alembic_test.ini"

sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.test_database import (
    isolated_connection_arguments,
    read_test_database_identity,
    validate_test_branch_configuration,
    validated_test_database_url,
)


# ==============================================
# TEST DATABASE SAFETY
# ==============================================


def get_test_database_url() -> str:
    """Return the configured test URL after enforcing the isolated target."""
    validate_test_branch_configuration(
        branch_id=settings.TEST_DATABASE_BRANCH_ID,
        project_id=settings.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
    )
    return validated_test_database_url(
        test_database_url=settings.TEST_DATABASE_URL,
        test_endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
        protected_endpoint_id=settings.PROTECTED_DATABASE_ENDPOINT_ID,
    )


# ==============================================
# ALEMBIC BOOTSTRAP
# ==============================================


def apply_test_migrations() -> None:
    """Upgrade the isolated test schema to the dedicated Alembic head."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(TEST_ALEMBIC_CONFIG),
            "upgrade",
            "head",
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )


# ==============================================
# READ-ONLY SCHEMA SUMMARY
# ==============================================


async def get_schema_summary(*, test_database_url: str) -> tuple[str, int]:
    """Return the installed test revision and public-table count for verification."""
    engine = create_async_engine(
        test_database_url,
        pool_pre_ping=True,
        connect_args=isolated_connection_arguments(),
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(
                lambda sync: read_test_database_identity(
                    sync,
                    endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
                    branch_id=settings.TEST_DATABASE_BRANCH_ID,
                    project_id=settings.TEST_DATABASE_PROJECT_ID,
                    protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
                )
            )
            revision_result = await connection.execute(
                text("SELECT version_num FROM alembic_version"),
            )
            revision = revision_result.scalar_one()
            table_count_result = await connection.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'",
                ),
            )
            return revision, int(table_count_result.scalar_one())
    finally:
        await engine.dispose()


# ==============================================
# COMMAND-LINE ENTRY POINT
# ==============================================


def parse_arguments(*, arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the explicit maintenance options."""
    parser = argparse.ArgumentParser(
        description="Upgrade the isolated MoulAI test schema through Alembic.",
    )
    return parser.parse_args(arguments)


def main(*, arguments: Sequence[str] | None = None) -> None:
    """Validate the isolated target and migrate without resetting its data."""
    parse_arguments(arguments=arguments)
    test_database_url = get_test_database_url()

    apply_test_migrations()
    revision, table_count = asyncio.run(
        get_schema_summary(test_database_url=test_database_url),
    )
    print(f"Test schema ready: revision={revision}, public_tables={table_count}")


if __name__ == "__main__":
    main()
