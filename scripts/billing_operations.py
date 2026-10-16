# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Guarded billing deployment, administrator identity, and webhook operations.

Run from the project root. Configuration comes from the same Settings instance
as the application. Reports never contain credentials, OIDC subjects, or receipt
content. Database writes require an exact database-name confirmation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import (
    Any,
    TypeAlias,
)
from urllib.parse import urlsplit

import httpx
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import (
    Select,
    inspect,
    literal,
    select,
    text,
    update,
)
from sqlalchemy.engine import (
    Connection,
    make_url,
)
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    create_async_engine,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.logger import logger
from app.models.admin import Admin
from app.models.admin_log import AdminLog
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)

# ==============================================
# TYPES AND DATABASE DEPLOYMENT LOCK
# ==============================================

OperationReport: TypeAlias = dict[str, Any]
DEPLOYMENT_LOCK_ID = 636052368236128
REQUIRED_TABLES = frozenset(
    {
        "admins",
        "admin_logs",
        "payments",
        "roles",
        "permissions",
        "role_permissions",
        "manual_payment_receipts",
        "manual_payment_audit",
    }
)


# ==============================================
# SAFE OPERATIONAL ERRORS
# ==============================================


class BillingOperationError(ValueError):
    """Carry a stable public code without credential-bearing exception text."""


# ==============================================
# LOCAL DIAGNOSTIC REPORT FILES
# ==============================================


def report_output_path(*, filename: str) -> Path:
    """Confine an explicit report filename to this project's local artifacts."""
    reserved_names = {"CON", "PRN", "AUX", "NUL"}
    reserved_names.update(
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    )
    if (
        len(filename) > 128
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.json", filename) is None
        or filename.split(".", maxsplit=1)[0].upper() in reserved_names
    ):
        raise BillingOperationError("invalid_billing_report_filename")
    project_root = PROJECT_ROOT.resolve()
    directory = (project_root / "artifacts" / "billing-reports").resolve()
    if not directory.is_relative_to(project_root):
        raise BillingOperationError("unsafe_billing_report_directory")
    output_path = directory / filename
    if output_path.is_dir():
        raise BillingOperationError("invalid_billing_report_filename")
    return output_path


def write_report(*, output_path: Path, report: OperationReport) -> None:
    """Atomically persist one UTF-8 JSON report without console log records."""
    checked_path = report_output_path(filename=output_path.name)
    if checked_path != output_path:
        raise BillingOperationError("unsafe_billing_report_directory")
    checked_path.parent.mkdir(parents=True, exist_ok=True)
    if report_output_path(filename=output_path.name) != checked_path:
        raise BillingOperationError("unsafe_billing_report_directory")
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{checked_path.name}.",
            suffix=".tmp",
            dir=checked_path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        temporary_path.replace(checked_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


# ==============================================
# ALEMBIC CONFIGURATION
# ==============================================


def alembic_configuration() -> Config:
    """Use an absolute migration directory without copying database secrets."""
    configuration = Config(str(PROJECT_ROOT / "alembic.ini"))
    configuration.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    configuration.set_main_option("path_separator", "os")
    return configuration


# ==============================================
# EXPECTED MIGRATION HEAD
# ==============================================


def expected_head() -> str:
    """Require one production migration head before deployment or provisioning."""
    head = ScriptDirectory.from_config(alembic_configuration()).get_current_head()
    if head is None:
        raise BillingOperationError("production_migration_head_missing")
    return head


# ==============================================
# TARGET DATABASE GUARD
# ==============================================


def validate_database_confirmation(*, database_name: str) -> None:
    """Reject writes to a different database or the isolated test database."""
    configured_name = make_url(settings.DATABASE_URL).database
    test_name = (
        make_url(settings.TEST_DATABASE_URL).database
        if settings.TEST_DATABASE_URL
        else None
    )
    if not database_name or configured_name != database_name:
        raise BillingOperationError("database_confirmation_does_not_match")
    if configured_name == test_name:
        raise BillingOperationError("production_operation_cannot_target_test_database")


# ==============================================
# OPERATIONAL DATABASE ENGINE
# ==============================================


def operation_engine() -> AsyncEngine:
    """Disable SQL echo and apply bounded connections and lock acquisition."""
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={
            "timeout": 30,
            "command_timeout": 120,
            "server_settings": {
                "search_path": "public",
                "lock_timeout": "15000",
            },
        },
    )


# ==============================================
# BASE ADMINISTRATOR AND PERMISSION SELECTS
# ==============================================


def _base_admin_select(
    *,
    identity_available: bool = True,
    role_available: bool = True,
) -> Select[Any]:
    """Read only the identity and authorization columns needed for provisioning."""
    return select(
        Admin.id,
        Admin.is_active,
        Admin.role_id if role_available else literal(None).label("role_id"),
        (
            Admin.auth_subject
            if identity_available
            else literal(None).label("auth_subject")
        ),
        Admin.chat_id,
    )


def _base_permission_select() -> Select[tuple[str]]:
    """Use active normalized RBAC roles as the source of administrative power."""
    return (
        select(Permission.code)
        .join(role_permissions, Permission.id == role_permissions.c.permission_id)
        .join(Role, Role.id == role_permissions.c.role_id)
        .where(Role.is_active.is_(True))
    )


# ==============================================
# READ-ONLY SCHEMA SNAPSHOT (DATABASE HELPER)
# ==============================================


def _schema_snapshot(connection: Connection) -> OperationReport:
    """Inspect installed revisions and columns without creating schema objects."""
    inspector = inspect(connection)
    tables = set(inspector.get_table_names(schema="public"))
    columns = {
        table_name: {
            column["name"]
            for column in inspector.get_columns(table_name, schema="public")
        }
        for table_name in ("admins", "payments")
        if table_name in tables
    }
    revisions = list(MigrationContext.configure(connection).get_current_heads())
    schema_ready = (
        REQUIRED_TABLES.issubset(tables)
        and {"auth_subject", "role_id"}.issubset(columns.get("admins", set()))
        and {"payment_provider", "currency"}.issubset(columns.get("payments", set()))
    )
    manual_schema_validation = _existing_manual_schema_validation(inspector, tables)
    schema_ready = schema_ready and manual_schema_validation["compatible"]
    return {
        "installed_revisions": revisions,
        "expected_revision": expected_head(),
        "table_count": len(tables),
        "missing_billing_tables": sorted(REQUIRED_TABLES.difference(tables)),
        "admin_identity_column_present": "auth_subject" in columns.get("admins", set()),
        "admin_role_column_present": "role_id" in columns.get("admins", set()),
        "payment_provider_column_present": "payment_provider"
        in columns.get("payments", set()),
        "payment_currency_column_present": "currency" in columns.get("payments", set()),
        "billing_schema_ready": schema_ready,
        "rbac_schema_ready": {"roles", "permissions", "role_permissions"}.issubset(
            tables
        ),
        "manual_evidence_schema": {
            table_name: _manual_table_inventory(
                connection, inspector, table_name, tables
            )
            for table_name in ("manual_payment_receipts", "manual_payment_audit")
        },
        "existing_manual_schema_validation": manual_schema_validation,
    }


# ==============================================
# READ-ONLY MIGRATION ADOPTION GUARD
# ==============================================


def _existing_manual_schema_validation(
    inspector: Inspector,
    tables: set[str],
) -> OperationReport:
    """Run the frozen migration's adoption checks without locks or writes."""
    revision = ScriptDirectory.from_config(alembic_configuration()).get_revision(
        "c413b7918a20"
    )
    if revision is None:
        raise BillingOperationError("manual_payment_migration_contract_missing")
    validator = revision.module._validate_manual_table
    validated: list[str] = []
    for table_name in ("manual_payment_receipts", "manual_payment_audit"):
        if table_name not in tables:
            continue
        try:
            validator(inspector, table_name)
        except RuntimeError as error:
            reason = str(error)
            return {
                "compatible": False,
                "validated_tables": validated,
                "reason": (
                    reason
                    if reason.startswith("manual_payment_schema_drift:")
                    else "manual_payment_schema_validation_failed"
                ),
            }
        validated.append(table_name)
    return {
        "compatible": True,
        "validated_tables": validated,
        "contract_revision": "c413b7918a20",
    }


# ==============================================
# MANUAL EVIDENCE TABLE INVENTORY (DATABASE HELPER)
# ==============================================


def _manual_table_inventory(
    connection: Connection,
    inspector: Inspector,
    table_name: str,
    tables: set[str],
) -> OperationReport:
    """Report constraints and aggregate counts without exposing evidence data."""
    if table_name not in {"manual_payment_receipts", "manual_payment_audit"}:
        raise BillingOperationError("unsupported_manual_evidence_table")
    if table_name not in tables:
        return {"exists": False}
    return {
        "exists": True,
        "row_count": connection.execute(
            text(f'SELECT count(*) FROM public."{table_name}"')
        ).scalar_one(),
        "columns": [
            {
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column["nullable"],
                "has_server_default": column.get("default") is not None,
            }
            for column in inspector.get_columns(table_name, schema="public")
        ],
        "primary_key_columns": inspector.get_pk_constraint(table_name, schema="public")[
            "constrained_columns"
        ],
        "unique_constraints": [
            {"name": constraint["name"], "columns": constraint["column_names"]}
            for constraint in inspector.get_unique_constraints(
                table_name, schema="public"
            )
        ],
        "check_constraints": [
            {"name": constraint["name"], "sql": constraint["sqltext"]}
            for constraint in inspector.get_check_constraints(
                table_name, schema="public"
            )
        ],
        "foreign_keys": [
            {
                "name": constraint["name"],
                "columns": constraint["constrained_columns"],
                "referenced_table": constraint["referred_table"],
                "referenced_columns": constraint["referred_columns"],
                "on_delete": constraint.get("options", {}).get("ondelete"),
            }
            for constraint in inspector.get_foreign_keys(table_name, schema="public")
        ],
        "indexes": [
            {
                "name": index["name"],
                "columns": index["column_names"],
                "unique": index["unique"],
            }
            for index in inspector.get_indexes(table_name, schema="public")
        ],
    }


# ==============================================
# LIVE REVIEW PERMISSION (DATABASE HELPER)
# ==============================================


async def _review_permission(connection: AsyncConnection, role_id: int | None) -> bool:
    """Check the current active role and its current permission assignments."""
    if role_id is None:
        return False
    permission_codes = set(
        (
            await connection.execute(
                _base_permission_select().where(Role.id == role_id)
            )
        ).scalars()
    )
    return "*" in permission_codes or "payments.review" in permission_codes


# ==============================================
# PRODUCTION PREFLIGHT
# ==============================================


async def preflight(*, include_telegram: bool = False) -> OperationReport:
    """Report deployment readiness within a PostgreSQL read-only transaction."""
    engine = operation_engine()
    try:
        async with engine.connect() as connection:
            async with connection.begin():
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                report = await connection.run_sync(_schema_snapshot)
                report["database_name"] = make_url(settings.DATABASE_URL).database
                report["application_environment"] = settings.APP_ENV
                report["debug_enabled"] = settings.DEBUG
                report["oidc_configured"] = bool(
                    settings.OIDC_ISSUER
                    and settings.OIDC_AUDIENCE
                    and settings.OIDC_JWKS_URL
                )
                report["missing_oidc_configuration_keys"] = [
                    key
                    for key in ("OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_JWKS_URL")
                    if not getattr(settings, key)
                ]
                try:
                    validate_oidc_configuration()
                except BillingOperationError:
                    report["oidc_trust_configuration_valid"] = False
                else:
                    report["oidc_trust_configuration_valid"] = True
                report["transfer_instruction_configuration"] = (
                    transfer_instruction_configuration()
                )
                report["webhook_secret_configured"] = bool(
                    settings.TELEGRAM_WEBHOOK_SECRET_TOKEN
                    and settings.TELEGRAM_WEBHOOK_SECRET_TOKEN.get_secret_value()
                )
                report["administrators"] = []
                if "admins" not in report["missing_billing_tables"]:
                    administrators = (
                        await connection.execute(
                            _base_admin_select(
                                identity_available=report[
                                    "admin_identity_column_present"
                                ],
                                role_available=report["admin_role_column_present"],
                            ).order_by(Admin.id)
                        )
                    ).mappings()
                    report["administrators"] = [
                        {
                            "admin_id": administrator["id"],
                            "active": administrator["is_active"],
                            "oidc_subject_linked": administrator["auth_subject"]
                            is not None,
                            "telegram_identity_linked": administrator["chat_id"]
                            is not None,
                            "can_review_payments": bool(
                                administrator["is_active"]
                                and report["rbac_schema_ready"]
                                and await _review_permission(
                                    connection, administrator["role_id"]
                                )
                            ),
                        }
                        for administrator in administrators
                    ]
        if include_telegram:
            try:
                report["telegram"] = await inspect_telegram_webhook()
            except Exception as error:
                report["telegram"] = {
                    "inspection_succeeded": False,
                    "reason": (
                        str(error)
                        if isinstance(error, BillingOperationError)
                        else "telegram_inspection_failed"
                    ),
                    "error_type": type(error).__name__,
                }
        return report
    finally:
        await engine.dispose()


# ==============================================
# GUARDED, ATOMIC PRODUCTION MIGRATION
# ==============================================


async def migrate(*, database_name: str, expected_revision: str) -> OperationReport:
    """Upgrade a tracked database under a deployment lock in one transaction."""
    validate_database_confirmation(database_name=database_name)
    target_revision = expected_head()
    engine = operation_engine()
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": DEPLOYMENT_LOCK_ID},
            )
            before = await connection.run_sync(_schema_snapshot)
            installed = before["installed_revisions"]
            if installed == [target_revision]:
                if not before["billing_schema_ready"]:
                    raise BillingOperationError(
                        "installed_revision_does_not_match_billing_schema"
                    )
                return {
                    "operation": "migrate",
                    "changed": False,
                    "revision": target_revision,
                }
            if installed != [expected_revision]:
                raise BillingOperationError(
                    "installed_revision_does_not_match_expected_revision"
                )
            if (
                ScriptDirectory.from_config(alembic_configuration()).get_revision(
                    expected_revision
                )
                is None
            ):
                raise BillingOperationError(
                    "expected_revision_is_not_in_production_history"
                )

            def apply_upgrade(shared_connection: Connection) -> None:
                """Run Alembic on the already locked SQLAlchemy connection."""
                configuration = alembic_configuration()
                configuration.attributes["connection"] = shared_connection
                command.upgrade(configuration, target_revision)

            logger.info(
                "billing_production_migration_started",
                extra={"target_revision": target_revision},
            )
            await connection.run_sync(apply_upgrade)
            after = await connection.run_sync(_schema_snapshot)
            if (
                after["installed_revisions"] != [target_revision]
                or not after["billing_schema_ready"]
            ):
                raise BillingOperationError("billing_migration_verification_failed")
        logger.info(
            "billing_production_migration_completed",
            extra={"target_revision": target_revision},
        )
        return {"operation": "migrate", "changed": True, "revision": target_revision}
    finally:
        await engine.dispose()


# ==============================================
# TRUSTED OIDC CONFIGURATION GUARD
# ==============================================


def validate_oidc_configuration() -> None:
    """Require the same trusted issuer, audience, and HTTPS JWKS as the API."""
    if (
        not settings.OIDC_ISSUER
        or not settings.OIDC_AUDIENCE
        or not settings.OIDC_JWKS_URL
    ):
        raise BillingOperationError("trusted_oidc_configuration_required")
    for value in (settings.OIDC_ISSUER, settings.OIDC_JWKS_URL):
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise BillingOperationError("trusted_oidc_https_configuration_required")


# ==============================================
# BENEFICIARY INSTRUCTION READINESS
# ==============================================


def transfer_instruction_configuration() -> OperationReport:
    """Expose only readiness and missing setting names, never account values."""
    beneficiary_configured = bool(
        settings.MANUAL_TRANSFER_BENEFICIARY
        and settings.MANUAL_TRANSFER_BENEFICIARY.strip()
    )
    ccp_keys = (
        "MANUAL_TRANSFER_BENEFICIARY",
        "MANUAL_CCP_ACCOUNT",
        "MANUAL_CCP_KEY",
    )
    baridimob_keys = (
        "MANUAL_TRANSFER_BENEFICIARY",
        "MANUAL_BARIDIMOB_RIP",
    )
    missing_ccp = [
        key for key in ccp_keys if not str(getattr(settings, key) or "").strip()
    ]
    missing_baridimob = [
        key for key in baridimob_keys if not str(getattr(settings, key) or "").strip()
    ]
    return {
        "beneficiary_configured": beneficiary_configured,
        "ccp_enabled": settings.MANUAL_CCP_ENABLED,
        "ccp_instructions_configured": not missing_ccp,
        "ccp_missing_setting_names": missing_ccp,
        "baridimob_enabled": settings.MANUAL_BARIDIMOB_ENABLED,
        "baridimob_instructions_configured": not missing_baridimob,
        "baridimob_missing_setting_names": missing_baridimob,
    }


# ==============================================
# ADMINISTRATOR IDENTITY BINDING
# ==============================================


async def bind_admin(
    *,
    database_name: str,
    admin_id: int,
    subject: str,
    expected_subject: str | None = None,
) -> OperationReport:
    """Bind an explicitly supplied trusted subject without silently replacing one."""
    validate_database_confirmation(database_name=database_name)
    validate_oidc_configuration()
    if admin_id <= 0 or not subject or subject != subject.strip() or len(subject) > 255:
        raise BillingOperationError("invalid_administrator_identity")
    engine = operation_engine()
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": DEPLOYMENT_LOCK_ID},
            )
            snapshot = await connection.run_sync(_schema_snapshot)
            if (
                snapshot["installed_revisions"] != [expected_head()]
                or not snapshot["billing_schema_ready"]
            ):
                raise BillingOperationError(
                    "billing_schema_must_be_migrated_before_identity_binding"
                )
            administrator = (
                (
                    await connection.execute(
                        _base_admin_select()
                        .where(Admin.id == admin_id)
                        .with_for_update()
                    )
                )
                .mappings()
                .one_or_none()
            )
            if administrator is None or not administrator["is_active"]:
                raise BillingOperationError("active_administrator_not_found")
            if not await _review_permission(connection, administrator["role_id"]):
                raise BillingOperationError(
                    "administrator_has_no_active_payment_review_permission"
                )
            current_subject = administrator["auth_subject"]
            if current_subject == subject:
                return {
                    "operation": "bind-admin",
                    "changed": False,
                    "admin_id": admin_id,
                }
            if expected_subject is not None and current_subject != expected_subject:
                raise BillingOperationError(
                    "administrator_identity_compare_and_swap_failed"
                )
            if current_subject is not None and expected_subject is None:
                raise BillingOperationError("administrator_identity_already_linked")
            duplicate = (
                await connection.execute(
                    _base_admin_select().where(Admin.auth_subject == subject)
                )
            ).first()
            if duplicate is not None:
                raise BillingOperationError(
                    "identity_is_linked_to_another_administrator"
                )
            await connection.execute(
                update(Admin).where(Admin.id == admin_id).values(auth_subject=subject)
            )
            await connection.execute(
                AdminLog.__table__.insert().values(
                    admin_id=admin_id,
                    action="bind_identity",
                    resource="admin",
                    resource_id=admin_id,
                    details=json.dumps(
                        {
                            "source": "billing_operations",
                            "replaced_existing_identity": current_subject is not None,
                        }
                    ),
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
        logger.info(
            "billing_administrator_identity_bound", extra={"admin_id": admin_id}
        )
        return {"operation": "bind-admin", "changed": True, "admin_id": admin_id}
    finally:
        await engine.dispose()


# ==============================================
# SANITIZED TELEGRAM API REQUEST
# ==============================================


async def _telegram_request(
    *, client: httpx.AsyncClient, method: str, payload: OperationReport
) -> OperationReport:
    """Avoid credential-bearing HTTP logs and never surface raw API exceptions."""
    if not settings.BOT_TOKEN:
        raise BillingOperationError("telegram_bot_token_required")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    response = await client.post(
        f"https://api.telegram.org/bot{settings.BOT_TOKEN}/{method}", json=payload
    )
    try:
        result = response.json()
    except ValueError as error:
        raise BillingOperationError("telegram_api_invalid_response") from error
    if (
        response.status_code != 200
        or not isinstance(result, dict)
        or result.get("ok") is not True
    ):
        raise BillingOperationError("telegram_api_operation_failed")
    return result


# ==============================================
# READ-ONLY TELEGRAM WEBHOOK INSPECTION
# ==============================================


async def inspect_telegram_webhook() -> OperationReport:
    """Inspect registration without sending messages or changing Telegram state."""
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        response = await _telegram_request(
            client=client, method="getWebhookInfo", payload={}
        )
    information = response.get("result")
    if not isinstance(information, dict):
        raise BillingOperationError("telegram_webhook_info_invalid")
    return {
        "registered": bool(information.get("url")),
        "matches_configured_url": information.get("url") == settings.WEBHOOK_URL,
        "pending_update_count": information.get("pending_update_count", 0),
        "delivery_error_present": bool(information.get("last_error_message")),
    }


# ==============================================
# VERIFY DEPLOYED SECRET BEFORE WEBHOOK REGISTRATION
# ==============================================


async def configure_webhook(*, url: str) -> OperationReport:
    """Register only after the deployed endpoint proves it enforces our secret.

    The empty update has no chat or user and cannot dispatch a Telegram message.
    Pending updates remain intact. The secret must already exist in the deployed
    application environment; this operation never creates or persists credentials.
    """
    parsed = urlsplit(url)
    if (
        url != settings.WEBHOOK_URL
        or parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path != settings.WEBHOOK_PATH
    ):
        raise BillingOperationError("configured_https_webhook_url_required")
    secret = settings.TELEGRAM_WEBHOOK_SECRET_TOKEN
    value = secret.get_secret_value() if secret else ""
    if not 1 <= len(value) <= 256 or any(
        not character.isascii() or not (character.isalnum() or character in "_-")
        for character in value
    ):
        raise BillingOperationError("valid_telegram_webhook_secret_required")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        unauthenticated = await client.post(url, json={})
        if unauthenticated.status_code != 403:
            raise BillingOperationError(
                "deployed_webhook_does_not_reject_unauthenticated_updates"
            )
        authenticated = await client.post(
            url, json={}, headers={"X-Telegram-Bot-Api-Secret-Token": value}
        )
        if authenticated.status_code != 200 or authenticated.json() != {"ok": False}:
            raise BillingOperationError("deployed_webhook_secret_does_not_match")
        await _telegram_request(
            client=client,
            method="setWebhook",
            payload={"url": url, "secret_token": value, "drop_pending_updates": False},
        )
    inspection = await inspect_telegram_webhook()
    if not inspection["matches_configured_url"]:
        raise BillingOperationError("telegram_webhook_registration_verification_failed")
    logger.info("billing_telegram_webhook_configured")
    return {"operation": "configure-webhook", "configured": True, **inspection}


# ==============================================
# READ-ONLY CONSTRAINT AND DRIVER DIAGNOSTICS
# ==============================================


async def constraint_diagnostics() -> OperationReport:
    """Inspect constraint metadata and driver decoding without reading receipts."""
    engine = operation_engine()
    try:
        async with engine.connect() as connection:
            async with connection.begin():
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                version = (
                    await connection.execute(
                        text("SELECT current_setting('server_version')")
                    )
                ).scalar_one()
                rows = (
                    (
                        await connection.execute(
                            text(
                                "SELECT t.relname AS table_name, c.conname AS constraint_name, "
                                "c.contype AS raw_constraint_type, "
                                "c.contype::text AS constraint_type, "
                                "c.convalidated, c.condeferrable, c.condeferred "
                                "FROM pg_catalog.pg_constraint c "
                                "JOIN pg_catalog.pg_class t ON t.oid = c.conrelid "
                                "JOIN pg_catalog.pg_namespace n ON n.oid = t.relnamespace "
                                "WHERE n.nspname = 'public' "
                                "AND t.relname IN (:receipt_table, :audit_table) "
                                "ORDER BY t.relname, c.conname"
                            ),
                            {
                                "receipt_table": "manual_payment_receipts",
                                "audit_table": "manual_payment_audit",
                            },
                        )
                    )
                    .mappings()
                    .all()
                )
                return {
                    "operation": "constraint-diagnostics",
                    "database_name": make_url(settings.DATABASE_URL).database,
                    "server_version": version,
                    "constraints": [
                        {
                            "table_name": row["table_name"],
                            "constraint_name": row["constraint_name"],
                            "constraint_type": row["constraint_type"],
                            "raw_type_python_class": type(
                                row["raw_constraint_type"]
                            ).__name__,
                            "raw_type_representation": repr(row["raw_constraint_type"]),
                            "validated": row["convalidated"],
                            "deferrable": row["condeferrable"],
                            "initially_deferred": row["condeferred"],
                        }
                        for row in rows
                    ],
                }
    finally:
        await engine.dispose()


# ==============================================
# COMMAND-LINE ARGUMENTS
# ==============================================


def argument_parser() -> argparse.ArgumentParser:
    """Expose independent inspection, migration, binding, and webhook commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="operation", required=True)
    inspect_parser = subcommands.add_parser(
        "preflight", help="Read-only database readiness report"
    )
    inspect_parser.add_argument(
        "--telegram", action="store_true", help="Also read Telegram getWebhookInfo"
    )
    inspect_parser.add_argument(
        "--output",
        metavar="FILENAME.json",
        help="Save one JSON report under artifacts/billing-reports",
    )
    diagnostics_parser = subcommands.add_parser(
        "constraint-diagnostics",
        help="Read only PostgreSQL constraint types, validation flags, and driver decoding",
    )
    diagnostics_parser.add_argument(
        "--output",
        metavar="FILENAME.json",
        help="Save one JSON report under artifacts/billing-reports",
    )
    migration_parser = subcommands.add_parser(
        "migrate", help="Guarded atomic upgrade to production head"
    )
    migration_parser.add_argument("--confirm-database", required=True)
    migration_parser.add_argument("--expected-revision", required=True)
    binding_parser = subcommands.add_parser(
        "bind-admin", help="Bind an existing payment reviewer to trusted OIDC sub"
    )
    binding_parser.add_argument("--confirm-database", required=True)
    binding_parser.add_argument("--admin-id", type=int, required=True)
    binding_parser.add_argument("--subject", required=True)
    binding_parser.add_argument(
        "--expected-subject",
        help="Explicit compare-and-swap guard for replacing a binding",
    )
    webhook_parser = subcommands.add_parser(
        "configure-webhook", help="Verify deployed authentication before registration"
    )
    webhook_parser.add_argument("--url", required=True)
    return parser


# ==============================================
# COMMAND DISPATCH
# ==============================================


async def run_operation(*, arguments: argparse.Namespace) -> OperationReport:
    """Run the selected operation without printing its sensitive arguments."""
    if arguments.operation == "preflight":
        return await preflight(include_telegram=arguments.telegram)
    if arguments.operation == "constraint-diagnostics":
        return await constraint_diagnostics()
    if arguments.operation == "migrate":
        return await migrate(
            database_name=arguments.confirm_database,
            expected_revision=arguments.expected_revision,
        )
    if arguments.operation == "bind-admin":
        return await bind_admin(
            database_name=arguments.confirm_database,
            admin_id=arguments.admin_id,
            subject=arguments.subject,
            expected_subject=arguments.expected_subject,
        )
    if arguments.operation == "configure-webhook":
        return await configure_webhook(url=arguments.url)
    raise BillingOperationError("unsupported_billing_operation")


# ==============================================
# ENTRY POINT
# ==============================================


def main() -> int:
    """Print sanitized JSON and optionally save a separate diagnostic report."""
    parser = argument_parser()
    arguments = parser.parse_args()
    output_path: Path | None = None
    if getattr(arguments, "output", None) is not None:
        try:
            output_path = report_output_path(filename=arguments.output)
        except (BillingOperationError, OSError, RuntimeError) as error:
            reason = (
                str(error)
                if isinstance(error, BillingOperationError)
                else "unsafe_billing_report_directory"
            )
            parser.error(reason)
    exit_code = 0
    try:
        report = asyncio.run(run_operation(arguments=arguments))
    except Exception as error:
        message = (
            str(error)
            if isinstance(error, BillingOperationError)
            else "billing_operation_failed"
        )
        logger.error(
            "billing_operation_failed",
            extra={
                "operation": arguments.operation,
                "error_type": type(error).__name__,
            },
        )
        result: OperationReport = {
            "ok": False,
            "operation": arguments.operation,
            "reason": message,
            "error_type": type(error).__name__,
        }
        exit_code = 1
    else:
        result = {"ok": True, **report}
    if output_path is not None:
        try:
            write_report(output_path=output_path, report=result)
        except Exception as error:
            logger.error(
                "billing_report_write_failed",
                extra={
                    "operation": arguments.operation,
                    "error_type": type(error).__name__,
                },
            )
            result = {
                "ok": False,
                "operation": arguments.operation,
                "reason": "billing_report_write_failed",
                "error_type": type(error).__name__,
            }
            exit_code = 1
    print(json.dumps(result, indent=2 if exit_code == 0 else None))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
