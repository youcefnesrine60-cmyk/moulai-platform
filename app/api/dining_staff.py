# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OPT-IN PROFESSIONAL MANAGEMENT ROUTES
# Reuse the hosting router's signed principal and explicit request session dependencies.
# ==============================================

"""No login endpoint, role override, implicit registration in main or remote connection."""

# isort: split
# ==============================================
# EXISTING AUTHORITY AND EXPLICIT HOST DEPENDENCIES
# No account credentials or application connection settings are read by this router.
# ==============================================

from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
)
from contextlib import contextmanager

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import (
    TenantAccessDenied,
    TenantConflict,
)
from app.schemas.dining import JsonObject
from app.schemas.dining_staff import StaffCommand
from app.services.business.dining.staff import DiningStaffService
from app.services.business.dining.values import DiningError

# ==============================================
# SAFE BUSINESS FAILURE TRANSLATION
# Return bounded rejection codes and never SQL, identity keys or provider tokens.
# ==============================================


@contextmanager
def staff_http_errors() -> Iterator[None]:
    """Translate only known domain failures; transaction rollback stays in the service."""
    try:
        yield
    except TenantAccessDenied as error:
        raise HTTPException(
            status_code=403, detail="Professional access denied"
        ) from error
    except DiningError as error:
        raise HTTPException(status_code=409, detail={"code": error.code}) from error
    except (TenantConflict, IntegrityError) as error:
        raise HTTPException(
            status_code=409, detail="Professional operation conflict"
        ) from error


# ==============================================
# EXPLICIT ROUTER FACTORY
# Callers must supply the existing authentication and session lifecycle.
# ==============================================


def dining_staff_router(
    *,
    session_dependency: Callable[[], AsyncIterator[AsyncSession]],
    principal_dependency: Callable[..., Awaitable[OIDCPrincipal]]
) -> APIRouter:
    """Expose owner mutations and personal acceptance without mounting anything globally."""
    router = APIRouter(tags=["dining-staff"])
    session_dep = Depends(session_dependency)
    principal_dep = Depends(principal_dependency)
    prefix = "/organizations/{organization_id}/restaurants/{restaurant_id}/branches/{branch_id}/dining/staff"

    # ==============================================
    # OWNER PROFESSIONAL WRITE
    # Every request revalidates the actor, target member, company and physical branch.
    # ==============================================

    @router.post(prefix)
    async def manage_staff(
        *,
        organization_id: int,
        restaurant_id: int,
        branch_id: int,
        data: StaffCommand,
        session: AsyncSession = session_dep,
        principal: OIDCPrincipal = principal_dep
    ) -> JsonObject:
        """Execute one revision-controlled or descriptive professional command."""
        with staff_http_errors():
            return await DiningStaffService(session=session).execute(
                principal=principal,
                organization_id=organization_id,
                restaurant_id=restaurant_id,
                branch_id=branch_id,
                command=data,
            )

    # ==============================================
    # PERSONAL METADATA DISCOVERY
    # An inactive professional relation can be acknowledged without business access.
    # ==============================================

    @router.get("/dining/employment/invitations")
    async def own_invitations(
        *, session: AsyncSession = session_dep, principal: OIDCPrincipal = principal_dep
    ) -> list[JsonObject]:
        """Return only the signed identity's invitations, never an employee directory."""
        with staff_http_errors():
            return await DiningStaffService(session=session).invitations(
                principal=principal
            )

    # ==============================================
    # PERSONAL ACCEPTANCE
    # An owner's request or knowledge of another account key cannot supply this consent.
    # ==============================================

    @router.post("/dining/employment/{organization_id}/{membership_id}/accept")
    async def accept_invitation(
        *,
        organization_id: int,
        membership_id: int,
        session: AsyncSession = session_dep,
        principal: OIDCPrincipal = principal_dep
    ) -> JsonObject:
        """Record self-acceptance; no owner activation or capability grant is implied."""
        with staff_http_errors():
            return await DiningStaffService(session=session).accept(
                principal=principal,
                organization_id=organization_id,
                membership_id=membership_id,
            )

    return router
