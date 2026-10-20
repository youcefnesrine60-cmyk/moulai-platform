# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Admit disposable loopback PostgreSQL tests independently of app/Neon settings."""

from typing import Literal

from pydantic import (
    SecretStr,
    field_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from sqlalchemy import text
from sqlalchemy.engine import (
    Connection,
    make_url,
)
from sqlalchemy.exc import ArgumentError

from test_support.health_only_safety import OfflineNetworkGuard

LOCAL_DATABASE = "moulai_pytest"
LOCAL_ROLE = "moulai_pytest"
LOCAL_PORT = 55432
LOCAL_REVISION = "dce91870b4a2"

# ==============================================
# EXACT LOCAL DESTINATION ALLOWLIST
# ==============================================


def validate_local_test_url(*, value: str) -> str:
    """Reject DNS hosts, Neon, other databases/users/ports and routing overrides."""
    try:
        url = make_url(value)
        admitted = (
            url.drivername == "postgresql+asyncpg"
            and url.host == "127.0.0.1"
            and url.port == LOCAL_PORT
            and url.database == LOCAL_DATABASE
            and url.username == LOCAL_ROLE
            and isinstance(url.password, str)
            and len(url.password) >= 20
            and not url.query
        )
    except (ArgumentError, TypeError, ValueError):
        admitted = False
    if not admitted:
        raise ValueError("local_postgres_destination_not_allowlisted")
    return value


# ==============================================
# INDEPENDENT PROCESS-ONLY SETTINGS
# ==============================================


class LocalPostgresSettings(BaseSettings):
    """Require fresh local credentials and an instance marker; never read .env."""

    model_config = SettingsConfigDict(
        env_prefix="LOCAL_POSTGRES_TEST_",
        env_file=None,
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
    )
    URL: SecretStr
    INSTANCE_ID: str
    SERVER_PORT: Literal[5432, 55432] = LOCAL_PORT
    PROFILE: Literal["legacy"] = "legacy"

    # ==============================================
    # PARSE ONLY THE TWO APPROVED SERVER PORT ENVIRONMENT VALUES
    # ==============================================

    @field_validator("SERVER_PORT", mode="before")
    @classmethod
    def parse_server_port(cls, value: object) -> object:
        """Normalize environment strings before the strict literal check."""
        if isinstance(value, str) and value in {"5432", "55432"}:
            return int(value)
        return value

    # ==============================================
    # VALIDATE THE URL BEFORE CREATING AN ENGINE
    # ==============================================

    @field_validator("URL")
    @classmethod
    def validate_url(cls, value: SecretStr) -> SecretStr:
        """Keep credentials out of representations and validation errors."""
        validate_local_test_url(value=value.get_secret_value())
        return value

    # ==============================================
    # VALIDATE THE INDEPENDENT SERVER MARKER
    # ==============================================

    @field_validator("INSTANCE_ID")
    @classmethod
    def validate_instance_id(cls, value: str) -> str:
        """Require the launcher's generated 128-bit hexadecimal instance ID."""
        if len(value) != 32 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("local_postgres_instance_id_invalid")
        return value


# ==============================================
# SELECT-ONLY LIVE IDENTITY ATTESTATION
# ==============================================


def read_local_test_identity(
    connection: Connection, *, configuration: LocalPostgresSettings
) -> None:
    """Reject wrong server, role, owner, marker or elevated test credentials."""
    validate_local_test_url(
        value=connection.engine.url.render_as_string(hide_password=False)
    )
    row = (
        connection.execute(
            text(
                "SELECT current_database() AS database, current_user AS role, "
                "inet_server_port() AS port, r.rolsuper, r.rolcreatedb, r.rolcreaterole, "
                "pg_get_userbyid(d.datdba) AS owner, "
                "shobj_description(d.oid,'pg_database') AS marker "
                "FROM pg_database d JOIN pg_roles r ON r.rolname=current_user "
                "WHERE d.datname=current_database()"
            )
        )
        .mappings()
        .one()
    )
    if (
        row["database"] != LOCAL_DATABASE
        or row["role"] != LOCAL_ROLE
        or row["owner"] != LOCAL_ROLE
        or row["port"] != configuration.SERVER_PORT
        or row["rolsuper"]
        or row["rolcreatedb"]
        or row["rolcreaterole"]
        or row["marker"] != f"moulai-local-pytest:{configuration.INSTANCE_ID}"
    ):
        raise RuntimeError("local_postgres_live_identity_mismatch")


# ==============================================
# BLOCK ALL NETWORK DESTINATIONS EXCEPT THE LOCAL TEST SERVER
# ==============================================


class LocalPostgresNetworkGuard(OfflineNetworkGuard):
    """Extend the existing audit policy with one numeric loopback destination."""

    # ==============================================
    # ADMIT ONLY THE EXACT LOOPBACK ADDRESS AND PORT
    # ==============================================

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        """Keep DNS, other local services and remote endpoints denied."""
        if event == "socket.connect" and len(arguments) > 1:
            address = arguments[1]
            if isinstance(address, tuple) and address[:2] == ("127.0.0.1", LOCAL_PORT):
                return
        if event == "socket.getaddrinfo" and arguments[:2] == ("127.0.0.1", LOCAL_PORT):
            return
        super().__call__(event, arguments)
