# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICITLY AUTHORIZED SAAS CAMPAIGN ADMINISTRATION
# Reuse persisted promotions and the existing calculation engine without rewriting invoices.
# ==============================================

"""Local integration service: exact permission, locked changes, dated drafts and durable audit."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Use existing schema entities and parameterized BASE SELECT roots throughout.
# ==============================================

import hashlib
import json
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from typing import TypedDict
from uuid import uuid4

from fastapi import HTTPException
from pydantic import (
    JsonValue,
    TypeAdapter,
)
from sqlalchemy import (
    Select,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.security.oidc import OIDCPrincipal
from app.core.security.platform_permissions import SUBSCRIPTION_PRICING_MANAGE
from app.models.admin_log import AdminLog
from app.models.loyalty_discount import Promotion
from app.models.owner import Owner
from app.models.rbac import role_permissions
from app.models.restaurant import Restaurant
from app.models.subscription import SubscriptionPlan
from app.models.subscription_pricing import SubscriptionPricingConfig
from app.repositories.subscription_queries import base_select
from app.schemas.saas_pricing import (
    BasePriceCommand,
    CampaignCommand,
    CampaignValues,
    ReminderCommand,
)

# ==============================================
# CURRENT DZD BASE REPRESENTATION
# Read the existing singleton and its revision metadata; do not introduce another price store.
# ==============================================


class BasePriceView(TypedDict):
    """Expose exact current B and the revision used by new quotations."""

    amount: str
    country_code: str
    currency: str
    revision: str
    sha256: str


# ==============================================
# LOSSLESS PUBLIC REPRESENTATION
# Do not serialize percentages through float or expose account credentials.
# ==============================================


class CampaignView(TypedDict):
    """Retain full calculation inputs and an optimistic representation digest."""

    id: int
    name: str
    discount_percent: str
    starts_at: str | None
    expires_at: str | None
    priority: int
    restaurant_id: int | None
    owner_id: int | None
    plan_id: int | None
    active: bool
    state: str
    sha256: str


# ==============================================
# DURABLE AUTHORIZED AUDIT VIEW
# Keep actor, time and retained before/after values separate from live commercial calculations.
# ==============================================


class PricingAuditView(TypedDict):
    """Represent persisted administrative evidence only, not reconstructed historical values."""

    id: int
    author_admin_id: int
    author_name: str | None
    action: str
    recorded_at: str
    details: dict[str, JsonValue]


# ==============================================
# CAMPAIGN BASE QUERY
# This SQL root grants no authority; every service entry first checks the exact permission.
# ==============================================


def campaign_select() -> Select[tuple[Promotion]]:
    """Build the shared promotion root without dropping scope or date predicates."""
    return base_select(Promotion)


# ==============================================
# EXPLICIT PERMISSION ASSOCIATION ROOT
# Select the stored role-permission relation without inferring grants from role labels.
# ==============================================


def permission_grant_select() -> Select[tuple[int]]:
    """Build the SQL association root; exact permission predicates remain mandatory."""
    return select(role_permissions.c.permission_id)


# ==============================================
# AUTHORITATIVE CAMPAIGN SERVICE
# Each operation owns one transaction and checks current explicit grants under locks.
# ==============================================


class SaasPricingAdministration:
    """Offer read, draft, publication and deactivation with no inferred administrator grant."""

    # ==============================================
    # INIT
    # Require a fresh request session using the project's explicit-flush policy.
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Require a fresh request session using the project's explicit-flush policy."""
        self.session = session

    # ==============================================
    # FRESH COMMITTED AUDIT CONSULTATION
    # No caller-provided author filter can expand the explicit platform pricing authority.
    # ==============================================

    async def history(
        self, *, principal: OIDCPrincipal, resource: str, identifier: int
    ) -> list[PricingAuditView]:
        """Read at most 100 actual audit entries from a new authorized request transaction."""
        if (
            resource not in {"saas_base", "saas_promotion", "saas_configuration"}
            or identifier < 1
        ):
            raise ValueError("invalid_pricing_audit_target")
        async with self.session.begin():
            await self.authorize(principal=principal)
            target = (AdminLog.resource == resource) & (
                AdminLog.resource_id == identifier
            )
            if resource == "saas_base" and identifier == 1:
                target = target | (AdminLog.resource == "saas_base_country")
            rows = (
                await self.session.execute(
                    base_select(AdminLog)
                    .where(target)
                    .order_by(AdminLog.id.desc())
                    .limit(100)
                )
            ).all()
            return [
                {
                    "id": row.id,
                    "author_admin_id": row.actor_admin_id,
                    "author_name": row.actor_name,
                    "action": row.action,
                    "recorded_at": row.timestamp.replace(
                        tzinfo=timezone.utc
                    ).isoformat(),
                    "details": TypeAdapter(dict[str, JsonValue]).validate_json(
                        row.details
                    ),
                }
                for (row,) in rows
            ]

    # ==============================================
    # CANONICAL EXISTING BASE VALUE
    # A missing required parameter remains a configuration error, never a 3000 fallback.
    # ==============================================

    def base_view(
        self,
        *,
        amount: Decimal,
        policies: dict[str, JsonValue],
        revision: str,
        country_code: str = "DZ",
        currency: str = "DZD",
    ) -> BasePriceView:
        """Hash only the selected price and monetary policy; reminder edits do not reversion B."""
        currency_policy = policies.get("currencies", {})
        if not isinstance(currency_policy, dict):
            raise TypeError("currency_configuration_invalid")
        if currency not in currency_policy:
            raise ValueError("currency_configuration_missing")
        if not isinstance(currency_policy[currency], dict):
            raise TypeError("currency_configuration_invalid")
        decimals = currency_policy[currency].get("decimals")
        if (
            isinstance(decimals, bool)
            or not isinstance(decimals, int)
            or not 0 <= decimals <= 8
        ):
            raise ValueError("currency_configuration_missing")
        value = {
            "amount": format(amount, ".8f"),
            "country_code": country_code,
            "currency": currency,
            "revision": revision,
            "currency_policy": currency_policy[currency],
        }
        return {
            "amount": format(amount, f".{decimals}f"),
            "country_code": country_code,
            "currency": currency,
            "revision": revision,
            "sha256": hashlib.sha256(
                json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

    # ==============================================
    # SHARED POLICY VERSION WITHOUT A PRICE DEPENDENCY
    # Changes to reminder offsets affect their policy revision, never a selected country's B.
    # ==============================================

    def policy_view(self, *, row: SubscriptionPricingConfig) -> dict[str, JsonValue]:
        """Return a technical policy digest without exposing recipient identifiers."""
        return {
            "revision": row.policies.get(
                "policy_revision", "legacy:subscription-policy:1"
            ),
            "sha256": hashlib.sha256(
                json.dumps(row.policies, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

    # ==============================================
    # SINGLE PRICE SOURCE FOR THE ADMITTED SCHEMA
    # Legacy reads are limited to physically legacy databases; O3/O4 use only country versions.
    # ==============================================

    async def load_base(self, *, country_code: str, currency: str) -> BasePriceView:
        """Read within the facade transaction; no country is inferred for owner calculations."""
        from app.repositories.subscription_configuration import (
            country_storage_enabled,
            legacy_base,
            read_pricing_policy,
        )

        policies = await read_pricing_policy(session=self.session)
        if await country_storage_enabled(session=self.session):
            from app.services.business.subscription_country_base import resolve_country_base  # isort: skip  # fmt: skip

            selected = await resolve_country_base(
                session=self.session,
                country_code=country_code,
                currency=currency,
                at=datetime.now(timezone.utc),
            )
            amount, revision = selected.amount, selected.revision
        else:
            if country_code != "DZ" or currency != "DZD":
                raise ValueError("legacy_country_context_unavailable")
            amount = await legacy_base(
                session=self.session, currency=currency, policies=policies
            )
            revision = policies.get(
                "base_revision", "legacy:subscription_pricing_config:1"
            )
        return self.base_view(
            amount=amount,
            policies=policies,
            revision=revision,
            country_code=country_code,
            currency=currency,
        )

    # ==============================================
    # CONFIGURED BASE CONSULTATION
    # Platform editing authority remains separate from a tenant's own price calculation.
    # ==============================================

    async def current_base(
        self,
        *,
        principal: OIDCPrincipal,
        country_code: str = "DZ",
        currency: str = "DZD",
    ) -> BasePriceView:
        """Read an explicit administrative reference pair, separate from the owner's verified billing context."""
        async with self.session.begin():
            await self.authorize(principal=principal)
            return await self.load_base(country_code=country_code, currency=currency)

    # ==============================================
    # EXISTING REMINDER POLICY READ
    # Expose schedule offsets and readiness only; recipient identifiers are not needed by this editor.
    # ==============================================

    async def base_contexts(
        self, *, principal: OIDCPrincipal
    ) -> list[dict[str, JsonValue]]:
        """List only configured current country/currency pairs under the exact pricing permission."""
        from app.repositories.subscription_configuration import country_storage_enabled

        async with self.session.begin():
            await self.authorize(principal=principal)
            if not await country_storage_enabled(session=self.session):
                await self.load_base(country_code="DZ", currency="DZD")
                return [{"country_code": "DZ", "currency": "DZD"}]
            from app.models.subscription_base_price import SubscriptionBasePrice

            now = datetime.now(timezone.utc)
            rows = (
                await self.session.execute(
                    base_select(SubscriptionBasePrice)
                    .with_only_columns(
                        SubscriptionBasePrice.country_code,
                        SubscriptionBasePrice.currency,
                    )
                    .where(
                        SubscriptionBasePrice.effective_from <= now,
                        (SubscriptionBasePrice.effective_until.is_(None))
                        | (SubscriptionBasePrice.effective_until > now),
                    )
                    .order_by(
                        SubscriptionBasePrice.country_code,
                        SubscriptionBasePrice.currency,
                    )
                )
            ).all()
            return [
                {"country_code": row.country_code, "currency": row.currency}
                for row in rows
            ]

    # ==============================================
    # POLICY CONSULTATION WITHOUT PRICE FALLBACK
    # Schedule offsets are independent of the selected country's retained B version.
    # ==============================================

    async def reminder_configuration(
        self, *, principal: OIDCPrincipal
    ) -> dict[str, JsonValue]:
        """Read the actual singleton under the exact pricing permission, without any delivery."""
        async with self.session.begin():
            await self.authorize(principal=principal)
            row = await self.session.scalar(
                base_select(SubscriptionPricingConfig).where(
                    SubscriptionPricingConfig.id == 1
                )
            )
            if row is None or not isinstance(row.policies.get("reminder_days"), list):
                raise HTTPException(
                    status_code=409, detail="reminder_configuration_missing"
                )
            return {
                "days": row.policies["reminder_days"],
                "sha256": self.policy_view(row=row)["sha256"],
                "responsible_configured": bool(
                    row.policies.get("moulai_responsible_chat_id")
                ),
                "applies_to": "new_schedules_only",
                "delivery_active": False,
            }

    # ==============================================
    # VERSIONED FUTURE SCHEDULE CHANGE
    # Preserve existing outbox rows and their results; only later scheduling reads this new policy.
    # ==============================================

    async def change_reminders(
        self, *, principal: OIDCPrincipal, command: ReminderCommand
    ) -> dict[str, JsonValue]:
        """Commit the offset policy, revision and before/after audit atomically, with no sends or activation."""
        async with self.session.begin():
            admin = await self.authorize(principal=principal)
            row = await self.session.scalar(
                base_select(SubscriptionPricingConfig)
                .where(SubscriptionPricingConfig.id == 1)
                .with_for_update()
            )
            if row is None:
                raise HTTPException(
                    status_code=409, detail="reminder_configuration_missing"
                )
            before = self.policy_view(row=row)
            if (
                command.expected_sha256 != before["sha256"]
                or row.policies.get("reminder_days") == command.days
            ):
                raise HTTPException(
                    status_code=409,
                    detail="reminder_configuration_changed_or_unchanged",
                )
            old_days = row.policies.get("reminder_days")
            row.policies = {
                **row.policies,
                "reminder_days": command.days,
                "policy_revision": uuid4().hex,
            }
            await self.session.flush()
            after = self.policy_view(row=row)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            self.session.add(
                AdminLog(
                    admin_id=admin,
                    action="pricing.reminders.change",
                    resource="saas_configuration",
                    resource_id=1,
                    timestamp=now,
                    details=json.dumps(
                        {
                            "before": {
                                "days": old_days,
                                "revision": before["revision"],
                            },
                            "after": {
                                "days": command.days,
                                "revision": after["revision"],
                            },
                            "reason": command.reason,
                            "effective_at": now.isoformat() + "Z",
                            "scope": "new_schedules_only",
                        },
                        sort_keys=True,
                    ),
                )
            )
        logger.info(
            "Reminder configuration transaction committed",
            extra={"admin_id": admin, "revision": after["revision"]},
        )
        return {
            "days": command.days,
            "sha256": after["sha256"],
            "revision": after["revision"],
            "applies_to": "new_schedules_only",
        }

    # ==============================================
    # EXPLICIT IMMEDIATE BASE CHANGE
    # Freeze the old and new values in the same transaction; never touch retained calculations.
    # ==============================================

    async def change_base(
        self, *, principal: OIDCPrincipal, command: BasePriceCommand
    ) -> BasePriceView:
        """Publish a replacement country version or update an explicitly admitted historical singleton."""
        from app.repositories.subscription_configuration import country_storage_enabled

        async with self.session.begin():
            admin_id = await self.authorize(principal=principal)
            policy = await self.session.scalar(
                base_select(SubscriptionPricingConfig)
                .where(SubscriptionPricingConfig.id == 1)
                .with_for_update()
            )
            if policy is None:
                raise HTTPException(
                    status_code=409, detail="subscription_pricing_configuration_missing"
                )
            before = await self.load_base(
                country_code=command.country_code, currency=command.currency
            )
            if before["sha256"] != command.expected_sha256 or Decimal(
                command.amount
            ) == Decimal(before["amount"]):
                raise HTTPException(
                    status_code=409, detail="Pricing parameter changed or unchanged"
                )
            if await country_storage_enabled(session=self.session):
                from app.services.business.subscription_country_base import stage_country_base  # isort: skip  # fmt: skip

                await stage_country_base(
                    session=self.session,
                    principal=principal,
                    country_code=command.country_code,
                    currency=command.currency,
                    amount=Decimal(command.amount),
                    expected_revision=before["revision"],
                    source_reference=command.reason,
                )
            else:
                from app.models.subscription_pricing_legacy import LegacySubscriptionPricingConfig  # isort: skip  # fmt: skip

                row = await self.session.scalar(
                    base_select(LegacySubscriptionPricingConfig)
                    .where(LegacySubscriptionPricingConfig.id == 1)
                    .with_for_update()
                )
                if row is None:
                    raise ValueError("subscription_pricing_configuration_missing")
                row.base_price = Decimal(command.amount)
                policy.policies = {**policy.policies, "base_revision": uuid4().hex}
                await self.session.flush()
            after = await self.load_base(
                country_code=command.country_code, currency=command.currency
            )
            if not await country_storage_enabled(session=self.session):
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                self.session.add(
                    AdminLog(
                        admin_id=admin_id,
                        action="pricing.base.change",
                        resource="saas_base",
                        resource_id=1,
                        timestamp=now,
                        details=json.dumps(
                            {
                                "author_admin_id": admin_id,
                                "recorded_at": now.isoformat() + "Z",
                                "effective": "on_commit",
                                "effective_at": now.isoformat() + "Z",
                                "reason": command.reason,
                                "before": before,
                                "after": after,
                            },
                            sort_keys=True,
                        ),
                    )
                )
        logger.info(
            "SaaS base parameter transaction committed",
            extra={
                "admin_id": admin_id,
                "revision": after["revision"],
                "country": command.country_code,
                "currency": command.currency,
            },
        )
        return after

    # ==============================================
    # EXACT CURRENT AUTHORITY
    # Neither a wildcard, a role label nor another platform permission satisfies this grant.
    # ==============================================

    async def authorize(self, *, principal: OIDCPrincipal) -> int:
        """Require the exact stored pricing grant, never a role label or another platform permission."""
        from app.services.business.platform_authority import require_platform_permission

        return await require_platform_permission(
            session=self.session,
            principal=principal,
            permission=SUBSCRIPTION_PRICING_MANAGE,
        )

    # ==============================================
    # RETAINED LIFECYCLE STATE
    # Unmanaged historical rows remain readable but cannot be edited as new drafts.
    # ==============================================

    async def view(
        self, *, row: Promotion, pending_action: str | None = None
    ) -> CampaignView:
        """Derive managed state from the same transactional admin audit, preserving legacy data."""
        action = pending_action or await self.session.scalar(
            base_select(AdminLog)
            .with_only_columns(AdminLog.action)
            .where(
                AdminLog.resource == "saas_promotion", AdminLog.resource_id == row.id
            )
            .order_by(AdminLog.id.desc())
            .limit(1)
        )
        state = {
            "pricing.create": "draft",
            "pricing.update": "draft",
            "pricing.publish": "published",
            "pricing.deactivate": "deactivated",
        }.get(action, "legacy")
        value: CampaignView = {
            "id": row.id,
            "name": row.name,
            "discount_percent": format(row.discount_percent, ".8f"),
            "starts_at": (
                row.starts_at.replace(tzinfo=timezone.utc).isoformat()
                if row.starts_at
                else None
            ),
            "expires_at": (
                row.expires_at.replace(tzinfo=timezone.utc).isoformat()
                if row.expires_at
                else None
            ),
            "priority": row.priority,
            "restaurant_id": row.restaurant_id,
            "owner_id": row.owner_id,
            "plan_id": row.plan_id,
            "active": row.active is True,
            "state": state,
            "sha256": "",
        }
        value["sha256"] = hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return value

    # ==============================================
    # BOUNDED CAMPAIGN CONSULTATION
    # Platform configuration is separate from a tenant's own quotation or invoice access.
    # ==============================================

    async def campaigns(self, *, principal: OIDCPrincipal) -> list[CampaignView]:
        """List at most 100 latest persisted records; never manufacture example offers."""
        async with self.session.begin():
            await self.authorize(principal=principal)
            rows = (
                await self.session.scalars(
                    campaign_select().order_by(Promotion.id.desc()).limit(100)
                )
            ).all()
            return [await self.view(row=row) for row in rows]

    # ==============================================
    # VERIFIED TARGETS AND FUTURE INTERVAL
    # Reject unknown identifiers and contradictory owner/restaurant targeting before writes.
    # ==============================================

    async def validate_targets(self, *, data: CampaignValues, now: datetime) -> None:
        """A new draft may not rewrite past pricing or target nonexistent business entities."""
        if data.starts_at.astimezone(timezone.utc).replace(tzinfo=None) <= now:
            raise HTTPException(
                status_code=409, detail="New campaign must start in the future"
            )
        if (
            data.owner_id is not None
            and await self.session.scalar(
                base_select(Owner)
                .with_only_columns(Owner.id)
                .where(Owner.id == data.owner_id)
            )
            is None
        ):
            raise HTTPException(status_code=409, detail="Campaign target unavailable")
        if (
            data.plan_id is not None
            and await self.session.scalar(
                base_select(SubscriptionPlan)
                .with_only_columns(SubscriptionPlan.id)
                .where(
                    SubscriptionPlan.id == data.plan_id,
                    SubscriptionPlan.active.is_(True),
                )
            )
            is None
        ):
            raise HTTPException(status_code=409, detail="Campaign target unavailable")
        if data.restaurant_id is not None:
            owner = await self.session.scalar(
                base_select(Restaurant)
                .with_only_columns(Restaurant.owner_id)
                .where(Restaurant.id == data.restaurant_id)
            )
            if owner is None or data.owner_id is not None and owner != data.owner_id:
                raise HTTPException(
                    status_code=409, detail="Campaign target unavailable"
                )

    # ==============================================
    # TRANSACTIONAL MUTATION AND AUDIT
    # Published values are frozen; changes require a new draft and old calculations stay untouched.
    # ==============================================

    async def execute(
        self, *, principal: OIDCPrincipal, command: CampaignCommand
    ) -> CampaignView:
        """Commit one explicitly authorized intent and its before/after audit, or roll back both."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with self.session.begin():
            admin_id = await self.authorize(principal=principal)
            row = (
                None
                if command.identifier is None
                else await self.session.scalar(
                    campaign_select()
                    .where(Promotion.id == command.identifier)
                    .with_for_update()
                )
            )
            if command.identifier is not None and row is None:
                raise HTTPException(status_code=404, detail="Campaign unavailable")
            before = await self.view(row=row) if row is not None else None
            if before is not None and before["sha256"] != command.expected_sha256:
                raise HTTPException(status_code=409, detail="Campaign version changed")
            if command.operation in {"create", "update"}:
                if before is not None and before["state"] != "draft":
                    raise HTTPException(
                        status_code=409,
                        detail="Published or historical campaign is immutable; create a new draft",
                    )
                data = command.values
                if data is None:
                    raise ValueError("validated_campaign_values_required")
                await self.validate_targets(data=data, now=now)
                if row is None:
                    row = Promotion(active=False)
                    self.session.add(row)
                row.name, row.discount_percent, row.priority = (
                    data.name,
                    Decimal(data.discount_percent),
                    data.priority,
                )
                row.starts_at, row.expires_at = (
                    date.astimezone(timezone.utc).replace(tzinfo=None)
                    for date in (data.starts_at, data.expires_at)
                )
                row.restaurant_id, row.owner_id, row.plan_id = (
                    data.restaurant_id,
                    data.owner_id,
                    data.plan_id,
                )
            elif row is not None and command.operation == "publish":
                if before is None or before["state"] != "draft" or row.starts_at <= now:
                    raise HTTPException(
                        status_code=409, detail="Only a future draft can be published"
                    )
                await self.validate_targets(
                    data=CampaignValues(
                        name=row.name,
                        discount_percent=format(row.discount_percent, ".8f"),
                        starts_at=row.starts_at.replace(tzinfo=timezone.utc),
                        expires_at=row.expires_at.replace(tzinfo=timezone.utc),
                        priority=row.priority,
                        restaurant_id=row.restaurant_id,
                        owner_id=row.owner_id,
                        plan_id=row.plan_id,
                    ),
                    now=now,
                )
                row.active = True
            elif row is not None and command.operation == "deactivate":
                if before is None or before["state"] != "published":
                    raise HTTPException(
                        status_code=409,
                        detail="Only a published campaign can be deactivated",
                    )
                row.active = False
            if row is None:
                raise ValueError("validated_campaign_target_required")
            await self.session.flush()
            result = await self.view(
                row=row, pending_action="pricing." + command.operation
            )
            audit = AdminLog(
                admin_id=admin_id,
                action="pricing." + command.operation,
                resource="saas_promotion",
                resource_id=row.id,
                timestamp=now,
            )
            audit.details = json.dumps(
                {
                    "author_admin_id": admin_id,
                    "recorded_at": now.isoformat() + "Z",
                    "effective_at": (
                        (row.starts_at.isoformat() + "Z")
                        if command.operation != "deactivate"
                        else now.isoformat() + "Z"
                    ),
                    "reason": command.reason,
                    "before": before,
                    "after": result,
                },
                sort_keys=True,
            )
            self.session.add(audit)
        logger.info(
            "SaaS campaign transaction committed",
            extra={
                "admin_id": admin_id,
                "campaign_id": result["id"],
                "operation": command.operation,
            },
        )
        return result
