# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# REAL DINING D1 CATALOGUE TESTS
# Verify actual post-S1a PostgreSQL objects without substituting create_all.
# ==============================================

"""Opt-in live catalogue proofs; no configured application database is used."""

# isort: split
# ==============================================
# IMPORTS AND ISOLATED PROFILE MARKER
# Require the owner's disposable launcher before any SQL connection can open.
# ==============================================


import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from migration_support.dining_d1_schema import D1_TABLES
from migration_support.dining_d1d import D1D_TABLES

pytestmark = pytest.mark.dining_postgres


# ==============================================
# ACTUAL SCHEMA OBJECTS
# Check physical constraints, indexes and retention triggers after real migrations.
# ==============================================


async def test_actual_d1_schema_and_protections(dining_engine: AsyncEngine) -> None:
    """Assert 24 new tables, valid exclusion and an untouched S1a FK status set."""
    async with dining_engine.connect() as connection:
        tables = set(
            (
                await connection.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
                )
            ).scalars()
        )
        assert len(tables) == 92 and set(D1_TABLES + D1D_TABLES) <= tables
        exclusions = set(
            (
                await connection.execute(
                    text(
                        "SELECT conname FROM pg_constraint WHERE contype='x' AND convalidated"
                    )
                )
            ).scalars()
        )
        assert {
            "ex_dining_active_table_period",
            "ex_dining_tariff_validity",
        } <= exclusions
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE contype='f' AND NOT convalidated"
                )
            )
            == 6
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM pg_trigger WHERE tgname='tr_dining_invoice_retain' AND NOT tgisinternal"
                )
            )
            == 1
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT indisvalid AND indisunique FROM pg_index WHERE indexrelid='uq_d1_branch_restaurant'::regclass"
                )
            )
            is True
        )
