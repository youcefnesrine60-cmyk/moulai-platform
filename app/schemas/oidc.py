# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Minimal verified identity response for the protected local OIDC probes."""

from pydantic import BaseModel


class OIDCDiagnosticResponse(BaseModel):
    """Expose the caller's verified identity without raw claims or credentials."""

    authenticated: bool
    subject: str
    issuer: str
    realm_roles: list[str]
