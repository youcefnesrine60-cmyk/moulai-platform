# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Prove rehearsal boundary failures stop before database mutation or migration."""

# ==============================================
# IMPORTS AND OFFLINE TARGET CONFIGURATION
# ==============================================

import unittest
from types import SimpleNamespace
from typing import cast
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

from sqlalchemy.engine import Connection

from app.core.test_database import UnsafeTestDatabaseError
from scripts import billing_test_rehearsal as rehearsal


def target_settings() -> SimpleNamespace:
    """Return explicit synthetic endpoints without reading or using a real DSN."""
    return SimpleNamespace(
        TEST_DATABASE_URL="postgresql+asyncpg://ep-development-test.aws.neon.tech/neondb_test?ssl=require",
        TEST_DATABASE_ENDPOINT_ID="ep-development-test",
        PROTECTED_DATABASE_ENDPOINT_ID="ep-protected-test",
        TEST_DATABASE_BRANCH_ID="br-development-test",
        TEST_DATABASE_PROJECT_ID="test-project-01",
        PROTECTED_DATABASE_BRANCH_ID="br-protected-test",
    )


# ==============================================
# EARLY FAILURES MUST NOT OPEN OR ALTER A DATABASE
# ==============================================


class TestRehearsalBoundary(unittest.IsolatedAsyncioTestCase):
    """Use fake connection results to verify fail-closed runtime boundaries."""

    async def test_protected_endpoint_fails_before_engine_creation(self) -> None:
        """A declaration mistake must never produce a database connection."""
        values = target_settings()
        values.TEST_DATABASE_ENDPOINT_ID = values.PROTECTED_DATABASE_ENDPOINT_ID
        with (
            patch.object(rehearsal, "settings", values),
            patch.object(rehearsal, "create_async_engine") as create_engine,
        ):
            with self.assertRaises(UnsafeTestDatabaseError):
                await rehearsal.rehearse(scenario="fresh")
        create_engine.assert_not_called()

    async def test_unexpected_actual_database_fails_before_any_write(self) -> None:
        """Verify current_database(), then refuse a misrouted live connection."""
        connection = AsyncMock()
        sync_connection = MagicMock()
        sync_connection.execute.return_value.scalar_one.return_value = "neondb"
        connection.run_sync.side_effect = lambda callback: callback(sync_connection)
        engine = MagicMock()
        engine.connect.return_value.__aenter__.return_value = connection
        engine.dispose = AsyncMock()
        with (
            patch.object(rehearsal, "settings", target_settings()),
            patch.object(rehearsal, "create_async_engine", return_value=engine),
        ):
            with self.assertRaisesRegex(UnsafeTestDatabaseError, "unexpected database"):
                await rehearsal.rehearse(scenario="fresh")
        self.assertEqual(connection.execute.await_count, 1)
        self.assertEqual(
            str(connection.execute.await_args.args[0]), "SET TRANSACTION READ ONLY"
        )
        self.assertEqual(
            str(sync_connection.execute.call_args.args[0]), "SELECT current_database()"
        )
        self.assertEqual(sync_connection.execute.call_count, 1)
        connection.begin.assert_not_called()
        self.assertEqual(connection.run_sync.await_count, 1)
        engine.dispose.assert_awaited_once()

    def test_alembic_shared_connection_rechecks_database(self) -> None:
        """Prevent Alembic configuration even when a caller supplies a bad connection."""
        connection = MagicMock()
        connection.execute.return_value.scalar_one.return_value = "neondb"
        with patch.object(rehearsal, "Config") as configuration:
            with self.assertRaisesRegex(
                rehearsal.RehearsalError, "unexpected_database"
            ):
                rehearsal._configuration(cast(Connection, connection))
        configuration.assert_not_called()


if __name__ == "__main__":
    unittest.main()
