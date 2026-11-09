# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DINING REQUESTS AND HUMAN AVAILABILITY EVIDENCE
# Collect demands without certifying space and retain distinct human approvals.
# ==============================================

"""Requests, criteria and prior confirmations; no payment or model call occurs."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND STABLE SYNTHETIC-SAFE REFERENCES
# Identity comes from a verified principal, never a supplied role or owner ID.
# ==============================================

import secrets
from datetime import timedelta

from sqlalchemy import delete

from app.core.security.oidc import OIDCPrincipal
from app.models.dining import (
    DiningConfirmation,
    DiningReference,
    DiningRequest,
    DiningRequestTable,
    DiningTable,
    DiningTrait,
)
from app.models.product import Product
from app.repositories.subscription_queries import base_select
from app.repositories.tenant_repo import (
    IdentityRepository,
    TenantRepository,
)
from app.schemas.dining import RequestInput
from app.services.business.dining.core import DiningCore
from app.services.business.dining.values import (
    DiningError,
    Period,
    elapsed_period,
)

# ==============================================
# REQUEST COLLECTION AND HUMAN EVIDENCE
# An assistant may collect and transmit, but cannot issue a human confirmation.
# ==============================================


class DiningRequests(DiningCore):
    """Persist requests and human evidence while preserving authority separation."""

    async def _operator(self) -> str:
        """Require explicit assistant or human service authority for collection."""
        try:
            return await self.guard(capability="service", human=True)
        except PermissionError:
            await self.guard(capability="assistant")
            return "assistant"

    # ==============================================
    # CREATE REQUEST
    # Record an identified customer's demand without confirming availability.
    # ==============================================

    async def create_request(
        self, *, data: RequestInput, customer: OIDCPrincipal
    ) -> int:
        """Record an identified customer's demand without confirming availability."""
        actor_kind = await self._operator()
        policy = await self.policy()
        if (
            not isinstance(customer, OIDCPrincipal)
            or not customer.subject
            or not customer.issuer
        ):
            raise DiningError(code="dining_verified_customer_identity_required")
        if data.starts_at <= self.now():
            raise DiningError(code="dining_request_start_must_be_future")
        period = elapsed_period(start=data.starts_at, seconds=data.duration_seconds)
        criteria = data.criteria
        allowed_criteria = {
            "zone_id",
            "category_id",
            "view_ids",
            "proximity_ids",
            "feature_ids",
        }
        if set(criteria) - allowed_criteria:
            raise DiningError(code="dining_criteria_unsupported")
        for name, value in criteria.items():
            ids = value if name.endswith("_ids") else [value]
            if not isinstance(ids, list) or any(
                type(identifier) is not int or identifier <= 0 for identifier in ids
            ):
                raise DiningError(code="dining_criteria_invalid")
            expected = {
                "view_ids": "view",
                "proximity_ids": "proximity",
                "feature_ids": "feature",
                "zone_id": "zone",
                "category_id": "category",
            }[name]
            for identifier in ids:
                reference = await self.repo.one(
                    model=DiningReference, identifier=identifier
                )
                if not reference.active or reference.kind != expected:
                    raise DiningError(code="dining_criteria_reference_invalid")
        if data.event_id is not None:
            event = await self.repo.one(model=DiningReference, identifier=data.event_id)
            if event.kind != "event" or not event.active:
                raise DiningError(code="dining_event_reference_invalid")
        for line in data.menu:
            product = (
                await self.session.execute(
                    base_select(Product)
                    .with_only_columns(Product.id)
                    .where(
                        Product.id == line.product_id,
                        Product.restaurant_id == self.repo.restaurant_id,
                        Product.is_available.is_(True),
                    )
                )
            ).scalar_one_or_none()
            if product is None:
                raise DiningError(code="dining_menu_product_unavailable")
        if data.table_ids:
            tables = await self.tables(identifiers=data.table_ids)
            await self.capacity(tables=tables, party_size=data.party_size)
        request = await self.repo.persist(
            record=DiningRequest(
                **self.scope(),
                reference=secrets.token_hex(16),
                customer_issuer=customer.issuer,
                customer_subject=customer.subject,
                customer_name=data.customer_name,
                contact=data.contact,
                starts_at=period.start,
                ends_at=period.end,
                party_size=data.party_size,
                event_id=data.event_id,
                preparation=data.preparation,
                criteria=criteria,
                menu=[line.model_dump(mode="json") for line in data.menu],
                status="pending",
            )
        )
        for identifier in data.table_ids:
            await self.repo.persist(
                record=DiningRequestTable(
                    **self.scope(), request_id=request.id, table_id=identifier
                )
            )
        await self.event(
            kind="request.created",
            request_id=request.id,
            details={
                "table_ids": list(data.table_ids),
                "availability_confirmed": False,
            },
            author_kind=actor_kind,
        )
        for recipient in policy.service_recipients:
            await self.queue(
                request_id=request.id,
                event_key=f"request.transmit:{request.id}",
                target=f"membership:{recipient}",
                payload={"kind": "request.transmit", "request_id": request.id},
                due_at=self.now(),
            )
        return request.id

    # ==============================================
    # MATCHING TABLES
    # Return descriptive matches, not a silent choice or human vacancy approval.
    # ==============================================

    async def matching_tables(self, *, request_id: int) -> tuple[int, ...]:
        """Return descriptive matches, not a silent choice or human vacancy approval."""
        await self.guard(capability="read")
        request = await self.request(identifier=request_id)
        statement = self.repo.statement(model=DiningTable).where(
            DiningTable.in_service.is_(True),
            DiningTable.min_capacity <= request.party_size,
            DiningTable.max_capacity >= request.party_size,
        )
        for key in ("zone_id", "category_id"):
            if key in request.criteria:
                statement = statement.where(
                    getattr(DiningTable, key) == request.criteria[key]
                )
        candidates = tuple(
            (
                await self.session.execute(
                    statement.order_by(DiningTable.id).limit(250)
                )
            ).scalars()
        )
        result: list[int] = []
        for table in candidates:
            traits = (
                (
                    await self.session.execute(
                        self.repo.statement(model=DiningTrait).where(
                            DiningTrait.table_id == table.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            if all(
                set(request.criteria.get(f"{kind}_ids", []))
                <= {row.reference_id for row in traits if row.kind == kind}
                for kind in ("view", "proximity", "feature")
            ):
                result.append(table.id)
        return tuple(result)

    # ==============================================
    # SELECT TABLES
    # Select an explicit assignment before money; never move a paid reservation.
    # ==============================================

    async def select_tables(
        self, *, request_id: int, table_ids: tuple[int, ...]
    ) -> None:
        """Select an explicit assignment before money; never move a paid reservation."""
        actor = await self._operator()
        await self.policy()
        request = await self.request(identifier=request_id)
        await self.assert_unpaid(request_id=request_id)
        if request.status != "pending":
            raise DiningError(code="dining_selection_requires_pending_request")
        tables = await self.tables(identifiers=table_ids)
        await self.capacity(tables=tables, party_size=request.party_size)
        await self.session.execute(
            delete(DiningRequestTable).where(
                DiningRequestTable.restaurant_id == self.repo.restaurant_id,
                DiningRequestTable.branch_id == self.repo.branch_id,
                DiningRequestTable.request_id == request_id,
            )
        )
        for identifier in table_ids:
            await self.repo.persist(
                record=DiningRequestTable(
                    **self.scope(), request_id=request_id, table_id=identifier
                )
            )
        await self.event(
            kind="request.tables_selected",
            request_id=request_id,
            details={"table_ids": list(table_ids), "new_quote_required": True},
            author_kind=actor,
        )

    # ==============================================
    # CONFIRM AVAILABILITY
    # Record only an explicitly habilitated human's bounded availability proof.
    # ==============================================

    async def confirm_availability(
        self,
        *,
        table_ids: tuple[int, ...],
        period: Period,
        request_id: int | None = None,
    ) -> int:
        """Record only an explicitly habilitated human's bounded availability proof."""
        await self.guard(capability="service", human=True)
        policy = await self.policy()
        tables = await self.tables(identifiers=table_ids)
        if request_id is not None:
            request = await self.request(identifier=request_id)
            if set(table_ids) != set(
                await self.selected(request_id=request_id)
            ) or not period.contains(
                other=await self.expanded(
                    period=Period(start=request.starts_at, end=request.ends_at)
                )
            ):
                raise DiningError(code="dining_human_confirmation_scope_mismatch")
        if period.end <= self.now():
            raise DiningError(code="dining_human_confirmation_past_period")
        confirmation = await self.repo.persist(
            record=DiningConfirmation(
                **self.scope(),
                request_id=request_id,
                starts_at=period.start,
                ends_at=period.end,
                valid_until=self.now() + timedelta(seconds=policy.confirmation_seconds),
                table_versions={str(table.id): table.revision for table in tables},
                membership_id=self.context.membership_id,
                origin="human",
            )
        )
        await self.event(
            kind="availability.human_confirmed",
            request_id=request_id,
            details={"confirmation_id": confirmation.id, "table_ids": list(table_ids)},
        )
        return confirmation.id

    # ==============================================
    # HUMAN CONFIRMATION
    # Require full period coverage, current table revisions and unexpired proof.
    # ==============================================

    async def human_confirmation(
        self, *, request: DiningRequest, tables: tuple[DiningTable, ...]
    ) -> DiningConfirmation:
        """Require full period coverage, current table revisions and unexpired proof."""
        period = await self.expanded(
            period=Period(start=request.starts_at, end=request.ends_at)
        )
        candidates = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningConfirmation)
                    .where(
                        DiningConfirmation.valid_until > self.now(),
                        DiningConfirmation.starts_at <= period.start,
                        DiningConfirmation.ends_at >= period.end,
                    )
                    .order_by(DiningConfirmation.id.desc())
                )
            )
            .scalars()
            .all()
        )
        for row in candidates:
            if row.request_id not in (None, request.id):
                continue
            if all(
                row.table_versions.get(str(table.id)) == table.revision
                for table in tables
            ):
                authority = TenantRepository(session=self.session)
                member = await authority.lock_membership(
                    organization_id=self.context.organization_id,
                    membership_id=row.membership_id,
                )
                if (
                    member is None
                    or member.status != "active"
                    or member.accepted_at is None
                    or member.activated_at is None
                ):
                    continue
                identity = await IdentityRepository(session=self.session).lock(
                    identity_id=member.identity_id
                )
                if identity is None or identity.status != "active":
                    continue
                permitted = await authority.grants(
                    organization_id=self.context.organization_id,
                    membership_id=member.id,
                )
                if (
                    member.access_mode == "explicit-grants"
                    and self.repo.restaurant_id not in permitted
                ):
                    continue
                from app.models.dining import DiningGrant

                grant = (
                    await self.session.execute(
                        self.repo.statement(model=DiningGrant)
                        .where(
                            DiningGrant.membership_id == member.id,
                            DiningGrant.capability == "service",
                            DiningGrant.actor_kind == "human",
                            DiningGrant.active.is_(True),
                        )
                        .with_for_update(read=True)
                    )
                ).scalar_one_or_none()
                if grant is not None:
                    return row
        raise DiningError(code="dining_current_human_confirmation_required")

    # ==============================================
    # REPORT SIGNAL
    # Retain departure/cancellation/late signals without promoting them to approval.
    # ==============================================

    async def report_signal(
        self,
        *,
        request_id: int,
        kind: str,
        customer: OIDCPrincipal | None = None,
        reason: str | None = None,
    ) -> None:
        """Retain departure/cancellation/late signals without promoting them to approval."""
        actor = await self._operator()
        request = await self.request(identifier=request_id)
        if kind not in {
            "customer_departure",
            "customer_cancellation_requested",
            "late_arrival",
            "expected_end_passed",
        }:
            raise DiningError(code="dining_signal_kind_invalid")
        if customer is not None and (
            request.customer_issuer,
            request.customer_subject,
        ) != (customer.issuer, customer.subject):
            raise DiningError(code="dining_resource_unavailable")
        if kind == "customer_cancellation_requested":
            from app.services.business.dining.cancellation import queue_cancellation_signal  # fmt: skip # isort: skip

            await queue_cancellation_signal(
                session=self.session,
                repo=self.repo,
                request_id=request_id,
                origin="customer" if customer is not None else actor,
                reason=reason
                or "Cancellation request forwarded by authorized operator",
                author={"kind": actor, "membership_id": self.context.membership_id},
                at=self.now(),
            )
            return
        await self.event(
            kind=f"signal.{kind}",
            request_id=request_id,
            details={"does_not_confirm_or_cancel": True},
            author_kind="customer" if customer is not None else actor,
        )
        await self.alert(
            request_id=request_id,
            event_key=f"signal.{kind}",
            details={"manual_decision_required": True},
        )
