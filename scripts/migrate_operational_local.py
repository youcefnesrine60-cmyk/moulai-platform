# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNED LOCAL ADDITIVE MIGRATIONS
# Back up and rehearse the explicit O1/O2 parent transition before committing on the identified local instance.
# ==============================================

"""No remote URL, automatic retry, stamp, administrator grant or application startup."""

from __future__ import annotations

# isort: split
# ==============================================
# LOCAL DEPENDENCIES
# Secrets stay in memory and private backup storage; only attested local PostgreSQL is allowed.
# ==============================================

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from app.integration.local_setup import (
    PG,
    local_process,
)
from app.integration.process import local_host_lease
from scripts.prepare_operational_o4 import (
    fingerprint,
    verified_restoration_proof,
)
from scripts.run_operational_local import (
    IntegrationNetworkGuard,
    require_free_application_ports,
    resolve_instance,
)

# ==============================================
# REHEARSED TRANSACTION
# Alembic writes its own version in the same checked transaction; rollback rehearsal changes nothing durably.
# ==============================================


async def migrate(*, target: str) -> dict[str, object]:
    """Refuse foreign clients and unexpected revisions, then apply the selected exact parent transition once."""
    expected = {
        "o120261108": "d1d20261105",
        "o220261108": "o120261108",
        "o420261108": "o220261108",
        "o520261111": "o420261108",
    }[target]
    configuration = resolve_instance(supplied=None)
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT current_database(),current_user,inet_server_port(),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"
                    )
                )
            ).one()
            if tuple(row) != (
                "moulai_integrated",
                "moulai_integrated",
                55433,
                "moulai-operational-local:" + configuration.instance_id,
            ):
                raise RuntimeError("local_migration_target_mismatch")
            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            clients = await connection.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"
                )
            )
            if revision != expected or clients:
                raise RuntimeError("local_migration_revision_or_writer_mismatch")
            if target in {"o420261108", "o520261111"}:
                proof = verified_restoration_proof(
                    configuration=configuration, target=target
                )
                current = await fingerprint(connection=connection)
                if json.dumps(current, sort_keys=True) != json.dumps(
                    proof["source_before"], sort_keys=True
                ):
                    raise RuntimeError(
                        "local_migration_source_changed_since_restoration"
                    )
            await connection.rollback()

            # ==============================================
            # CHECKED ALEMBIC ENTRY
            # Reuse the restricted environment and one supplied connection, never a discovered URL.
            # ==============================================

            def upgrade(sync: Connection) -> None:
                """Apply the new revision without modifying historical migrations or revision rows manually."""
                settings = Config()
                settings.set_main_option(
                    "script_location", str(ROOT / "alembic_operational_local")
                )
                settings.set_main_option(
                    "version_locations", str(ROOT / "alembic/versions")
                )
                settings.set_main_option("path_separator", "os")
                settings.attributes.update(
                    connection=sync, operational_configuration=configuration
                )
                command.upgrade(settings, target)

            transaction = await connection.begin()
            await connection.run_sync(upgrade)
            assert (
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                == target
            )
            await transaction.rollback()
            assert (
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                == expected
            )
            await connection.rollback()
            async with connection.begin():
                await connection.execute(
                    text(
                        "LOCK TABLE public.admin_logs,public.admins IN ACCESS EXCLUSIVE MODE"
                    )
                )
                await connection.run_sync(upgrade)
        async with engine.connect() as observer:
            assert (
                await observer.scalar(text("SELECT version_num FROM alembic_version"))
                == target
            )
            if target == "o520261111":
                final = await fingerprint(connection=observer)
                if json.dumps(final, sort_keys=True) != json.dumps(
                    proof["forward"], sort_keys=True
                ):
                    raise RuntimeError(
                        "local_migration_final_catalogue_or_rows_mismatch"
                    )
        return {
            "before": expected,
            "after": target,
            "transaction_rollback_rehearsal": True,
            "independent_observer": True,
        }
    finally:
        await engine.dispose()


# ==============================================
# PRIVATE BACKUP AND EXCLUSIVE PROCESS
# Start only the marker-owned cluster; a running host or occupied port prevents any action.
# ==============================================


def main() -> int:
    """Prepare a verified archive, migrate once and stop this script's owned PostgreSQL process."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        required=True,
        choices=("o120261108", "o220261108", "o420261108", "o520261111"),
    )
    options = parser.parse_args()
    configuration = resolve_instance(supplied=None)
    sys.addaudithook(IntegrationNetworkGuard())
    with local_host_lease(directory=configuration.directory):
        require_free_application_ports()
        local_process(
            arguments=[
                str(PG / "pg_ctl.exe"),
                "-D",
                str(configuration.directory / "postgres-data"),
                "-l",
                str(configuration.directory / "postgres.log"),
                "-o",
                "-h 127.0.0.1 -p 55433 -c log_min_error_statement=panic",
                "-w",
                "start",
            ]
        )
        try:
            from sqlalchemy.engine import make_url

            if options.target in {"o420261108", "o520261111"}:
                proof = verified_restoration_proof(
                    configuration=configuration, target=options.target
                )
                result = asyncio.run(migrate(target=options.target))
                result.update(
                    backup_reference=proof["backup_reference"],
                    backup_sha256=proof["backup_sha256"],
                    actual_restore_verified=True,
                    source_instance=configuration.instance_id,
                )
                destination = ROOT / (
                    "artifacts/operational-o3-20261108/review-migration.json"
                    if options.target == "o420261108"
                    else "artifacts/saas-documents-20261111/review-migration.json"
                )
                destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
                (configuration.directory / "schema.json").write_text(
                    json.dumps(
                        {
                            "revision": result["after"],
                            "public_tables": (
                                101 if options.target == "o420261108" else 103
                            ),
                            "target": "127.0.0.1:55433/moulai_integrated",
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                print(
                    json.dumps(
                        {
                            "status": "PASS",
                            "revision": result["after"],
                            "actual_restore_verified": True,
                        }
                    )
                )
                return 0

            backups = configuration.directory / "private" / "backups"
            backups.mkdir(exist_ok=True)
            backup = backups / (
                "before-" + options.target + "-" + uuid4().hex + ".dump"
            )
            environment = {
                **os.environ,
                "PGPASSWORD": make_url(configuration.database_url).password or "",
                "PGSSLMODE": "disable",
            }
            arguments = ["-h", "127.0.0.1", "-p", "55433", "-U", "moulai_integrated"]
            dumped = subprocess.run(
                [
                    str(PG / "pg_dump.exe"),
                    *arguments,
                    "-d",
                    "moulai_integrated",
                    "-Fc",
                    "-f",
                    str(backup),
                ],
                env=environment,
                capture_output=True,
                timeout=120,
                check=False,
            )
            if dumped.returncode != 0:
                raise RuntimeError("local_backup_failed")
            listed = subprocess.run(
                [str(PG / "pg_restore.exe"), "--list", str(backup)],
                capture_output=True,
                timeout=30,
                check=False,
            )
            if (
                listed.returncode != 0
                or b"admin_logs" not in listed.stdout
                or b"alembic_version" not in listed.stdout
            ):
                raise RuntimeError("local_backup_inventory_failed")
            result = asyncio.run(migrate(target=options.target))
            result.update(
                backup_reference=str(backup),
                backup_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
                backup_inventory_checked=True,
                target="127.0.0.1:55433/moulai_integrated",
            )
            destination = (
                ROOT
                / "artifacts/operational-milestone-20261108"
                / ("migration-" + options.target + ".json")
            )
            destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "revision": result["after"],
                        "local_backup": True,
                    }
                )
            )
            return 0
        finally:
            local_process(
                arguments=[
                    str(PG / "pg_ctl.exe"),
                    "-D",
                    str(configuration.directory / "postgres-data"),
                    "-m",
                    "fast",
                    "-w",
                    "stop",
                ]
            )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        RuntimeError,
        ValueError,
        SQLAlchemyError,
        subprocess.SubprocessError,
    ) as error:
        print(
            json.dumps({"status": "STOPPED", "type": type(error).__name__}),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
