# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Opt-in health observation, isolated from business authorization policies."""

from dataclasses import dataclass
from typing import (
    Protocol,
    cast,
)

from sqlalchemy import event
from sqlalchemy.engine import (
    Connection,
    make_url,
)
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.responses import JSONResponse
from starlette.types import (
    ASGIApp,
    Receive,
    Scope,
    Send,
)

from app.core.test_database import (
    read_test_database_identity,
    validate_test_branch_configuration,
    validated_test_database_url,
)

# ==============================================
# CONFIGURATION CONTRACT AND SAFE FAILURE
# ==============================================


class HealthOnlyConfiguration(Protocol):
    """Describe central Settings without importing its eager package initializer."""

    HEALTH_ONLY_MODE: bool
    APP_ENV: str
    DATABASE_TARGET: str
    DATABASE_URL: str
    TEST_DATABASE_URL: str
    TEST_DATABASE_PROJECT_ID: str | None
    TEST_DATABASE_BRANCH_ID: str | None
    TEST_DATABASE_ENDPOINT_ID: str | None
    PROTECTED_DATABASE_BRANCH_ID: str | None
    PROTECTED_DATABASE_ENDPOINT_ID: str | None
    REDIS_URL: str
    DEBUG: bool
    DB_ECHO: bool
    OIDC_DIAGNOSTICS_ENABLED: bool
    OIDC_ALLOW_LOCAL_HTTP: bool


class HealthOnlyConfigurationError(RuntimeError):
    """Carry a fixed failure code without embedding Settings or credentials."""


# ==============================================
# FAIL-CLOSED HEALTH PROFILE VALIDATION
# ==============================================


def validate_health_only_configuration(
    *, configuration: HealthOnlyConfiguration
) -> None:
    """Require an isolated, quiet development profile before engine creation.

    DATABASE_URL remains an unused protected reference. Its endpoint must agree
    with the declared production exclusion; swapping the two target labels
    cannot admit that endpoint through TEST_DATABASE_URL.
    """
    if not configuration.HEALTH_ONLY_MODE:
        return
    if (
        configuration.APP_ENV != "development"
        or configuration.DATABASE_TARGET != "development"
    ):
        raise HealthOnlyConfigurationError("health_only_development_target_required")
    if configuration.REDIS_URL != "":
        raise HealthOnlyConfigurationError("health_only_empty_redis_url_required")
    if any(
        (
            configuration.DEBUG,
            configuration.DB_ECHO,
            configuration.OIDC_DIAGNOSTICS_ENABLED,
            configuration.OIDC_ALLOW_LOCAL_HTTP,
        )
    ):
        raise HealthOnlyConfigurationError("health_only_quiet_profile_required")
    validate_test_branch_configuration(
        branch_id=configuration.TEST_DATABASE_BRANCH_ID,
        project_id=configuration.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=configuration.PROTECTED_DATABASE_BRANCH_ID,
    )
    validated_test_database_url(
        test_database_url=configuration.TEST_DATABASE_URL,
        test_endpoint_id=configuration.TEST_DATABASE_ENDPOINT_ID,
        protected_endpoint_id=configuration.PROTECTED_DATABASE_ENDPOINT_ID,
    )
    try:
        primary = make_url(configuration.DATABASE_URL)
        hostname = (primary.host or "").lower()
        primary_endpoint = hostname.split(".", 1)[0].removesuffix("-pooler")
        protected_reference_valid = (
            primary.drivername == "postgresql+asyncpg"
            and primary.database == "neondb"
            and hostname.endswith(".neon.tech")
            and primary_endpoint == configuration.PROTECTED_DATABASE_ENDPOINT_ID
        )
        test_url = make_url(configuration.TEST_DATABASE_URL)
    except (ArgumentError, TypeError, ValueError):
        raise HealthOnlyConfigurationError(
            "health_only_protected_reference_invalid"
        ) from None
    if not protected_reference_valid:
        raise HealthOnlyConfigurationError("health_only_protected_reference_invalid")
    if test_url.query or test_url.port not in {None, 5432}:
        raise HealthOnlyConfigurationError("health_only_connection_options_forbidden")


# ==============================================
# IMMUTABLE DATABASE IDENTITY AND TRANSACTION GUARD
# ==============================================


@dataclass(frozen=True, slots=True)
class HealthOnlyDatabasePolicy:
    """Capture validated identity independently of mutable runtime Settings."""

    endpoint_id: str
    branch_id: str
    project_id: str
    protected_branch_id: str

    # ==============================================
    # ENFORCE EACH APPLICATION TRANSACTION
    # ==============================================

    def begin(self, connection: Connection) -> None:
        """Set READ ONLY and attest the actual server before application SQL.

        The identity SELECT also takes a transaction snapshot. A later attempt
        to change this transaction to READ WRITE must fail on PostgreSQL.
        """
        if connection.dialect.name != "postgresql" or getattr(
            connection.connection.dbapi_connection, "autocommit", True
        ):
            raise HealthOnlyConfigurationError("health_only_transaction_required")
        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
        if (
            connection.exec_driver_sql("SHOW transaction_read_only").scalar_one()
            != "on"
        ):
            raise HealthOnlyConfigurationError("health_only_read_only_required")
        read_test_database_identity(
            connection,
            endpoint_id=self.endpoint_id,
            branch_id=self.branch_id,
            project_id=self.project_id,
            protected_branch_id=self.protected_branch_id,
        )


# ==============================================
# CAPTURE THE VALIDATED TRANSACTION POLICY
# ==============================================


def health_only_database_policy(
    *, configuration: HealthOnlyConfiguration
) -> HealthOnlyDatabasePolicy | None:
    """Build the transaction contract only after complete profile validation."""
    validate_health_only_configuration(configuration=configuration)
    if not configuration.HEALTH_ONLY_MODE:
        return None
    return HealthOnlyDatabasePolicy(
        endpoint_id=cast(str, configuration.TEST_DATABASE_ENDPOINT_ID),
        branch_id=cast(str, configuration.TEST_DATABASE_BRANCH_ID),
        project_id=cast(str, configuration.TEST_DATABASE_PROJECT_ID),
        protected_branch_id=cast(str, configuration.PROTECTED_DATABASE_BRANCH_ID),
    )


# ==============================================
# INSTALL THE GUARD BEFORE THE FIRST ENGINE CONNECTION
# ==============================================


def install_health_only_database_guard(
    *, engine: AsyncEngine, policy: HealthOnlyDatabasePolicy
) -> None:
    """Protect the ORM engine, including sessions, reconnects and direct Core SQL."""
    if not event.contains(engine.sync_engine, "begin", policy.begin):
        event.listen(engine.sync_engine, "begin", policy.begin)


# ==============================================
# OUTERMOST HTTP ADMISSION BEFORE BUSINESS MIDDLEWARE
# ==============================================


class HealthOnlyMiddleware:
    """Reject business traffic without reading its body or invoking inner apps."""

    # ==============================================
    # CAPTURE THE PROCESS MODE
    # ==============================================

    def __init__(self, app: ASGIApp, *, enabled: bool) -> None:
        """Freeze admission at application construction, rather than per request."""
        self.app = app
        self.enabled = enabled

    # ==============================================
    # ADMIT EXACT GET HEALTH PATHS ONLY
    # ==============================================

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass lifespan through; deny all non-health HTTP and WebSocket traffic."""
        if not self.enabled or scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            if "websocket.http.response" in scope.get("extensions", {}):
                await send(
                    {
                        "type": "websocket.http.response.start",
                        "status": 503,
                        "headers": [],
                    }
                )
                await send({"type": "websocket.http.response.body", "body": b""})
            else:
                await send({"type": "websocket.close", "code": 1008})
            return
        path = scope.get("path", "")
        if (
            scope["type"] == "http"
            and scope.get("method") == "GET"
            and path in {"/", "/health"}
            and scope.get("raw_path", path.encode()) == path.encode()
        ):
            await self.app(scope, receive, send)
            return
        response = JSONResponse(
            {"detail": "Service available for health checks only"},
            status_code=503,
            headers={"Cache-Control": "no-store"},
        )
        await response(scope, receive, send)
