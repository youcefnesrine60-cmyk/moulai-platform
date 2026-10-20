# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Opt-in tenant dependencies; no router registration or OIDC activation."""

from collections.abc import (
    AsyncIterator,
    Callable,
)
from typing import (
    Annotated,
    TypeAlias,
)

from fastapi import (
    Depends,
    HTTPException,
    Path,
    Query,
)
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.core.database import get_db
from app.core.security.oidc import (
    OIDCPrincipal,
    extract_realm_roles,
)
from app.core.security.tenant_types import (
    TenantAccessDenied,
    TenantConflict,
)
from app.schemas.tenant_access import MembershipSummary
from app.services.business.tenant_access import (
    TenantAccessService,
    TenantReadUnit,
    validate_permission,
)

TenantReadDependency: TypeAlias = Callable[..., AsyncIterator[TenantReadUnit]]


# ==============================================
# CONSISTENT TENANT DENIAL TRANSLATION
# ==============================================


def _tenant_http_error(*, error: TenantAccessDenied | TenantConflict) -> HTTPException:
    """Expose generic outcomes without revealing identities or foreign resources."""
    if isinstance(error, TenantConflict):
        return HTTPException(status_code=409, detail="Tenant operation conflict")
    missing = str(error) in {
        "tenant_membership_unavailable",
        "tenant_resource_unavailable",
    }
    return HTTPException(
        status_code=404 if missing else 403,
        detail="Resource not found" if missing else "Tenant access denied",
    )


# ==============================================
# EXISTING STRICT BUSINESS JWT VERIFIER
# ==============================================


async def get_business_oidc_principal(
    *,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(auth.bearer_scheme)
    ],
) -> OIDCPrincipal:
    """Reuse HTTPS RS256/JWKS validation; diagnostic HTTP flags cannot relax it."""
    claims = await auth._verified_access_token_claims(credentials=credentials)
    try:
        roles = extract_realm_roles(claims=claims)
    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    return OIDCPrincipal(subject=claims["sub"], issuer=claims["iss"], realm_roles=roles)


# ==============================================
# AUTHENTICATED PERSONAL MEMBERSHIP DISCOVERY
# ==============================================


async def get_own_tenant_memberships(
    *,
    principal: Annotated[OIDCPrincipal, Depends(get_business_oidc_principal)],
    session: Annotated[AsyncSession, Depends(get_db)],
    after_id: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> tuple[MembershipSummary, ...]:
    """Read only this exact identity's association metadata; never select a tenant."""
    try:
        return await TenantAccessService(session=session).own_memberships(
            principal=principal, after_id=after_id, limit=limit
        )
    except (TenantAccessDenied, TenantConflict) as error:
        raise _tenant_http_error(error=error) from error


# ==============================================
# UNREGISTERED TRANSACTION-BOUND REQUEST DEPENDENCY
# ==============================================


def tenant_read_access(*, permission: str) -> TenantReadDependency:
    """Build an explicit tenant action dependency for separately reviewed routes."""
    validate_permission(permission=permission)

    # ==============================================
    # AUTHENTICATED COMPANY RESOLUTION AND BOUNDED READS
    # ==============================================
    async def dependency(
        *,
        organization_id: Annotated[int, Path(gt=0)],
        principal: Annotated[OIDCPrincipal, Depends(get_business_oidc_principal)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> AsyncIterator[TenantReadUnit]:
        """Use only local membership authority; never a realm-role tenant bypass."""
        try:
            async with TenantAccessService(session=session).authorized(
                principal=principal,
                organization_id=organization_id,
                permission=permission,
            ) as unit:
                yield unit
        except (TenantAccessDenied, TenantConflict) as error:
            raise _tenant_http_error(error=error) from error

    return dependency
