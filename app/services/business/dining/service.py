# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNED DINING BUSINESS TRANSACTIONS
# Bind current tenant authority and commit receipts separately from booking work.
# ==============================================

"""Opt-in facade; no automatic route registration, notification or provider call."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND CONCRETE UNIT COMPOSITION
# Reuse the existing clean tenant transaction boundary and exact restaurant scope.
# ==============================================

from collections.abc import (
    AsyncIterator,
    Callable,
)
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

from sqlalchemy import (
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import TenantAccessDenied
from app.models.branch import Branch
from app.models.dining import DiningPolicy
from app.schemas.dining import ReceiptInput, TableInput
from app.schemas.dining_public import PublicLinkInput
from app.services.business.dining.cancellation import DiningCancellation
from app.services.business.dining.configuration import DiningConfiguration
from app.services.business.dining.public_resources import DiningPublicManagement
from app.services.business.dining.reservations import DiningReservations
from app.services.business.dining.values import (
    DiningError,
    utc_now,
)
from app.services.business.dining.views import DiningViews
from app.services.business.tenant_access import TenantAccessService
from app.services.business.tenant_foundation import TenantAuthorizationService
from migration_support.operational_revisions import DINING_SERVICE_REVISIONS

# ==============================================
# LIVE BUSINESS UNIT
# All operations share the same current identity, branch and owned transaction.
# ==============================================


class DiningUnit(
    DiningConfiguration,
    DiningReservations,
    DiningPublicManagement,
    DiningViews,
    DiningCancellation,
):
    """Compose concrete operations; instances are issued only by the facade scope."""

    # ==============================================
    # CREATE THE TABLE AND ITS PERMANENT MENU REFERENCE
    # A failed QR emission rolls back the new table; public physical state stays private by default.
    # ==============================================

    async def create_table(
        self,
        *,
        data: TableInput,
        initial_state: Literal["available", "maintenance", "out_of_service"],
    ) -> int:
        """Compose existing configuration and QR issuance inside the same authorized transaction."""
        identifier = await super().create_table(data=data, initial_state=initial_state)
        await self.manage_public_link(
            data=PublicLinkInput(
                operation="issue",
                kind="table",
                resource_id=identifier,
                public_physical_state=False,
            )
        )
        return identifier


# ==============================================
# REQUEST-OWNED FACADE
# Reject an outer or autobegun transaction rather than committing unrelated work.
# ==============================================


class DiningService:
    """Issue bounded units and report success only after the existing owner commits."""

    # ==============================================
    # INIT
    # Keep an injected trusted clock; never consult application connection settings.
    # ==============================================

    def __init__(
        self, *, session: AsyncSession, clock: Callable[[], datetime] = utc_now
    ) -> None:
        """Keep an injected trusted clock; never consult application connection settings."""
        self.session = session
        self.clock = clock

    # ==============================================
    # AUTHORIZED
    # Resolve active authority and hold it through exactly one clean transaction.
    # ==============================================

    @asynccontextmanager
    async def authorized(
        self,
        *,
        principal: OIDCPrincipal,
        organization_id: int,
        restaurant_id: int,
        branch_id: int,
    ) -> AsyncIterator[DiningUnit]:
        """Resolve active authority and hold it through exactly one clean transaction."""
        unit: DiningUnit | None = None
        try:
            async with TenantAccessService(session=self.session).authorized(
                principal=principal,
                organization_id=organization_id,
                permission="tenant.restaurants.read",
            ) as read:
                await TenantAuthorizationService(
                    session=self.session
                ).require_restaurant(
                    context=read.context,
                    restaurant_id=restaurant_id,
                    permission="tenant.restaurants.read",
                )
                branch = (
                    await self.session.execute(
                        select(Branch.id).where(
                            Branch.id == branch_id,
                            Branch.restaurant_id == restaurant_id,
                            Branch.is_active.is_(True),
                        )
                    )
                ).scalar_one_or_none()
                if branch is None:
                    raise TenantAccessDenied("dining_branch_unavailable")
                if (
                    await self.session.scalar(
                        text("SELECT version_num FROM public.alembic_version")
                    )
                    not in DINING_SERVICE_REVISIONS
                ):
                    raise DiningError(code="dining_schema_not_enabled")
                # Serialize branch work before locking dining grants. This shared
                # order prevents an approval and a concurrent grant revocation
                # from acquiring policy/grant locks in opposite orders.
                await self.session.execute(
                    select(DiningPolicy.id)
                    .where(
                        DiningPolicy.restaurant_id == restaurant_id,
                        DiningPolicy.branch_id == branch_id,
                    )
                    .with_for_update()
                )
                unit = DiningUnit(
                    session=self.session,
                    context=read.context,
                    principal=principal,
                    restaurant_id=restaurant_id,
                    branch_id=branch_id,
                    clock=self.clock,
                )
                yield unit
            if unit is not None and unit.event_count:
                logger.info(
                    "Dining transaction committed",
                    extra={
                        "restaurant_id": restaurant_id,
                        "branch_id": branch_id,
                        "event_count": unit.event_count,
                    },
                )
        finally:
            if unit is not None:
                unit.active = False

    # ==============================================
    # RECORD RECEIPT
    # Commit actual received-fund facts in a clean operation of their own.
    # ==============================================

    async def record_receipt(
        self,
        *,
        principal: OIDCPrincipal,
        organization_id: int,
        restaurant_id: int,
        branch_id: int,
        data: ReceiptInput,
    ) -> int:
        """Commit actual received-fund facts in a clean operation of their own.

        An existing outer transaction is rejected by authorized(). Callers cannot
        accidentally put receipt creation in a later booking rollback. No
        reservation confirmation or invoice allocation is called here.
        """
        async with self.authorized(
            principal=principal,
            organization_id=organization_id,
            restaurant_id=restaurant_id,
            branch_id=branch_id,
        ) as unit:
            identifier = await unit._record_receipt(data=data)
        return identifier
