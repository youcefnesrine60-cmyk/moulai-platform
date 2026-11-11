# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# INDEPENDENT READ-ONLY DOCUMENTARY OBSERVATION
# Compare financial rows with the verified pre-O5 backup and inspect documentary evidence from a separate session.
# ==============================================

"""No mutation, worker, notification, financial command or remote database access."""

from __future__ import annotations

# isort: split
# ==============================================
# EXPLICIT LOCAL CONNECTION AND EVIDENCE
# Read only the protected instance configuration; report digests and counts rather than private financial records.
# ==============================================

import asyncio
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from scripts.prepare_operational_o4 import verified_restoration_proof
from scripts.run_operational_local import (
    IntegrationNetworkGuard,
    resolve_instance,
)

# ==============================================
# INDEPENDENT COMMITTED-STATE READ
# An explicitly read-only transaction cannot hide writes or substitute a fixture rollback for service atomicity.
# ==============================================


async def verify() -> dict[str, object]:
    """Require exact local identity/revision and unchanged retained financial tables, or stop."""
    configuration = resolve_instance(supplied=None)
    configuration.process_environment()
    from app.integration.web import attest_database

    proof = verified_restoration_proof(configuration=configuration, target="o520261111")
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with AsyncSession(engine) as session, session.begin():
            await session.execute(text("SET TRANSACTION READ ONLY"))
            await attest_database(session=session, configuration=configuration)
            assert (
                await session.scalar(text("SELECT version_num FROM alembic_version"))
                == "o520261111"
            )
            checked: dict[str, object] = {}
            for table in (
                "payments",
                "subscriptions",
                "subscription_pricing_snapshots",
                "manual_payment_receipts",
                "manual_payment_audit",
                "cash_collections",
                "cash_collection_attempts",
            ):
                row = (
                    await session.execute(
                        text(
                            f"SELECT count(*),md5(coalesce(string_agg(to_jsonb(t)::text,chr(10) ORDER BY to_jsonb(t)::text),'')) FROM public.\"{table}\" t"
                        )
                    )
                ).one()
                current = {"count": row[0], "digest": row[1]}
                if current != proof["source_before"]["tables"][table]:
                    raise RuntimeError("document_recipe_changed_financial_history")
                checked[table] = current
            documents = (
                await session.execute(
                    text(
                        "SELECT id,public_id,content,sha256 FROM subscription_documents ORDER BY id"
                    )
                )
            ).all()
            for document in documents:
                digest = hashlib.sha256(
                    json.dumps(
                        document.content,
                        sort_keys=True,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode()
                ).hexdigest()
                if digest != document.sha256:
                    raise RuntimeError("document_retained_content_digest_mismatch")
            return {
                "status": "PASS",
                "target": "127.0.0.1:55433/moulai_integrated",
                "revision": "o520261111",
                "read_only": True,
                "financial_history_identical_to_pre_migration_backup": checked,
                "documents": len(documents),
                "document_events": await session.scalar(
                    text("SELECT count(*) FROM subscription_document_events")
                ),
                "content_digests_verified": True,
                "remote_connection": False,
            }
    finally:
        await engine.dispose()


# ==============================================
# ALLOWLISTED REPORT ENTRY
# No credential or bank proof is written into the public evidence artifact.
# ==============================================


if __name__ == "__main__":
    sys.addaudithook(IntegrationNetworkGuard())
    result = asyncio.run(verify())
    output = ROOT / "artifacts/saas-documents-20261111/independent-observer.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "report": str(output),
                "financial_history_unchanged": True,
            }
        )
    )
