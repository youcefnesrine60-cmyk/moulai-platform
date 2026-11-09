# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OPT-IN PUBLIC DINING BOUNDARY
# Public references select reads; a separate secret binds a controlled customer visit.
# ==============================================

"""No public endpoint can approve occupation, preparation, payment or a staff grant."""

from __future__ import annotations

# isort: split
# ==============================================
# EXPLICIT DEPENDENCIES AND BOUNDED INPUTS
# Use the host's isolated session without importing application configuration.
# ==============================================

from collections.abc import (
    AsyncIterator,
    Callable,
)
from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
)
from pydantic import Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.dining import (
    DiningInput,
    JsonObject,
)
from app.schemas.dining_public import (
    PresenceInput,
    VisitOrderInput,
)
from app.services.business.dining.public_service import PublicDiningService
from app.services.business.dining.values import DiningError

# ==============================================
# PUBLIC READ REFERENCE BODY
# Keep opaque IDs out of ordinary URL access logs and reject arbitrary keys.
# ==============================================


class PublicReadInput(DiningInput):
    """One opaque read target with an optional explicit currency selection."""

    public_id: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


# ==============================================
# PRESENCE REQUEST BODY
# Party size remains a request for staff attention, never a physical-state update.
# ==============================================


class PublicPresenceInput(PresenceInput):
    """Add the exact public table reference without an administrative identifier."""

    public_id: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


# ==============================================
# ORDER REQUEST BODY
# The caller selects products and quantities, not prices, approvals or payment states.
# ==============================================


class PublicOrderInput(VisitOrderInput):
    """Bind a reviewed menu and idempotency key to one controlled table visit."""

    public_id: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


# ==============================================
# PUBLIC ROUTER FACTORY
# These routes stay opt-in and inherit the local host's origin and network boundary.
# ==============================================


def dining_public_router(
    *,
    session_dependency: Callable[[], AsyncIterator[AsyncSession]],
    clock: Callable[[], datetime],
) -> APIRouter:
    """Build bounded public operations with domain-safe errors and no automatic retries."""
    router = APIRouter(prefix="/dining/public", tags=["dining-public"])
    session_dep = Depends(session_dependency)

    # ==============================================
    # TRANSACTION AND ERROR DEPENDENCY
    # Missing or revoked resources never expose SQL, credentials or foreign IDs.
    # ==============================================

    async def service(
        *, session: AsyncSession = session_dep
    ) -> AsyncIterator[PublicDiningService]:
        """Supply a clean session; domain rejections leave its owned transaction rolled back."""
        try:
            yield PublicDiningService(session=session, clock=clock)
        except DiningError as error:
            raise HTTPException(status_code=409, detail={"code": error.code}) from error
        except IntegrityError as error:
            raise HTTPException(
                status_code=409, detail={"code": "dining_public_integrity_conflict"}
            ) from error

    service_dep = Depends(service, scope="function")

    # ==============================================
    # MENU READ
    # POST transports only a read reference; the service performs no application writes.
    # ==============================================

    @router.post("/menu")
    async def menu(
        *, data: PublicReadInput, unit: PublicDiningService = service_dep
    ) -> JsonObject:
        """Return current public table identification and exact published menu prices."""
        return await unit.menu(public_id=data.public_id, currency=data.currency)

    # ==============================================
    # CUSTOMER SIGNAL
    # Keep the independent tab secret in a header excluded from diagnostic logging.
    # ==============================================

    @router.post("/presence")
    async def presence(
        *,
        data: PublicPresenceInput,
        token: Annotated[str, Header(alias="X-Visit-Token")],
        unit: PublicDiningService = service_dep,
    ) -> JsonObject:
        """Persist a deduplicated request for staff observation, with no installation."""
        return await unit.signal(
            public_id=data.public_id,
            token=token,
            data=PresenceInput(party_size=data.party_size),
        )

    # ==============================================
    # PRIVATE VISIT PROJECTION
    # Possession of the public QR alone cannot enumerate any customer's orders.
    # ==============================================

    @router.post("/visit")
    async def visit(
        *,
        data: PublicReadInput,
        token: Annotated[str, Header(alias="X-Visit-Token")],
        unit: PublicDiningService = service_dep,
    ) -> JsonObject:
        """Return only the orders tied to the supplied active visit credential."""
        return await unit.visit(public_id=data.public_id, token=token)

    # ==============================================
    # BOUNDED ORDER REQUEST
    # The server rechecks active occupation, exact menu digest and duplicate submission.
    # ==============================================

    @router.post("/orders")
    async def order(
        *,
        data: PublicOrderInput,
        token: Annotated[str, Header(alias="X-Visit-Token")],
        unit: PublicDiningService = service_dep,
    ) -> JsonObject:
        """Create a pending order only; no kitchen approval or money transfer occurs."""
        return await unit.order(
            public_id=data.public_id,
            token=token,
            data=VisitOrderInput.model_validate(data.model_dump(exclude={"public_id"})),
        )

    # ==============================================
    # CURRENT DOCUMENT VALIDITY READ
    # Public data excludes customers, amounts, contacts, detailed lines and visit credentials.
    # ==============================================

    @router.post("/verify")
    async def verify(
        *, data: PublicReadInput, unit: PublicDiningService = service_dep
    ) -> JsonObject:
        """Read a retained version's current validity without any financial mutation."""
        return await unit.verify(public_id=data.public_id)

    return router
