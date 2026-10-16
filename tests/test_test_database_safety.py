# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Offline regressions for endpoint isolation without opening database connections."""

# ==============================================
# IMPORTS
# ==============================================

import unittest
import copy
import ssl
from typing import (
    Any,
    cast,
)
from unittest.mock import MagicMock

from sqlalchemy.engine import Connection

from app.core.test_database import (
    UnsafeTestDatabaseError,
    isolated_connection_arguments,
    read_test_database_identity,
    validate_test_branch_configuration,
    validated_test_database_url,
)


# ==============================================
# ISOLATION AND SECRET-SAFE FAILURE CONTRACTS
# ==============================================


class TestDatabaseIsolation(unittest.TestCase):
    """Keep test tooling away from the protected branch, including pooler aliases."""

    def validate(
        self, *, url: str, endpoint: str | None = "ep-development-test"
    ) -> str:
        """Validate explicit synthetic test configuration without environment reads."""
        return validated_test_database_url(
            test_database_url=url,
            test_endpoint_id=endpoint,
            protected_endpoint_id="ep-protected-test",
        )

    def test_development_direct_and_pooler_endpoints_are_accepted(self) -> None:
        """Accept only the declared endpoint for the exact asynchronous database."""
        for host in ("ep-development-test", "ep-development-test-pooler"):
            url = f"postgresql+asyncpg://{host}.eu-central-1.aws.neon.tech/neondb_test?ssl=require"
            with self.subTest(host=host):
                self.assertEqual(self.validate(url=url), url)

    def test_same_branch_different_database_is_rejected(self) -> None:
        """A neondb_test database name does not authorize the production endpoint."""
        for host in ("ep-protected-test", "ep-protected-test-pooler"):
            with self.subTest(host=host), self.assertRaises(RuntimeError):
                self.validate(
                    url=f"postgresql+asyncpg://{host}.aws.neon.tech/neondb_test"
                )

    def test_missing_or_protected_development_declaration_is_rejected(self) -> None:
        """Require independently declared target and protected endpoint IDs."""
        for endpoint in (None, "", "ep-protected-test", "ep-development-test-pooler"):
            with self.subTest(endpoint=endpoint), self.assertRaises(RuntimeError):
                self.validate(
                    url="postgresql+asyncpg://ep-development-test.aws.neon.tech/neondb_test",
                    endpoint=endpoint,
                )

    def test_routing_overrides_wrong_database_driver_and_host_are_rejected(
        self,
    ) -> None:
        """Reject driver mistakes and query options that redirect a verified URL."""
        prefix = "postgresql+asyncpg://ep-development-test.aws.neon.tech/neondb_test"
        invalid = (
            prefix.replace("neondb_test", "neondb"),
            prefix.replace("postgresql+asyncpg", "postgresql"),
            prefix.replace("aws.neon.tech", "example.invalid"),
            *(
                f"{prefix}?{key}=override"
                for key in (
                    "host",
                    "hostaddr",
                    "port",
                    "database",
                    "dbname",
                    "options",
                    "dsn",
                    "service",
                    "user",
                    "password",
                )
            ),
            *(f"{prefix}?ssl={mode}" for mode in ("disable", "allow", "prefer")),
        )
        for url in invalid:
            with self.subTest(case=invalid.index(url)), self.assertRaises(RuntimeError):
                self.validate(url=url)

    def test_error_never_contains_credentials_or_url(self) -> None:
        """Configuration errors must not echo credentials even for malformed input."""
        url = "postgresql+asyncpg://private-user:secret-value@ep-protected-test.aws.neon.tech/neondb_test"
        with self.assertRaises(RuntimeError) as error:
            self.validate(url=url)
        for sensitive in (url, "private-user", "secret-value"):
            self.assertNotIn(sensitive, str(error.exception))


# ==============================================
# SERVER ATTESTATION AND TRANSPORT BOUNDARIES
# ==============================================


class TestServerIdentity(unittest.TestCase):
    """Reject session-controlled or incomplete metadata even if values look right."""

    def rows(self) -> list[dict[str, Any]]:
        """Build explicit synthetic configuration-file identities for offline checks."""
        values = {
            "neon.branch_id": "br-development-test",
            "neon.project_id": "test-project-01",
            "neon.endpoint_id": "ep-development-test",
        }
        return [
            {
                "name": name,
                "setting": value,
                "reset_val": value,
                "context": "postmaster",
                "source": "configuration file",
                "vartype": "string",
                "pending_restart": False,
            }
            for name, value in values.items()
        ]

    def check(
        self, *, rows: list[dict[str, Any]], database: str = "neondb_test"
    ) -> dict[str, str]:
        """Call the real identity validator using fake read-only SQL results."""
        connection = MagicMock()
        database_result = MagicMock()
        database_result.scalar_one.return_value = database
        settings_result = MagicMock()
        settings_result.mappings.return_value.all.return_value = rows
        connection.execute.side_effect = [database_result, settings_result]
        return read_test_database_identity(
            cast(Connection, connection),
            endpoint_id="ep-development-test",
            branch_id="br-development-test",
            project_id="test-project-01",
            protected_branch_id="br-protected-test",
        )

    def test_immutable_branch_project_and_configured_endpoint_are_accepted(
        self,
    ) -> None:
        """The endpoint may be supplementary superuser metadata, never the branch."""
        for context in ("postmaster", "superuser"):
            rows = self.rows()
            rows[-1]["context"] = context
            with self.subTest(context=context):
                identity = self.check(rows=rows)
                self.assertEqual(identity["branch_id"], "br-development-test")
                self.assertEqual(identity["endpoint_context"], context)

    def test_session_sources_spoofs_and_pending_settings_are_rejected(self) -> None:
        """Matching strings cannot excuse a mutable branch or session override."""
        for index in range(3):
            for key, value in (
                ("setting", "different"),
                ("reset_val", "different"),
                ("source", "session"),
                ("source", "client"),
                ("source", "default"),
                ("source", "database"),
                ("context", "user"),
                ("vartype", "bool"),
                ("pending_restart", True),
            ):
                rows = copy.deepcopy(self.rows())
                rows[index][key] = value
                with (
                    self.subTest(row=index, property=key, value=value),
                    self.assertRaises(UnsafeTestDatabaseError),
                ):
                    self.check(rows=rows)
        rows = self.rows()
        rows[0]["context"] = "superuser"
        with self.assertRaises(UnsafeTestDatabaseError):
            self.check(rows=rows)

    def test_missing_identity_and_actual_production_database_are_rejected(self) -> None:
        """Every identity row and the actual database name are mandatory."""
        for index in range(3):
            rows = self.rows()
            rows.pop(index)
            with (
                self.subTest(missing=index),
                self.assertRaises(UnsafeTestDatabaseError),
            ):
                self.check(rows=rows)
        with self.assertRaises(UnsafeTestDatabaseError):
            self.check(rows=self.rows(), database="neondb")

    def test_tls_verifies_hostname_and_never_sets_server_identities(self) -> None:
        """Connections must validate CA and hostname without identity overrides."""
        arguments = isolated_connection_arguments()
        self.assertIs(arguments["ssl"].check_hostname, True)
        self.assertEqual(arguments["ssl"].verify_mode, ssl.CERT_REQUIRED)
        self.assertFalse(
            any(name.startswith("neon.") for name in arguments["server_settings"])
        )

    def test_missing_branch_configuration_and_protected_branch_are_rejected(
        self,
    ) -> None:
        """There is no inferred or production-branch fallback."""
        valid = {
            "branch_id": "br-development-test",
            "project_id": "test-project-01",
            "protected_branch_id": "br-protected-test",
        }
        for key in valid:
            with self.subTest(missing=key), self.assertRaises(UnsafeTestDatabaseError):
                validate_test_branch_configuration(**(valid | {key: None}))
        with self.assertRaises(UnsafeTestDatabaseError):
            validate_test_branch_configuration(
                **(valid | {"branch_id": "br-protected-test"})
            )


if __name__ == "__main__":
    unittest.main()
