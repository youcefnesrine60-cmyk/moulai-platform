# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SYNTHETIC COMMITTED DINING FIXTURES
# Build real E1 authority and explicit test-only restaurant policies and rates.
# ==============================================

"""No fixture price, grant or customer identity is a commercial configuration."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND DETERMINISTIC TEST CLOCK
# Every operation opens an independent session and owns its actual transaction.
# ==============================================

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from itertools import count

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from app.core.security.oidc import OIDCPrincipal
from app.models.dining import DiningQuote
from app.repositories.dining_repo import DiningRepository
from app.schemas.dining import (
    DiningPolicyInput,
    ReceiptInput,
    ReferenceInput,
    RequestInput,
    TableInput,
    TariffInput,
)
from app.services.business.dining.customer import accept_customer_quote
from app.services.business.dining.service import (
    DiningService,
    DiningUnit,
)
from app.services.business.dining.values import Period

BLOCKS = count(7_000_000, 1000)
ISSUER = "https://dining.example.invalid/realms/synthetic"
ACTORS = ("owner", "service", "cleaner", "collector", "assistant", "outsider")


# ==============================================
# INJECTED TRUSTED CLOCK
# Tests advance actual service time without accepting HTTP clock overrides.
# ==============================================


@dataclass
class TestClock:
    """Synthetic time isolated to this graph; no system clock is modified."""

    value: datetime

    # ==============================================
    # CALL
    # Return the current synthetic UTC instant to the explicitly injected facade.
    # ==============================================

    def __call__(self) -> datetime:
        """Return the current synthetic UTC instant to the explicitly injected facade."""
        return self.value


# ==============================================
# COMMITTED GRAPH AND INDEPENDENT SERVICE SESSIONS
# Retain every committed row until the disposable server is stopped.
# ==============================================


@dataclass
class DiningGraph:
    """Hold synthetic identifiers, an explicit scope and an isolated session factory."""

    base: int
    factory: async_sessionmaker[AsyncSession]
    clock: TestClock
    table_id: int = 0
    second_table_id: int = 0
    references: dict[str, int] | None = None

    # ==============================================
    # PRINCIPAL
    # Create only a test principal; it is never a real provider identity/token.
    # ==============================================

    def principal(self, *, actor: str) -> OIDCPrincipal:
        """Create only a test principal; it is never a real provider identity/token."""
        return OIDCPrincipal(
            issuer=ISSUER,
            subject=f"synthetic-dining-{self.base}-{actor}",
            realm_roles=frozenset({"owner", "admin"}),
        )

    # ==============================================
    # ARGUMENTS
    # Choose the explicit restaurant and physical branch for this graph.
    # ==============================================

    def arguments(self, *, actor: str = "owner") -> dict[str, OIDCPrincipal | int]:
        """Choose the explicit restaurant and physical branch for this graph."""
        return {
            "principal": self.principal(actor=actor),
            "organization_id": self.base + 10,
            "restaurant_id": self.base + 200,
            "branch_id": self.base + 300,
        }

    # ==============================================
    # UNIT
    # Own a real commit on success, with no external fixture transaction.
    # ==============================================

    @asynccontextmanager
    async def unit(self, *, actor: str = "owner") -> AsyncIterator[DiningUnit]:
        """Own a real commit on success, with no external fixture transaction."""
        async with (
            self.factory() as session,
            DiningService(session=session, clock=self.clock).authorized(
                principal=self.principal(actor=actor),
                organization_id=self.base + 10,
                restaurant_id=self.base + 200,
                branch_id=self.base + 300,
            ) as unit,
        ):
            yield unit

    # ==============================================
    # QUOTE
    # Read detached quote evidence from a distinct observer session.
    # ==============================================

    async def quote(self, *, identifier: int) -> DiningQuote:
        """Read detached quote evidence from a distinct observer session."""
        async with self.factory() as session:
            return await DiningRepository(
                session=session,
                restaurant_id=self.base + 200,
                branch_id=self.base + 300,
            ).one(model=DiningQuote, identifier=identifier)


# ==============================================
# SYNTHETIC E1 AUTHORITY SETUP
# Preserve active-owner/retention triggers and never bypass identity protections.
# ==============================================


async def create_graph(*, engine: AsyncEngine) -> DiningGraph:
    """Commit scoped real membership fixtures without global truncation or create_all."""
    base = next(BLOCKS)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    graph = DiningGraph(
        base=base,
        factory=factory,
        clock=TestClock(datetime(2026, 11, 2, 18, tzinfo=timezone.utc)),
    )
    async with engine.begin() as connection:
        for offset, actor in enumerate(ACTORS):
            await connection.execute(
                text(
                    "INSERT INTO identities(id,issuer,subject,status) VALUES (:id,:issuer,:subject,'active')"
                ),
                {
                    "id": base + offset,
                    "issuer": ISSUER,
                    "subject": graph.principal(actor=actor).subject,
                },
            )
        for offset in (10, 11):
            await connection.execute(
                text("INSERT INTO organizations(id,name) VALUES (:id,:name)"),
                {"id": base + offset, "name": f"Synthetic dining {base + offset}"},
            )
        await connection.execute(
            text(
                "INSERT INTO owners(id,chat_id,full_name,registration_status) VALUES (:id,:chat,'Synthetic owner','approved')"
            ),
            {"id": base + 100, "chat": base + 100},
        )
        for offset, company in ((200, 10), (201, 11)):
            await connection.execute(
                text(
                    "INSERT INTO restaurants(id,owner_id,organization_id,name,type,phone,wilaya,is_active) VALUES (:id,:owner,:company,:name,'restaurant','synthetic','Test',true)"
                ),
                {
                    "id": base + offset,
                    "owner": base + 100,
                    "company": base + company,
                    "name": f"Synthetic {base + offset}",
                },
            )
        for offset, restaurant in ((300, 200), (301, 200), (302, 201)):
            await connection.execute(
                text(
                    "INSERT INTO branches(id,restaurant_id,name,is_active) VALUES (:id,:restaurant,'Synthetic branch',true)"
                ),
                {"id": base + offset, "restaurant": base + restaurant},
            )
        for index, actor in enumerate(ACTORS):
            company = 11 if actor == "outsider" else 10
            role = "owner" if actor in {"owner", "outsider"} else "employee"
            mode = "company-wide" if role == "owner" else "explicit-grants"
            await connection.execute(
                text(
                    "INSERT INTO organization_memberships(id,organization_id,identity_id,role_code,access_mode,status,enrollment_generation,accepted_at,activated_at) VALUES (:id,:org,:identity,:role,:mode,'active',1,now(),now())"
                ),
                {
                    "id": base + 30 + index,
                    "org": base + company,
                    "identity": base + index,
                    "role": role,
                    "mode": mode,
                },
            )
            if mode == "explicit-grants":
                await connection.execute(
                    text(
                        "INSERT INTO membership_restaurant_grants(organization_id,membership_id,restaurant_id) VALUES (:org,:member,:restaurant)"
                    ),
                    {
                        "org": base + company,
                        "member": base + 30 + index,
                        "restaurant": base + 200,
                    },
                )
        for company in (10, 11):
            await connection.execute(
                text(
                    "UPDATE organizations SET status='active',tenant_enforced_at=now(),revision=revision+1 WHERE id=:id"
                ),
                {"id": base + company},
            )
    return graph


# ==============================================
# EXPLICIT TEST-ONLY POLICY AND TABLES
# Prices and timings below are synthetic fixtures, not approved commercial seeds.
# ==============================================


async def configure_graph(*, graph: DiningGraph) -> DiningGraph:
    """Configure actual services through their owner authority and persist all setup."""
    policy = DiningPolicyInput(
        timezone="Africa/Algiers",
        response_seconds=60,
        hold_seconds=1200,
        lateness_seconds=300,
        preparation_seconds=0,
        cleaning_seconds=0,
        confirmation_seconds=7200,
        confirmation_scope="tables",
        alert_offsets_seconds=(0, 60),
        service_recipients=(graph.base + 31,),
        escalation_recipients=(graph.base + 30,),
        currencies={"DZD": 2, "USD": 2, "JPY": 0},
        payment_instructions={
            "cash": "Synthetic restaurant cash desk",
            "ccp": "Synthetic restaurant transfer instructions",
        },
        terms="Synthetic terms; no real payment or refund instructions.",
    )
    references: dict[str, int] = {}
    async with graph.unit() as unit:
        await unit.configure(data=policy)
        for offset, capability in (
            (30, "service"),
            (30, "clean"),
            (30, "collect"),
            (31, "service"),
            (32, "clean"),
            (33, "collect"),
            (34, "assistant"),
            (30, "finance.read"),
            (30, "invoices.create"),
            (30, "invoices.finalize"),
            (30, "advances.allocate"),
            (33, "finance.read"),
            (33, "advances.allocate"),
        ):
            await unit.grant(
                membership_id=graph.base + offset,
                capability=capability,
                actor_kind="assistant" if offset == 34 else "human",
                active=True,
            )
        for kind, code in (
            ("shape", "round"),
            ("category", "standard"),
            ("zone", "terrace"),
            ("location", "ground"),
            ("view", "sea"),
            ("proximity", "garden"),
            ("event", "birthday"),
        ):
            references[kind] = await unit.create_reference(
                data=ReferenceInput(
                    kind=kind,
                    code=code,
                    labels={
                        "fr": f"Test {code}",
                        "en": f"Test {code}",
                        "ar": f"اختبار {code}",
                    },
                    active=True,
                    pricing_ref="test-event" if kind == "event" else None,
                )
            )
        from app.schemas.dining import OpeningWindow

        for day in range(7):
            await unit.save_calendar(
                weekday=day,
                service_date=None,
                windows=(OpeningWindow(start="00:00", end="00:00", next_day=True),),
            )
        data = TableInput(
            code="T1",
            name="Synthetic table",
            min_capacity=1,
            max_capacity=4,
            shape_id=references["shape"],
            category_id=references["category"],
            zone_id=references["zone"],
            location_id=references["location"],
            description="Synthetic table description",
            photos=(),
            pricing_ref="test-table",
            in_service=True,
            trait_ids=(references["view"], references["proximity"]),
        )
        graph.table_id = await unit.create_table(data=data, initial_state="available")
        graph.second_table_id = await unit.create_table(
            data=data.model_copy(update={"code": "T2"}), initial_state="available"
        )
        await unit.create_tariff(
            data=TariffInput(
                reference="test-table",
                component="table",
                currency="DZD",
                unit="per_hour",
                unit_price=Decimal(1000),
                valid_from=graph.clock.value - timedelta(days=1),
                valid_until=None,
            )
        )
    graph.references = references
    return graph


# ==============================================
# NORMAL RESERVATION PREPARATION
# Customer consent and receipt use independent committed operations.
# ==============================================


async def create_request_quote(
    *, graph: DiningGraph, table_id: int | None = None
) -> tuple[int, int]:
    """Prepare the synthetic ninety-minute, four-person request and its exact quote."""
    starts_at = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    async with graph.unit() as unit:
        request_id = await unit.create_request(
            data=RequestInput(
                customer_name="Synthetic customer",
                contact="synthetic@example.invalid",
                starts_at=starts_at,
                duration_seconds=5400,
                party_size=4,
                table_ids=(graph.table_id if table_id is None else table_id,),
                criteria={},
                event_id=None,
                preparation=False,
                menu=(),
            ),
            customer=graph.principal(actor="customer"),
        )
        quote_id = await unit.create_quote(
            request_id=request_id,
            currency="DZD",
            expires_at=graph.clock.value + timedelta(hours=1),
        )
    return request_id, quote_id


# ==============================================
# ACCEPT AND HOLD
# Use the real customer boundary, then create the exclusive hold as service.
# ==============================================


async def accept_and_hold(
    *, graph: DiningGraph, request_id: int, quote_id: int
) -> None:
    """Use the real customer boundary, then create the exclusive hold as service."""
    quote = await graph.quote(identifier=quote_id)
    async with graph.factory() as session:
        await accept_customer_quote(
            session=session,
            principal=graph.principal(actor="customer"),
            restaurant_id=graph.base + 200,
            branch_id=graph.base + 300,
            quote_id=quote_id,
            expected_digest=quote.digest,
            clock=graph.clock,
        )
    async with graph.unit() as unit:
        await unit.hold(request_id=request_id, quote_id=quote_id)


# ==============================================
# RECEIVE ADVANCE
# Commit an actual human collection fact in a distinct service transaction.
# ==============================================


async def receive_advance(
    *,
    graph: DiningGraph,
    request_id: int,
    quote_id: int,
    amount: Decimal = Decimal(1500),
    currency: str = "DZD",
    reference: str = "synthetic-receipt",
) -> int:
    """Commit an actual human collection fact in a distinct service transaction."""
    async with graph.factory() as session:
        return await DiningService(session=session, clock=graph.clock).record_receipt(
            principal=graph.principal(actor="collector"),
            organization_id=graph.base + 10,
            restaurant_id=graph.base + 200,
            branch_id=graph.base + 300,
            data=ReceiptInput(
                request_id=request_id,
                quote_id=quote_id,
                received_amount=amount,
                currency=currency,
                mode="cash",
                reference=reference,
                received_at=graph.clock.value,
            ),
        )


# ==============================================
# CONFIRM BOOKING
# Record explicit service confirmation and finalize within one owned transaction.
# ==============================================


async def confirm_booking(
    *, graph: DiningGraph, request_id: int, quote_id: int, receipt_id: int
) -> dict[str, str | int]:
    """Record explicit service confirmation and finalize within one owned transaction."""
    async with graph.unit() as unit:
        await unit.confirm_availability(
            table_ids=(graph.table_id,),
            period=Period(
                start=datetime(2026, 11, 3, 20, tzinfo=timezone.utc),
                end=datetime(2026, 11, 3, 21, 30, tzinfo=timezone.utc),
            ),
            request_id=request_id,
        )
        return await unit.finalize_human(
            request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
        )
