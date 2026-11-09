# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ISOLATED POSTGRESQL TEST SAFETY
# Validate exact local database identities, schema profiles and permitted test
# connections.
# ==============================================

"""Admit disposable loopback PostgreSQL tests independently of app/Neon settings."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from typing import Literal

from pydantic import (
    SecretStr,
    ValidationInfo,
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

from scripts.run_offline_api_tests import OfflineNetworkGuard

# ==============================================
# CONFIGURATION AND CONSTANTS
# Group the existing configuration values without changing their defaults.
# ==============================================

LOCAL_DATABASE = "moulai_pytest"
LOCAL_ROLE = "moulai_pytest"
LOCAL_PORT = 55432
LOCAL_REVISION = "dce91870b4a2"
LOCAL_E1_REVISION = "e1b92b200001"
LOCAL_S1_REVISION = "s1b20261028"
LOCAL_MAIN_REVISION = "s1a20261028"
LOCAL_DINING_REVISION = "d1d20261105"


# ==============================================
# EXACT LOCAL DESTINATION ALLOWLIST
# Reject DNS hosts, Neon, other databases/users/ports and routing overrides.
# ==============================================


def validate_local_test_url(*, value: str, client_port: int = LOCAL_PORT) -> str:
    """Reject DNS hosts, Neon, other databases/users/ports and routing overrides."""
    try:
        url = make_url(value)
        admitted = (
            url.drivername == "postgresql+asyncpg"
            and url.host == "127.0.0.1"
            and client_port in {55432, 55435}
            and url.port == client_port
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
# Require fresh local credentials and an instance marker; never read .env.
# ==============================================


class LocalPostgresSettings(BaseSettings):
    """Require fresh local credentials and an instance marker; never read .env."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    model_config = SettingsConfigDict(
        env_prefix="LOCAL_POSTGRES_TEST_",
        env_file=None,
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
    )
    CLIENT_PORT: Literal[55432, 55435] = LOCAL_PORT
    URL: SecretStr
    INSTANCE_ID: str
    SERVER_PORT: Literal[5432, 55432, 55435] = LOCAL_PORT
    PROFILE: Literal["legacy", "k10", "subscription", "main", "dining"] = "legacy"

    # ==============================================
    # PARSE ONLY THE TWO APPROVED SERVER PORT ENVIRONMENT VALUES
    # Normalize environment strings before the strict literal check.
    # ==============================================

    @field_validator("SERVER_PORT", "CLIENT_PORT", mode="before")
    @classmethod
    def parse_server_port(cls, value: object) -> object:
        """Normalize environment strings before the strict literal check."""
        if isinstance(value, str) and value in {"5432", "55432", "55435"}:
            return int(value)
        return value

    # ==============================================
    # VALIDATE THE URL BEFORE CREATING AN ENGINE
    # Keep credentials out of representations and validation errors.
    # ==============================================

    @field_validator("URL")
    @classmethod
    def validate_url(cls, value: SecretStr, info: ValidationInfo) -> SecretStr:
        """Keep credentials out of representations and validation errors."""
        validate_local_test_url(
            value=value.get_secret_value(),
            client_port=info.data.get("CLIENT_PORT", LOCAL_PORT),
        )
        return value

    # ==============================================
    # VALIDATE THE INDEPENDENT SERVER MARKER
    # Require the launcher's generated 128-bit hexadecimal instance ID.
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
# Reject wrong server, role, owner, marker or elevated test credentials.
# ==============================================


def read_local_test_identity(
    connection: Connection, *, configuration: LocalPostgresSettings
) -> None:
    """Reject wrong server, role, owner, marker or elevated test credentials."""
    validate_local_test_url(
        value=connection.engine.url.render_as_string(hide_password=False),
        client_port=configuration.CLIENT_PORT,
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
# Extend the existing audit policy with one numeric loopback destination.
# ==============================================


class LocalPostgresNetworkGuard(OfflineNetworkGuard):
    """Extend the existing audit policy with one numeric loopback destination."""

    # ==============================================
    # ONE EXPLICIT CLIENT PORT
    # An alternate test port preserves another local review without admitting a second connection destination.
    # ==============================================

    def __init__(self, *, client_port: int = LOCAL_PORT) -> None:
        """Retain exactly one admitted disposable-test port; default behavior remains unchanged."""
        super().__init__()
        if client_port not in {55432, 55435}:
            raise ValueError("local_postgres_test_port_not_admitted")
        self.client_port = client_port

    # ==============================================
    # ADMIT ONLY THE EXACT LOOPBACK ADDRESS AND PORT
    # Keep DNS, other local services and remote endpoints denied.
    # ==============================================

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        """Keep DNS, other local services and remote endpoints denied."""
        if event == "socket.connect" and len(arguments) > 1:
            address = arguments[1]
            if isinstance(address, tuple) and address[:2] == (
                "127.0.0.1",
                self.client_port,
            ):
                return
        if event == "socket.getaddrinfo" and arguments[:2] == (
            "127.0.0.1",
            self.client_port,
        ):
            return
        super().__call__(event, arguments)
