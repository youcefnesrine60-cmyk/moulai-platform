# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PINNED OPERATIONAL INSTANCE CONFIGURATION
# Admit only the owned development cluster and TLS Keycloak on loopback.
# ==============================================

"""Explicit local configuration; this module never reads the project's .env."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Validate identifiers and paths before any database or provider connection.
# ==============================================

import json
import os
from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
INSTANCE_ROOT = ROOT / "artifacts" / "operational-local"


# ==============================================
# INTEGRATIONCONFIG
# Bind all IO to one explicitly initialized isolated local instance.
# ==============================================


@dataclass(frozen=True, kw_only=True)
class IntegrationConfig:
    """Bind all IO to one explicitly initialized isolated local instance."""

    directory: Path
    instance_id: str
    database_url: str = field(repr=False)
    client_secret: str = field(repr=False)
    session_key: str = field(repr=False)
    admin_password: str = field(repr=False)
    origin: str = "https://127.0.0.1:5180"
    issuer: str = "https://127.0.0.1:8444/realms/moulai-local"
    client_id: str = "moulai-browser"
    audience: str = "moulai-api"

    # ==============================================
    # CONSTRUCTOR NETWORK INVARIANTS
    # Direct construction cannot silently turn this local host into a remote database or provider client.
    # ==============================================

    def __post_init__(self) -> None:
        """Reject nonlocal targets before settings are installed or an engine is created."""
        url = make_url(self.database_url)
        if not (
            url.drivername == "postgresql+asyncpg"
            and url.host == "127.0.0.1"
            and url.port == 55433
            and url.database == "moulai_integrated"
            and url.username == "moulai_integrated"
            and not url.query
            and url.password
            and len(url.password) >= 32
            and self.origin == "https://127.0.0.1:5180"
            and self.issuer == "https://127.0.0.1:8444/realms/moulai-local"
            and self.client_id == "moulai-browser"
            and self.audience == "moulai-api"
        ):
            raise ValueError("integration_nonlocal_configuration_refused")

    # ==============================================
    # CA FILE
    # Return only the owned trust root, without changing the OS trust store.
    # ==============================================

    @property
    def ca_file(self) -> Path:
        """Return only the owned trust root, without changing the OS trust store."""
        return self.directory / "private" / "ca.pem"

    # ==============================================
    # LOCAL ENVIRONMENT AUTHORITY
    # Existing local identities retain their established admission behavior.
    # ==============================================

    @property
    def environment_role(self) -> None:
        """Require no additional staging realm role for the existing local review."""
        return None

    # ==============================================
    # LOAD
    # Refuse remote URLs, copied markers or unexpected paths before IO.
    # ==============================================

    @classmethod
    def load(cls, *, directory: Path) -> IntegrationConfig:
        """Refuse remote URLs, copied markers or unexpected paths before IO."""
        directory = directory.resolve()
        if not directory.is_relative_to(INSTANCE_ROOT.resolve()):
            raise ValueError("integration_directory_not_owned")
        data = json.loads(
            (directory / "private" / "instance.json").read_text(encoding="utf-8")
        )
        identifier = data["instance_id"]
        if len(identifier) != 32 or any(
            c not in "0123456789abcdef" for c in identifier
        ):
            raise ValueError("integration_marker_invalid")
        if (directory / "instance-marker").read_text(encoding="ascii") != identifier:
            raise ValueError("integration_marker_mismatch")
        url = make_url(data["database_url"])
        if not (
            url.drivername == "postgresql+asyncpg"
            and url.host == "127.0.0.1"
            and url.port == 55433
            and url.database == "moulai_integrated"
            and url.username == "moulai_integrated"
            and not url.query
            and url.password
            and len(url.password) >= 32
        ):
            raise ValueError("integration_database_not_allowlisted")
        result = cls(
            directory=directory,
            instance_id=identifier,
            database_url=data["database_url"],
            client_secret=data["client_secret"],
            session_key=data["session_key"],
            admin_password=data["admin_password"],
        )
        for value in (result.origin, result.issuer):
            parts = urlsplit(value)
            if (
                parts.hostname != "127.0.0.1"
                or parts.scheme != "https"
                or parts.username
                or parts.password
            ):
                raise ValueError("integration_origin_invalid")
        return result

    # ==============================================
    # PROCESS ENVIRONMENT
    # Override only this process before legacy settings imports; never edit .env.
    # ==============================================

    def process_environment(self) -> None:
        """Override only this process before legacy settings imports; never edit .env."""
        os.environ.update(
            {
                "DATABASE_URL": self.database_url,
                "DATABASE_TARGET": "primary",
                "APP_ENV": "development",
                "DEBUG": "false",
                "DB_ECHO": "false",
                "HEALTH_ONLY_MODE": "false",
                "OIDC_ISSUER": self.issuer,
                "OIDC_AUDIENCE": self.audience,
                "OIDC_JWKS_URL": self.issuer + "/protocol/openid-connect/certs",
                "OIDC_DIAGNOSTICS_ENABLED": "false",
                "OIDC_ALLOW_LOCAL_HTTP": "false",
                "MANUAL_CCP_ENABLED": "true",
                "MANUAL_BARIDIMOB_ENABLED": "true",
                "SSL_CERT_FILE": str(self.ca_file),
                "NO_PROXY": "127.0.0.1,localhost",
            }
        )
        for key in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ):
            os.environ.pop(key, None)
