# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# HISTORICAL MAIN BOOTSTRAP FREEZER
# Extract reviewed historical column declarations and leave migration-owned objects to Alembic.
# ==============================================

"""Generate frozen DDL from local Git evidence without importing application models."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND IMMUTABLE SOURCE REFERENCES
# Read local Git objects only; no checkout, network operation or application initialization.
# ==============================================

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import (
    AddConstraint,
    CreateIndex,
    CreateTable,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "7a667633f593afbabc9949cef12f603535eba94e"
EARLIER_COMMIT = "59c4b9bb007b93ea61bacb92b537df8af0a2c144"
VERSION = "main-bootstrap-v1"
TARGET = ROOT / "migration_support/main_bootstrap_v1.json"
ALLOWED = {
    name: getattr(sa, name)
    for name in (
        "Column",
        "Integer",
        "BigInteger",
        "String",
        "Text",
        "Boolean",
        "DateTime",
        "Float",
        "Numeric",
        "JSON",
        "LargeBinary",
        "ForeignKey",
        "UniqueConstraint",
        "CheckConstraint",
        "Index",
    )
}
ALLOWED["func"] = sa.func


# ==============================================
# SAFE HISTORICAL DECLARATION READING
# Evaluate only SQLAlchemy DDL constructors, literals and func.now expressions.
# ==============================================


def git_text(*, revision: str, path: str) -> str:
    """Read one versioned source without changing the working tree."""
    return subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT
    ).decode("utf-8")


# ==============================================
# DECLARATION
# Reject executable application expressions before constructing DDL objects.
# ==============================================


def declaration(*, node: ast.AST) -> Any:
    """Reject executable application expressions before constructing DDL objects."""
    for part in ast.walk(node):
        if not isinstance(
            part,
            (
                ast.Call,
                ast.Name,
                ast.Load,
                ast.Constant,
                ast.keyword,
                ast.Attribute,
                ast.Tuple,
                ast.List,
                ast.Dict,
                ast.UnaryOp,
                ast.USub,
            ),
        ):
            raise TypeError("unsupported_historical_expression:" + type(part).__name__)
        if isinstance(part, ast.Name) and part.id not in ALLOWED:
            raise ValueError("unsupported_historical_name:" + part.id)
        if isinstance(part, ast.Attribute) and ast.unparse(part) != "func.now":
            raise ValueError("unsupported_historical_attribute")
    return eval(
        compile(ast.Expression(node), "<reviewed-historical-ddl>", "eval"),
        {"__builtins__": {}},
        ALLOWED,
    )


# ==============================================
# DECLARATIONS
# Select Column declarations only, excluding methods and relationships.
# ==============================================


def declarations(*, cls: ast.ClassDef) -> dict[str, ast.Call]:
    """Select Column declarations only, excluding methods and relationships."""
    return {
        node.targets[0].id: node.value
        for node in cls.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "Column"
    }


# ==============================================
# MIGRATION OBJECT OWNERSHIP
# Let the unchanged main revisions create their tables, columns and associated constraints.
# ==============================================


def migration_ownership() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """Identify literal table/column additions in main upgrade functions."""
    tables: dict[str, str] = {}
    columns: dict[str, dict[str, str]] = {}
    for path in sorted((ROOT / "alembic/versions").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        upgrade = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
            ),
            None,
        )
        if upgrade is None:
            continue
        for node in ast.walk(upgrade):
            if (
                not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Attribute)
                or not isinstance(node.func.value, ast.Name)
                or node.func.value.id != "op"
                or not node.args
                or not isinstance(node.args[0], ast.Constant)
            ):
                continue
            table = node.args[0].value
            if node.func.attr == "create_table":
                tables[table] = path.name
            elif (
                node.func.attr == "add_column"
                and len(node.args) > 1
                and isinstance(node.args[1], ast.Call)
                and node.args[1].args
                and isinstance(node.args[1].args[0], ast.Constant)
            ):
                columns.setdefault(table, {})[node.args[1].args[0].value] = path.name
    return tables, columns


# ==============================================
# FROZEN DDL AND PROVENANCE
# Build a compatibility contract, not a claim of an unavailable exact pre-August archive.
# ==============================================


def build() -> dict[str, Any]:
    """Derive bootstrap-only tables and retain column-level historical evidence."""
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", SOURCE_COMMIT, "app/models"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    sources = {
        path: git_text(revision=SOURCE_COMMIT, path=path)
        for path in paths
        if path.endswith(".py")
    }
    base_tree = ast.parse(sources["app/models/base.py"])
    bases = {
        node.name: declarations(cls=node)
        for node in base_tree.body
        if isinstance(node, ast.ClassDef)
    }
    owned_tables, owned_columns = migration_ownership()
    metadata = sa.MetaData()
    provenance: dict[str, Any] = {}
    for path, source in sources.items():
        for cls in ast.parse(source).body:
            if not isinstance(cls, ast.ClassDef):
                continue
            table_name = next(
                (
                    ast.literal_eval(node.value)
                    for node in cls.body
                    if isinstance(node, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == "__tablename__"
                        for target in node.targets
                    )
                ),
                None,
            )
            if not table_name or table_name in owned_tables:
                continue
            inherited = next(
                (
                    bases[base.id]
                    for base in cls.bases
                    if isinstance(base, ast.Name) and base.id in bases
                ),
                {},
            )
            fields = {
                **declarations(cls=cls),
                **{
                    name: value
                    for name, value in inherited.items()
                    if name not in declarations(cls=cls)
                },
            }
            columns: list[sa.Column[Any]] = []
            evidence: dict[str, Any] = {}
            for attribute, expression in fields.items():
                column = declaration(node=expression)
                name = column.name or attribute
                if name in owned_columns.get(table_name, {}):
                    continue
                column.name = name
                columns.append(column)
                inherited_field = attribute not in declarations(cls=cls)
                source_path = "app/models/base.py" if inherited_field else path
                evidence[name] = {
                    "path": source_path,
                    "attribute": attribute,
                    "declaration": ast.unparse(expression),
                }
            constraints: list[Any] = []
            for node in cls.body:
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "__table_args__"
                    for target in node.targets
                ):
                    for expression in getattr(node.value, "elts", []):
                        if isinstance(expression, ast.Dict):
                            continue
                        item = declaration(node=expression)
                        referenced = (
                            [
                                argument.value
                                for argument in expression.args[1:]
                                if isinstance(argument, ast.Constant)
                                and isinstance(argument.value, str)
                            ]
                            if ast.unparse(expression.func) == "Index"
                            else [
                                argument.value
                                for argument in expression.args
                                if isinstance(argument, ast.Constant)
                                and isinstance(argument.value, str)
                            ]
                        )
                        if any(
                            name in owned_columns.get(table_name, {})
                            for name in referenced
                        ):
                            continue
                        constraints.append(item)
            sa.Table(table_name, metadata, *columns, *constraints)
            provenance[table_name] = {
                "class": cls.name,
                "path": path,
                "columns": evidence,
            }
    statements: list[str] = ["REVOKE ALL ON SCHEMA public FROM PUBLIC"]
    for table in sorted(metadata.tables.values(), key=lambda table: table.name):
        statements.append(
            str(
                CreateTable(table, include_foreign_key_constraints=[]).compile(
                    dialect=postgresql.dialect()
                )
            ).strip()
        )
    for table in sorted(metadata.tables.values(), key=lambda table: table.name):
        for constraint in sorted(
            table.foreign_key_constraints,
            key=lambda constraint: (
                str(constraint.name),
                str(constraint.elements[0].target_fullname),
            ),
        ):
            statements.append(
                str(
                    AddConstraint(constraint).compile(dialect=postgresql.dialect())
                ).strip()
            )
        for index in sorted(table.indexes, key=lambda index: str(index.name)):
            statements.append(
                str(CreateIndex(index).compile(dialect=postgresql.dialect())).strip()
            )
    return {
        "version": VERSION,
        "source_commit": SOURCE_COMMIT,
        "first_complete_model_commit": EARLIER_COMMIT,
        "historical_exactness": "pre-August physical DDL unavailable; explicit historical compatibility reconstruction",
        "source_files_sha256": {
            path: hashlib.sha256(source.encode()).hexdigest()
            for path, source in sources.items()
        },
        "schema_privilege_policy": "PUBLIC schema rights revoked, matching verified development snapshot; local database owner retains authority via pg_database_owner; Neon platform default ACLs not copied",
        "tables": sorted(metadata.tables),
        "migration_owned_tables_excluded": owned_tables,
        "migration_owned_columns_excluded": owned_columns,
        "table_provenance": provenance,
        "statements": statements,
    }


# ==============================================
# REPRODUCIBLE CHECK OR EXPLICIT WRITE
# Require a deliberate flag before replacing the versioned frozen contract.
# ==============================================


def main() -> None:
    """Generate the contract once or verify that local historical evidence reproduces it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    options = parser.parse_args()
    data = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if options.write:
        TARGET.write_bytes(data.encode("utf-8"))
    elif not TARGET.exists() or TARGET.read_bytes() != data.encode("utf-8"):
        raise SystemExit("bootstrap_contract_not_reproducible")
    print(
        json.dumps(
            {
                "version": VERSION,
                "sha256": hashlib.sha256(data.encode()).hexdigest(),
                "tables": len(json.loads(data)["tables"]),
            }
        )
    )


if __name__ == "__main__":
    main()
