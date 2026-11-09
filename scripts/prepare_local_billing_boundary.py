# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT FICTITIOUS BILLING CLOCK FIXTURE
# Advance only the dedicated empty financial-recipe company's trial to a measured boundary, preserving the first UI trial unchanged.
# ==============================================

"""Synthetic dates only, never a reconstruction of real service history or a remotely callable operation."""

from __future__ import annotations

# isort: split
# ==============================================
# PINNED LOCAL PREPARATION
# Resolve the dedicated authenticated test subject from protected local setup, not from arbitrary owner input.
# ==============================================

import argparse
import asyncio
import json
import sys
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from scripts.run_operational_local import (
    IntegrationNetworkGuard,
    resolve_instance,
)

# ==============================================
# SINGLE SYNTHETIC TRIAL BOUNDARY
# Refuse an ordinary company, existing commerce, missing country, prior quote, reused fixture or non-trial coverage.
# ==============================================


async def prepare() -> dict[str, object]:
    """Record original dates and fixture provenance, collect actual empty-table metrics, and leave all payment state uncreated."""
    configuration = resolve_instance(supplied=None)
    configuration.process_environment()
    from app.models.subscription import Subscription
    from app.models.subscription_pricing import SubscriptionPricingSnapshot
    from app.repositories.subscription_queries import base_select
    from app.services.business import subscription_metrics
    from app.services.business.enrollment_documents import require_document_rehearsal

    account = json.loads(
        (configuration.directory / "private/acceptance-accounts.json").read_text(
            encoding="utf-8"
        )
    )["billing-scenario"]
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with async_sessionmaker(
            engine, expire_on_commit=False
        )() as session, session.begin():
            await require_document_rehearsal(
                session=session, marker=configuration.instance_id
            )
            row = (
                await session.execute(
                    text(
                        "SELECT d.id,d.restaurant_id,r.owner_id,o.name FROM enrollment_dossiers d JOIN identities i ON i.id=d.identity_id JOIN organizations o ON o.id=d.organization_id JOIN restaurants r ON r.id=d.restaurant_id WHERE i.issuer=:issuer AND i.subject=:subject AND d.status='completed' AND o.status='active' AND o.name='LOCAL-FAKE — Société de recette O4 paiement' FOR UPDATE OF d,r"
                    ),
                    {"issuer": configuration.issuer, "subject": account["subject"]},
                )
            ).one()
            if (
                await session.scalar(
                    text("SELECT count(*) FROM orders WHERE restaurant_id=:id"),
                    {"id": row.restaurant_id},
                )
                or await session.scalar(
                    text("SELECT count(*) FROM products WHERE restaurant_id=:id"),
                    {"id": row.restaurant_id},
                )
                or await session.scalar(
                    text("SELECT count(*) FROM categories WHERE restaurant_id=:id"),
                    {"id": row.restaurant_id},
                )
            ):
                raise ValueError(
                    "synthetic_billing_clock_requires_empty_catalogue_and_orders"
                )
            subscriptions = (
                await session.scalars(
                    base_select(Subscription)
                    .where(Subscription.restaurant_id == row.restaurant_id)
                    .with_for_update()
                )
            ).all()
            if (
                len(subscriptions) != 1
                or subscriptions[0].status != "trial"
                or subscriptions[0].billing_cycle != "trial"
            ):
                raise ValueError("synthetic_billing_clock_requires_single_fresh_trial")
            trial = subscriptions[0]
            if await session.scalar(
                text(
                    "SELECT count(*) FROM subscription_pricing_snapshots WHERE restaurant_id=:id"
                ),
                {"id": row.restaurant_id},
            ) or await session.scalar(
                text("SELECT count(*) FROM payments WHERE restaurant_id=:id"),
                {"id": row.restaurant_id},
            ):
                raise ValueError(
                    "synthetic_billing_clock_refuses_existing_quotes_or_payments"
                )
            original = {
                "starts_at": trial.starts_at.isoformat(),
                "expires_at": trial.expires_at.isoformat(),
            }
            end = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
            trial.starts_at = end - timedelta(days=30)
            trial.expires_at = end
            measured = await subscription_metrics.collect(
                session=session,
                owner_id=row.owner_id,
                restaurant_id=row.restaurant_id,
                end=end,
            )
            provenance = {
                "exact_average_order_value": str(measured["average_order_value"]),
                "synthetic_clock_fixture": {
                    "account": "billing-scenario",
                    "original_dates": original,
                    "advanced_dates": {
                        "starts_at": trial.starts_at.isoformat(),
                        "expires_at": trial.expires_at.isoformat(),
                    },
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "commercial_history": False,
                },
            }
            snapshot = SubscriptionPricingSnapshot(
                owner_id=row.owner_id,
                restaurant_id=row.restaurant_id,
                source_subscription_id=trial.id,
                context="active_month",
                calculated_at=end,
                pricing={},
                parameters=provenance,
                **measured,
            )
            session.add(snapshot)
            trial.status = "expired"
            await session.flush()
            result = {
                "fixture": "explicit fictitious clock advancement, not 30 days of observed commercial service",
                "restaurant_id": row.restaurant_id,
                "trial_id": trial.id,
                "snapshot_id": snapshot.id,
                "original_dates": original,
                "advanced_dates": {
                    "starts_at": trial.starts_at.isoformat(),
                    "expires_at": trial.expires_at.isoformat(),
                },
                "metrics_source": "actual empty local catalogue and order tables",
                "first_enrollment_trial_changed": False,
                "payments_created": False,
                "target": "127.0.0.1:55433/moulai_integrated",
            }
        (
            ROOT / "artifacts/operational-o3-20261108/finance-clock-fixture.json"
        ).write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    finally:
        await engine.dispose()


# ==============================================
# EXPLICIT LOCAL TEST ACKNOWLEDGEMENT
# No startup hook, worker, environment toggle or HTTP route can advance this clock.
# ==============================================


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--advance-fictitious-trial", action="store_true", required=True
    )
    parser.parse_args()
    sys.addaudithook(IntegrationNetworkGuard())
    print(json.dumps(asyncio.run(prepare())))
