# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT SYNTHETIC STAGING CONFIGURATION
# Keep real target identity separate from secrets and refuse production fallback.
# ==============================================

"""No .env discovery, inferred country, administrator grants or shared credentials."""

from __future__ import annotations

# isort: split
# ==============================================
# CONFIGURATION VALIDATION
# Every deployment-specific value is required rather than silently guessed.
# ==============================================

import os
from dataclasses import (
    dataclass,
    field,
)
from ipaddress import (
    IPv4Network,
    IPv6Network,
    ip_network,
)
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.fernet import Fernet

from app.staging.target import StagingTarget

# ==============================================
# STAGING HOST INPUTS
# The application role cannot be substituted with the migration owner.
# ==============================================


@dataclass(frozen=True, kw_only=True)
class StagingConfig:
    """One synthetic acceptance host, a separate OIDC realm and durable local sessions."""

    target: StagingTarget
    directory: Path
    database_url: str = field(repr=False)
    client_secret: str = field(repr=False)
    session_key: str = field(repr=False)
    origin: str
    issuer: str
    client_id: str
    audience: str
    proxy_networks: tuple[IPv4Network | IPv6Network, ...]

    # ==============================================
    # FAIL-CLOSED INPUT CHECKS
    # Hostnames, role, isolated realm and filesystem path must be explicit.
    # ==============================================

    def __post_init__(self) -> None:
        """Reject local issuers, shared realms, wildcard trust and incomplete secrets."""
        for value in (self.origin, self.issuer):
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            ):
                raise ValueError("staging_https_origin_required")
        if urlsplit(self.origin).path or not self.issuer.endswith(
            "/realms/moulai-staging"
        ):
            raise ValueError("staging_origin_or_realm_invalid")
        self.target.check_url(value=self.database_url, migration=False)
        Fernet(self.session_key.encode("ascii"))
        if (
            len(self.client_secret) < 32
            or not self.client_id
            or not self.audience
            or not self.proxy_networks
            or any(network.prefixlen == 0 for network in self.proxy_networks)
        ):
            raise ValueError("staging_explicit_secrets_and_proxy_trust_required")
        if not self.directory.is_absolute():
            raise ValueError("staging_durable_directory_required")

    # ==============================================
    # PUBLIC TRUST AND INSTANCE IDENTITY
    # Never reuse the local self-signed certificate or local private instance directory.
    # ==============================================

    @property
    def ca_file(self) -> None:
        """Verify the public OIDC endpoint with the platform certificate store."""
        return None

    # ==============================================
    # ISOLATED SESSION NAMESPACE
    # Sessions cannot cross between local review and the staging instance.
    # ==============================================

    @property
    def instance_id(self) -> str:
        """Bind sessions and fictitious document authority to the staging marker."""
        return self.target.instance_id

    # ==============================================
    # TESTER ACCESS GATE
    # A signed realm role admits the host only, without any business permission.
    # ==============================================

    @property
    def environment_role(self) -> str:
        """Require an explicitly invited synthetic tester before API access."""
        return "moulai-staging-tester"

    # ==============================================
    # PROCESS-ONLY CONFIGURATION LOADING
    # Required environment names contain no fallback to DATABASE_URL or a local .env.
    # ==============================================

    @classmethod
    def load(cls) -> StagingConfig:
        """Read only staging-named inputs; missing settings block startup."""
        if os.environ.get("MOULAI_STAGING_SYNTHETIC_ONLY") != "true":
            raise ValueError("staging_synthetic_only_acknowledgement_required")
        target = StagingTarget.load(path=Path(os.environ["MOULAI_STAGING_TARGET_FILE"]))
        return cls(
            target=target,
            directory=Path(os.environ["MOULAI_STAGING_DATA_DIR"]),
            database_url=target.check_url(
                value=os.environ["MOULAI_STAGING_DATABASE_URL"], migration=False
            ),
            client_secret=os.environ["MOULAI_STAGING_OIDC_CLIENT_SECRET"],
            session_key=os.environ["MOULAI_STAGING_SESSION_KEY"],
            origin=os.environ["MOULAI_STAGING_ORIGIN"],
            issuer=os.environ["MOULAI_STAGING_ISSUER"],
            client_id=os.environ["MOULAI_STAGING_CLIENT_ID"],
            audience=os.environ["MOULAI_STAGING_AUDIENCE"],
            proxy_networks=tuple(
                ip_network(value.strip(), strict=True)
                for value in os.environ["MOULAI_STAGING_PROXY_CIDRS"].split(",")
            ),
        )

    # ==============================================
    # LEGACY SETTINGS INSTALLATION
    # Explicitly disable every unrelated remote transport before legacy imports.
    # ==============================================

    def process_environment(self) -> None:
        """Install only this process; never change Render or the project's .env."""
        os.environ.update(
            {
                "APP_ENV": "staging",
                "DEBUG": "false",
                "DB_ECHO": "false",
                "DATABASE_TARGET": "primary",
                "DATABASE_URL": self.database_url,
                "REDIS_URL": "",
                # Legacy validation requires a value, not an operational provider key.
                "OPENAI_API_KEY": "staging-provider-disabled",
                "OPENAI_BASE_URL": "https://provider-disabled.invalid",
                "AI_MODEL": "staging-provider-disabled",
                "GEMINI_API_KEY": "",
                "TELEGRAM_WEBHOOK_SECRET_TOKEN": "",
                "WEBHOOK_URL": "",
                # This disabled sentinel satisfies legacy validation, not a real credential.
                "BOT_TOKEN": "staging-transport-disabled",
                "SECRET_KEY": self.session_key,
                "HEALTH_ONLY_MODE": "false",
                "OIDC_ISSUER": self.issuer,
                "OIDC_AUDIENCE": self.audience,
                "OIDC_JWKS_URL": self.issuer + "/protocol/openid-connect/certs",
                "OIDC_ALLOW_LOCAL_HTTP": "false",
                "OIDC_DIAGNOSTICS_ENABLED": "false",
                "PYTHON_DOTENV_DISABLED": "1",
                "MANUAL_CCP_ENABLED": "false",
                "MANUAL_BARIDIMOB_ENABLED": "false",
            }
        )
        for name in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ):
            os.environ.pop(name, None)
