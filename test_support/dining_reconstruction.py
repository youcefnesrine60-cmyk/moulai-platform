# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DISPOSABLE POST-S1A DINING VERIFICATION
# Check the real D1 catalogue and startup without contacting permanent services.
# ==============================================

"""Read-only catalogue and real FastAPI lifespan proof after the actual D1 chain."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXACT REVISION CONTRACT
# Reuse local identity admission and preserve all six accepted S1a NOT VALID FKs.
# ==============================================

import json
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from migration_support.dining_d1_schema import D1_TABLES
from migration_support.dining_d1d import (
    D1D_REVISION,
    D1D_TABLES,
)
from test_support.local_postgres import (
    LocalPostgresSettings,
    read_local_test_identity,
)

# ==============================================
# REAL MIGRATION CATALOGUE AND APPLICATION ADMISSION
# Refuse drift and seed data; no schema or price is manufactured by this check.
# ==============================================


async def verify_dining_reconstruction(
    *, configuration: LocalPostgresSettings, output: Path
) -> dict[str, str | int | bool | list[str]]:
    """Verify D1 and complete actual ASGI startup without opening a network server."""
    if configuration.PROFILE != "dining":
        raise RuntimeError("dining_reconstruction_profile_required")
    engine = create_async_engine(
        configuration.URL.get_secret_value(),
        connect_args={"ssl": False},
        hide_parameters=True,
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            await connection.run_sync(
                lambda sync: read_local_test_identity(sync, configuration=configuration)
            )
            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT tablename FROM pg_tables WHERE schemaname='public'"
                        )
                    )
                ).scalars()
            )
            if (
                revision != D1D_REVISION
                or len(tables) != 92
                or not set(D1_TABLES + D1D_TABLES) <= tables
            ):
                raise RuntimeError("dining_catalogue_contract_mismatch")
            missing_valid_exclusions = {
                "ex_dining_active_table_period",
                "ex_dining_tariff_validity",
            } - set(
                (
                    await connection.execute(
                        text(
                            "SELECT conname FROM pg_constraint WHERE contype='x' AND convalidated"
                        )
                    )
                ).scalars()
            )
            unvalidated = sorted(
                (
                    await connection.execute(
                        text(
                            "SELECT conname FROM pg_constraint WHERE contype='f' AND NOT convalidated"
                        )
                    )
                ).scalars()
            )
            if missing_valid_exclusions or unvalidated != sorted(
                [
                    "fk_admin_identity",
                    "fk_owner_identity",
                    "fk_restaurants_org",
                    "fk_groups_org",
                    "fk_group_link_group_org",
                    "fk_group_link_restaurant_org",
                ]
            ):
                raise RuntimeError("dining_or_s1a_protection_drift")
            for name in D1_TABLES + D1D_TABLES:
                if await connection.scalar(
                    text(f'SELECT count(*) FROM public."{name}"')
                ):
                    raise RuntimeError(
                        "dining_reconstruction_contains_unapproved_seed_data"
                    )
            observed: dict[str, str | int | bool | list[str]] = {
                "revision": str(revision),
                "public_tables": len(tables),
                "dining_tables": len(D1_TABLES + D1D_TABLES),
                "all_dining_tables_initially_empty": True,
                "exclusion_constraints_validated": True,
                "not_valid_foreign_keys": unvalidated,
            }
    finally:
        await engine.dispose()
    from app.core.config import settings
    from app.main import app

    if (
        settings.DATABASE_URL != configuration.URL.get_secret_value()
        or settings.DATABASE_TARGET != "primary"
    ):
        raise RuntimeError("dining_startup_not_pinned_to_local")
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://dining-rehearsal"
    ) as client:
        observed["root_http_status"] = (await client.get("/")).status_code
        observed["health_http_status"] = (await client.get("/health")).status_code
    if observed["root_http_status"] != 200 or observed["health_http_status"] != 200:
        raise RuntimeError("dining_local_startup_failed")
    observed["actual_lifespan_completed"] = True
    observed["network_server_started"] = False
    (output / "dining-catalogue.json").write_text(
        json.dumps(observed, indent=2) + "\n", encoding="utf-8"
    )
    return observed
