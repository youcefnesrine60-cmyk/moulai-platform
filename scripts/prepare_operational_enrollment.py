# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT LOCAL ENROLLMENT REFERENCE SETUP
# Publish approved trial/basic inclusions and fictitious documents, with separate synthetic country and payment reviewers.
# ==============================================

"""No company CLI creation, foreign tariff, paid feature price, bank account instruction, cash grant or remote operation."""

from __future__ import annotations

# isort: split
# ==============================================
# PINNED LOCAL DEPENDENCIES
# Account credentials remain in the existing protected acceptance file and never enter reports or command arguments.
# ==============================================

import asyncio
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from scripts.run_operational_local import (
    IntegrationNetworkGuard,
    resolve_instance,
)

# ==============================================
# APPROVED REFERENCES AND LOCAL TEST IDENTITIES
# The legacy numeric plan column is neutral compatibility metadata; only subscription_base_prices supplies B.
# ==============================================


async def prepare() -> dict[str, object]:
    """Create only missing explicit local references, refusing contradictory existing plan or feature configuration."""
    configuration = resolve_instance(supplied=None)
    configuration.process_environment()
    from app.integration.provision import (
        create_account,
        create_platform_admin,
    )
    from app.integration.web import attest_database
    from app.models.billing_country import EnrollmentDossier
    from app.models.subscription import (
        Feature,
        PlanFeature,
        Subscription,
        SubscriptionPlan,
    )
    from app.repositories.subscription_queries import base_select
    from app.services.business.enrollment_documents import publish_rehearsal_documents
    from app.services.business.subscription_contract import INCLUDED
    from app.services.business.subscription_reminders import schedule

    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await attest_database(session=session, configuration=configuration)
            await session.rollback()
            async with session.begin():
                await publish_rehearsal_documents(
                    session=session, marker=configuration.instance_id
                )
                for code in ("trial", "basic"):
                    plan = await session.scalar(
                        base_select(SubscriptionPlan).where(
                            SubscriptionPlan.code == code
                        )
                    )
                    if plan is None:
                        plan = SubscriptionPlan(
                            code=code,
                            name=code,
                            base_price=0,
                            plan_discount_percent=0,
                            active=True,
                            description="Approved inclusion contract; B resolved only from country price versions",
                        )
                        session.add(plan)
                        await session.flush()
                    if not plan.active:
                        raise ValueError("enrollment_existing_plan_inactive")
                    existing = set(
                        (
                            await session.scalars(
                                base_select(Feature)
                                .with_only_columns(Feature.code)
                                .join(PlanFeature, PlanFeature.feature_id == Feature.id)
                                .where(
                                    PlanFeature.plan_id == plan.id,
                                    PlanFeature.included.is_(True),
                                )
                            )
                        ).all()
                    )
                    if existing and existing != INCLUDED[code]:
                        raise ValueError("enrollment_existing_inclusions_conflict")
                    if not existing:
                        for key in sorted(INCLUDED[code]):
                            feature = await session.scalar(
                                base_select(Feature).where(Feature.code == key)
                            )
                            if feature is None:
                                feature = Feature(code=key, name=key)
                                session.add(feature)
                                await session.flush()
                            session.add(
                                PlanFeature(
                                    plan_id=plan.id,
                                    feature_id=feature.id,
                                    included=True,
                                )
                            )
                browser_subscriptions = (
                    await session.scalars(
                        base_select(Subscription)
                        .join(
                            EnrollmentDossier,
                            EnrollmentDossier.restaurant_id
                            == Subscription.restaurant_id,
                        )
                        .where(
                            EnrollmentDossier.status == "completed",
                            Subscription.status.in_(["active", "trial", "scheduled"]),
                        )
                    )
                ).all()
                for subscription in browser_subscriptions:
                    await schedule(session=session, subscription=subscription)
        accounts_path = configuration.directory / "private/acceptance-accounts.json"
        accounts = json.loads(accounts_path.read_text(encoding="utf-8"))
        if "billing-scenario" not in accounts:
            password = secrets.token_urlsafe(24)
            record = await create_account(
                configuration=configuration,
                username="billing-scenario",
                password=password,
            )
            accounts["billing-scenario"] = {**record, "password": password}
            accounts_path.write_text(json.dumps(accounts, indent=2), encoding="utf-8")
        for username, permission, legacy in (
            ("country-reviewer", "tenant.billing_country.manage", -970001),
            ("saas-reviewer", "payments.review", -970002),
        ):
            if username in accounts:
                continue
            password = secrets.token_urlsafe(24)
            record = await create_account(
                configuration=configuration, username=username, password=password
            )
            await create_platform_admin(
                configuration=configuration,
                subject=record["subject"],
                legacy_id=legacy,
                permissions=(permission,),
            )
            accounts[username] = {**record, "password": password}
            accounts_path.write_text(json.dumps(accounts, indent=2), encoding="utf-8")
        result = {
            "target": "127.0.0.1:55433/moulai_integrated",
            "revision": "o420261108",
            "plans": ["trial", "basic"],
            "feature_prices_created": False,
            "foreign_prices_created": False,
            "companies_created_by_cli": False,
            "local_reviewers": {
                "country-reviewer": ["tenant.billing_country.manage"],
                "saas-reviewer": ["payments.review"],
            },
            "documents": "LOCAL-TEST-20261108-v1; fictitious, no contractual value",
            "notifications_enabled": False,
        }
        (
            ROOT / "artifacts/operational-o3-20261108/local-prerequisites.json"
        ).write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    finally:
        await engine.dispose()


# ==============================================
# LOCAL OPERATOR ENTRY
# The socket guard is active before any setup call; no configuration file or commercial offer is fabricated.
# ==============================================


if __name__ == "__main__":
    sys.addaudithook(IntegrationNetworkGuard())
    print(json.dumps(asyncio.run(prepare())))
