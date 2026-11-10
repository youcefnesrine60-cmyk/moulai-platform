# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SHARED AUTHENTICATED BROWSER HOST CONTRACT
# Share business adapters without broadening the local configuration allowlist.
# ==============================================

"""Local review and staging supply different attestation and network policies."""

# isort: split
# ==============================================
# STRUCTURAL CONFIGURATION
# No provider password, token or identity is projected into frontend configuration.
# ==============================================

from pathlib import Path
from typing import Protocol

# ==============================================
# BROWSER HOST INPUTS
# Concrete validated configurations own their destination and trust decisions.
# ==============================================


class BrowserHostConfig(Protocol):
    """Inputs required by the existing server-side session and OIDC adapters."""

    directory: Path
    instance_id: str
    database_url: str
    client_secret: str
    session_key: str
    origin: str
    issuer: str
    client_id: str
    audience: str

    # ==============================================
    # EXPLICIT ENVIRONMENT ADMISSION
    # Admission never substitutes for restaurant-scoped business authorization.
    # ==============================================

    @property
    def environment_role(self) -> str | None:
        """Optional host access gate; it never grants business or restaurant permissions."""
        ...

    # ==============================================
    # CERTIFICATE TRUST SOURCE
    # Local private CA and public staging trust remain separate decisions.
    # ==============================================

    @property
    def ca_file(self) -> Path | None:
        """Use a private local CA only for local review; staging uses public trust."""
        ...
