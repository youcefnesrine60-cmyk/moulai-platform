# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# AUTHORIZED DINING UNIT PRIMITIVES
# Revalidate existing tenant authority and apply explicit branch capabilities.
# ==============================================

"""Shared scoped operations; the facade owns commit and the lifetime of this unit."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND TRUSTED CLOCK CONTRACT
# Reuse the existing tenant authority without changing its closed permissions.
# ==============================================

from collections.abc import Callable
from datetime import (
    date,
    datetime,
    timedelta,
)

from pydantic import JsonValue
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_context import TenantContext
from app.core.security.tenant_types import TenantAccessDenied
from app.models.dining import (
    DiningBlackout,
    DiningCalendar,
    DiningClaim,
    DiningCombination,
    DiningEvent,
    DiningGrant,
    DiningMember,
    DiningOccupation,
    DiningOccupationTable,
    DiningOutbox,
    DiningReceipt,
    DiningRequest,
    DiningRequestTable,
    DiningTable,
)
from app.repositories.dining_repo import DiningRepository
from app.schemas.dining import (
    Capability,
    DiningPolicyInput,
    JsonObject,
    OpeningWindow,
)
from app.services.business.dining.calendar import calendar_covers
from app.services.business.dining.values import (
    DiningError,
    Period,
    utc,
)
from app.services.business.tenant_foundation import TenantAuthorizationService

# ==============================================
# LIVE AUTHORIZED UNIT STATE
# Never expose a unit after its owned transaction has closed.
# ==============================================


class DiningCore:
    """Provide current authority, scoped data and deterministic planning helpers."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        context: TenantContext,
        principal: OIDCPrincipal,
        restaurant_id: int,
        branch_id: int,
        clock: Callable[[], datetime],
    ) -> None:
        """Store only an already-resolved context; no permission is granted here."""
        self.session = session
        self.context = context
        self.principal = principal
        self.repo = DiningRepository(
            session=session, restaurant_id=restaurant_id, branch_id=branch_id
        )
        self.clock = clock
        self.active = True
        self.event_count = 0

    # ==============================================
    # NOW
    # Read trusted server/test time; no request body can override this clock.
    # ==============================================

    def now(self) -> datetime:
        """Read trusted server/test time; no request body can override this clock."""
        return utc(value=self.clock())

    # ==============================================
    # SCOPE
    # Return server-resolved keys for writes, never customer-supplied ownership.
    # ==============================================

    def scope(self) -> dict[str, int]:
        """Return server-resolved keys for writes, never customer-supplied ownership."""
        return {
            "restaurant_id": self.repo.restaurant_id,
            "branch_id": self.repo.branch_id,
        }

    # ==============================================
    # GUARD
    # Revalidate company/restaurant scope and an explicit dining capability.
    # ==============================================

    async def guard(self, *, capability: Capability | str, human: bool = False) -> str:
        """Revalidate company/restaurant scope and an explicit dining capability.

        An owner may configure and inspect their branch, but service, cleaning
        and collection still require separate human grants. Assistant identities
        can never acquire those human capabilities through a role-name claim.
        """
        if not self.active or not self.session.in_transaction():
            raise DiningError(code="dining_unit_closed")
        await TenantAuthorizationService(session=self.session).require_restaurant(
            context=self.context,
            restaurant_id=self.repo.restaurant_id,
            permission="tenant.restaurants.read",
        )
        if capability == "configure":
            assistant_grant = (
                await self.session.execute(
                    self.repo.statement(model=DiningGrant)
                    .where(
                        DiningGrant.membership_id == self.context.membership_id,
                        DiningGrant.actor_kind == "assistant",
                        DiningGrant.active.is_(True),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if self.context.role_code != "owner" or assistant_grant is not None:
                raise TenantAccessDenied("dining_configuration_owner_required")
            return "human"
        if capability == "read" and self.context.role_code == "owner":
            return "human"
        statement = self.repo.statement(model=DiningGrant).where(
            DiningGrant.membership_id == self.context.membership_id,
            DiningGrant.active.is_(True),
        )
        if capability != "read":
            statement = statement.where(DiningGrant.capability == capability)
        grants = (
            (await self.session.execute(statement.with_for_update(read=True)))
            .scalars()
            .all()
        )
        if not grants or (human and any(row.actor_kind != "human" for row in grants)):
            raise TenantAccessDenied("dining_explicit_capability_required")
        kinds = {row.actor_kind for row in grants}
        if len(kinds) != 1:
            raise TenantAccessDenied("dining_actor_kind_ambiguous")
        return next(iter(kinds))

    # ==============================================
    # POLICY
    # Load actual persisted settings; missing rules block only dependent work.
    # ==============================================

    async def policy(self, *, lock: bool = True) -> DiningPolicyInput:
        """Load actual persisted settings; missing rules block only dependent work."""
        row = await self.repo.policy(lock=lock)
        return DiningPolicyInput.model_validate(
            {**row.settings, "timezone": row.timezone}
        )

    # ==============================================
    # EVENT
    # Append a staged event; it becomes durable only with the facade commit.
    # ==============================================

    async def event(
        self,
        *,
        kind: str,
        details: JsonObject,
        request_id: int | None = None,
        author_kind: str = "human",
    ) -> None:
        """Append a staged event; it becomes durable only with the facade commit."""
        self.event_count += 1
        await self.repo.persist(
            record=DiningEvent(
                **self.scope(),
                request_id=request_id,
                kind=kind,
                author={
                    "kind": author_kind,
                    "identity_id": self.context.identity_id,
                    "membership_id": self.context.membership_id,
                },
                details=details,
                occurred_at=self.now(),
            )
        )

    # ==============================================
    # QUEUE
    # Create at most one staged delivery job; do not contact any transport.
    # ==============================================

    async def queue(
        self,
        *,
        request_id: int | None,
        event_key: str,
        target: str,
        payload: JsonObject,
        due_at: datetime,
    ) -> None:
        """Create at most one staged delivery job; do not contact any transport."""
        previous = (
            await self.session.execute(
                self.repo.statement(model=DiningOutbox).where(
                    DiningOutbox.event_key == event_key, DiningOutbox.target == target
                )
            )
        ).scalar_one_or_none()
        if previous is None:
            await self.repo.persist(
                record=DiningOutbox(
                    **self.scope(),
                    request_id=request_id,
                    event_key=event_key,
                    target=target,
                    payload=payload,
                    due_at=due_at,
                    status="pending",
                    attempts=0,
                )
            )

    # ==============================================
    # TABLES
    # Lock a complete sorted table set and reject a foreign member uniformly.
    # ==============================================

    async def tables(
        self, *, identifiers: tuple[int, ...], lock: bool = True
    ) -> tuple[DiningTable, ...]:
        """Lock a complete sorted table set and reject a foreign member uniformly."""
        if (
            not identifiers
            or len(set(identifiers)) != len(identifiers)
            or any(type(x) is not int or x <= 0 for x in identifiers)
        ):
            raise DiningError(code="dining_table_set_invalid")
        statement = (
            self.repo.statement(model=DiningTable)
            .where(DiningTable.id.in_(identifiers))
            .order_by(DiningTable.id)
            .execution_options(populate_existing=True)
        )
        if lock:
            statement = statement.with_for_update()
        rows = tuple((await self.session.execute(statement)).scalars())
        if len(rows) != len(identifiers):
            raise DiningError(code="dining_resource_unavailable")
        return rows

    # ==============================================
    # SELECTED
    # Read the selected resource set inside this exact restaurant and branch.
    # ==============================================

    async def selected(self, *, request_id: int) -> tuple[int, ...]:
        """Read the selected resource set inside this exact restaurant and branch."""
        rows = (
            await self.session.execute(
                self.repo.statement(model=DiningRequestTable)
                .where(DiningRequestTable.request_id == request_id)
                .order_by(DiningRequestTable.table_id)
            )
        ).scalars()
        return tuple(row.table_id for row in rows)

    # ==============================================
    # CAPACITY
    # Return an explicit tariff reference for a valid single table or grouping.
    # ==============================================

    async def capacity(
        self, *, tables: tuple[DiningTable, ...], party_size: int
    ) -> str:
        """Return an explicit tariff reference for a valid single table or grouping."""
        if len(tables) == 1:
            row = tables[0]
            if not row.min_capacity <= party_size <= row.max_capacity:
                raise DiningError(code="dining_capacity_exceeded")
            return row.pricing_ref
        groups = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningCombination).where(
                        DiningCombination.active.is_(True)
                    )
                )
            )
            .scalars()
            .all()
        )
        matching: list[DiningCombination] = []
        identifiers = {row.id for row in tables}
        for group in groups:
            members = (
                (
                    await self.session.execute(
                        self.repo.statement(model=DiningMember).where(
                            DiningMember.combination_id == group.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            if (
                {row.table_id for row in members} == identifiers
                and group.min_capacity <= party_size <= group.max_capacity
            ):
                matching.append(group)
        if len(matching) != 1:
            raise DiningError(code="dining_explicit_combination_required")
        return matching[0].pricing_ref

    # ==============================================
    # REQUEST
    # Lock and refresh only the scoped request; do not trust cached status.
    # ==============================================

    async def request(self, *, identifier: int) -> DiningRequest:
        """Lock and refresh only the scoped request; do not trust cached status."""
        return await self.repo.one(
            model=DiningRequest, identifier=identifier, lock=True
        )

    # ==============================================
    # ASSERT UNPAID
    # Received funds require an approved post-payment change workflow.
    # ==============================================

    async def assert_unpaid(self, *, request_id: int) -> None:
        """Received funds require an approved post-payment change workflow."""
        existing = (
            await self.session.execute(
                self.repo.statement(model=DiningReceipt)
                .where(DiningReceipt.request_id == request_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DiningError(code="dining_post_payment_change_requires_manual_review")

    # ==============================================
    # EXPIRE HOLDS
    # Release expired claims while preserving requests, receipts and history.
    # ==============================================

    async def expire_holds(self) -> None:
        """Release expired claims while preserving requests, receipts and history."""
        claims = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningClaim)
                    .where(
                        DiningClaim.kind == "hold",
                        DiningClaim.active.is_(True),
                        DiningClaim.expires_at <= self.now(),
                    )
                    .order_by(DiningClaim.id)
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        request_ids: set[int] = set()
        for claim in claims:
            claim.active = False
            if claim.request_id is not None:
                request_ids.add(claim.request_id)
        await self.session.flush()
        for identifier in sorted(request_ids):
            request = await self.request(identifier=identifier)
            paid = (
                await self.session.execute(
                    self.repo.statement(model=DiningReceipt)
                    .where(DiningReceipt.request_id == identifier)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if request.status == "held":
                request.status = "manual_review" if paid else "pending"
            await self.session.flush()
            await self.event(
                kind="hold.expired",
                request_id=identifier,
                details={"money_facts_retained": paid is not None},
                author_kind="system",
            )

    # ==============================================
    # EXPANDED
    # Include the configured preparation and cleaning margins exactly once.
    # ==============================================

    async def expanded(self, *, period: Period) -> Period:
        """Include the configured preparation and cleaning margins exactly once."""
        policy = await self.policy()
        return Period(
            start=period.start - timedelta(seconds=policy.preparation_seconds),
            end=period.end + timedelta(seconds=policy.cleaning_seconds),
        )

    # ==============================================
    # AVAILABILITY
    # Check the complete expanded interval, capacity, schedule and physical facts.
    # ==============================================

    async def availability(
        self,
        *,
        identifiers: tuple[int, ...],
        period: Period,
        party_size: int,
        ignore_request: int | None = None,
    ) -> tuple[DiningTable, ...]:
        """Check the complete expanded interval, capacity, schedule and physical facts.

        Future planning may rely on a forecast of cleaning completion, but final
        human authority is checked separately and installation still requires
        actual physical vacancy. Elapsed expected ends never update table state.
        """
        policy = await self.policy()
        await self.expire_holds()
        rows = await self.tables(identifiers=identifiers)
        await self.capacity(tables=rows, party_size=party_size)
        expanded = await self.expanded(period=period)
        calendar = (
            (await self.session.execute(self.repo.statement(model=DiningCalendar)))
            .scalars()
            .all()
        )
        weekly: dict[int, tuple[OpeningWindow, ...]] = {}
        dated: dict[date, tuple[OpeningWindow, ...]] = {}
        for entry in calendar:
            windows = tuple(
                OpeningWindow.model_validate(window) for window in entry.windows
            )
            if entry.weekday is not None:
                weekly[entry.weekday] = windows
            elif entry.service_date is not None:
                dated[entry.service_date] = windows
        if not calendar_covers(
            period=expanded, timezone_name=policy.timezone, weekly=weekly, dated=dated
        ):
            raise DiningError(code="dining_outside_opening_hours")
        claims = self.repo.statement(model=DiningClaim).where(
            DiningClaim.table_id.in_(identifiers),
            DiningClaim.active.is_(True),
            DiningClaim.starts_at < expanded.end,
            DiningClaim.ends_at > expanded.start,
        )
        if ignore_request is not None:
            claims = claims.where(
                or_(
                    DiningClaim.request_id.is_(None),
                    DiningClaim.request_id != ignore_request,
                )
            )
        conflict = (await self.session.execute(claims)).scalars().first()
        if conflict is not None:
            raise DiningError(code="dining_period_unavailable")
        zones = {row.zone_id for row in rows}
        blackout = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningBlackout).where(
                        DiningBlackout.active.is_(True),
                        DiningBlackout.starts_at < expanded.end,
                        DiningBlackout.ends_at > expanded.start,
                        or_(
                            DiningBlackout.table_id.in_(identifiers),
                            DiningBlackout.zone_id.in_(zones),
                            (
                                DiningBlackout.table_id.is_(None)
                                & DiningBlackout.zone_id.is_(None)
                            ),
                        ),
                    )
                )
            )
            .scalars()
            .first()
        )
        if blackout is not None:
            raise DiningError(code="dining_period_blocked")
        for row in rows:
            if not row.in_service or row.physical_state in {
                "maintenance",
                "out_of_service",
            }:
                raise DiningError(code="dining_table_not_in_service")
            if row.physical_state != "available":
                if period.start <= self.now():
                    raise DiningError(code="dining_physical_table_not_available")
                occupation = (
                    await self.session.execute(
                        self.repo.statement(model=DiningOccupation)
                        .join(
                            DiningOccupationTable,
                            DiningOccupationTable.occupation_id == DiningOccupation.id,
                        )
                        .where(
                            DiningOccupationTable.restaurant_id
                            == self.repo.restaurant_id,
                            DiningOccupationTable.branch_id == self.repo.branch_id,
                            DiningOccupationTable.table_id == row.id,
                            DiningOccupationTable.active.is_(True),
                        )
                    )
                ).scalar_one_or_none()
                if (
                    occupation is None
                    or occupation.cleaning_expected_end > expanded.start
                ):
                    raise DiningError(code="dining_cleaning_forecast_not_compatible")
        return rows

    # ==============================================
    # FUTURE CONFLICTS
    # Return scoped affected requests without deleting or silently cancelling them.
    # ==============================================

    async def future_conflicts(
        self, *, table_ids: tuple[int, ...], period: Period | None = None
    ) -> tuple[int, ...]:
        """Return scoped affected requests without deleting or silently cancelling them."""
        statement = self.repo.statement(model=DiningClaim).where(
            DiningClaim.table_id.in_(table_ids),
            DiningClaim.active.is_(True),
            DiningClaim.ends_at > self.now(),
            DiningClaim.request_id.is_not(None),
        )
        if period is not None:
            statement = statement.where(
                DiningClaim.starts_at < period.end, DiningClaim.ends_at > period.start
            )
        rows = (await self.session.execute(statement)).scalars()
        return tuple(
            sorted({row.request_id for row in rows if row.request_id is not None})
        )

    # ==============================================
    # ALERT
    # Queue configured service/escalation recipients with stable delivery keys.
    # ==============================================

    async def alert(
        self, *, request_id: int | None, event_key: str, details: JsonObject
    ) -> None:
        """Queue configured service/escalation recipients with stable delivery keys."""
        policy = await self.policy()
        payload: dict[str, JsonValue] = {
            "kind": event_key,
            "request_id": request_id,
            **details,
        }
        for member in sorted(
            {*policy.service_recipients, *policy.escalation_recipients}
        ):
            await self.queue(
                request_id=request_id,
                event_key=f"{event_key}:{request_id}",
                target=f"membership:{member}",
                payload=payload,
                due_at=self.now(),
            )

    # ==============================================
    # SCAN OCCUPANCY DELAYS
    # Queue configured actual-occupation/cleaning delays without freeing a table.
    # ==============================================

    async def scan_occupancy_delays(self) -> tuple[int, ...]:
        """Queue configured actual-occupation/cleaning delays without freeing a table."""
        try:
            await self.guard(capability="service", human=True)
        except PermissionError:
            await self.guard(capability="assistant")
        policy = await self.policy()
        rows = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningOccupation)
                    .where(
                        DiningOccupation.status.in_(("occupied", "dirty", "cleaning"))
                    )
                    .order_by(DiningOccupation.id)
                    .with_for_update()
                )
            ).scalars()
        )
        delayed: list[int] = []
        for row in rows:
            expected = (
                row.expected_end
                if row.status == "occupied"
                else row.cleaning_expected_end
            )
            for offset in policy.alert_offsets_seconds:
                if self.now() >= expected + timedelta(seconds=offset):
                    await self.alert(
                        request_id=row.request_id,
                        event_key=f"occupation.delay:{row.id}:{expected.isoformat()}:{offset}",
                        details={
                            "occupation_id": row.id,
                            "physical_state_not_released": True,
                            "expected_end": expected.isoformat(),
                            "observed_state": row.status,
                        },
                    )
                    delayed.append(row.id)
        return tuple(sorted(set(delayed)))
