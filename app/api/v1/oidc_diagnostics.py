# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Opt-in local OIDC probes; no database or business operation is exposed."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Response,
)

from app.api.auth import (
    get_current_oidc_principal,
    require_realm_roles,
)
from app.core.security.oidc import OIDCPrincipal
from app.schemas.oidc import OIDCDiagnosticResponse

router = APIRouter(prefix="/diagnostics/oidc", tags=["Local OIDC diagnostics"])


# ==============================================
# MINIMAL AUTHENTICATED DIAGNOSTIC RESPONSE
# ==============================================


def _identity_response(
    *, principal: OIDCPrincipal, response: Response
) -> OIDCDiagnosticResponse:
    """Prevent caching of the successful caller-specific diagnostic response."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return OIDCDiagnosticResponse(
        authenticated=True,
        subject=principal.subject,
        issuer=principal.issuer,
        realm_roles=sorted(principal.realm_roles),
    )


# ==============================================
# PROTECTED AUTHENTICATION AND ROLE PROBES
# ==============================================


@router.get("/me", response_model=OIDCDiagnosticResponse)
async def authenticated_identity(
    *,
    principal: Annotated[OIDCPrincipal, Depends(get_current_oidc_principal)],
    response: Response,
) -> OIDCDiagnosticResponse:
    """Return 200 for a valid access token, independently of tenant mapping."""
    return _identity_response(principal=principal, response=response)


@router.get("/owner", response_model=OIDCDiagnosticResponse)
async def owner_role_probe(
    *,
    principal: Annotated[
        OIDCPrincipal, Depends(require_realm_roles(roles=frozenset({"owner"})))
    ],
    response: Response,
) -> OIDCDiagnosticResponse:
    """Test the owner realm role without assigning or accessing any business."""
    return _identity_response(principal=principal, response=response)


@router.get("/admin", response_model=OIDCDiagnosticResponse)
async def admin_role_probe(
    *,
    principal: Annotated[
        OIDCPrincipal, Depends(require_realm_roles(roles=frozenset({"admin"})))
    ],
    response: Response,
) -> OIDCDiagnosticResponse:
    """Test only a realm role; success grants no administrative API permission."""
    return _identity_response(principal=principal, response=response)
