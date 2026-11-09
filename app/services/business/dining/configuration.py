# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNER DINING CONFIGURATION OPERATIONS
# Persist branch policy, references and tables while surfacing future conflicts.
# ==============================================

"""No commercial seed prices, implicit staff grants, or silent booking deletion."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND SCOPED CONFIGURATION CONTRACTS
# Reuse tenant membership records without modifying K9/K10 policy templates.
# ==============================================

from datetime import date
from typing import Literal

from sqlalchemy import delete

from app.core.security.tenant_types import TenantAccessDenied
from app.models.dining import (
    DiningBlackout,
    DiningCalendar,
    DiningCombination,
    DiningGrant,
    DiningMember,
    DiningPolicy,
    DiningReference,
    DiningTable,
    DiningTrait,
)
from app.repositories.tenant_repo import TenantRepository
from app.schemas.dining import (
    Capability,
    CombinationInput,
    DiningPolicyInput,
    OpeningWindow,
    ReferenceInput,
    TableInput,
    TariffInput,
)
from app.services.business.dining.core import DiningCore
from app.services.business.dining.values import (
    DiningError,
    Period,
)

# ==============================================
# CONFIGURATION AND CONFLICT ACKNOWLEDGEMENT
# Apply only owner-authorized changes and retain every affected request.
# ==============================================


class DiningConfiguration(DiningCore):
    """Owner configuration; human service/cleaning/collection remain independent."""

    async def configure(self, *, data: DiningPolicyInput) -> int:
        """Set explicit settings; reject changes while future claims need review."""
        await self.guard(capability="configure")
        current = (
            await self.session.execute(
                self.repo.statement(model=DiningPolicy).with_for_update()
            )
        ).scalar_one_or_none()
        if current is not None:
            table_ids = tuple(
                (
                    await self.session.execute(self.repo.statement(model=DiningTable))
                ).scalars()
            )
            conflicts = (
                await self.future_conflicts(
                    table_ids=tuple(row.id for row in table_ids)
                )
                if table_ids
                else ()
            )
            if conflicts:
                raise DiningError(
                    code="dining_policy_future_claims_require_review",
                    conflicts=conflicts,
                )
            current.timezone = data.timezone
            current.settings = data.model_dump(mode="json", exclude={"timezone"})
            await self.session.flush()
            identifier = current.id
        else:
            row = await self.repo.persist(
                record=DiningPolicy(
                    **self.scope(),
                    timezone=data.timezone,
                    settings=data.model_dump(mode="json", exclude={"timezone"}),
                )
            )
            identifier = row.id
        repo = TenantRepository(session=self.session)
        for recipient in {*data.service_recipients, *data.escalation_recipients}:
            member = await repo.lock_membership(
                organization_id=self.context.organization_id, membership_id=recipient
            )
            if (
                member is None
                or member.status != "active"
                or member.accepted_at is None
                or member.activated_at is None
            ):
                raise DiningError(code="dining_recipient_active_membership_required")
        await self.event(kind="policy.configured", details={"policy_id": identifier})
        return identifier

    # ==============================================
    # GRANT
    # Assign one explicit module capability to an already eligible member.
    # ==============================================

    async def grant(
        self,
        *,
        membership_id: int,
        capability: Capability,
        actor_kind: Literal["human", "assistant"],
        active: bool,
    ) -> int:
        """Assign one explicit module capability to an already eligible member."""
        await self.guard(capability="configure")
        await self.policy()
        repo = TenantRepository(session=self.session)
        member = await repo.lock_membership(
            organization_id=self.context.organization_id, membership_id=membership_id
        )
        if member is None or (
            active
            and (
                member.status != "active"
                or member.accepted_at is None
                or member.activated_at is None
            )
        ):
            raise TenantAccessDenied("dining_member_unavailable")
        grants = await repo.grants(
            organization_id=self.context.organization_id, membership_id=membership_id
        )
        if (
            member.access_mode == "explicit-grants"
            and self.repo.restaurant_id not in grants
        ):
            raise TenantAccessDenied("dining_member_restaurant_unavailable")
        if actor_kind == "assistant" and member.role_code == "owner":
            raise TenantAccessDenied("dining_assistant_owner_identity_forbidden")
        if actor_kind == "assistant" and capability not in {"assistant", "read"}:
            raise TenantAccessDenied("dining_assistant_human_capability_forbidden")
        records = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningGrant)
                    .where(DiningGrant.membership_id == membership_id)
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        if active and any(
            row.active and row.actor_kind != actor_kind and row.capability != capability
            for row in records
        ):
            raise DiningError(code="dining_actor_kind_conflict")
        row = next(
            (record for record in records if record.capability == capability), None
        )
        if row is None:
            row = await self.repo.persist(
                record=DiningGrant(
                    **self.scope(),
                    membership_id=membership_id,
                    capability=capability,
                    actor_kind=actor_kind,
                    active=active,
                    granted_by=self.context.membership_id,
                )
            )
        else:
            row.active, row.actor_kind, row.granted_by = (
                active,
                actor_kind,
                self.context.membership_id,
            )
            await self.session.flush()
        await self.event(
            kind="capability.changed",
            details={
                "membership_id": membership_id,
                "capability": capability,
                "actor_kind": actor_kind,
                "active": active,
            },
        )
        return row.id

    # ==============================================
    # CREATE REFERENCE
    # Store localized reference data with a concrete semantic kind.
    # ==============================================

    async def create_reference(self, *, data: ReferenceInput) -> int:
        """Store localized reference data with a concrete semantic kind."""
        await self.guard(capability="configure")
        await self.policy()
        row = await self.repo.persist(
            record=DiningReference(**self.scope(), **data.model_dump(mode="json"))
        )
        await self.event(
            kind="reference.created",
            details={"reference_id": row.id, "kind": data.kind},
        )
        return row.id

    # ==============================================
    # SAVE CALENDAR
    # Persist a work/rest day or dated override and explicitly surface claims.
    # ==============================================

    async def save_calendar(
        self,
        *,
        weekday: int | None,
        service_date: date | None,
        windows: tuple[OpeningWindow, ...],
        acknowledge_conflicts: bool = False,
    ) -> tuple[int, tuple[int, ...]]:
        """Persist a work/rest day or dated override and explicitly surface claims."""
        await self.guard(capability="configure")
        await self.policy()
        if (weekday is None) == (service_date is None) or (
            weekday is not None and (type(weekday) is not int or not 0 <= weekday <= 6)
        ):
            raise DiningError(code="dining_calendar_target_invalid")
        rows = tuple(
            (
                await self.session.execute(self.repo.statement(model=DiningTable))
            ).scalars()
        )
        conflicts = (
            await self.future_conflicts(table_ids=tuple(row.id for row in rows))
            if rows
            else ()
        )
        if conflicts and not acknowledge_conflicts:
            raise DiningError(
                code="dining_calendar_future_conflicts", conflicts=conflicts
            )
        statement = self.repo.statement(model=DiningCalendar)
        statement = (
            statement.where(DiningCalendar.weekday == weekday)
            if weekday is not None
            else statement.where(DiningCalendar.service_date == service_date)
        )
        row = (
            await self.session.execute(statement.with_for_update())
        ).scalar_one_or_none()
        values = [window.model_dump(mode="json") for window in windows]
        if row is None:
            row = await self.repo.persist(
                record=DiningCalendar(
                    **self.scope(),
                    weekday=weekday,
                    service_date=service_date,
                    windows=values,
                )
            )
        else:
            row.windows = values
        for table in rows:
            table.revision += 1
        await self.session.flush()
        await self.event(
            kind="calendar.changed",
            details={"calendar_id": row.id, "conflicts": list(conflicts)},
        )
        for identifier in conflicts:
            await self.alert(
                request_id=identifier,
                event_key=f"calendar.changed:{row.id}",
                details={"manual_review": True},
            )
        return row.id, conflicts

    # ==============================================
    # TABLE REFERENCES
    # Verify each reference kind, activity and branch before a descriptive write.
    # ==============================================

    async def _table_references(self, *, data: TableInput) -> None:
        """Verify each reference kind, activity and branch before a descriptive write."""
        for kind in ("shape", "category", "zone", "location"):
            row = await self.repo.one(
                model=DiningReference, identifier=getattr(data, f"{kind}_id")
            )
            if row.kind != kind or not row.active:
                raise DiningError(code="dining_reference_kind_or_activity_invalid")
        for identifier in data.trait_ids:
            row = await self.repo.one(model=DiningReference, identifier=identifier)
            if row.kind not in {"view", "proximity", "feature"} or not row.active:
                raise DiningError(code="dining_trait_kind_invalid")

    # ==============================================
    # CREATE TABLE
    # Create a described table with an explicit owner-declared physical state.
    # ==============================================

    async def create_table(
        self,
        *,
        data: TableInput,
        initial_state: Literal["available", "maintenance", "out_of_service"],
    ) -> int:
        """Create a described table with an explicit owner-declared physical state."""
        await self.guard(capability="configure")
        await self.policy()
        await self._table_references(data=data)
        row = await self.repo.persist(
            record=DiningTable(
                **self.scope(),
                **data.model_dump(mode="json", exclude={"trait_ids"}),
                physical_state=initial_state,
                revision=1,
            )
        )
        for identifier in data.trait_ids:
            reference = await self.repo.one(
                model=DiningReference, identifier=identifier
            )
            await self.repo.persist(
                record=DiningTrait(
                    **self.scope(),
                    table_id=row.id,
                    reference_id=identifier,
                    kind=reference.kind,
                )
            )
        await self.event(
            kind="table.created",
            details={"table_id": row.id, "initial_state": initial_state},
        )
        return row.id

    # ==============================================
    # UPDATE TABLE
    # Change description/capacity without altering physical occupation or bookings.
    # ==============================================

    async def update_table(
        self, *, table_id: int, data: TableInput, acknowledge_conflicts: bool = False
    ) -> tuple[int, ...]:
        """Change description/capacity without altering physical occupation or bookings."""
        await self.guard(capability="configure")
        await self.policy()
        await self._table_references(data=data)
        row = await self.repo.one(model=DiningTable, identifier=table_id, lock=True)
        conflicts = await self.future_conflicts(table_ids=(table_id,))
        if conflicts and not acknowledge_conflicts:
            raise DiningError(code="dining_table_future_conflicts", conflicts=conflicts)
        for key, value in data.model_dump(mode="json", exclude={"trait_ids"}).items():
            setattr(row, key, value)
        row.revision += 1
        await self.session.flush()
        await self.session.execute(
            delete(DiningTrait).where(
                DiningTrait.restaurant_id == self.repo.restaurant_id,
                DiningTrait.branch_id == self.repo.branch_id,
                DiningTrait.table_id == table_id,
            )
        )
        for identifier in data.trait_ids:
            reference = await self.repo.one(
                model=DiningReference, identifier=identifier
            )
            await self.repo.persist(
                record=DiningTrait(
                    **self.scope(),
                    table_id=table_id,
                    reference_id=identifier,
                    kind=reference.kind,
                )
            )
        await self.event(
            kind="table.changed",
            details={"table_id": table_id, "conflicts": list(conflicts)},
        )
        for identifier in conflicts:
            await self.alert(
                request_id=identifier,
                event_key=f"table.changed:{table_id}:{row.revision}",
                details={"manual_review": True},
            )
        return conflicts

    # ==============================================
    # CREATE COMBINATION
    # Persist an explicitly authorized physical grouping and its tariff reference.
    # ==============================================

    async def create_combination(self, *, data: CombinationInput) -> int:
        """Persist an explicitly authorized physical grouping and its tariff reference."""
        await self.guard(capability="configure")
        await self.policy()
        tables = await self.tables(identifiers=data.table_ids)
        if data.max_capacity > sum(row.max_capacity for row in tables):
            raise DiningError(code="dining_combination_exceeds_physical_capacity")
        row = await self.repo.persist(
            record=DiningCombination(
                **self.scope(), **data.model_dump(exclude={"table_ids"})
            )
        )
        for table in tables:
            await self.repo.persist(
                record=DiningMember(
                    **self.scope(), combination_id=row.id, table_id=table.id
                )
            )
        await self.event(
            kind="combination.created",
            details={"combination_id": row.id, "table_ids": list(data.table_ids)},
        )
        return row.id

    # ==============================================
    # AMEND EXPLICIT TABLE COMBINATION
    # Retain reservation history, invalidate proofs and require conflict acknowledgement.
    # ==============================================

    async def update_combination(
        self,
        *,
        identifier: int,
        data: CombinationInput,
        acknowledge_conflicts: bool = False,
    ) -> tuple[int, ...]:
        """Replace a scoped grouping after checking capacities and retained reservations.

        The stable identifier and code remain unchanged. All affected table
        revisions advance, so an old human proof cannot silently authorize the
        new arrangement. Confirmed claims are never erased by configuration.
        """
        await self.guard(capability="configure")
        await self.policy()
        row = await self.repo.one(
            model=DiningCombination, identifier=identifier, lock=True
        )
        if row.code != data.code:
            raise DiningError(code="dining_combination_identity_is_retained")
        previous = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningMember).where(
                        DiningMember.combination_id == identifier
                    )
                )
            ).scalars()
        )
        affected_ids = tuple(
            sorted({member.table_id for member in previous} | set(data.table_ids))
        )
        affected = await self.tables(identifiers=affected_ids)
        selected = [table for table in affected if table.id in data.table_ids]
        if data.max_capacity > sum(table.max_capacity for table in selected):
            raise DiningError(code="dining_combination_exceeds_physical_capacity")
        conflicts = await self.future_conflicts(table_ids=affected_ids)
        if conflicts and not acknowledge_conflicts:
            raise DiningError(
                code="dining_combination_future_conflicts", conflicts=conflicts
            )
        for member in previous:
            await self.session.delete(member)
        await self.session.flush()
        for table_id in data.table_ids:
            await self.repo.persist(
                record=DiningMember(
                    **self.scope(), combination_id=identifier, table_id=table_id
                )
            )
        for key, value in data.model_dump(exclude={"table_ids", "code"}).items():
            setattr(row, key, value)
        for table in affected:
            table.revision += 1
        await self.session.flush()
        await self.event(
            kind="combination.updated",
            details={
                "combination_id": identifier,
                "table_ids": list(data.table_ids),
                "conflicts": list(conflicts),
            },
        )
        for request_id in conflicts:
            await self.alert(
                request_id=request_id,
                event_key=f"combination.changed:{identifier}:{affected[0].revision}",
                details={"manual_review": True},
            )
        return conflicts

    # ==============================================
    # CREATE BLACKOUT
    # Block a branch, zone or table and report all retained affected reservations.
    # ==============================================

    async def create_blackout(
        self,
        *,
        period: Period,
        kind: Literal["closure", "maintenance", "preparation", "cleaning"],
        reason: str,
        table_id: int | None,
        zone_id: int | None,
        acknowledge_conflicts: bool = False,
    ) -> tuple[int, tuple[int, ...]]:
        """Block a branch, zone or table and report all retained affected reservations."""
        await self.guard(capability="configure")
        await self.policy()
        if (table_id is not None and zone_id is not None) or not reason.strip():
            raise DiningError(code="dining_blackout_target_invalid")
        statement = self.repo.statement(model=DiningTable)
        if table_id is not None:
            statement = statement.where(DiningTable.id == table_id)
        if zone_id is not None:
            zone = await self.repo.one(model=DiningReference, identifier=zone_id)
            if zone.kind != "zone":
                raise DiningError(code="dining_zone_reference_required")
            statement = statement.where(DiningTable.zone_id == zone_id)
        rows = tuple(
            (
                await self.session.execute(
                    statement.order_by(DiningTable.id).with_for_update()
                )
            ).scalars()
        )
        if table_id is not None and not rows:
            raise DiningError(code="dining_resource_unavailable")
        conflicts = (
            await self.future_conflicts(
                table_ids=tuple(row.id for row in rows), period=period
            )
            if rows
            else ()
        )
        if conflicts and not acknowledge_conflicts:
            raise DiningError(
                code="dining_blackout_future_conflicts", conflicts=conflicts
            )
        row = await self.repo.persist(
            record=DiningBlackout(
                **self.scope(),
                table_id=table_id,
                zone_id=zone_id,
                starts_at=period.start,
                ends_at=period.end,
                kind=kind,
                reason=reason,
                active=True,
            )
        )
        for table in rows:
            table.revision += 1
        await self.session.flush()
        await self.event(
            kind="blackout.created",
            details={"blackout_id": row.id, "conflicts": list(conflicts)},
        )
        for identifier in conflicts:
            await self.alert(
                request_id=identifier,
                event_key=f"blackout:{row.id}",
                details={"manual_review": True},
            )
        return row.id, conflicts

    # ==============================================
    # CREATE TARIFF
    # Append an exact rate; configuration currency and SQL overlap both apply.
    # ==============================================

    async def create_tariff(self, *, data: TariffInput) -> int:
        """Append an exact rate; configuration currency and SQL overlap both apply."""
        from app.models.dining import DiningTariff

        await self.guard(capability="configure")
        policy = await self.policy()
        if data.currency not in policy.currencies:
            raise DiningError(code="dining_currency_configuration_missing")
        row = await self.repo.persist(
            record=DiningTariff(**self.scope(), **data.model_dump())
        )
        await self.event(
            kind="tariff.created",
            details={"tariff_id": row.id, "currency": data.currency},
        )
        return row.id

    # ==============================================
    # UPDATE REFERENCE
    # Amend labels/status without changing reference identity or erasing claims.
    # ==============================================

    async def update_reference(
        self,
        *,
        identifier: int,
        data: ReferenceInput,
        acknowledge_conflicts: bool = False,
    ) -> tuple[int, ...]:
        """Amend labels/status without changing reference identity or erasing claims."""
        await self.guard(capability="configure")
        await self.policy()
        row = await self.repo.one(
            model=DiningReference, identifier=identifier, lock=True
        )
        if (row.kind, row.code) != (data.kind, data.code):
            raise DiningError(code="dining_reference_identity_is_retained")
        tables = tuple(
            (
                await self.session.execute(self.repo.statement(model=DiningTable))
            ).scalars()
        )
        traits = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningTrait).where(
                        DiningTrait.reference_id == identifier
                    )
                )
            ).scalars()
        )
        affected = tuple(
            table
            for table in tables
            if identifier
            in {table.shape_id, table.category_id, table.zone_id, table.location_id}
            or table.id in {trait.table_id for trait in traits}
        )
        conflicts = (
            await self.future_conflicts(table_ids=tuple(table.id for table in affected))
            if affected
            else ()
        )
        if conflicts and not acknowledge_conflicts:
            raise DiningError(
                code="dining_reference_future_conflicts", conflicts=conflicts
            )
        row.labels, row.active, row.pricing_ref = (
            data.labels,
            data.active,
            data.pricing_ref,
        )
        for table in affected:
            table.revision += 1
        await self.session.flush()
        await self.event(
            kind="reference.updated",
            details={"reference_id": identifier, "conflicts": list(conflicts)},
        )
        return conflicts

    # ==============================================
    # CLOSE BLACKOUT
    # Deactivate only a scoped planning block; physical state needs its own action.
    # ==============================================

    async def close_blackout(self, *, identifier: int) -> None:
        """Deactivate only a scoped planning block; physical state needs its own action."""
        await self.guard(capability="configure")
        await self.policy()
        row = await self.repo.one(
            model=DiningBlackout, identifier=identifier, lock=True
        )
        if not row.active:
            return
        row.active = False
        statement = self.repo.statement(model=DiningTable)
        if row.table_id is not None:
            statement = statement.where(DiningTable.id == row.table_id)
        elif row.zone_id is not None:
            statement = statement.where(DiningTable.zone_id == row.zone_id)
        for table in (
            await self.session.execute(
                statement.order_by(DiningTable.id).with_for_update()
            )
        ).scalars():
            table.revision += 1
        await self.session.flush()
        await self.event(
            kind="blackout.closed",
            details={"blackout_id": identifier, "physical_state_unchanged": True},
        )
