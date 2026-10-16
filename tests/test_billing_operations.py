# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Deployment guards and webhook safety without production side effects."""

from __future__ import annotations

import json
import unittest
from functools import partial
from types import SimpleNamespace
from typing import Any
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import httpx
from pydantic import SecretStr

from scripts import (
    billing_operations,
    create_admin,
)

# ==============================================
# TEST CONFIGURATION
# ==============================================


def operation_settings() -> SimpleNamespace:
    """Supply isolated test values without reading or replacing real secrets."""
    return SimpleNamespace(
        DATABASE_URL="postgresql+asyncpg://localhost/production_test_case",
        TEST_DATABASE_URL="postgresql+asyncpg://localhost/neondb_test",
        OIDC_ISSUER="https://identity.example.test/",
        OIDC_AUDIENCE="moulai-test",
        OIDC_JWKS_URL="https://identity.example.test/jwks",
        BOT_TOKEN="test-only-token",
        WEBHOOK_URL="https://moulai.example.test/webhook",
        WEBHOOK_PATH="/webhook",
        TELEGRAM_WEBHOOK_SECRET_TOKEN=SecretStr("test_only_webhook_secret"),
        MANUAL_CCP_ENABLED=True,
        MANUAL_BARIDIMOB_ENABLED=True,
        MANUAL_TRANSFER_BENEFICIARY=None,
        MANUAL_CCP_ACCOUNT=None,
        MANUAL_CCP_KEY=None,
        MANUAL_BARIDIMOB_RIP=None,
    )


# ==============================================
# FAKE DATABASE TRANSACTION
# ==============================================


def transaction_engine(
    *, snapshots: list[dict[str, Any]]
) -> tuple[MagicMock, MagicMock]:
    """Model transaction boundaries without connecting to any database."""
    connection = MagicMock()
    connection.execute = AsyncMock()
    connection.run_sync = AsyncMock(side_effect=snapshots)
    engine = MagicMock()
    engine.begin.return_value.__aenter__ = AsyncMock(return_value=connection)
    engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    engine.dispose = AsyncMock()
    return engine, connection


# ==============================================
# DATABASE AND IDENTITY GUARDS
# ==============================================


class TestBillingOperationGuards(unittest.IsolatedAsyncioTestCase):
    """Ensure writes fail before effects when identity or revision is uncertain."""

    # ==========================================
    # MISSING REAL BENEFICIARY CONFIGURATION
    # ==========================================

    def test_preflight_reports_missing_transfer_setting_names(self) -> None:
        """Ensure preflight reports missing transfer setting names."""
        with patch.object(billing_operations, "settings", operation_settings()):
            report = billing_operations.transfer_instruction_configuration()
        self.assertFalse(report["ccp_instructions_configured"])
        self.assertFalse(report["baridimob_instructions_configured"])
        self.assertIn("MANUAL_CCP_ACCOUNT", report["ccp_missing_setting_names"])
        self.assertIn("MANUAL_BARIDIMOB_RIP", report["baridimob_missing_setting_names"])

    # ==========================================
    # BENEFICIARY VALUES ARE NEVER EXPOSED BY PREFLIGHT
    # ==========================================

    def test_preflight_never_reports_account_or_beneficiary_values(self) -> None:
        """Ensure preflight never reports account or beneficiary values."""
        values = operation_settings()
        values.MANUAL_TRANSFER_BENEFICIARY = "private_test_beneficiary"
        values.MANUAL_CCP_ACCOUNT = "private_test_account"
        values.MANUAL_CCP_KEY = "42"
        values.MANUAL_BARIDIMOB_RIP = "private_test_rip"
        with patch.object(billing_operations, "settings", values):
            report = billing_operations.transfer_instruction_configuration()
        self.assertTrue(report["ccp_instructions_configured"])
        self.assertTrue(report["baridimob_instructions_configured"])
        serialized = json.dumps(report)
        for sensitive_value in (
            values.MANUAL_TRANSFER_BENEFICIARY,
            values.MANUAL_CCP_ACCOUNT,
            values.MANUAL_CCP_KEY,
            values.MANUAL_BARIDIMOB_RIP,
        ):
            self.assertNotIn(sensitive_value, serialized)

    # ==========================================
    # INVENTORY TABLE NAMES CANNOT SELECT OTHER DATA
    # ==========================================

    def test_manual_inventory_rejects_unapproved_table_before_querying(self) -> None:
        """Ensure manual inventory rejects unapproved table before querying."""
        connection = MagicMock()
        inspector = MagicMock()
        with self.assertRaisesRegex(ValueError, "unsupported_manual_evidence_table"):
            billing_operations._manual_table_inventory(
                connection, inspector, "payments", {"payments"}
            )
        connection.execute.assert_not_called()
        inspector.get_columns.assert_not_called()

    # ==========================================
    # DATABASE TARGET CONFIRMATION
    # ==========================================

    def test_wrong_database_confirmation_is_rejected(self) -> None:
        """Ensure wrong database confirmation is rejected."""
        with patch.object(billing_operations, "settings", operation_settings()):
            with self.assertRaisesRegex(
                ValueError, "database_confirmation_does_not_match"
            ):
                billing_operations.validate_database_confirmation(
                    database_name="another_database"
                )

    # ==========================================
    # ISOLATED TEST DATABASE WRITE PROTECTION
    # ==========================================

    def test_test_database_cannot_be_used_for_production_writes(self) -> None:
        """Ensure test database cannot be used for production writes."""
        values = operation_settings()
        values.DATABASE_URL = values.TEST_DATABASE_URL
        with patch.object(billing_operations, "settings", values):
            with self.assertRaisesRegex(ValueError, "cannot_target_test_database"):
                billing_operations.validate_database_confirmation(
                    database_name="neondb_test"
                )

    # ==========================================
    # UNTRACKED OR UNEXPECTED SCHEMA
    # ==========================================

    async def test_migration_refuses_an_unexpected_revision(self) -> None:
        """Ensure migration refuses an unexpected revision."""
        engine, connection = transaction_engine(
            snapshots=[
                {"installed_revisions": ["unexpected"], "billing_schema_ready": False}
            ]
        )
        with (
            patch.object(billing_operations, "settings", operation_settings()),
            patch.object(billing_operations, "operation_engine", return_value=engine),
            patch.object(
                billing_operations, "expected_head", return_value="expected_head"
            ),
            patch.object(billing_operations.command, "upgrade") as upgrade,
        ):
            with self.assertRaisesRegex(ValueError, "does_not_match_expected_revision"):
                await billing_operations.migrate(
                    database_name="production_test_case",
                    expected_revision="known_parent",
                )
            upgrade.assert_not_called()
            self.assertEqual(connection.run_sync.await_count, 1)
            engine.dispose.assert_awaited_once()
            self.assertIs(
                engine.begin.return_value.__aexit__.await_args.args[0],
                billing_operations.BillingOperationError,
            )

    # ==========================================
    # IDEMPOTENT DEPLOYMENT
    # ==========================================

    async def test_current_head_is_idempotent(self) -> None:
        """Ensure current head is idempotent."""
        engine, _ = transaction_engine(
            snapshots=[
                {"installed_revisions": ["expected_head"], "billing_schema_ready": True}
            ]
        )
        with (
            patch.object(billing_operations, "settings", operation_settings()),
            patch.object(billing_operations, "operation_engine", return_value=engine),
            patch.object(
                billing_operations, "expected_head", return_value="expected_head"
            ),
            patch.object(billing_operations.command, "upgrade") as upgrade,
        ):
            result = await billing_operations.migrate(
                database_name="production_test_case", expected_revision="known_parent"
            )
            self.assertFalse(result["changed"])
            upgrade.assert_not_called()

    # ==========================================
    # SCHEMA DRIFT AT THE CLAIMED HEAD
    # ==========================================

    async def test_current_head_with_missing_schema_is_rejected(self) -> None:
        """Ensure current head with missing schema is rejected."""
        engine, _ = transaction_engine(
            snapshots=[
                {
                    "installed_revisions": ["expected_head"],
                    "billing_schema_ready": False,
                }
            ]
        )
        with (
            patch.object(billing_operations, "settings", operation_settings()),
            patch.object(billing_operations, "operation_engine", return_value=engine),
            patch.object(
                billing_operations, "expected_head", return_value="expected_head"
            ),
        ):
            with self.assertRaisesRegex(ValueError, "does_not_match_billing_schema"):
                await billing_operations.migrate(
                    database_name="production_test_case",
                    expected_revision="known_parent",
                )

    # ==========================================
    # MISSING TRUSTED IDENTITY PROVIDER
    # ==========================================

    async def test_admin_binding_requires_trusted_oidc_before_connecting(self) -> None:
        """Ensure admin binding requires trusted oidc before connecting."""
        values = operation_settings()
        values.OIDC_JWKS_URL = None
        with (
            patch.object(billing_operations, "settings", values),
            patch.object(billing_operations, "operation_engine") as engine,
        ):
            with self.assertRaisesRegex(
                ValueError, "trusted_oidc_configuration_required"
            ):
                await billing_operations.bind_admin(
                    database_name="production_test_case",
                    admin_id=1,
                    subject="test-subject",
                )
            engine.assert_not_called()

    # ==========================================
    # EXISTING IDENTITY IS NEVER SILENTLY REPLACED
    # ==========================================

    async def test_admin_binding_requires_explicit_compare_and_swap(self) -> None:
        """Ensure admin binding requires explicit compare and swap."""
        for expected_subject in (None, "incorrect_previous_subject"):
            with self.subTest(expected_subject=expected_subject):
                engine, connection = transaction_engine(
                    snapshots=[
                        {
                            "installed_revisions": ["expected_head"],
                            "billing_schema_ready": True,
                        }
                    ]
                )
                administrator = MagicMock()
                administrator.mappings.return_value.one_or_none.return_value = {
                    "id": 1,
                    "is_active": True,
                    "role_id": 2,
                    "auth_subject": "previous_subject",
                }
                permissions = MagicMock()
                permissions.scalars.return_value = ["payments.review"]
                connection.execute.side_effect = [
                    MagicMock(),
                    administrator,
                    permissions,
                ]
                with (
                    patch.object(billing_operations, "settings", operation_settings()),
                    patch.object(
                        billing_operations, "operation_engine", return_value=engine
                    ),
                    patch.object(
                        billing_operations,
                        "expected_head",
                        return_value="expected_head",
                    ),
                ):
                    with self.assertRaises(ValueError):
                        await billing_operations.bind_admin(
                            database_name="production_test_case",
                            admin_id=1,
                            subject="new_subject",
                            expected_subject=expected_subject,
                        )
                    self.assertEqual(connection.execute.await_count, 3)

    # ==========================================
    # ACTIVE NORMALIZED REVIEW AUTHORITY IS REQUIRED
    # ==========================================

    async def test_binding_cannot_grant_authority_to_a_non_reviewer(self) -> None:
        """Ensure binding cannot grant authority to a non reviewer."""
        engine, connection = transaction_engine(
            snapshots=[
                {"installed_revisions": ["expected_head"], "billing_schema_ready": True}
            ]
        )
        administrator = MagicMock()
        administrator.mappings.return_value.one_or_none.return_value = {
            "id": 1,
            "is_active": True,
            "role_id": 2,
            "auth_subject": None,
        }
        permissions = MagicMock()
        permissions.scalars.return_value = ["orders.read"]
        connection.execute.side_effect = [MagicMock(), administrator, permissions]
        with (
            patch.object(billing_operations, "settings", operation_settings()),
            patch.object(billing_operations, "operation_engine", return_value=engine),
            patch.object(
                billing_operations, "expected_head", return_value="expected_head"
            ),
        ):
            with self.assertRaisesRegex(
                ValueError, "no_active_payment_review_permission"
            ):
                await billing_operations.bind_admin(
                    database_name="production_test_case",
                    admin_id=1,
                    subject="new_subject",
                )
        self.assertEqual(connection.execute.await_count, 3)

    # ==========================================
    # IDENTITY DUPLICATES DO NOT CROSS ADMINISTRATORS
    # ==========================================

    async def test_duplicate_subject_is_rejected_without_writing(self) -> None:
        """Ensure duplicate subject is rejected without writing."""
        engine, connection = transaction_engine(
            snapshots=[
                {"installed_revisions": ["expected_head"], "billing_schema_ready": True}
            ]
        )
        administrator = MagicMock()
        administrator.mappings.return_value.one_or_none.return_value = {
            "id": 1,
            "is_active": True,
            "role_id": 2,
            "auth_subject": None,
        }
        permissions = MagicMock()
        permissions.scalars.return_value = ["payments.review"]
        duplicate = MagicMock()
        duplicate.first.return_value = (2,)
        connection.execute.side_effect = [
            MagicMock(),
            administrator,
            permissions,
            duplicate,
        ]
        with (
            patch.object(billing_operations, "settings", operation_settings()),
            patch.object(billing_operations, "operation_engine", return_value=engine),
            patch.object(
                billing_operations, "expected_head", return_value="expected_head"
            ),
        ):
            with self.assertRaisesRegex(ValueError, "linked_to_another_administrator"):
                await billing_operations.bind_admin(
                    database_name="production_test_case",
                    admin_id=1,
                    subject="new_subject",
                )
        self.assertEqual(connection.execute.await_count, 4)

    # ==========================================
    # INSECURE IDENTITY PROVIDER
    # ==========================================

    def test_oidc_configuration_rejects_http_and_userinfo(self) -> None:
        """Ensure oidc configuration rejects http and userinfo."""
        for issuer in (
            "http://identity.example.test/",
            "https://user:password@identity.example.test/",
        ):
            with self.subTest(issuer=issuer):
                values = operation_settings()
                values.OIDC_ISSUER = issuer
                with patch.object(billing_operations, "settings", values):
                    with self.assertRaisesRegex(
                        ValueError, "trusted_oidc_https_configuration_required"
                    ):
                        billing_operations.validate_oidc_configuration()

    # ==========================================
    # NO INVENTED INITIAL TELEGRAM IDENTITY
    # ==========================================

    async def test_bootstrap_rejects_missing_private_chat_identity(self) -> None:
        """Ensure bootstrap rejects missing private chat identity."""
        with (
            patch.object(billing_operations, "settings", operation_settings()),
            patch.object(create_admin, "operation_engine") as engine,
        ):
            with self.assertRaisesRegex(
                ValueError, "explicit_valid_administrator_identity_required"
            ):
                await create_admin.create_admin(
                    database_name="production_test_case",
                    chat_id=0,
                    username="test_admin",
                    full_name="Test Administrator",
                )
            engine.assert_not_called()


# ==============================================
# WEBHOOK DEPLOYMENT SAFETY
# ==============================================


class TestWebhookDeploymentSafety(unittest.IsolatedAsyncioTestCase):
    """Do not register before the deployed endpoint enforces the current secret."""

    # ==========================================
    # LEGACY DEPLOYMENT IS NEVER RECONFIGURED
    # ==========================================

    async def test_legacy_endpoint_blocks_registration(self) -> None:
        """Ensure legacy endpoint blocks registration."""
        requests: list[httpx.Request] = []

        def endpoint(request: httpx.Request) -> httpx.Response:
            """Return the configured webhook deployment response for this verification case."""
            requests.append(request)
            return httpx.Response(200, json={"ok": False})

        factory = httpx.AsyncClient
        transport = httpx.MockTransport(endpoint)
        with (
            patch.object(billing_operations, "settings", operation_settings()),
            patch.object(
                billing_operations.httpx,
                "AsyncClient",
                side_effect=partial(factory, transport=transport),
            ),
        ):
            with self.assertRaisesRegex(
                ValueError, "does_not_reject_unauthenticated_updates"
            ):
                await billing_operations.configure_webhook(
                    url="https://moulai.example.test/webhook"
                )
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.host, "moulai.example.test")

    # ==========================================
    # MISMATCHED DEPLOYED SECRET BLOCKS REGISTRATION
    # ==========================================

    async def test_mismatched_secret_blocks_registration(self) -> None:
        """Ensure mismatched secret blocks registration."""
        requests: list[httpx.Request] = []

        def endpoint(request: httpx.Request) -> httpx.Response:
            """Return the configured webhook deployment response for this verification case."""
            requests.append(request)
            return httpx.Response(403, json={"detail": "rejected"})

        factory = httpx.AsyncClient
        transport = httpx.MockTransport(endpoint)
        with (
            patch.object(billing_operations, "settings", operation_settings()),
            patch.object(
                billing_operations.httpx,
                "AsyncClient",
                side_effect=partial(factory, transport=transport),
            ),
        ):
            with self.assertRaisesRegex(
                ValueError, "deployed_webhook_secret_does_not_match"
            ):
                await billing_operations.configure_webhook(
                    url="https://moulai.example.test/webhook"
                )
        self.assertEqual(len(requests), 2)
        self.assertTrue(
            all(request.url.host == "moulai.example.test" for request in requests)
        )

    # ==========================================
    # VERIFIED REGISTRATION RETAINS PENDING UPDATES
    # ==========================================

    async def test_verified_deployment_registers_without_dropping_updates(self) -> None:
        """Ensure verified deployment registers without dropping updates."""
        requests: list[httpx.Request] = []
        values = operation_settings()

        def endpoint(request: httpx.Request) -> httpx.Response:
            """Return the configured webhook deployment response for this verification case."""
            requests.append(request)
            if request.url.host == "moulai.example.test":
                if "X-Telegram-Bot-Api-Secret-Token" not in request.headers:
                    return httpx.Response(403, json={"detail": "rejected"})
                return httpx.Response(200, json={"ok": False})
            if request.url.path.endswith("/setWebhook"):
                return httpx.Response(200, json={"ok": True, "result": True})
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {"url": values.WEBHOOK_URL, "pending_update_count": 4},
                },
            )

        factory = httpx.AsyncClient
        transport = httpx.MockTransport(endpoint)
        with (
            patch.object(billing_operations, "settings", values),
            patch.object(
                billing_operations.httpx,
                "AsyncClient",
                side_effect=partial(factory, transport=transport),
            ),
        ):
            result = await billing_operations.configure_webhook(url=values.WEBHOOK_URL)
        self.assertTrue(result["configured"])
        registration = json.loads(requests[2].content)
        self.assertIs(registration["drop_pending_updates"], False)
        self.assertEqual(result["pending_update_count"], 4)
        self.assertNotIn(values.BOT_TOKEN, json.dumps(result))
        self.assertNotIn(
            values.TELEGRAM_WEBHOOK_SECRET_TOKEN.get_secret_value(), json.dumps(result)
        )


if __name__ == "__main__":
    unittest.main()
