# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Strict migration adoption and unchanged fresh-schema behavior."""

from __future__ import annotations

import ast
import copy
import importlib.util
import re
import unittest
from pathlib import Path
from types import (
    ModuleType,
    SimpleNamespace,
)
from typing import (
    Any,
    cast,
)
from unittest.mock import (
    MagicMock,
    patch,
)

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

from app.models.manual_payment import (
    ManualPaymentAudit,
    ManualPaymentReceipt,
)
from scripts import billing_operations

# ==============================================
# MIGRATION SOURCE PATHS
# ==============================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_MIGRATION = (
    PROJECT_ROOT / "alembic/versions/2026_10_13_10_00_00_manual_payment_review.py"
)
TEST_MIGRATION = (
    PROJECT_ROOT / "alembic_test/versions/dce91870b4a2_manual_payment_review.py"
)


# ==============================================
# LOAD A SELF-CONTAINED MIGRATION
# ==============================================


def load_migration(*, path: Path) -> ModuleType:
    """Load migration functions without invoking Alembic or any database."""
    specification = importlib.util.spec_from_file_location(
        "migration_adoption_test", path
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("migration_test_source_unavailable")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


# ==============================================
# POSTGRESQL REFLECTION TEST DOUBLE
# ==============================================


class ReflectedManualSchema:
    """Model PostgreSQL reflection from independently declared application tables."""

    def __init__(
        self, *, tables: tuple[sa.Table, ...], database_rewrites: bool = True
    ) -> None:
        """Build independent reflected constraints and indexes for migration drift tests."""
        self.bind = SimpleNamespace(
            dialect=postgresql.dialect(),
            execute=MagicMock(side_effect=self._catalog_result),
        )
        self.columns: dict[str, list[dict[str, Any]]] = {}
        self.primary_keys: dict[str, dict[str, Any]] = {}
        self.uniques: dict[str, list[dict[str, Any]]] = {}
        self.foreign_keys: dict[str, list[dict[str, Any]]] = {}
        self.checks: dict[str, list[dict[str, Any]]] = {}
        self.indexes: dict[str, list[dict[str, Any]]] = {}
        self.catalog_constraints: dict[str, list[dict[str, Any]]] = {}
        for table in tables:
            self.columns[table.name] = []
            for column in table.columns:
                default = (
                    str(column.server_default.arg) if column.server_default else None
                )
                if column.primary_key and isinstance(column.type, sa.Integer):
                    default = f"nextval('{table.name}_{column.name}_seq'::regclass)"
                self.columns[table.name].append(
                    {
                        "name": column.name,
                        "type": column.type,
                        "nullable": column.nullable,
                        "default": default,
                    }
                )
            self.primary_keys[table.name] = {
                "constrained_columns": [
                    column.name for column in table.primary_key.columns
                ]
            }
            self.uniques[table.name] = []
            self.foreign_keys[table.name] = []
            self.checks[table.name] = []
            self.indexes[table.name] = []
            self.catalog_constraints[table.name] = []
            for constraint in table.constraints:
                kind = (
                    "p"
                    if isinstance(constraint, sa.PrimaryKeyConstraint)
                    else (
                        "u"
                        if isinstance(constraint, sa.UniqueConstraint)
                        else (
                            "f"
                            if isinstance(constraint, sa.ForeignKeyConstraint)
                            else (
                                "c"
                                if isinstance(constraint, sa.CheckConstraint)
                                else None
                            )
                        )
                    )
                )
                if kind is not None:
                    self.catalog_constraints[table.name].append(
                        {
                            "contype": kind,
                            "convalidated": True,
                            "condeferrable": bool(
                                getattr(constraint, "deferrable", False)
                            ),
                            "condeferred": getattr(constraint, "initially", None)
                            == "DEFERRED",
                        }
                    )
                if isinstance(constraint, sa.UniqueConstraint):
                    names = [column.name for column in constraint.columns]
                    name = constraint.name or f"{table.name}_{'_'.join(names)}_key"
                    self.uniques[table.name].append(
                        {"name": name, "column_names": names}
                    )
                    self.indexes[table.name].append(
                        {
                            "name": name,
                            "column_names": names,
                            "unique": True,
                            "duplicates_constraint": name,
                        }
                    )
                elif isinstance(constraint, sa.ForeignKeyConstraint):
                    target_parts = constraint.elements[0].target_fullname.split(".")
                    self.foreign_keys[table.name].append(
                        {
                            "constrained_columns": [
                                element.parent.name for element in constraint.elements
                            ],
                            "referred_table": target_parts[-2],
                            "referred_columns": [
                                element.target_fullname.split(".")[-1]
                                for element in constraint.elements
                            ],
                            "referred_schema": None,
                            "options": {"ondelete": constraint.ondelete},
                        }
                    )
                elif isinstance(constraint, sa.CheckConstraint):
                    sql = str(constraint.sqltext)
                    if database_rewrites and sql.startswith("review_status IN"):
                        sql = "review_status::text = ANY (ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying]::text[])"
                    elif database_rewrites and "BETWEEN" in sql:
                        sql = "octet_length(content) >= 1 AND octet_length(content) <= 2097152"
                    self.checks[table.name].append({"sqltext": sql})
            for index in table.indexes:
                self.indexes[table.name].append(
                    {
                        "name": index.name,
                        "column_names": [column.name for column in index.columns],
                        "unique": index.unique,
                    }
                )

    # ==========================================
    # PHYSICAL CATALOG VALIDATION STATE
    # ==========================================

    def _catalog_result(
        self,
        statement: sa.sql.Executable,
        parameters: dict[str, Any] | None = None,
    ) -> MagicMock:
        """Return catalog flags independently of Inspector's reflected shapes."""
        result = MagicMock()
        rows = copy.deepcopy(
            self.catalog_constraints[parameters["table_name"]] if parameters else []
        )
        source = str(statement)
        if "AND c.contype IN ('p', 'u', 'f', 'c')" in source:
            rows = [row for row in rows if row["contype"] in {"p", "u", "f", "c"}]
        if "c.contype::text AS contype" not in source:
            # asyncpg decodes PostgreSQL's internal "char" (OID 18) as bytes.
            # SQL text casts select the driver's text codec instead.
            for row in rows:
                row["contype"] = row["contype"].encode("ascii")
        result.mappings.return_value.all.return_value = rows
        return result

    # ==========================================
    # REFLECTED TABLE NAMES AND COLUMN DEFINITIONS
    # ==========================================

    def get_table_names(self, *, schema: str) -> list[str]:
        """Return only the independently declared test tables."""
        return list(self.columns)

    def get_columns(self, table_name: str, *, schema: str) -> list[dict[str, Any]]:
        """Return reflected column definitions for drift mutation tests."""
        return self.columns[table_name]

    # ==========================================
    # REFLECTED PRIMARY AND UNIQUE CONSTRAINTS
    # ==========================================

    def get_pk_constraint(self, table_name: str, *, schema: str) -> dict[str, Any]:
        """Return the table's primary key contract."""
        return self.primary_keys[table_name]

    def get_unique_constraints(
        self, table_name: str, *, schema: str
    ) -> list[dict[str, Any]]:
        """Return global uniqueness contracts independently from indexes."""
        return self.uniques[table_name]

    # ==========================================
    # REFLECTED FOREIGN KEYS, CHECKS, AND INDEXES
    # ==========================================

    def get_foreign_keys(self, table_name: str, *, schema: str) -> list[dict[str, Any]]:
        """Return the foreign keys and their deletion behavior."""
        return self.foreign_keys[table_name]

    def get_check_constraints(
        self, table_name: str, *, schema: str
    ) -> list[dict[str, Any]]:
        """Return PostgreSQL or original constraint expressions."""
        return self.checks[table_name]

    def get_indexes(self, table_name: str, *, schema: str) -> list[dict[str, Any]]:
        """Return physical indexes including unique-constraint backing indexes."""
        return self.indexes[table_name]


# ==============================================
# MIGRATION CONTRACT AND ADOPTION TESTS
# ==============================================


class TestManualPaymentMigrationAdoption(unittest.TestCase):
    """Protect global deduplication, audit references, and non-destructive adoption."""

    def setUp(self) -> None:
        """Load the migration and independently reflect its required model tables."""
        self.migration = load_migration(path=PRODUCTION_MIGRATION)
        self.reflection = ReflectedManualSchema(
            tables=(ManualPaymentReceipt.__table__, ManualPaymentAudit.__table__)
        )

    # ==========================================
    # EXISTING MODEL TABLES AND POSTGRESQL REWRITES
    # ==========================================

    def test_existing_application_tables_are_accepted(self) -> None:
        """Ensure existing application tables are accepted."""
        for table_name in self.reflection.get_table_names(schema="public"):
            self.migration._validate_manual_table(
                cast(Inspector, self.reflection), table_name
            )

    # ==========================================
    # ASYNCPG INTERNAL CHAR CODEC REGRESSION
    # ==========================================

    def test_catalog_query_casts_internal_char_before_counting_constraints(
        self,
    ) -> None:
        """Select the text codec before comparing physical constraint counts."""
        receipt = "manual_payment_receipts"
        raw_query = sa.text("SELECT c.contype FROM pg_catalog.pg_constraint c")
        raw_rows = (
            self.reflection._catalog_result(raw_query, {"table_name": receipt})
            .mappings()
            .all()
        )
        self.assertTrue(all(isinstance(row["contype"], bytes) for row in raw_rows))
        self.migration._validate_manual_table(cast(Inspector, self.reflection), receipt)
        query = str(self.reflection.bind.execute.call_args.args[0])
        self.assertIn("c.contype::text AS contype", query)
        self.assertIn("AND c.contype IN ('p', 'u', 'f', 'c')", query)

    # ==========================================
    # POSTGRESQL 18 NOT NULL CONSTRAINTS
    # ==========================================

    def test_postgres18_not_null_catalog_rows_do_not_replace_column_checks(
        self,
    ) -> None:
        """Keep column nullability checks independent of new catalog row kinds."""
        receipt = "manual_payment_receipts"
        self.reflection.catalog_constraints[receipt].append(
            {
                "contype": "n",
                "convalidated": True,
                "condeferrable": False,
                "condeferred": False,
            }
        )
        self.migration._validate_manual_table(cast(Inspector, self.reflection), receipt)
        next(
            column
            for column in self.reflection.columns[receipt]
            if column["name"] == "sha256"
        )["nullable"] = True
        with self.assertRaisesRegex(RuntimeError, "column_nullability:sha256"):
            self.migration._validate_manual_table(
                cast(Inspector, self.reflection), receipt
            )

    def test_original_check_expressions_are_accepted(self) -> None:
        """Ensure original check expressions are accepted."""
        reflection = ReflectedManualSchema(
            tables=(ManualPaymentReceipt.__table__, ManualPaymentAudit.__table__),
            database_rewrites=False,
        )
        for table_name in reflection.get_table_names(schema="public"):
            self.migration._validate_manual_table(
                cast(Inspector, reflection), table_name
            )

    # ==========================================
    # PREFLIGHT VALIDATION IS STRICTLY READ ONLY
    # ==========================================

    def test_preflight_validation_never_locks_or_changes_schema(self) -> None:
        """Ensure preflight validation never locks or changes schema."""
        report = billing_operations._existing_manual_schema_validation(
            cast(Inspector, self.reflection), set(self.reflection.columns)
        )
        self.assertTrue(report["compatible"])
        self.assertEqual(len(report["validated_tables"]), 2)
        self.assertTrue(
            all(
                str(call.args[0]).startswith("SELECT")
                for call in self.reflection.bind.execute.call_args_list
            )
        )

    def test_preflight_reports_the_same_schema_drift_as_upgrade(self) -> None:
        """Ensure preflight reports the same schema drift as upgrade."""
        next(
            column
            for column in self.reflection.columns["manual_payment_receipts"]
            if column["name"] == "content"
        )["nullable"] = True
        report = billing_operations._existing_manual_schema_validation(
            cast(Inspector, self.reflection), set(self.reflection.columns)
        )
        self.assertFalse(report["compatible"])
        self.assertEqual(
            report["reason"],
            "manual_payment_schema_drift:manual_payment_receipts:column_nullability:content",
        )

    # ==========================================
    # SCHEMA DRIFT IS REJECTED BEFORE ADOPTION
    # ==========================================

    def test_column_constraint_and_index_drift_are_rejected(self) -> None:
        """Ensure column constraint and index drift are rejected."""
        receipt = "manual_payment_receipts"
        audit = "manual_payment_audit"
        cases: list[tuple[str, str, ReflectedManualSchema]] = []

        reflection = copy.deepcopy(self.reflection)
        reflection.columns[receipt] = [
            column
            for column in reflection.columns[receipt]
            if column["name"] != "content"
        ]
        cases.append(("missing_content", receipt, reflection))
        reflection = copy.deepcopy(self.reflection)
        reflection.columns[receipt].append(
            {
                "name": "unexpected",
                "type": sa.Integer(),
                "nullable": True,
                "default": None,
            }
        )
        cases.append(("extra_column", receipt, reflection))
        for column_name, change in (
            ("sha256", {"nullable": True}),
            ("payment_id", {"type": sa.BigInteger()}),
            ("received_amount", {"type": sa.Numeric(12, 3)}),
            ("created_at", {"type": sa.DateTime(timezone=True)}),
            ("id", {"default": None}),
            ("created_at", {"default": None}),
            ("content", {"default": "unexpected_default"}),
            ("received_amount", {"computed": {"sqltext": "1"}}),
        ):
            reflection = copy.deepcopy(self.reflection)
            next(
                column
                for column in reflection.columns[receipt]
                if column["name"] == column_name
            ).update(change)
            cases.append(
                (f"column_{column_name}_{next(iter(change))}", receipt, reflection)
            )
        reflection = copy.deepcopy(self.reflection)
        reflection.primary_keys[receipt]["constrained_columns"] = ["payment_id"]
        cases.append(("wrong_primary_key", receipt, reflection))
        reflection = copy.deepcopy(self.reflection)
        reflection.uniques[receipt] = [
            constraint
            for constraint in reflection.uniques[receipt]
            if constraint["column_names"] != ["sha256"]
        ]
        cases.append(("missing_global_hash_uniqueness", receipt, reflection))
        reflection = copy.deepcopy(self.reflection)
        next(
            constraint
            for constraint in reflection.uniques[receipt]
            if constraint["column_names"] == ["transaction_reference"]
        )["column_names"] = ["payment_id", "transaction_reference"]
        cases.append(
            ("tenant_or_invoice_scoped_reference_uniqueness", receipt, reflection)
        )
        for case_name, key, value in (
            ("cascade_delete", "ondelete", "CASCADE"),
            ("deferred_fk", "deferrable", True),
            ("cascade_update", "onupdate", "CASCADE"),
        ):
            reflection = copy.deepcopy(self.reflection)
            next(
                key_record
                for key_record in reflection.foreign_keys[receipt]
                if key_record["constrained_columns"] == ["payment_id"]
            )["options"][key] = value
            cases.append((case_name, receipt, reflection))
        reflection = copy.deepcopy(self.reflection)
        reflection.foreign_keys[receipt][0]["referred_schema"] = "other_tenant"
        cases.append(("cross_schema_reference", receipt, reflection))
        reflection = copy.deepcopy(self.reflection)
        reflection.foreign_keys[audit].pop()
        cases.append(("missing_audit_fk", audit, reflection))
        for sql in (
            "review_status IN ('pending', 'approved', 'rejected', 'paid')",
            "review_status IN ('pending::text', 'approved', 'rejected')",
            "octet_length(content) BETWEEN 0 AND 2097152",
            "octet_length(content) BETWEEN 1 AND 3097152",
            "octet_length(content) >= 1 OR true",
        ):
            reflection = copy.deepcopy(self.reflection)
            target = (
                "review_status" if sql.startswith("review_status") else "octet_length"
            )
            next(
                check
                for check in reflection.checks[receipt]
                if check["sqltext"].startswith(target)
            )["sqltext"] = sql
            cases.append((f"weakened_check_{len(cases)}", receipt, reflection))
        reflection = copy.deepcopy(self.reflection)
        reflection.checks[receipt][0]["dialect_options"] = {
            "postgresql_not_valid": True
        }
        cases.append(("unvalidated_check", receipt, reflection))
        reflection = copy.deepcopy(self.reflection)
        reflection.indexes[audit] = [
            index
            for index in reflection.indexes[audit]
            if index["name"] != "ix_manual_payment_audit_payment_id"
        ]
        cases.append(("missing_audit_index", audit, reflection))
        reflection = copy.deepcopy(self.reflection)
        reflection.indexes[receipt][0]["dialect_options"] = {
            "postgresql_where": "payment_id > 0"
        }
        cases.append(("partial_index", receipt, reflection))
        reflection = copy.deepcopy(self.reflection)
        reflection.indexes[audit].append(
            {
                "name": "unexpected_audit_index",
                "column_names": ["owner_id"],
                "unique": True,
            }
        )
        cases.append(("unexpected_index", audit, reflection))
        reflection = copy.deepcopy(self.reflection)
        reflection.indexes[receipt] = [
            index
            for index in reflection.indexes[receipt]
            if index["column_names"] != ["sha256"]
        ]
        cases.append(("missing_hash_backing_index", receipt, reflection))
        reflection = copy.deepcopy(self.reflection)
        next(
            constraint
            for constraint in reflection.catalog_constraints[audit]
            if constraint["contype"] == "f"
        )["convalidated"] = False
        cases.append(("unvalidated_fk_catalog_flag", audit, reflection))
        reflection = copy.deepcopy(self.reflection)
        next(
            constraint
            for constraint in reflection.catalog_constraints[receipt]
            if constraint["contype"] == "u"
        )["condeferrable"] = True
        cases.append(("deferred_unique_catalog_flag", receipt, reflection))
        for name, table_name, reflection in cases:
            with self.subTest(drift=name):
                with self.assertRaisesRegex(
                    RuntimeError, "manual_payment_schema_drift"
                ):
                    self.migration._validate_manual_table(
                        cast(Inspector, reflection), table_name
                    )

    # ==========================================
    # EXISTING MATCHING TABLES ARE NEVER RECREATED
    # ==========================================

    def test_upgrade_adopts_existing_tables_without_drops_or_creates(self) -> None:
        """Ensure upgrade adopts existing tables without drops or creates."""
        operations = MagicMock()
        operations.get_bind.return_value = self.reflection.bind
        with (
            patch.object(self.migration, "op", operations),
            patch.object(self.migration.sa, "inspect", return_value=self.reflection),
        ):
            self.migration.upgrade()
        operations.create_table.assert_not_called()
        operations.create_index.assert_not_called()
        operations.drop_table.assert_not_called()
        self.assertEqual(operations.add_column.call_count, 3)
        locks = [
            call
            for call in self.reflection.bind.execute.call_args_list
            if str(call.args[0]).startswith("LOCK TABLE")
        ]
        self.assertEqual(len(locks), 2)

    # ==========================================
    # VALIDATE BOTH TABLES BEFORE ALTERING CORE TABLES
    # ==========================================

    def test_drift_in_second_table_blocks_every_schema_write(self) -> None:
        """Ensure drift in second table blocks every schema write."""
        self.reflection.foreign_keys["manual_payment_audit"].pop()
        operations = MagicMock()
        operations.get_bind.return_value = self.reflection.bind
        with (
            patch.object(self.migration, "op", operations),
            patch.object(self.migration.sa, "inspect", return_value=self.reflection),
        ):
            with self.assertRaisesRegex(RuntimeError, "manual_payment_schema_drift"):
                self.migration.upgrade()
        operations.add_column.assert_not_called()
        operations.create_table.assert_not_called()
        operations.create_unique_constraint.assert_not_called()
        operations.execute.assert_not_called()
        operations.drop_table.assert_not_called()

    # ==========================================
    # UNCHANGED FRESH SCHEMA CREATION
    # ==========================================

    def test_fresh_upgrade_creates_the_full_valid_schema(self) -> None:
        """Ensure fresh upgrade creates the full valid schema."""
        reflection = ReflectedManualSchema(tables=())
        operations = MagicMock()
        operations.get_bind.return_value = reflection.bind
        with (
            patch.object(self.migration, "op", operations),
            patch.object(self.migration.sa, "inspect", return_value=reflection),
        ):
            self.migration.upgrade()
        self.assertEqual(operations.create_table.call_count, 2)
        self.assertEqual(operations.create_index.call_count, 1)
        reflection.bind.execute.assert_not_called()
        metadata = sa.MetaData()
        tables = tuple(
            sa.Table(call.args[0], metadata, *call.args[1:])
            for call in operations.create_table.call_args_list
        )
        for call in operations.create_index.call_args_list:
            sa.Index(
                call.args[0],
                *(metadata.tables[call.args[1]].c[name] for name in call.args[2]),
            )
        fresh = ReflectedManualSchema(tables=tables)
        for table_name in fresh.get_table_names(schema="public"):
            self.migration._validate_manual_table(cast(Inspector, fresh), table_name)

    # ==========================================
    # INDEPENDENT LEAST-PRIVILEGE MIGRATION CONTRACT
    # ==========================================

    def test_upgrade_defines_review_without_role_or_identity_assignments(self) -> None:
        """Permit only provider backfill and permission registration as data writes."""
        for path in (PRODUCTION_MIGRATION, TEST_MIGRATION):
            with self.subTest(migration=path.name):
                migration = load_migration(path=path)
                reflection = ReflectedManualSchema(tables=())
                operations = MagicMock()
                operations.get_bind.return_value = reflection.bind
                with (
                    patch.object(migration, "op", operations),
                    patch.object(migration.sa, "inspect", return_value=reflection),
                ):
                    migration.upgrade()

                sql = [
                    " ".join(str(call.args[0]).replace('"', "").split()).lower()
                    for call in (
                        operations.execute.call_args_list
                        + reflection.bind.execute.call_args_list
                    )
                ]
                writes: list[tuple[str, str]] = []
                for statement in sql:
                    matches = re.findall(
                        r"\b(insert\s+into|update|delete\s+from|merge\s+into)\s+"
                        r"([a-z_][a-z0-9_.]*)",
                        statement,
                    )
                    writes.extend(
                        (operation, table.rsplit(".", 1)[-1])
                        for operation, table in matches
                    )
                self.assertCountEqual(
                    writes, [("update", "payments"), ("insert into", "permissions")]
                )
                operations.bulk_insert.assert_not_called()
                payment_update = next(
                    statement for statement in sql if statement.startswith("update ")
                )
                self.assertEqual(
                    payment_update,
                    "update payments set payment_provider = 'manual_transfer' "
                    "where payment_method in ('ccp', 'baridimob')",
                )
                self.assertTrue(
                    any(
                        "insert into permissions" in statement
                        and "'payments.review'" in statement
                        and "on conflict (code) do nothing" in statement
                        for statement in sql
                    )
                )
                identity_columns = [
                    call.args[1]
                    for call in operations.add_column.call_args_list
                    if call.args[0] == "admins"
                ]
                self.assertEqual(len(identity_columns), 1)
                identity_column = identity_columns[0]
                self.assertEqual(identity_column.name, "auth_subject")
                self.assertTrue(identity_column.nullable)
                self.assertIsNone(identity_column.default)
                self.assertIsNone(identity_column.server_default)

    # ==========================================
    # PARTIAL METADATA CREATION
    # ==========================================

    def test_existing_receipt_table_does_not_block_new_audit_table(self) -> None:
        """Ensure existing receipt table does not block new audit table."""
        reflection = ReflectedManualSchema(tables=(ManualPaymentReceipt.__table__,))
        operations = MagicMock()
        operations.get_bind.return_value = reflection.bind
        with (
            patch.object(self.migration, "op", operations),
            patch.object(self.migration.sa, "inspect", return_value=reflection),
        ):
            self.migration.upgrade()
        self.assertEqual(operations.create_table.call_count, 1)
        self.assertEqual(
            operations.create_table.call_args.args[0], "manual_payment_audit"
        )
        self.assertEqual(operations.create_index.call_count, 1)

    # ==========================================
    # PRODUCTION AND TEST UPGRADES STAY IDENTICAL
    # ==========================================

    def test_production_and_test_upgrade_ast_match(self) -> None:
        """Ensure production and test upgrade ast match."""
        bodies = []
        for path in (PRODUCTION_MIGRATION, TEST_MIGRATION):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            bodies.append(
                {
                    node.name: ast.dump(node)
                    for node in tree.body
                    if isinstance(node, ast.FunctionDef)
                }
            )
        self.assertEqual(bodies[0], bodies[1])


if __name__ == "__main__":
    unittest.main()
