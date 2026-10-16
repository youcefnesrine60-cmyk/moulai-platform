# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Private manual billing evidence, provider identity, and reviewer authorization."""

from __future__ import annotations

# ==============================================
# IMPORTS
# ==============================================

import logging
import re
from collections import Counter
from typing import (
    Any,
    NoReturn,
    TypeAlias,
    cast,
)

import sqlalchemy as sa

from alembic import op
from sqlalchemy.engine import Connection
from sqlalchemy.engine.reflection import Inspector

# ==============================================
# REVISION METADATA
# ==============================================

revision: str = "dce91870b4a2"
down_revision: str = "b7d33e89f4a1"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


# ==============================================
# FROZEN MIGRATION CONTRACTS
# ==============================================

ColumnSpecifications: TypeAlias = dict[
    str, tuple[sa.types.TypeEngine[Any], bool, str | None]
]
MANUAL_TABLE_NAMES = ("manual_payment_receipts", "manual_payment_audit")
logger = logging.getLogger("alembic.runtime.migration")


# ==============================================
# EXPECTED MANUAL TABLE COLUMNS
# ==============================================


def _expected_columns(table_name: str) -> ColumnSpecifications:
    """Freeze column contracts independently of future application model changes."""
    common: ColumnSpecifications = {
        "id": (sa.Integer(), False, "sequence"),
        "created_at": (sa.DateTime(), True, "timestamp"),
        "updated_at": (sa.DateTime(), True, "timestamp"),
    }
    if table_name == "manual_payment_receipts":
        return common | {
            "payment_id": (sa.Integer(), False, None),
            "transaction_reference": (sa.String(120), False, None),
            "sha256": (sa.String(64), False, None),
            "media_type": (sa.String(50), False, None),
            "content": (sa.LargeBinary(), False, None),
            "review_status": (sa.String(20), False, None),
            "reviewed_by": (sa.Integer(), True, None),
            "reviewed_at": (sa.DateTime(), True, None),
            "received_amount": (sa.Numeric(12, 2), True, None),
            "received_currency": (sa.String(3), True, None),
            "review_note": (sa.Text(), True, None),
        }
    if table_name == "manual_payment_audit":
        return common | {
            "payment_id": (sa.Integer(), False, None),
            "receipt_id": (sa.Integer(), False, None),
            "owner_id": (sa.Integer(), False, None),
            "admin_id": (sa.Integer(), True, None),
            "action": (sa.String(30), False, None),
            "details": (sa.JSON(), False, None),
        }
    raise RuntimeError("unsupported_manual_payment_table")


# ==============================================
# STRICT CHECK-CONSTRAINT NORMALIZATION
# ==============================================


def _normalize_check(sql: str) -> str:
    """Normalize PostgreSQL's known rewrites while preserving quoted literals."""
    pattern = r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|::|>=|<=|=|[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[(),\[\]]"
    matches = list(re.finditer(pattern, sql))
    cursor = 0
    tokens: list[str] = []
    for match in matches:
        if sql[cursor : match.start()].strip():
            raise RuntimeError("unsupported_manual_payment_check_expression")
        value = match.group()
        tokens.append(value if value.startswith("'") else value.lower())
        cursor = match.end()
    if sql[cursor:].strip():
        raise RuntimeError("unsupported_manual_payment_check_expression")
    normalized: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "::":
            index += 1
            if tokens[index : index + 2] == ["character", "varying"]:
                index += 2
            elif tokens[index : index + 1] in (["text"], ["varchar"]):
                index += 1
            else:
                raise RuntimeError("unsupported_manual_payment_check_cast")
            if tokens[index : index + 2] == ["[", "]"]:
                index += 2
            continue
        if token not in {"(", ")"}:
            normalized.append(token.strip('"') if token.startswith('"') else token)
        index += 1
    return "".join(normalized)


# ==============================================
# VERIFIED ADOPTION OF AN EXISTING MANUAL TABLE
# ==============================================


def _validate_manual_table(inspector: Inspector, table_name: str) -> None:
    """Reject schema drift before adopting metadata-created evidence tables."""
    expected_columns = _expected_columns(table_name)
    actual_columns = {
        column["name"]: column
        for column in inspector.get_columns(table_name, schema="public")
    }

    def mismatch(component: str) -> NoReturn:
        """Raise a stable schema diagnostic without exposing stored values."""
        raise RuntimeError(f"manual_payment_schema_drift:{table_name}:{component}")

    if set(actual_columns) != set(expected_columns):
        mismatch("columns")
    for name, (column_type, nullable, default_kind) in expected_columns.items():
        actual = actual_columns[name]
        if str(actual["type"].compile(dialect=inspector.bind.dialect)) != str(
            column_type.compile(dialect=inspector.bind.dialect)
        ):
            mismatch(f"column_type:{name}")
        if actual["nullable"] != nullable:
            mismatch(f"column_nullability:{name}")
        if actual.get("computed") is not None or actual.get("identity") is not None:
            mismatch(f"column_generation:{name}")
        raw_default = re.sub(r"\s+", "", str(actual.get("default") or ""))
        default = raw_default.lower()
        if default_kind == "sequence":
            sequence_pattern = (
                r"nextval\('(?:public\.)?"
                + re.escape(table_name)
                + r"_id_seq'::regclass\)"
            )
            if re.fullmatch(sequence_pattern, raw_default.replace('"', "")) is None:
                mismatch(f"column_default:{name}")
        elif default_kind == "timestamp":
            if default not in {"now()", "current_timestamp", "transaction_timestamp()"}:
                mismatch(f"column_default:{name}")
        elif actual.get("default") is not None:
            mismatch(f"column_default:{name}")
    if inspector.get_pk_constraint(table_name, schema="public")[
        "constrained_columns"
    ] != ["id"]:
        mismatch("primary_key")

    expected_unique = (
        {("payment_id",), ("transaction_reference",), ("sha256",)}
        if table_name == "manual_payment_receipts"
        else set()
    )
    unique_constraints = inspector.get_unique_constraints(table_name, schema="public")
    unique_by_name = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in unique_constraints
    }
    if set(unique_by_name.values()) != expected_unique or len(
        unique_constraints
    ) != len(expected_unique):
        mismatch("unique_constraints")

    expected_foreign_keys = (
        {
            (("payment_id",), "payments", ("id",), "RESTRICT"),
            (("reviewed_by",), "admins", ("id",), "SET NULL"),
        }
        if table_name == "manual_payment_receipts"
        else {
            (("payment_id",), "payments", ("id",), "RESTRICT"),
            (("receipt_id",), "manual_payment_receipts", ("id",), "RESTRICT"),
            (("admin_id",), "admins", ("id",), "SET NULL"),
        }
    )
    foreign_keys = inspector.get_foreign_keys(table_name, schema="public")
    actual_foreign_keys = set()
    for foreign_key in foreign_keys:
        options = foreign_key.get("options", {})
        if (
            foreign_key.get("referred_schema") not in {None, "public"}
            or options.get("deferrable", False)
            or str(options.get("onupdate") or "NO ACTION").upper() != "NO ACTION"
            or str(options.get("match") or "SIMPLE").upper() != "SIMPLE"
        ):
            mismatch("foreign_key_options")
        actual_foreign_keys.add(
            (
                tuple(foreign_key["constrained_columns"]),
                foreign_key["referred_table"],
                tuple(foreign_key["referred_columns"]),
                str(options.get("ondelete") or "NO ACTION").upper(),
            )
        )
    if actual_foreign_keys != expected_foreign_keys or len(foreign_keys) != len(
        expected_foreign_keys
    ):
        mismatch("foreign_keys")

    checks = inspector.get_check_constraints(table_name, schema="public")
    if table_name == "manual_payment_receipts":
        if len(checks) != 2:
            mismatch("check_constraints")
        try:
            normalized_checks = {_normalize_check(check["sqltext"]) for check in checks}
        except RuntimeError:
            mismatch("check_constraints")
        status_checks = {
            "review_statusin'pending','approved','rejected'",
            "review_status=anyarray['pending','approved','rejected']",
        }
        content_checks = {
            "octet_lengthcontentbetween1and2097152",
            "octet_lengthcontent>=1andoctet_lengthcontent<=2097152",
        }
        if (
            len(normalized_checks.intersection(status_checks)) != 1
            or len(normalized_checks.intersection(content_checks)) != 1
            or any(
                check.get("dialect_options", {}).get("postgresql_not_valid")
                for check in checks
            )
        ):
            mismatch("check_constraints")
    elif checks:
        mismatch("check_constraints")

    indexes = inspector.get_indexes(table_name, schema="public")
    required_audit_index_found = table_name != "manual_payment_audit"
    validated_unique_indexes: set[str] = set()
    for index in indexes:
        name = index["name"]
        columns = tuple(index["column_names"])
        options = index.get("dialect_options", {})
        if (
            options.get("postgresql_where") is not None
            or options.get("postgresql_include")
            or options.get("postgresql_ops")
            or options.get("postgresql_using", "btree") != "btree"
        ):
            mismatch("index_options")
        if index["unique"] and unique_by_name.get(name) == columns:
            validated_unique_indexes.add(name)
            continue
        if not index["unique"] and name == f"ix_{table_name}_id" and columns == ("id",):
            continue
        if (
            table_name == "manual_payment_audit"
            and name == "ix_manual_payment_audit_payment_id"
            and columns == ("payment_id",)
            and not index["unique"]
        ):
            required_audit_index_found = True
            continue
        mismatch("indexes")
    if not required_audit_index_found:
        mismatch("audit_payment_index")
    if validated_unique_indexes != set(unique_by_name):
        mismatch("unique_indexes")

    # Inspector omits FK validation state. The PostgreSQL catalog also proves
    # that all adopted constraints are validated and enforce writes immediately.
    # Cast PostgreSQL's internal "char" to text: asyncpg decodes it as bytes.
    catalog_constraints = (
        cast(Connection, inspector.bind)
        .execute(
            sa.text(
                "SELECT c.contype::text AS contype, c.convalidated, "
                "c.condeferrable, c.condeferred "
                "FROM pg_catalog.pg_constraint c "
                "JOIN pg_catalog.pg_class t ON t.oid = c.conrelid "
                "JOIN pg_catalog.pg_namespace n ON n.oid = t.relnamespace "
                "WHERE n.nspname = 'public' AND t.relname = :table_name "
                "AND c.contype IN ('p', 'u', 'f', 'c')"
            ),
            {"table_name": table_name},
        )
        .mappings()
        .all()
    )
    actual_constraint_counts = Counter(
        constraint["contype"] for constraint in catalog_constraints
    )
    expected_constraint_counts = Counter(
        {
            "p": 1,
            "u": len(unique_constraints),
            "f": len(foreign_keys),
            "c": len(checks),
        }
    )
    if actual_constraint_counts != expected_constraint_counts or any(
        not constraint["convalidated"]
        or constraint["condeferrable"]
        or constraint["condeferred"]
        for constraint in catalog_constraints
    ):
        mismatch("constraint_validation")


# ==============================================
# VALIDATE EXISTING TABLES BEFORE ANY SCHEMA WRITE
# ==============================================


def _validated_existing_tables() -> set[str]:
    """Lock and validate existing evidence tables before changing billing fields."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names(schema="public")).intersection(
        MANUAL_TABLE_NAMES
    )
    for table_name in MANUAL_TABLE_NAMES:
        if table_name in existing:
            bind.execute(
                sa.text(f'LOCK TABLE public."{table_name}" IN SHARE ROW EXCLUSIVE MODE')
            )
            _validate_manual_table(inspector, table_name)
    for table_name in sorted(existing):
        logger.info("Validated existing manual payment table %s", table_name)
    return existing


# ==============================================
# APPLY MANUAL BILLING SCHEMA
# ==============================================


def upgrade() -> None:
    """Create billing fields and define review permission without assigning access.

    Reviewer role grants and trusted identity bindings require a separate
    administrative decision. This migration never binds administrator subjects.
    """

    existing_tables = _validated_existing_tables()

    op.add_column(
        "payments", sa.Column("payment_provider", sa.String(50), nullable=True)
    )
    op.add_column(
        "payments",
        sa.Column("currency", sa.String(3), nullable=False, server_default="DZD"),
    )
    op.execute(
        "UPDATE payments SET payment_provider = 'manual_transfer' "
        "WHERE payment_method IN ('ccp', 'baridimob')"
    )
    op.add_column("admins", sa.Column("auth_subject", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_admins_auth_subject", "admins", ["auth_subject"])
    if "manual_payment_receipts" not in existing_tables:
        op.create_table(
            "manual_payment_receipts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column(
                "payment_id",
                sa.Integer(),
                sa.ForeignKey("payments.id", ondelete="RESTRICT"),
                nullable=False,
                unique=True,
            ),
            sa.Column(
                "transaction_reference", sa.String(120), nullable=False, unique=True
            ),
            sa.Column("sha256", sa.String(64), nullable=False, unique=True),
            sa.Column("media_type", sa.String(50), nullable=False),
            sa.Column("content", sa.LargeBinary(), nullable=False),
            sa.Column("review_status", sa.String(20), nullable=False),
            sa.Column(
                "reviewed_by",
                sa.Integer(),
                sa.ForeignKey("admins.id", ondelete="SET NULL"),
            ),
            sa.Column("reviewed_at", sa.DateTime()),
            sa.Column("received_amount", sa.Numeric(12, 2)),
            sa.Column("received_currency", sa.String(3)),
            sa.Column("review_note", sa.Text()),
            sa.CheckConstraint("review_status IN ('pending', 'approved', 'rejected')"),
            sa.CheckConstraint("octet_length(content) BETWEEN 1 AND 2097152"),
        )
    if "manual_payment_audit" not in existing_tables:
        op.create_table(
            "manual_payment_audit",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column(
                "payment_id",
                sa.Integer(),
                sa.ForeignKey("payments.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "receipt_id",
                sa.Integer(),
                sa.ForeignKey("manual_payment_receipts.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column(
                "admin_id",
                sa.Integer(),
                sa.ForeignKey("admins.id", ondelete="SET NULL"),
            ),
            sa.Column("action", sa.String(30), nullable=False),
            sa.Column("details", sa.JSON(), nullable=False),
        )
    if "manual_payment_audit" not in existing_tables:
        op.create_index(
            "ix_manual_payment_audit_payment_id", "manual_payment_audit", ["payment_id"]
        )
    # Register the permission only. Role grants and identity mappings are
    # separate administrative decisions and must never be inferred by migration.
    op.execute(
        "INSERT INTO permissions (code, name, description) "
        "VALUES ('payments.review', 'Review manual payments', "
        "'Independently verify received subscription funds') "
        "ON CONFLICT (code) DO NOTHING"
    )


# ==============================================
# REVERT MANUAL BILLING SCHEMA
# ==============================================


def downgrade() -> None:
    """Remove this revision's tables, billing fields, and reviewer permission.

    Dropping receipt tables removes their private evidence and audit events;
    operators must retain required evidence before choosing a downgrade.
    """

    op.drop_table("manual_payment_audit")
    op.drop_table("manual_payment_receipts")
    op.drop_constraint("uq_admins_auth_subject", "admins", type_="unique")
    op.drop_column("admins", "auth_subject")
    op.drop_column("payments", "currency")
    op.drop_column("payments", "payment_provider")
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE code = 'payments.review')"
    )
    op.execute("DELETE FROM permissions WHERE code = 'payments.review'")
