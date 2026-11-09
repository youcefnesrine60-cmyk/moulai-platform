# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# RESTRICTED ASSISTANT DINING TOOLS
# Allow proposal and conditional booking operations without money or human powers.
# ==============================================

"""No provider, action-executor registration, tools-by-name dispatch or live channel."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT TOOL SURFACE
# A verified dedicated assistant identity must enter an owned scoped unit first.
# ==============================================

from datetime import datetime

from app.core.security.oidc import OIDCPrincipal
from app.schemas.dining import (
    JsonObject,
    RequestInput,
)
from app.services.business.dining.service import DiningUnit
from app.services.business.dining.values import Period

# ==============================================
# DININGASSISTANTTOOLS
# Expose no receipt, grant, availability-proof, physical or invoice mutation.
# ==============================================


class DiningAssistantTools:
    """Expose no receipt, grant, availability-proof, physical or invoice mutation."""

    # ==============================================
    # INIT
    # Retain only a transaction-bound unit issued by DiningService.authorized.
    # ==============================================

    def __init__(self, *, unit: DiningUnit) -> None:
        """Retain only a transaction-bound unit issued by DiningService.authorized."""
        self._unit = unit

    # ==============================================
    # COLLECT
    # Collect a request with a customer principal verified by its trusted channel.
    # ==============================================

    async def collect(self, *, data: RequestInput, customer: OIDCPrincipal) -> int:
        """Collect a request with a customer principal verified by its trusted channel."""
        await self._unit.guard(capability="assistant")
        return await self._unit.create_request(data=data, customer=customer)

    # ==============================================
    # PLANNING
    # Read physical and planned facts without claiming a human confirmation.
    # ==============================================

    async def planning(self, *, period: Period) -> tuple[JsonObject, ...]:
        """Read physical and planned facts without claiming a human confirmation."""
        await self._unit.guard(capability="assistant")
        return await self._unit.planning(period=period)

    # ==============================================
    # QUOTE
    # Use explicit persisted prices and current assignment; never invent a rate.
    # ==============================================

    async def quote(
        self, *, request_id: int, currency: str, expires_at: datetime
    ) -> int:
        """Use explicit persisted prices and current assignment; never invent a rate."""
        await self._unit.guard(capability="assistant")
        return await self._unit.create_quote(
            request_id=request_id, currency=currency, expires_at=expires_at
        )

    # ==============================================
    # HOLD
    # Expose instructions only after actual exclusive hold and required consents.
    # ==============================================

    async def hold(self, *, request_id: int, quote_id: int) -> dict[str, str | int]:
        """Expose instructions only after actual exclusive hold and required consents."""
        await self._unit.guard(capability="assistant")
        return await self._unit.hold(request_id=request_id, quote_id=quote_id)

    # ==============================================
    # CONFIRM
    # Always use the restricted autonomy gate, even for a mixed-grant caller.
    # ==============================================

    async def confirm(
        self, *, request_id: int, quote_id: int, receipt_id: int
    ) -> dict[str, str | int]:
        """Always use the restricted autonomy gate, even for a mixed-grant caller."""
        return await self._unit.finalize_assistant(
            request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
        )
