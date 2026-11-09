# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXACT RESTAURANT ADVANCE QUOTATIONS
# Freeze applicable rates and bind each party's consent to one proposal version.
# ==============================================

"""No SaaS billing reuse, float pricing, implicit conversion or food surcharge."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND IMMUTABLE PRICING SNAPSHOTS
# Reuse catalogue product identity while requiring explicit Decimal special rates.
# ==============================================

from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_

from app.models.dining import (
    DiningAcceptance,
    DiningQuote,
    DiningReference,
    DiningRequest,
    DiningTariff,
)
from app.models.product import Product
from app.repositories.subscription_queries import base_select
from app.schemas.dining import JsonObject
from app.services.business.dining.core import DiningCore
from app.services.business.dining.values import (
    DiningError,
    Period,
    content_digest,
    exact_product,
    exact_sum,
    final_amount,
    utc,
)

# ==============================================
# QUOTATION AND RESTAURANT CONSENT
# Customer consent is a separate authenticated-customer transaction boundary.
# ==============================================


class DiningPricing(DiningCore):
    """Prepare exact advance components and retain immutable version evidence."""

    async def _tariff(
        self, *, reference: str, component: str, currency: str, period: Period
    ) -> DiningTariff:
        """Require one currency rate covering the whole service interval.

        A rate boundary inside the requested period is not silently split or
        converted. The owner must supply an applicable complete-period version.
        """
        records = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningTariff).where(
                        DiningTariff.reference == reference,
                        DiningTariff.component == component,
                        DiningTariff.currency == currency,
                        DiningTariff.valid_from <= period.start,
                        or_(
                            DiningTariff.valid_until.is_(None),
                            DiningTariff.valid_until >= period.end,
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        if len(records) != 1:
            raise DiningError(code="dining_exact_currency_whole_period_tariff_required")
        return records[0]

    # ==============================================
    # CREATE QUOTE
    # Calculate and freeze a proposal without inventing a tariff or validity.
    # ==============================================

    async def create_quote(
        self, *, request_id: int, currency: str, expires_at: datetime
    ) -> int:
        """Calculate and freeze a proposal without inventing a tariff or validity."""
        # Service or explicitly granted assistant collection authority may quote;
        # neither operation certifies payment receipt or physical availability.
        try:
            actor = await self.guard(capability="service", human=True)
        except PermissionError:
            actor = await self.guard(capability="assistant")
        policy = await self.policy()
        request = await self.request(identifier=request_id)
        await self.assert_unpaid(request_id=request_id)
        if request.status not in {"pending", "held"}:
            raise DiningError(code="dining_quote_request_state_invalid")
        expires = utc(value=expires_at)
        if expires <= self.now() or currency not in policy.currencies:
            raise DiningError(code="dining_quote_validity_or_currency_invalid")
        identifiers = await self.selected(request_id=request_id)
        tables = await self.tables(identifiers=identifiers)
        reference = await self.capacity(tables=tables, party_size=request.party_size)
        period = Period(start=request.starts_at, end=request.ends_at)
        components: list[JsonObject] = []

        # ==============================================
        # EXACT COMPONENT ACCUMULATOR
        # Preserve unrounded products as decimal strings in the frozen snapshot.
        # ==============================================

        def component(
            *, tariff: DiningTariff, quantity: Decimal, details: JsonObject
        ) -> Decimal:
            """Record the actual tariff version and its unrounded quantity product."""
            amount = exact_product(left=tariff.unit_price, right=quantity)
            components.append(
                {
                    "kind": tariff.component,
                    "currency_precision": policy.currencies[currency],
                    "tariff_id": tariff.id,
                    "reference": tariff.reference,
                    "unit": tariff.unit,
                    "rate": str(tariff.unit_price),
                    "quantity": str(quantity),
                    "amount": str(amount),
                    **details,
                }
            )
            return amount

        table_rate = await self._tariff(
            reference=reference, component="table", currency=currency, period=period
        )
        amounts = [
            component(
                tariff=table_rate,
                quantity=period.hours(),
                details={
                    "table_ids": list(identifiers),
                    "starts_at": period.start.isoformat(),
                    "ends_at": period.end.isoformat(),
                    "party_size": request.party_size,
                },
            )
        ]
        if request.preparation:
            if request.event_id is None:
                raise DiningError(code="dining_preparation_event_required")
            event = await self.repo.one(
                model=DiningReference, identifier=request.event_id
            )
            if not event.active or event.kind != "event" or not event.pricing_ref:
                raise DiningError(code="dining_event_tariff_reference_required")
            rate = await self._tariff(
                reference=event.pricing_ref,
                component="preparation",
                currency=currency,
                period=period,
            )
            quantity = {
                "flat": Decimal(1),
                "per_person": Decimal(request.party_size),
                "per_hour": period.hours(),
            }[rate.unit]
            amounts.append(
                component(
                    tariff=rate, quantity=quantity, details={"event_id": event.id}
                )
            )
        for item in request.menu:
            product_id = item["product_id"]
            product = (
                await self.session.execute(
                    base_select(Product)
                    .with_only_columns(Product.id, Product.name)
                    .where(
                        Product.id == product_id,
                        Product.restaurant_id == self.repo.restaurant_id,
                        Product.is_available.is_(True),
                    )
                )
            ).one_or_none()
            if product is None:
                raise DiningError(code="dining_menu_product_unavailable")
            rate = await self._tariff(
                reference=f"product:{product.id}",
                component="menu",
                currency=currency,
                period=period,
            )
            amounts.append(
                component(
                    tariff=rate,
                    quantity=Decimal(str(item["quantity"])),
                    details={"product_id": product.id, "description": product.name},
                )
            )
        previous = (
            await self.session.execute(
                self.repo.statement(model=DiningQuote)
                .where(DiningQuote.request_id == request_id)
                .order_by(DiningQuote.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        version = 1 if previous is None else previous.version + 1
        amount = final_amount(
            value=exact_sum(values=tuple(amounts)),
            precision=policy.currencies[currency],
        )
        menu_digest = content_digest(value=request.menu)
        digest = content_digest(
            value={
                "request_id": request_id,
                "version": version,
                "currency": currency,
                "amount": str(amount),
                "components": components,
                "terms": policy.terms,
                "expires_at": expires.isoformat(),
                "menu_digest": menu_digest,
            }
        )
        quote = await self.repo.persist(
            record=DiningQuote(
                **self.scope(),
                request_id=request_id,
                version=version,
                currency=currency,
                amount=amount,
                components=components,
                terms=policy.terms,
                menu_digest=menu_digest,
                digest=digest,
                expires_at=expires,
            )
        )
        await self.event(
            kind="quote.created",
            request_id=request_id,
            details={"quote_id": quote.id, "version": version, "currency": currency},
            author_kind=actor,
        )
        return quote.id

    # ==============================================
    # QUOTE
    # Require the current immutable quote and the exact matching assignment/menu.
    # ==============================================

    async def quote(
        self, *, identifier: int, request: DiningRequest, require_acceptance: bool
    ) -> DiningQuote:
        """Require the current immutable quote and the exact matching assignment/menu."""
        quote = await self.repo.one(model=DiningQuote, identifier=identifier)
        latest = (
            await self.session.execute(
                self.repo.statement(model=DiningQuote)
                .where(DiningQuote.request_id == request.id)
                .order_by(DiningQuote.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if (
            quote.request_id != request.id
            or latest is None
            or latest.id != quote.id
            or quote.expires_at <= self.now()
        ):
            raise DiningError(code="dining_current_unexpired_quote_required")
        table_line = next(
            (line for line in quote.components if line.get("kind") == "table"), None
        )
        period = Period(start=request.starts_at, end=request.ends_at)
        if (
            table_line is None
            or table_line.get("table_ids")
            != list(await self.selected(request_id=request.id))
            or table_line.get("starts_at") != period.start.isoformat()
            or table_line.get("ends_at") != period.end.isoformat()
            or table_line.get("party_size") != request.party_size
            or quote.menu_digest != content_digest(value=request.menu)
        ):
            raise DiningError(code="dining_quote_content_changed_new_consent_required")
        if require_acceptance:
            acceptances = (
                (
                    await self.session.execute(
                        self.repo.statement(model=DiningAcceptance).where(
                            DiningAcceptance.quote_id == quote.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            parties = {row.party for row in acceptances if row.digest == quote.digest}
            if "customer" not in parties or (
                request.menu and "restaurant" not in parties
            ):
                raise DiningError(code="dining_exact_quote_consents_required")
        return quote

    # ==============================================
    # ACCEPT RESTAURANT QUOTE
    # Record owner or human service approval of this exact special-menu version.
    # ==============================================

    async def accept_restaurant_quote(
        self, *, quote_id: int, expected_digest: str
    ) -> int:
        """Record owner or human service approval of this exact special-menu version."""
        if self.context.role_code == "owner":
            await self.guard(capability="configure")
        else:
            await self.guard(capability="service", human=True)
        await self.policy()
        selected = await self.repo.one(model=DiningQuote, identifier=quote_id)
        request = await self.request(identifier=selected.request_id)
        quote = await self.quote(
            identifier=quote_id, request=request, require_acceptance=False
        )
        if quote.digest != expected_digest:
            raise DiningError(code="dining_quote_digest_mismatch")
        previous = (
            await self.session.execute(
                self.repo.statement(model=DiningAcceptance).where(
                    DiningAcceptance.quote_id == quote_id,
                    DiningAcceptance.party == "restaurant",
                )
            )
        ).scalar_one_or_none()
        if previous is not None:
            return previous.id
        row = await self.repo.persist(
            record=DiningAcceptance(
                **self.scope(),
                quote_id=quote_id,
                party="restaurant",
                digest=quote.digest,
                author={
                    "kind": "human",
                    "membership_id": self.context.membership_id,
                    "identity_id": self.context.identity_id,
                },
            )
        )
        await self.event(
            kind="quote.restaurant_accepted",
            request_id=request.id,
            details={"quote_id": quote_id},
        )
        return row.id
