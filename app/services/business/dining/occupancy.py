# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# REAL TABLE OCCUPATION AND CLEANING
# Record actual human observations without deriving vacancy from predicted ends.
# ==============================================

"""Physical assignment, departure, cleaning and overrun alerts are separate facts."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND PHYSICAL WORKFLOW RECORDS
# Keep future reservations and maintenance intact through cleaning completion.
# ==============================================

from datetime import (
    datetime,
    timedelta,
)
from typing import Literal

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.models.dining import (
    DiningBlackout,
    DiningClaim,
    DiningOccupation,
    DiningOccupationTable,
)
from app.models.dining_service import DiningVisit
from app.services.business.dining.core import DiningCore
from app.services.business.dining.values import (
    DiningError,
    Period,
    utc,
)

# ==============================================
# HUMAN PHYSICAL WORKFLOW
# Every transition has its own capability and observed timestamp.
# ==============================================


class DiningOccupancy(DiningCore):
    """Protect actual assignments and record deviations without inventing a departure."""

    async def install(
        self,
        *,
        table_ids: tuple[int, ...],
        party_size: int,
        expected_end: datetime,
        request_id: int | None,
    ) -> int:
        """Install a confirmed party or an explicit human-authorized walk-in."""
        await self.guard(capability="service", human=True)
        policy = await self.policy()
        now = self.now()
        end = utc(value=expected_end)
        if type(party_size) is not int or party_size <= 0 or end <= now:
            raise DiningError(code="dining_actual_occupation_period_invalid")
        if request_id is not None:
            request = await self.request(identifier=request_id)
            if (
                request.status != "confirmed"
                or set(await self.selected(request_id=request_id)) != set(table_ids)
                or party_size > request.party_size
            ):
                raise DiningError(code="dining_confirmed_assignment_required")
            if now < request.starts_at:
                raise DiningError(code="dining_early_arrival_requires_explicit_policy")
        planning_size = request.party_size if request_id is not None else party_size
        tables = await self.availability(
            identifiers=table_ids,
            period=Period(start=now, end=end),
            party_size=planning_size,
            ignore_request=request_id,
        )
        if any(table.physical_state != "available" for table in tables):
            raise DiningError(code="dining_actual_vacancy_required_for_installation")
        occupation = await self.repo.persist(
            record=DiningOccupation(
                **self.scope(),
                request_id=request_id,
                party_size=party_size,
                arrived_at=now,
                expected_end=end,
                cleaning_expected_start=end,
                cleaning_expected_end=end + timedelta(seconds=policy.cleaning_seconds),
                status="occupied",
                installed_by=self.context.membership_id,
            )
        )
        expanded = await self.expanded(period=Period(start=now, end=end))
        for table in tables:
            await self.repo.persist(
                record=DiningOccupationTable(
                    **self.scope(),
                    occupation_id=occupation.id,
                    table_id=table.id,
                    active=True,
                )
            )
            if request_id is None:
                await self.repo.persist(
                    record=DiningClaim(
                        **self.scope(),
                        request_id=None,
                        table_id=table.id,
                        starts_at=expanded.start,
                        ends_at=expanded.end,
                        kind="occupation",
                        active=True,
                    )
                )
            else:
                claims = (
                    (
                        await self.session.execute(
                            self.repo.statement(model=DiningClaim)
                            .where(
                                DiningClaim.table_id == table.id,
                                DiningClaim.request_id == request_id,
                                DiningClaim.active.is_(True),
                            )
                            .with_for_update()
                        )
                    )
                    .scalars()
                    .all()
                )
                if len(claims) != 1 or claims[0].kind != "reservation":
                    raise DiningError(code="dining_confirmed_claim_missing")
                claims[0].ends_at = max(claims[0].ends_at, expanded.end)
            table.physical_state = "occupied"
            table.revision += 1
        if request_id is not None:
            request.status = "arrived"
        await self.session.flush()
        await self.event(
            kind="occupation.installed",
            request_id=request_id,
            details={
                "occupation_id": occupation.id,
                "table_ids": list(table_ids),
                "arrived_at": now.isoformat(),
                "expected_end": end.isoformat(),
                "cleaning_expected_end": occupation.cleaning_expected_end.isoformat(),
            },
        )
        return occupation.id

    # ==============================================
    # OCCUPATION TABLES
    # Lock an occupation and its complete still-active physical assignment.
    # ==============================================

    async def _occupation_tables(
        self, *, occupation_id: int
    ) -> tuple[DiningOccupation, tuple[int, ...]]:
        """Lock an occupation and its complete still-active physical assignment."""
        occupation = await self.repo.one(
            model=DiningOccupation, identifier=occupation_id, lock=True
        )
        links = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningOccupationTable)
                    .where(
                        DiningOccupationTable.occupation_id == occupation_id,
                        DiningOccupationTable.active.is_(True),
                    )
                    .order_by(DiningOccupationTable.table_id)
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        if not links:
            raise DiningError(code="dining_live_occupation_required")
        return occupation, tuple(row.table_id for row in links)

    # ==============================================
    # RECORD DEPARTURE
    # A habilitated cleaner's actual observation changes occupied to dirty.
    # ==============================================

    async def record_departure(self, *, occupation_id: int) -> None:
        """A habilitated cleaner's actual observation changes occupied to dirty."""
        await self.guard(capability="clean", human=True)
        policy = await self.policy()
        occupation, identifiers = await self._occupation_tables(
            occupation_id=occupation_id
        )
        if occupation.status != "occupied":
            raise DiningError(code="dining_departure_transition_invalid")
        tables = await self.tables(identifiers=identifiers)
        now = self.now()
        occupation.departed_at, occupation.departure_by = (
            now,
            self.context.membership_id,
        )
        occupation.status = "dirty"
        visits = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningVisit)
                    .where(
                        DiningVisit.occupation_id == occupation_id,
                        DiningVisit.status == "active",
                    )
                    .with_for_update()
                )
            ).scalars()
        )
        for visit in visits:
            visit.status, visit.ended_at = "ended", now
        previous_end = occupation.cleaning_expected_end
        occupation.cleaning_expected_end = max(
            previous_end, now + timedelta(seconds=policy.cleaning_seconds)
        )
        for table in tables:
            if table.physical_state != "occupied":
                raise DiningError(code="dining_occupation_physical_state_mismatch")
            table.physical_state = "dirty"
            table.revision += 1
        await self.session.flush()
        await self.event(
            kind="occupation.departure_observed",
            request_id=occupation.request_id,
            details={
                "occupation_id": occupation_id,
                "actual_departure": now.isoformat(),
                "previous_cleaning_expected_end": previous_end.isoformat(),
                "cleaning_expected_end": occupation.cleaning_expected_end.isoformat(),
            },
        )

    # ==============================================
    # START CLEANING
    # Record real cleaning start separately from the observed customer departure.
    # ==============================================

    async def start_cleaning(self, *, occupation_id: int) -> None:
        """Record real cleaning start separately from the observed customer departure."""
        await self.guard(capability="clean", human=True)
        await self.policy()
        occupation, identifiers = await self._occupation_tables(
            occupation_id=occupation_id
        )
        await self.tables(identifiers=identifiers)
        if occupation.status != "dirty" or occupation.departed_at is None:
            raise DiningError(code="dining_cleaning_start_transition_invalid")
        occupation.cleaning_actual_start, occupation.status = self.now(), "cleaning"
        await self.session.flush()
        await self.event(
            kind="cleaning.started",
            request_id=occupation.request_id,
            details={"occupation_id": occupation_id},
        )

    # ==============================================
    # FINISH CLEANING
    # Free actual assignment without erasing future reservations or maintenance.
    # ==============================================

    async def finish_cleaning(self, *, occupation_id: int) -> None:
        """Free actual assignment without erasing future reservations or maintenance."""
        await self.guard(capability="clean", human=True)
        await self.policy()
        occupation, identifiers = await self._occupation_tables(
            occupation_id=occupation_id
        )
        if occupation.status != "cleaning" or occupation.cleaning_actual_start is None:
            raise DiningError(code="dining_cleaning_completion_transition_invalid")
        now = self.now()
        tables = await self.tables(identifiers=identifiers)
        for table in tables:
            blocks = (
                (
                    await self.session.execute(
                        self.repo.statement(model=DiningBlackout).where(
                            DiningBlackout.active.is_(True),
                            DiningBlackout.kind == "maintenance",
                            DiningBlackout.starts_at <= now,
                            DiningBlackout.ends_at > now,
                            or_(
                                DiningBlackout.table_id == table.id,
                                DiningBlackout.zone_id == table.zone_id,
                                (
                                    DiningBlackout.table_id.is_(None)
                                    & DiningBlackout.zone_id.is_(None)
                                ),
                            ),
                        )
                    )
                )
                .scalars()
                .all()
            )
            table.physical_state = (
                "out_of_service"
                if not table.in_service
                else "maintenance" if blocks else "available"
            )
            table.revision += 1
        links = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningOccupationTable).where(
                        DiningOccupationTable.occupation_id == occupation_id
                    )
                )
            )
            .scalars()
            .all()
        )
        for link in links:
            link.active = False
        if occupation.request_id is None:
            claims = (
                (
                    await self.session.execute(
                        self.repo.statement(model=DiningClaim).where(
                            DiningClaim.table_id.in_(identifiers),
                            DiningClaim.kind == "occupation",
                            DiningClaim.active.is_(True),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for claim in claims:
                claim.active = False
        else:
            request = await self.request(identifier=occupation.request_id)
            if request.status == "arrived":
                request.status = "served"
        occupation.cleaning_actual_end, occupation.cleaned_by, occupation.status = (
            now,
            self.context.membership_id,
            "closed",
        )
        await self.session.flush()
        await self.event(
            kind="cleaning.completed",
            request_id=occupation.request_id,
            details={
                "occupation_id": occupation_id,
                "late": now > occupation.cleaning_expected_end,
                "future_claims_and_maintenance_retained": True,
            },
        )

    # ==============================================
    # EXTEND OCCUPATION
    # Retain an actual overrun even when a later booking requires intervention.
    # ==============================================

    async def extend_occupation(
        self, *, occupation_id: int, expected_end: datetime
    ) -> tuple[int, ...]:
        """Retain an actual overrun even when a later booking requires intervention."""
        await self.guard(capability="service", human=True)
        policy = await self.policy()
        occupation, identifiers = await self._occupation_tables(
            occupation_id=occupation_id
        )
        if occupation.status != "occupied":
            raise DiningError(code="dining_occupation_extension_transition_invalid")
        await self.tables(identifiers=identifiers)
        end = utc(value=expected_end)
        if end <= self.now() or end <= occupation.expected_end:
            raise DiningError(code="dining_occupation_extension_must_prolong")
        prior = occupation.expected_end
        occupation.expected_end = end
        occupation.cleaning_expected_start = end
        occupation.cleaning_expected_end = end + timedelta(
            seconds=policy.cleaning_seconds
        )
        for table in await self.tables(identifiers=identifiers):
            table.revision += 1
        await self.session.flush()
        affected = set(
            await self.future_conflicts(
                table_ids=identifiers,
                period=Period(start=self.now(), end=occupation.cleaning_expected_end),
            )
        )
        affected.discard(occupation.request_id)
        if not affected:
            # Preserve real observations outside this savepoint if a raw SQL
            # contender wins the exclusion race after our scoped preflight.
            try:
                async with self.session.begin_nested():
                    statement = self.repo.statement(model=DiningClaim).where(
                        DiningClaim.table_id.in_(identifiers),
                        DiningClaim.active.is_(True),
                    )
                    statement = (
                        statement.where(DiningClaim.request_id == occupation.request_id)
                        if occupation.request_id is not None
                        else statement.where(
                            DiningClaim.kind == "occupation",
                            DiningClaim.request_id.is_(None),
                        )
                    )
                    for claim in (
                        await self.session.execute(statement.with_for_update())
                    ).scalars():
                        claim.ends_at = max(
                            claim.ends_at, occupation.cleaning_expected_end
                        )
                    await self.session.flush()
            except IntegrityError as error:
                if getattr(error.orig, "sqlstate", None) != "23P01":
                    raise
                affected.update(
                    await self.future_conflicts(
                        table_ids=identifiers,
                        period=Period(
                            start=self.now(), end=occupation.cleaning_expected_end
                        ),
                    )
                )
                affected.discard(occupation.request_id)
        await self.event(
            kind="occupation.extended",
            request_id=occupation.request_id,
            details={
                "occupation_id": occupation_id,
                "previous_expected_end": prior.isoformat(),
                "expected_end": end.isoformat(),
                "conflicts": sorted(affected),
            },
        )
        for request_id in affected:
            await self.alert(
                request_id=request_id,
                event_key=f"occupation.overrun:{occupation_id}:{end.isoformat()}",
                details={"manual_intervention_required": True},
            )
        tables = await self.tables(identifiers=identifiers)
        block_ids = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningBlackout)
                    .with_only_columns(DiningBlackout.id)
                    .where(
                        DiningBlackout.active.is_(True),
                        DiningBlackout.starts_at < occupation.cleaning_expected_end,
                        DiningBlackout.ends_at > self.now(),
                        or_(
                            DiningBlackout.table_id.in_(identifiers),
                            DiningBlackout.zone_id.in_(
                                tuple(table.zone_id for table in tables)
                            ),
                            DiningBlackout.table_id.is_(None)
                            & DiningBlackout.zone_id.is_(None),
                        ),
                    )
                )
            ).scalars()
        )
        if block_ids:
            await self.alert(
                request_id=occupation.request_id,
                event_key=f"occupation.blackout_conflict:{occupation_id}:{end.isoformat()}",
                details={
                    "occupation_id": occupation_id,
                    "blackout_ids": list(block_ids),
                    "actual_occupation_retained": True,
                },
            )
        return tuple(sorted(affected))

    # ==============================================
    # SET OPERATIONAL STATE
    # Record a human service observation without bypassing occupied/dirty states.
    # ==============================================

    async def set_operational_state(
        self,
        *,
        table_id: int,
        state: Literal["available", "maintenance", "out_of_service"],
    ) -> tuple[int, ...]:
        """Record a human service observation without bypassing occupied/dirty states."""
        await self.guard(capability="service", human=True)
        await self.policy()
        table = (await self.tables(identifiers=(table_id,)))[0]
        if table.physical_state in {"occupied", "dirty"}:
            raise DiningError(code="dining_actual_departure_and_cleaning_required")
        conflicts = await self.future_conflicts(table_ids=(table_id,))
        table.physical_state, table.revision = state, table.revision + 1
        await self.session.flush()
        await self.event(
            kind="table.physical_state_observed",
            details={
                "table_id": table_id,
                "state": state,
                "conflicts": list(conflicts),
            },
        )
        for request_id in conflicts:
            await self.alert(
                request_id=request_id,
                event_key=f"physical.changed:{table_id}:{table.revision}",
                details={"manual_review": True},
            )
        return conflicts
