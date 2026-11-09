# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# INDEPENDENT LOCAL ENROLLMENT OBSERVATION
# Confirm the two UI-created fictitious companies and their payment states from a new, explicitly read-only connection.
# ==============================================

"""Read only the pinned local review; never send messages, run workers or modify subscription dates."""

from __future__ import annotations

# isort: split
# ==============================================
# EXPLICIT CONNECTION AND REPORT DEPENDENCIES
# Keep all credentials inside the protected instance configuration and exclude them from the resulting evidence.
# ==============================================

import asyncio
import json
import sys
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.run_operational_local import (
    IntegrationNetworkGuard,
    resolve_instance,
)

# ==============================================
# INDEPENDENT DATABASE OBSERVER
# Check the live database identity inside the same read-only transaction used for every subsequent assertion.
# ==============================================


async def verify() -> dict[str, object]:
    """Refuse any foreign target or unexpected result; preserve both successful and blocked recipe states."""
    configuration = resolve_instance(supplied=None)
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            identity = (
                (
                    await connection.execute(
                        text(
                            "SELECT current_database() AS database, current_user AS username, inet_server_addr()::text AS address, inet_server_port() AS port, shobj_description(oid,'pg_database') AS marker FROM pg_database WHERE datname=current_database()"
                        )
                    )
                )
                .mappings()
                .one()
            )
            assert dict(identity) == {
                "database": "moulai_integrated",
                "username": "moulai_integrated",
                "address": "127.0.0.1/32",
                "port": 55433,
                "marker": "moulai-operational-local:" + configuration.instance_id,
            }
            assert (
                await connection.scalar(
                    text("SELECT version_num FROM public.alembic_version")
                )
                == "o420261108"
            )
            assert await connection.scalar(text("SHOW transaction_read_only")) == "on"
            dossiers = (
                (
                    await connection.execute(
                        text(
                            "SELECT d.id,d.organization_id,d.restaurant_id,d.status,count(e.id) FILTER (WHERE e.event='accepted') AS accepted,count(e.id) FILTER (WHERE e.event='acknowledged') AS informed,count(e.id) FILTER (WHERE e.event='declined') AS optional_declined FROM enrollment_dossiers d JOIN enrollment_document_events e ON e.identity_id=d.identity_id WHERE d.id IN (1,2) GROUP BY d.id,d.organization_id,d.restaurant_id,d.status ORDER BY d.id"
                        )
                    )
                )
                .mappings()
                .all()
            )
            assert len(dossiers) == 2
            assert all(
                row["status"] == "completed"
                and row["accepted"] >= 1
                and row["informed"] >= 1
                and row["optional_declined"] >= 1
                for row in dossiers
            )
            subscriptions = (
                (
                    await connection.execute(
                        text(
                            "SELECT s.id,s.restaurant_id,s.status,s.billing_cycle,s.amount::text,s.currency,s.starts_at::text,s.expires_at::text,(SELECT count(*) FROM subscription_features f WHERE f.subscription_id=s.id) AS features FROM subscriptions s WHERE s.restaurant_id IN (8,9) ORDER BY s.id"
                        )
                    )
                )
                .mappings()
                .all()
            )
            assert (
                sum(
                    row["status"] == "trial" and row["restaurant_id"] == 8
                    for row in subscriptions
                )
                == 1
            )
            assert (
                sum(
                    row["status"] == "active" and row["restaurant_id"] == 9
                    for row in subscriptions
                )
                == 1
            )
            payments = (
                (
                    await connection.execute(
                        text(
                            "SELECT p.id,p.subscription_id,p.status,p.amount::text,p.currency,r.review_status,(SELECT count(*) FROM manual_payment_audit a WHERE a.payment_id=p.id AND a.action='receipt_approved') AS approvals FROM payments p JOIN manual_payment_receipts r ON r.payment_id=p.id WHERE p.restaurant_id=9 ORDER BY p.id"
                        )
                    )
                )
                .mappings()
                .all()
            )
            assert (
                len(payments) == 1
                and payments[0]["status"] == "paid"
                and payments[0]["review_status"] == "approved"
                and payments[0]["approvals"] == 1
            )
            # ==============================================
            # NO COMPATIBILITY NUMBER AS A CONTACT
            # Browser account linkage is not proof that a Telegram destination exists or that a message may be sent.
            # ==============================================

            reminders = (
                (
                    await connection.execute(
                        text(
                            "SELECT recipient,status,(target_chat_id IS NULL) AS no_contact,count(*) AS count FROM subscription_reminders WHERE subscription_id IN (SELECT id FROM subscriptions WHERE restaurant_id IN (8,9)) GROUP BY recipient,status,(target_chat_id IS NULL) ORDER BY recipient,status"
                        )
                    )
                )
                .mappings()
                .all()
            )
            assert reminders and all(
                row["no_contact"] and row["status"] in {"blocked", "cancelled"}
                for row in reminders
            )
            bases = (
                (
                    await connection.execute(
                        text(
                            "SELECT country_code,currency,amount::text,revision FROM subscription_base_prices WHERE effective_from<=now() AND (effective_until IS NULL OR now()<effective_until) ORDER BY country_code,currency"
                        )
                    )
                )
                .mappings()
                .all()
            )
            assert (
                len(bases) == 1
                and bases[0]["country_code"] == "DZ"
                and bases[0]["currency"] == "DZD"
            )
            return {
                "status": "PASS",
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "target": "127.0.0.1:55433/moulai_integrated",
                "transaction_read_only": True,
                "revision": "o420261108",
                "dossiers": [dict(row) for row in dossiers],
                "subscriptions": [dict(row) for row in subscriptions],
                "payments": [dict(row) for row in payments],
                "reminders": [dict(row) for row in reminders],
                "base_prices": [dict(row) for row in bases],
                "Neon_connection": False,
                "bank_transfer": False,
                "notifications": False,
            }
    finally:
        await engine.dispose()


# ==============================================
# SAFE LOCAL EVIDENCE DELIVERY
# Save only synthetic business facts; exceptions never print connection details or private account material.
# ==============================================


if __name__ == "__main__":
    sys.addaudithook(IntegrationNetworkGuard())
    try:
        report = asyncio.run(verify())
        (ROOT / "artifacts/operational-o3-20261108/persisted-observer.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "read_only": True,
                    "payments": len(report["payments"]),
                }
            )
        )
    except (
        AssertionError,
        OSError,
        RuntimeError,
        ValueError,
        SQLAlchemyError,
    ) as error:
        print(json.dumps({"status": "FAIL", "type": type(error).__name__}))
        raise SystemExit(1) from None
