# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION REMINDER OUTBOX
# Schedule both recipients and dispatch explicit reminder attempts with duplicate
# prevention.
# ==============================================

"""Transactional reminder outbox. Delivery is explicit, never triggered by imports."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from datetime import (
    datetime,
    timedelta,
)
from typing import cast

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.owner import Owner
from app.models.subscription import Subscription
from app.models.subscription_pricing import (
    SubscriptionPricingConfig,
    SubscriptionReminder,
)
from app.repositories.subscription_queries import base_select
from app.services.business.subscription_types import (
    PricingPolicies,
    ReminderTransport,
    SessionFactory,
    TelegramTransport,
    WorkerResults,
)

# ==============================================
# DEFINITELY NOT DELIVERED
# Only a transport proving no delivery may opt into automatic retry.
# ==============================================


class DefinitelyNotDelivered(Exception):
    """Only a transport proving no delivery may opt into automatic retry."""


# ==============================================
# REMINDER CONFIGURATION PREFLIGHT
# Validate scheduling prerequisites without creating a reminder or sending a message.
# ==============================================


async def reminder_configuration(*, session: AsyncSession) -> PricingPolicies:
    """Return valid persisted scheduling policies or reject missing/invalid configuration."""
    config = (
        await session.execute(
            base_select(SubscriptionPricingConfig)
            .with_only_columns(SubscriptionPricingConfig.policies)
            .where(SubscriptionPricingConfig.id == 1)
        )
    ).scalar_one_or_none()
    if config is None:
        raise ValueError("subscription_pricing_configuration_missing")
    offsets = config.get("reminder_days")
    if (
        not isinstance(offsets, list)
        or not offsets
        or any(type(n) is not int or n < 0 for n in offsets)
    ):
        raise ValueError("reminder_schedule_configuration_invalid")
    return cast(PricingPolicies, config)


# ==============================================
# SCHEDULE
# Upsert configured reminders for both recipients and cancel obsolete reminders.
# ==============================================


async def schedule(*, session: AsyncSession, subscription: Subscription) -> None:
    """Upsert configured reminders for both recipients and cancel obsolete reminders."""

    await session.flush()
    config = await reminder_configuration(session=session)
    offsets = config["reminder_days"]
    owner_chat = (
        await session.execute(
            base_select(Owner)
            .with_only_columns(Owner.chat_id)
            .where(Owner.id == subscription.owner_id)
        )
    ).scalar_one()
    # ==============================================
    # BROWSER IDENTITY IS NOT A TELEGRAM CONTACT
    # O4 enrollment uses a compatibility number only; leave delivery explicitly blocked until an authorized channel exists.
    # ==============================================

    from sqlalchemy import text

    if await session.scalar(text("SELECT version_num FROM public.alembic_version")) in {
        "o420261108",
        "o520261111",
    }:
        from app.models.billing_country import EnrollmentDossier
        from app.models.registration_request import RegistrationRequest

        browser_dossier = await session.scalar(
            base_select(EnrollmentDossier)
            .with_only_columns(EnrollmentDossier.id)
            .join(
                RegistrationRequest,
                RegistrationRequest.id == EnrollmentDossier.registration_request_id,
            )
            .join(Owner, Owner.chat_id == RegistrationRequest.chat_id)
            .where(Owner.id == subscription.owner_id)
            .limit(1)
        )
        if browser_dossier is not None:
            owner_chat = None
    # A confirmed renewal, including prepaid scheduled coverage, supersedes old reminders.
    previous = (
        base_select(Subscription)
        .with_only_columns(Subscription.id)
        .where(
            Subscription.restaurant_id == subscription.restaurant_id,
            Subscription.id != subscription.id,
        )
    )
    await session.execute(
        update(SubscriptionReminder)
        .where(
            SubscriptionReminder.subscription_id.in_(previous),
            SubscriptionReminder.expires_at <= subscription.expires_at,
            SubscriptionReminder.status.in_(["pending", "failed", "blocked"]),
        )
        .values(status="cancelled")
    )
    recipients = {
        "owner": owner_chat,
        "moulai_responsible": config.get("moulai_responsible_chat_id"),
    }
    await session.execute(
        update(SubscriptionReminder)
        .where(
            SubscriptionReminder.subscription_id == subscription.id,
            SubscriptionReminder.expires_at == subscription.expires_at,
            SubscriptionReminder.offset_days.not_in(offsets),
            SubscriptionReminder.status.in_(["pending", "failed", "blocked"]),
        )
        .values(status="cancelled")
    )
    for days in sorted(set(offsets), reverse=True):
        for recipient, target in recipients.items():
            await session.execute(
                insert(SubscriptionReminder)
                .values(
                    subscription_id=subscription.id,
                    expires_at=subscription.expires_at,
                    offset_days=days,
                    recipient=recipient,
                    target_chat_id=str(target) if target is not None else None,
                    due_at=subscription.expires_at - timedelta(days=days),
                    status="pending" if target is not None else "blocked",
                    attempts=0,
                    attempt_log=[],
                )
                .on_conflict_do_update(
                    constraint="uq_subscription_reminder",
                    set_={
                        "target_chat_id": str(target) if target is not None else None,
                        "status": "pending" if target is not None else "blocked",
                    },
                    where=SubscriptionReminder.status.in_(
                        ["pending", "failed", "blocked"]
                    ),
                )
            )


# ==============================================
# DISPATCH
# Claim/commit before I/O; never automatically retry an uncertain delivery.
# ==============================================


async def dispatch(
    *,
    session_factory: SessionFactory,
    sender: ReminderTransport,
    now: datetime,
    limit: int = 100,
) -> WorkerResults:
    """Claim/commit before I/O; never automatically retry an uncertain delivery.

    sender receives an existing authorized channel and a stable idempotency key.
    A crash after claim leaves 'delivering' for manual reconciliation, not resend.
    """
    async with session_factory() as reader:
        ids = list(
            (
                await reader.execute(
                    base_select(SubscriptionReminder)
                    .with_only_columns(SubscriptionReminder.id)
                    .where(
                        SubscriptionReminder.due_at <= now,
                        SubscriptionReminder.status.in_(
                            ["pending", "failed", "blocked"]
                        ),
                    )
                    .order_by(SubscriptionReminder.due_at, SubscriptionReminder.id)
                    .limit(limit)
                )
            ).scalars()
        )
    results: WorkerResults = []
    for identifier in ids:
        async with session_factory() as session:
            async with session.begin():
                row = (
                    await session.execute(
                        base_select(SubscriptionReminder)
                        .where(
                            SubscriptionReminder.id == identifier,
                            SubscriptionReminder.status.in_(
                                ["pending", "failed", "blocked"]
                            ),
                        )
                        .with_for_update(skip_locked=True)
                    )
                ).scalar_one_or_none()
                if row is None:
                    continue
                if row.target_chat_id is None:
                    config = (
                        await session.execute(
                            base_select(SubscriptionPricingConfig)
                            .with_only_columns(SubscriptionPricingConfig.policies)
                            .where(SubscriptionPricingConfig.id == 1)
                        )
                    ).scalar_one()
                    target = (
                        config.get("moulai_responsible_chat_id")
                        if row.recipient == "moulai_responsible"
                        else None
                    )
                    if target is None:
                        results.append((identifier, "missing_recipient"))
                        continue
                    row.target_chat_id = str(target)
                row.status = "delivering"
                row.attempts += 1
                row.attempt_log = [
                    *row.attempt_log,
                    {
                        "attempt": row.attempts,
                        "claimed_at": now.isoformat(),
                        "result": "delivering",
                    },
                ]
                target = row.target_chat_id
                message = f"Abonnement {row.subscription_id} — échéance {row.expires_at.isoformat()} UTC. Renouvellement nécessaire. Le prochain prix sera établi au calcul du renouvellement."
                key = f"subscription-reminder:{row.id}"
            # Claim is durable before the channel is invoked.
            try:
                await sender.send(target=target, message=message, idempotency_key=key)
                status = "sent"
            except DefinitelyNotDelivered:
                status = "failed"
            except Exception:  # noqa: BLE001
                status = "uncertain"
            async with session.begin():
                row = (
                    await session.execute(
                        base_select(SubscriptionReminder)
                        .where(SubscriptionReminder.id == identifier)
                        .with_for_update()
                    )
                ).scalar_one()
                row.status = status
                row.sent_at = now if status == "sent" else None
                row.attempt_log = [
                    *row.attempt_log,
                    {
                        "attempt": row.attempts,
                        "finished_at": now.isoformat(),
                        "result": status,
                    },
                ]
            logger.info(
                "subscription_reminder_delivery_result",
                extra={"reminder_id": identifier, "status": status},
            )
            results.append((identifier, status))
    return results


# ==============================================
# TELEGRAM REMINDER SENDER
# Adapter for an already authorized Telegram client; never constructs one.
# ==============================================


class TelegramReminderSender:
    """Adapter for an already authorized Telegram client; never constructs one."""

    # ==============================================
    # INIT
    # Bind the explicit dependencies without performing external operations.
    # ==============================================

    def __init__(self, *, client: TelegramTransport) -> None:
        """Bind the explicit dependencies without performing external operations."""

        self.client = client

    # ==============================================
    # SEND
    # Delegate to the injected authorized client without recording recipient details.
    # ==============================================

    async def send(self, *, target: str, message: str, idempotency_key: str) -> None:
        # Telegram has no general sendMessage idempotency guarantee. Unknown
        # failures remain uncertain in the outbox and are not retried blindly.
        """Delegate to the injected authorized client without recording recipient details."""

        result = await self.client.send_message(chat_id=int(target), text=message)
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise DefinitelyNotDelivered("telegram_delivery_not_accepted")
