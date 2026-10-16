# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Resolve persisted Telegram identities and tenant-scoped billing choices."""

# ==============================================
# IMPORTS
# ==============================================

from sqlalchemy import (
    Select,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.owner import Owner
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.subscription import SubscriptionPlan

# ==============================================
# TELEGRAM BILLING REPOSITORY
# ==============================================


class TelegramBillingRepository:
    """Keep chat identity and restaurant ownership checks in authoritative SQL."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Use the request-owned session without committing financial work."""
        self.session = session

    # ==========================================
    # BASE SELECT
    # ==========================================

    def _owner_select(self) -> Select[tuple[int]]:
        """Select approved owners only for billing access."""
        return select(Owner.id).where(Owner.registration_status == "approved")

    def _restaurant_select(self) -> Select[tuple[int, str]]:
        """Build the canonical tenant-selectable restaurant projection."""
        return select(Restaurant.id, Restaurant.name)

    def _plan_select(self) -> Select[tuple[int, str]]:
        """Build the active plan projection shared by billing choices."""
        return select(SubscriptionPlan.id, SubscriptionPlan.name).where(
            SubscriptionPlan.active.is_(True)
        )

    def _pending_payment_select(self) -> Select[tuple[int]]:
        """Join manual pending invoices to their authoritative restaurant."""
        return (
            select(Payment.id)
            .join(Restaurant, Restaurant.id == Payment.restaurant_id)
            .where(
                Payment.payment_provider == "manual_transfer",
                Payment.status == "pending",
            )
        )

    # ==========================================
    # RESOLVE IDENTITIES
    # ==========================================

    async def owner_id(self, *, chat_id: int) -> int | None:
        """Resolve the stored chat mapping; state never supplies the owner ID."""
        return await self.session.scalar(
            self._owner_select().where(Owner.chat_id == chat_id)
        )

    # ==========================================
    # LIST TENANT BILLING CHOICES
    # ==========================================

    async def restaurants(self, *, owner_id: int) -> list[tuple[int, str]]:
        """Return only this owner's restaurants in stable order."""
        rows = await self.session.execute(
            self._restaurant_select()
            .where(Restaurant.owner_id == owner_id)
            .order_by(Restaurant.id)
        )
        return [(row.id, row.name) for row in rows]

    async def owns_restaurant(self, *, owner_id: int, restaurant_id: int) -> bool:
        """Reject guessed restaurant identifiers in every checkout step."""
        return (
            await self.session.scalar(
                self._restaurant_select().where(
                    Restaurant.owner_id == owner_id, Restaurant.id == restaurant_id
                )
            )
            is not None
        )

    async def plans(self) -> list[tuple[int, str]]:
        """Read currently available plans without accepting client prices."""
        rows = await self.session.execute(
            self._plan_select().order_by(
                SubscriptionPlan.display_order, SubscriptionPlan.id
            )
        )
        return [(row.id, row.name) for row in rows]

    async def pending_payments(self, *, owner_id: int) -> list[int]:
        """Allow pending invoices to be resumed after state expiry or cancellation."""
        rows = await self.session.scalars(
            self._pending_payment_select()
            .where(
                Payment.owner_id == owner_id,
                Restaurant.owner_id == owner_id,
            )
            .order_by(Payment.id.desc())
            .limit(20)
        )
        return list(rows)
