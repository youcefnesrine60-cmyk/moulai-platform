# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================


# ==============================================
# STAGING SQL REPLAY SUPPORT
# Compare schema and data hashes and run only fixed local database tools.
# ==============================================

"""No remote credentials, environment discovery or application startup."""

from __future__ import annotations

# isort: split
# ==============================================
# HASHING AND LOCAL PROCESS DEPENDENCIES
# Keep diagnostic output independent of database row contents and credentials.
# ==============================================

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts/staging-preparation-20261109"
PG = Path(r"C:\Program Files\PostgreSQL\18\bin")

# ==============================================
# SECRET-FREE CHILD PROCESS OUTCOMES
# Driver and pg_dump errors can contain connection details, so retain only type/code.
# ==============================================


def child(*, arguments: list[str], environment: dict[str, str]) -> bytes:
    """Run a fixed tool once and refuse retries, printing no credential or SQL data."""
    with tempfile.TemporaryFile() as captured:
        result = subprocess.run(
            arguments,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=captured,
            stderr=captured,
            check=False,
        )
        if result.returncode:
            raise RuntimeError("staging_child_failed:" + Path(arguments[0]).stem)
        captured.seek(0)
        return captured.read()


# ==============================================
# COMPLETE APPLICATION CATALOGUE AND ROW HASHES
# Normalize timezone within the observation transaction without changing stored data.
# ==============================================


async def fingerprint(*, connection: asyncpg.Connection) -> dict[str, object]:
    """Hash public definitions and exact rows; credentials and row contents stay private."""
    async with connection.transaction(readonly=True):
        await connection.execute("SET LOCAL TIME ZONE 'UTC'")
        catalogue = {}
        queries = {
            "columns": "SELECT table_name,column_name,data_type,udt_name,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position",
            "constraints": "SELECT c.relname,k.conname,pg_get_constraintdef(k.oid),k.convalidated FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY 1,2",
            "indexes": "SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY 1,2",
            "triggers": "SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY 1,2",
        }
        for name, query in queries.items():
            rows = [list(row) for row in await connection.fetch(query)]
            catalogue[name] = hashlib.sha256(
                json.dumps(rows, sort_keys=True, default=str).encode()
            ).hexdigest()
        tables = {}
        for row in await connection.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        ):
            name = row[0]
            quoted = '"' + name.replace('"', '""') + '"'
            record = await connection.fetchrow(
                "SELECT count(*),md5(coalesce(string_agg(v,E'\\n' ORDER BY v),'')) "
                "FROM (SELECT to_jsonb(t)::text AS v FROM public." + quoted + " t) s"
            )
            tables[name] = {"count": record[0], "digest": record[1]}
        revision = await connection.fetchval("SELECT version_num FROM alembic_version")
    return {"revision": revision, "catalogue": catalogue, "tables": tables}
