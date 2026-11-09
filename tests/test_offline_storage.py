# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OFFLINE STORAGE REGRESSIONS
# Verify selective fixture DDL, intact integrity rules and independent workspace temporary paths.
# ==============================================

"""Use private SQLite engines and synthetic metadata; never connect to PostgreSQL."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND REAL LOCAL DDL
# Keep unsupported PostgreSQL syntax in unrelated metadata to reproduce the original failure.
# ==============================================

from unittest.mock import MagicMock

import pytest
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    create_engine,
    inspect,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Session,
    registry,
    relationship,
)

from test_support.offline_storage import (
    create_sqlite_schema,
    reserve_pytest_directory,
)

# ==============================================
# SELECTED TABLES RETAIN THEIR CONSTRAINTS
# Follow foreign keys recursively without compiling an unrelated interval constraint.
# ==============================================


def test_sqlite_selection_keeps_dependencies_and_integrity() -> None:
    """Create real parent/child tables and enforce their original CHECK without changing metadata."""
    metadata = MetaData()
    parent = Table("parent", metadata, Column("id", Integer, primary_key=True))
    child = Table(
        "child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", ForeignKey("parent.id")),
        Column("value", Integer, nullable=False),
        CheckConstraint("value > 0", name="positive_value"),
    )
    unrelated = Table(
        "postgresql_only",
        metadata,
        Column("id", Integer, primary_key=True),
        CheckConstraint(
            "INTERVAL '30 days' > INTERVAL '0 days'", name="postgresql_interval"
        ),
    )
    original_tables = dict(metadata.tables)
    original_constraints = set(unrelated.constraints)
    engine = create_engine("sqlite://")
    try:
        create_sqlite_schema(engine=engine, tables=[child])
        assert set(inspect(engine).get_table_names()) == {"parent", "child"}
        with engine.begin() as connection:
            connection.execute(parent.insert().values(id=1))
            connection.execute(child.insert().values(id=1, parent_id=1, value=2))
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(child.insert().values(id=2, parent_id=1, value=-1))
        assert dict(metadata.tables) == original_tables
        assert set(unrelated.constraints) == original_constraints
    finally:
        engine.dispose()


# ==============================================
# EAGER RELATIONSHIPS ARE REAL SQL DEPENDENCIES
# Include automatically loaded child tables without following every unrelated metadata entry.
# ==============================================


def test_sqlite_selection_includes_eager_child_relations() -> None:
    """Reproduce an actual selectin child query while an unrelated PG table stays excluded."""
    mappings = registry()
    metadata = mappings.metadata
    parent = Table("parent", metadata, Column("id", Integer, primary_key=True))
    child = Table(
        "child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", ForeignKey("parent.id")),
    )
    Table(
        "unrelated_pg",
        metadata,
        Column("id", Integer, primary_key=True),
        CheckConstraint("INTERVAL '30 days' > INTERVAL '0 days'"),
    )

    class ParentFixture:
        """Synthetic mapped parent for the real eager-loading regression."""

        id: int
        children: list[ChildFixture]

    class ChildFixture:
        """Synthetic mapped child used only in this independent registry."""

        id: int
        parent_id: int

    mappings.map_imperatively(ChildFixture, child)
    mappings.map_imperatively(
        ParentFixture,
        parent,
        properties={"children": relationship(ChildFixture, lazy="selectin")},
    )
    engine = create_engine("sqlite://")
    try:
        create_sqlite_schema(engine=engine, tables=[parent], mappers=mappings.mappers)
        assert set(inspect(engine).get_table_names()) == {"parent", "child"}
        with engine.begin() as connection:
            connection.execute(parent.insert().values(id=1))
            connection.execute(child.insert().values(id=2, parent_id=1))
        with Session(engine) as session:
            instance = session.scalar(select(ParentFixture))
            assert instance is not None and len(instance.children) == 1
    finally:
        engine.dispose()
        mappings.dispose()


# ==============================================
# NON-SQLITE AND AMBIGUOUS TARGETS FAIL BEFORE DDL
# The fixture helper never offers an alternate route into a persistent database.
# ==============================================


def test_schema_helper_refuses_postgresql_before_connecting() -> None:
    """A PostgreSQL engine double must not be used for local SQLite setup."""
    engine = MagicMock(spec=Engine)
    engine.dialect = MagicMock()
    engine.dialect.name = "postgresql"
    with pytest.raises(ValueError, match="requires_sqlite"):
        create_sqlite_schema(engine=engine, tables=[])
    engine.connect.assert_not_called()
    engine.begin.assert_not_called()


@pytest.mark.parametrize("mixed_metadata", [False, True])
def test_schema_helper_refuses_empty_or_mixed_metadata(mixed_metadata: bool) -> None:
    """Invalid selections leave the private SQLite database empty."""
    engine = create_engine("sqlite://")
    first = Table("first", MetaData(), Column("id", Integer, primary_key=True))
    second = Table("second", MetaData(), Column("id", Integer, primary_key=True))
    try:
        with pytest.raises(ValueError, match="requires_"):
            create_sqlite_schema(
                engine=engine, tables=[first, second] if mixed_metadata else []
            )
        assert inspect(engine).get_table_names() == []
    finally:
        engine.dispose()


# ==============================================
# INACCESSIBLE SYSTEM TEMP AND PARALLEL RUNS
# Explicit workspace storage must not consult or delete another temporary directory.
# ==============================================


def test_workspace_temp_paths_are_unique_without_system_temp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reproduce Windows temp denial and preserve a marker belonging to another run."""
    import tempfile

    denied = MagicMock(side_effect=PermissionError("system temp is inaccessible"))
    monkeypatch.setattr(tempfile, "gettempdir", denied)
    first = reserve_pytest_directory()
    marker = first / "first-run.txt"
    marker.write_text("synthetic", encoding="utf-8")
    second = reserve_pytest_directory()
    assert first != second
    assert first.parent == second.parent
    assert marker.read_text(encoding="utf-8") == "synthetic"
    denied.assert_not_called()
