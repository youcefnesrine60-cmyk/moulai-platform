# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OFFLINE TEST STORAGE
# Create only the relational fixture schema and reserve independent workspace temporary paths.
# ==============================================

"""Keep SQLite fixtures and pytest temporary storage separate from permanent databases."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND WORKSPACE BOUNDARY
# No application configuration, database credentials or external connection is loaded here.
# ==============================================

from collections.abc import Iterable
from pathlib import Path
from tempfile import mkdtemp

from sqlalchemy import Table
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapper

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ==============================================
# REQUIRED SQLITE RELATIONS AND THEIR PARENTS
# Preserve original table constraints while excluding unrelated PostgreSQL-specific tables.
# ==============================================


def create_sqlite_schema(
    *,
    engine: Engine,
    tables: Iterable[Table],
    mappers: Iterable[Mapper[object]] = (),
) -> None:
    """Create selected fixture tables and every referenced parent in a SQLite engine.

    Forward foreign-key and configured eager-loader dependencies are included recursively.
    The original metadata,
    constraints, ownership fields and session guards are never rewritten. A fixture
    requiring a PostgreSQL-specific table must use PostgreSQL instead of this helper.
    Non-SQLite engines, empty selections and mixed metadata are rejected before DDL.
    """
    if engine.dialect.name != "sqlite":
        raise ValueError("offline_schema_requires_sqlite")
    selected = set(tables)
    if not selected:
        raise ValueError("offline_schema_requires_tables")
    metadata = next(iter(selected)).metadata
    mapped = {mapper.local_table: mapper for mapper in mappers}
    pending = list(selected)
    while pending:
        table = pending.pop()
        if table.metadata is not metadata:
            raise ValueError("offline_schema_requires_shared_metadata")
        for foreign_key in table.foreign_keys:
            parent = foreign_key.column.table
            if parent not in selected:
                selected.add(parent)
                pending.append(parent)
        mapper = mapped.get(table)
        if mapper is not None:
            for relation in mapper.relationships:
                if relation.lazy not in {"joined", "selectin", "subquery", "immediate"}:
                    continue
                related = relation.mapper.local_table
                if not isinstance(related, Table):
                    raise TypeError("offline_schema_requires_table_mappings")
                if related not in selected:
                    selected.add(related)
                    pending.append(related)
    metadata.create_all(engine, tables=sorted(selected, key=lambda table: table.key))


# ==============================================
# OWNED PYTEST TEMPORARY DIRECTORY
# Reserve a unique path so pytest never reuses an inaccessible or shared Windows temp root.
# ==============================================


def reserve_pytest_directory() -> Path:
    """Reserve a new basetemp inside artifacts; never delete or repair another run's directory."""
    root = PROJECT_ROOT.resolve()
    parent = (root / "artifacts" / "pytest-temporary").resolve()
    if not parent.is_relative_to(root):
        raise RuntimeError("pytest_temporary_root_outside_workspace")
    parent.mkdir(parents=True, exist_ok=True)
    directory = Path(mkdtemp(prefix="run-", dir=parent)).resolve()
    if not directory.is_relative_to(parent) or not directory.is_relative_to(root):
        raise RuntimeError("pytest_temporary_directory_outside_workspace")
    return directory
