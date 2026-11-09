# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# INDEPENDENT READ-ONLY OFFER OBSERVER
# Check preview purity, immutable old evidence and absence of unintended activation.
# ==============================================

"""Only the known marked local O4 database is readable; no business write is issued."""

from __future__ import annotations

# isort: split
# ==============================================
# FIXED LOCAL OBSERVATION CONTRACT
# Persist only hashes, counts and synthetic identifiers, never connection credentials.
# ==============================================

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.prepare_operational_o4 import fingerprint
from scripts.run_operational_local import (
    IntegrationNetworkGuard,
    resolve_instance,
)

# ==============================================
# INDEPENDENT COMMITTED-STATE ASSERTIONS
# A distinct connection and explicit read-only transaction cannot rely on fixture rollback.
# ==============================================


async def verify(*, phase: str) -> None:
    """Observe before, after preview or after explicit confirmation and compare retained evidence."""
    configuration = resolve_instance(supplied=None)
    output = ROOT / "artifacts/operational-followup-20261109"
    fixture = json.loads(
        (output / "obsolete-offer-fixture.json").read_text(encoding="utf-8")
    )
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with engine.connect() as connection, connection.begin():
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            identity = (
                await connection.execute(
                    text(
                        "SELECT current_database(),current_user,host(inet_server_addr()),inet_server_port(),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"
                    )
                )
            ).one()
            if tuple(identity) != (
                "moulai_integrated",
                "moulai_integrated",
                "127.0.0.1",
                55433,
                "moulai-operational-local:" + configuration.instance_id,
            ):
                raise RuntimeError("requote_observer_target_mismatch")
            frozen = (
                await connection.execute(
                    text(
                        "SELECT pricing,parameters FROM subscription_pricing_snapshots WHERE subscription_id=:s"
                    ),
                    {"s": fixture["subscription_id"]},
                )
            ).one()
            digest = hashlib.sha256(
                json.dumps(list(frozen), sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if digest != fixture["frozen_snapshot_sha256"]:
                raise RuntimeError("requote_old_snapshot_changed")
            state = await fingerprint(connection=connection)
            active = (
                await connection.execute(
                    text(
                        "SELECT id,status,amount,currency,starts_at,expires_at FROM subscriptions WHERE restaurant_id=9 AND status='active' ORDER BY id"
                    )
                )
            ).all()
            active_digest = hashlib.sha256(
                json.dumps(
                    [list(row) for row in active], default=str, sort_keys=True
                ).encode()
            ).hexdigest()
            baseline_path = output / "requote-before.json"
            if phase == "before":
                if baseline_path.exists():
                    raise RuntimeError("requote_observer_baseline_exists")
            else:
                baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
                if active_digest != baseline["active_period_sha256"]:
                    raise RuntimeError("requote_active_period_changed")
                if phase == "complete":
                    allowed = {
                        "subscriptions",
                        "payments",
                        "subscription_pricing_snapshots",
                        "subscription_feature_requests",
                    }
                    for table, values in baseline["fingerprint"]["tables"].items():
                        if table not in allowed and state["tables"][table] != values:
                            raise RuntimeError("requote_unrelated_table_changed")
                # JSON round-tripping changes tuples to lists, not catalogue contents.
                # Preserve every fingerprint key and compare the canonical structures.
                if phase == "preview" and json.dumps(
                    state, sort_keys=True, default=str
                ) != json.dumps(baseline["fingerprint"], sort_keys=True, default=str):
                    raise RuntimeError("requote_preview_persisted_changes")
            status = await connection.scalar(
                text("SELECT status FROM payments WHERE id=:p"),
                {"p": fixture["payment_id"]},
            )
            if status != ("cancelled" if phase == "complete" else "pending"):
                raise RuntimeError("requote_unexpected_original_state")
            pending = await connection.scalar(
                text(
                    "SELECT count(*) FROM subscriptions WHERE restaurant_id=9 AND status IN ('pending','pending_payment')"
                )
            )
            if pending != 1:
                raise RuntimeError("requote_pending_not_unique")
            successor = await connection.scalar(
                text(
                    "SELECT subscription_id FROM subscription_pricing_snapshots WHERE parameters->'replacement'->>'payment_id'=:p"
                ),
                {"p": str(fixture["payment_id"])},
            )
            if phase == "complete" and successor is None:
                raise RuntimeError("requote_lineage_missing")
            report = {
                "status": "PASS",
                "phase": phase,
                "target": "127.0.0.1:55433/moulai_integrated",
                "revision": state["revision"],
                "old_snapshot_unchanged": True,
                "active_period_sha256": active_digest,
                "pending_count": pending,
                "successor_subscription_id": successor,
                "preview_read_only": phase == "preview",
                "fingerprint": state if phase == "before" else None,
            }
            (output / f"requote-{phase}.json").write_text(
                json.dumps(report, indent=2, default=str), encoding="utf-8"
            )
            print(
                json.dumps({"status": "PASS", "phase": phase, "pending_count": pending})
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase", choices=["before", "preview", "complete"], required=True
    )
    options = parser.parse_args()
    sys.addaudithook(IntegrationNetworkGuard())
    asyncio.run(verify(phase=options.phase))
