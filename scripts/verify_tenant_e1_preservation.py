# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""SELECT-only post-E1 preservation check on the already admitted W connection."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import Any

from sqlalchemy import (
    event,
    text,
)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.rehearse_tenant_e1 import (
    TARGET,
    WRITER_BRANCH,
    BoundRehearsal,
    bind_writer,
    check_connection,
    verify_e1_catalog,
    verify_original_data,
)
from scripts.validate_tenant_e1_postgres import (
    failure_location,
    original_catalogs,
    sqlstate,
)

# ==============================================
# READ-ONLY W PRESERVATION CHECK
# ==============================================


async def inspect(*, bound: BoundRehearsal) -> dict[str, Any]:
    """Read original projections/catalogs and roll back the observation boundary."""
    from app.core.rehearsal_admission import read_only_connection_arguments

    engine = create_async_engine(
        bound.url,
        poolclass=NullPool,
        echo=False,
        connect_args=read_only_connection_arguments(),
    )

    # ==============================================
    # REFUSE ALL SQL OUTSIDE SELECT AND READ-ONLY CONTROL
    # ==============================================
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def select_only(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Reject any accidental DML/DDL before it reaches the driver."""
        normalized = statement.strip().upper()
        if (
            not normalized.startswith("SELECT ")
            and normalized != "SET TRANSACTION READ ONLY"
        ):
            raise RuntimeError("preservation_check_non_select_refused")

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                await connection.run_sync(
                    lambda c: check_connection(c, bound=bound, expected_revision=TARGET)
                )
                if (
                    await connection.scalar(
                        text("SELECT current_setting('transaction_read_only')")
                    )
                    != "on"
                ):
                    raise RuntimeError("read_only_transaction_required")
                await verify_original_data(
                    connection, baseline=bound.baseline, revision=TARGET
                )
                catalog = await verify_e1_catalog(
                    connection, legacy_tables=set(bound.baseline["tables"])
                )
                preserved = await original_catalogs(connection, bound=bound)
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "branch_id": WRITER_BRANCH,
        "revision": TARGET,
        "read_only": True,
        "transaction_rolled_back": True,
        "original_rows_and_sequences_unchanged": True,
        "original_catalogs_unchanged": True,
        "catalog": catalog,
        "original_catalogs": preserved,
    }


# ==============================================
# EXPLICIT ADMITTED INPUTS AND SAFE FAILURE REPORT
# ==============================================


def main() -> int:
    """Use the original G2 proof and an explicit evidence path, with no writes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--approved-sha256", required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    os.chdir(ROOT)
    os.environ.update(
        {
            "DEBUG": "false",
            "DB_ECHO": "false",
            "OIDC_DIAGNOSTICS_ENABLED": "false",
            "OIDC_ALLOW_LOCAL_HTTP": "false",
        }
    )
    try:
        bound = bind_writer(
            manifest_path=arguments.manifest,
            approved_sha256=arguments.approved_sha256,
            proof_path=arguments.proof,
            baseline_path=arguments.baseline,
        )
        report = asyncio.run(inspect(bound=bound))
        status = 0
    # Driver messages and parameters never enter evidence.
    except Exception as error:  # noqa: BLE001
        report = {
            "outcome": "blocked",
            "error_class": type(error).__name__,
            "sqlstate": sqlstate(error),
            "locations": failure_location(error),
        }
        status = 1
    arguments.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
