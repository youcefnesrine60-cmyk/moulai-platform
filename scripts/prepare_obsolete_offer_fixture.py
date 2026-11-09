# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT SYNTHETIC LEGACY-OFFER FIXTURE
# Construct one unpaid test offer with pre-followup metadata before immutable insertion.
# ==============================================

"""Test data construction only: never alter an existing snapshot, tariff, receipt or payment.

The synthetic legacy contract omits the new payment-policy evidence but uses the
current approved calculation unchanged. This fixture is not a historical invoice
or proof that an old production writer remains operational.
"""

from __future__ import annotations

# isort: split
# ==============================================
# CLOSED LOCAL FIXTURE DEPENDENCIES
# Keep temporary metadata adaptation inside this process, never inside the running server.
# ==============================================

import asyncio
import hashlib
import json
import sys
from collections.abc import (
    Awaitable,
    Callable,
)
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    ParamSpec,
)
from unittest.mock import patch

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

if TYPE_CHECKING:
    from app.services.business.subscription_types import PricingResult

Arguments = ParamSpec("Arguments")


# ==============================================
# PRE-INSERTION LEGACY METADATA ADAPTER
# Preserve every monetary value while deliberately representing the older evidence contract.
# ==============================================


def legacy_metadata(
    *, calculation: Callable[Arguments, Awaitable[PricingResult]]
) -> Callable[Arguments, Awaitable[PricingResult]]:
    """Adapt only a newly constructed synthetic result, not a retained database record."""

    # ==============================================
    # FORWARDED HISTORICAL EVIDENCE CONTRACT
    # Strip new provenance only from this newly constructed fixture result.
    # ==============================================

    async def invoke(
        *args: Arguments.args, **kwargs: Arguments.kwargs
    ) -> PricingResult:
        """Forward the exact typed call and remove only the newly introduced evidence keys."""
        result = await calculation(*args, **kwargs)
        result["parameters"].pop("payment_adjustment_rates", None)
        result["parameters"].pop("payment_adjustment_rate", None)
        return result

    return invoke


# ==============================================
# ONE KNOWN SYNTHETIC RESTAURANT ONLY
# Refuse another instance, an existing pending offer, missing paid history or a changed reference price.
# ==============================================


async def prepare() -> None:
    """Create a receipt-free fixture once; the subsequent replacement uses real authenticated UI routes."""
    configuration = resolve_instance(supplied=None)
    configuration.process_environment()
    from app.integration.web import attest_database
    from app.schemas.manual_payment import ManualSubscriptionCheckout
    from app.services.business import subscription_service
    from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip

    output = (
        ROOT / "artifacts/operational-followup-20261109/obsolete-offer-fixture.json"
    )
    if output.exists():
        raise RuntimeError("obsolete_offer_fixture_already_prepared")
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await attest_database(session=session, configuration=configuration)
            await session.rollback()
            async with session.begin():
                row = (
                    await session.execute(
                        text(
                            "SELECT r.owner_id,r.organization_id,r.name FROM restaurants r WHERE r.id=9 FOR UPDATE"
                        )
                    )
                ).one()
                if (
                    row.organization_id != 11
                    or row.name != "LOCAL-FAKE — Restaurant O4"
                ):
                    raise RuntimeError("obsolete_offer_fixture_restaurant_changed")
                if await session.scalar(
                    text(
                        "SELECT count(*) FROM subscriptions WHERE restaurant_id=9 AND status IN ('pending','pending_payment')"
                    )
                ):
                    raise RuntimeError("obsolete_offer_fixture_pending_exists")
                if (
                    await session.scalar(
                        text(
                            "SELECT count(*) FROM subscriptions WHERE restaurant_id=9 AND status='active'"
                        )
                    )
                    != 1
                ):
                    raise RuntimeError("obsolete_offer_fixture_paid_history_required")
                if (
                    await session.scalar(
                        text(
                            "SELECT amount FROM subscription_base_prices WHERE country_code='DZ' AND currency='DZD' AND effective_until IS NULL"
                        )
                    )
                    != 3000
                ):
                    raise RuntimeError("obsolete_offer_fixture_reference_changed")
                plan = await session.scalar(
                    text(
                        "SELECT id FROM subscription_plans WHERE code='basic' AND active"
                    )
                )
                original = subscription_service.calculate_subscription_pricing
                with patch.object(
                    subscription_service,
                    "calculate_subscription_pricing",
                    legacy_metadata(calculation=original),
                ):
                    payment = await SubscriptionCheckoutService(session=session).create(
                        owner_id=row.owner_id,
                        data=ManualSubscriptionCheckout(
                            restaurant_id=9,
                            plan_id=plan,
                            billing_cycle="monthly",
                            payment_method="ccp",
                            currency="DZD",
                        ),
                    )
        async with async_sessionmaker(engine)() as observer:
            frozen = (
                await observer.execute(
                    text(
                        "SELECT pricing,parameters FROM subscription_pricing_snapshots WHERE subscription_id=:s"
                    ),
                    {"s": payment.subscription_id},
                )
            ).one()
            frozen_digest = hashlib.sha256(
                json.dumps(list(frozen), sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            active_rows = (
                await observer.execute(
                    text(
                        "SELECT id,status,amount,currency,starts_at,expires_at FROM subscriptions WHERE restaurant_id=9 AND status='active' ORDER BY id"
                    )
                )
            ).all()
            active_digest = hashlib.sha256(
                json.dumps(
                    [list(row) for row in active_rows], default=str, sort_keys=True
                ).encode()
            ).hexdigest()
            snapshot_count = await observer.scalar(
                text(
                    "SELECT count(*) FROM subscription_pricing_snapshots WHERE restaurant_id=9"
                )
            )
        output.write_text(
            json.dumps(
                {
                    "status": "PREPARED",
                    "synthetic_legacy_metadata_fixture": True,
                    "created_by": "explicit local technical fixture; replacement must use authenticated UI",
                    "payment_id": payment.id,
                    "subscription_id": payment.subscription_id,
                    "amount": str(payment.amount),
                    "B_unchanged": "3000 DZD",
                    "frozen_snapshot_sha256": frozen_digest,
                    "snapshot_count": snapshot_count,
                    "active_period_sha256": active_digest,
                    "existing_records_modified": False,
                    "receipt_or_funds": False,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": "PREPARED",
                    "payment_id": payment.id,
                    "synthetic_fixture": True,
                }
            )
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.addaudithook(IntegrationNetworkGuard())
    asyncio.run(prepare())
