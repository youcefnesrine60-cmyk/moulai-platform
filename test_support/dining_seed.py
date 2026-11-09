# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ATTESTED LOCAL DINING REHEARSAL FIXTURE
# Seed explicitly fictional identities and food sources only in the owned disposable database.
# ==============================================

"""No tariff, receipt, user or grant in this fixture is a commercial configuration."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT LOCAL CONTRACTS
# Reuse typed module dependencies without creating a connection or enabling a transport.
# ==============================================

from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.schemas.dining import TariffInput
from migration_support.dining_d1d import D1D_REVISION
from test_support.local_postgres import (
    LocalPostgresSettings,
    read_local_test_identity,
)
from tests.dining.support import (
    DiningGraph,
    configure_graph,
    create_graph,
)

# ==============================================
# PREPARE DINING REHEARSAL
# Attest destination/marker/revision before any fictional fixture write.
# ==============================================


async def prepare_dining_rehearsal(
    *, engine: AsyncEngine, configuration: LocalPostgresSettings, now: datetime
) -> DiningGraph:
    """Attest destination/marker/revision before any fictional fixture write."""
    if (
        configuration.PROFILE != "dining"
        or engine.url.render_as_string(hide_password=False)
        != configuration.URL.get_secret_value()
    ):
        raise RuntimeError("dining_seed_target_not_attested")
    async with engine.connect() as connection:
        await connection.run_sync(
            lambda sync: read_local_test_identity(sync, configuration=configuration)
        )
        if (
            await connection.scalar(text("SELECT version_num FROM alembic_version"))
            != D1D_REVISION
        ):
            raise RuntimeError("dining_seed_revision_mismatch")
    graph = await create_graph(engine=engine)
    graph.clock.value = now
    await configure_graph(graph=graph)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO identities(id,issuer,subject,status) VALUES (:id,:issuer,:subject,'active')"
            ),
            {
                "id": graph.base + 12,
                "issuer": graph.principal(actor="new_employee").issuer,
                "subject": graph.principal(actor="new_employee").subject,
            },
        )
        for offset, actor in (
            (6, "service_cleaner"),
            (7, "canceller"),
            (8, "finance"),
            (9, "finance_reader"),
            (10, "kitchen"),
        ):
            await connection.execute(
                text(
                    "INSERT INTO identities(id,issuer,subject,status) VALUES (:id,:issuer,:subject,'active')"
                ),
                {
                    "id": graph.base + offset,
                    "issuer": graph.principal(actor=actor).issuer,
                    "subject": graph.principal(actor=actor).subject,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO organization_memberships(id,organization_id,identity_id,role_code,access_mode,status,enrollment_generation,accepted_at,activated_at) VALUES (:id,:org,:identity,'employee','explicit-grants','active',1,now(),now())"
                ),
                {
                    "id": graph.base + 30 + offset,
                    "org": graph.base + 10,
                    "identity": graph.base + offset,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO membership_restaurant_grants(organization_id,membership_id,restaurant_id) VALUES (:org,:member,:restaurant)"
                ),
                {
                    "org": graph.base + 10,
                    "member": graph.base + 30 + offset,
                    "restaurant": graph.base + 200,
                },
            )
        # Local-only technical feature identity used by the legacy order adapter.
        # This is neither a paid plan nor a commercial tariff configuration.
        await connection.execute(
            text(
                "INSERT INTO features(id,name,code) VALUES (6,'Synthetic orders only','synthetic-orders') ON CONFLICT (id) DO NOTHING"
            )
        )
        category = await connection.scalar(
            text(
                "INSERT INTO categories(restaurant_id,name) VALUES (:restaurant,'Synthetic food source') RETURNING id"
            ),
            {"restaurant": graph.base + 200},
        )
        product = await connection.scalar(
            text(
                "INSERT INTO products(restaurant_id,category_id,name,price,is_available) VALUES (:restaurant,:category,'Synthetic special dish',6000,true) RETURNING id"
            ),
            {"restaurant": graph.base + 200, "category": category},
        )
        order = await connection.scalar(
            text(
                "INSERT INTO orders(restaurant_id,branch_id,table_id,order_number,order_type,status,subtotal_amount,discount_amount,tax_amount,delivery_amount,total_amount) VALUES (:restaurant,:branch,:table,:number,'dine_in','completed',6000,0,0,0,6000) RETURNING id"
            ),
            {
                "restaurant": graph.base + 200,
                "branch": graph.base + 300,
                "table": graph.table_id,
                "number": f"LOCAL-FOOD-SOURCE-{graph.base}",
            },
        )
        await connection.execute(
            text(
                "INSERT INTO order_items(order_id,product_id,product_name,unit_price,quantity,total_price) VALUES (:order,:product,'Synthetic food',6000,1,6000)"
            ),
            {"order": order, "product": product},
        )
    async with graph.unit() as unit:
        for membership, capability in (
            (graph.base + 36, "service"),
            (graph.base + 36, "clean"),
            (graph.base + 37, "reservations.cancel_before_arrival"),
            (graph.base + 30, "reservations.cancel_before_arrival"),
            (graph.base + 38, "read"),
            (graph.base + 39, "read"),
            (graph.base + 40, "read"),
        ):
            await unit.grant(
                membership_id=membership,
                capability=capability,
                actor_kind="human",
                active=True,
            )
        await unit.create_tariff(
            data=TariffInput(
                reference=f"product:{product}",
                component="menu",
                currency="DZD",
                unit="per_item",
                unit_price=Decimal("10.005"),
                valid_from=now,
                valid_until=None,
            )
        )
    return graph
