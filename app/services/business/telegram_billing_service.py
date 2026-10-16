# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Authorize Telegram billing through persisted identities and shared services."""

# ==============================================
# IMPORTS
# ==============================================

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.repositories.telegram_billing_repo import TelegramBillingRepository
from app.schemas.manual_payment import ManualPaymentMethod
from app.services.business.payment_providers import get_payment_provider

# ==============================================
# TRANSFER INSTRUCTIONS
# ==============================================


def transfer_instructions(*, method: ManualPaymentMethod) -> str:
    """Require real beneficiary details before offering a transfer checkout."""
    get_payment_provider(method=method)
    beneficiary = (settings.MANUAL_TRANSFER_BENEFICIARY or "").strip()
    if method == "ccp":
        account = (settings.MANUAL_CCP_ACCOUNT or "").strip()
        key = (settings.MANUAL_CCP_KEY or "").strip()
        if not beneficiary or not account or not key:
            raise UnauthorizedError(message="Transfer beneficiary is not configured")
        return f"المستفيد: {beneficiary}\nCCP: {account}\nالمفتاح: {key}"
    rip = (settings.MANUAL_BARIDIMOB_RIP or "").strip()
    if not beneficiary or not rip:
        raise UnauthorizedError(message="Transfer beneficiary is not configured")
    return f"المستفيد: {beneficiary}\nBaridiMob RIP: {rip}"


# ==============================================
# TELEGRAM BILLING SERVICE
# ==============================================


class TelegramBillingService:
    """Resolve identities independently of callback IDs and Redis state."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Share one request session with the canonical financial services."""
        self.session = session
        self.repo = TelegramBillingRepository(session=session)

    # ==========================================
    # AUTHORIZE OWNER
    # ==========================================

    async def owner_id(self, *, chat_id: int, restaurant_id: int | None = None) -> int:
        """Require an approved persisted owner and, when supplied, owned tenant."""
        owner_id = await self.repo.owner_id(chat_id=chat_id)
        if owner_id is None or (
            restaurant_id is not None
            and not await self.repo.owns_restaurant(
                owner_id=owner_id, restaurant_id=restaurant_id
            )
        ):
            raise UnauthorizedError(message="Billing access denied")
        return owner_id
