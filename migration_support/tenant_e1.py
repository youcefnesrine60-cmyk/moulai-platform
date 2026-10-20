# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Explicit additive E1 operations; no engines, reflection or application imports.

This versioned contract is shared by two separate Alembic histories. Freeze it
once applied; subsequent changes belong in new migration contracts/revisions.
"""

import sqlalchemy as sa
from alembic.operations import (
    Operations,
    ops,
)

from migration_support.tenant_e1_schema import (
    ROLE_PERMISSIONS,
    TENANT_TABLE_NAMES,
    define_tenant_tables,
)
from migration_support.tenant_e1_sql import (
    FUNCTION_DEFINITIONS,
    FUNCTION_SIGNATURES,
    TRIGGER_DEFINITIONS,
)

EXPANSIONS: tuple[tuple[str, str], ...] = (
    ("restaurants", "organization_id"),
    ("restaurant_groups", "organization_id"),
    ("restaurant_branches", "organization_id"),
    ("owners", "identity_id"),
    ("admins", "identity_id"),
)


# ==============================================
# ADD EXISTING-TABLE EXPANSIONS
# ==============================================


def _expand_metadata(*, metadata: sa.MetaData) -> None:
    """Describe only the five approved nullable additions on copied tables."""
    for table_name, column_name in EXPANSIONS:
        table = metadata.tables[table_name]
        if column_name in table.c:
            raise ValueError("E1 expansion already present in source metadata")
        table.append_column(sa.Column(column_name, sa.Integer(), nullable=True))
    for table_name, prefix in (
        ("restaurants", "restaurants"),
        ("restaurant_groups", "groups"),
    ):
        table = metadata.tables[table_name]
        table.append_constraint(
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name=f"fk_{prefix}_org",
                ondelete="RESTRICT",
                postgresql_not_valid=True,
            )
        )
        table.append_constraint(
            sa.UniqueConstraint("organization_id", "id", name=f"uq_{prefix}_org_id")
        )
        sa.Index(f"ix_{table_name}_organization_id", table.c.organization_id)
    links = metadata.tables["restaurant_branches"]
    for parent_name, column_name, suffix in (
        ("restaurant_groups", "group_id", "group"),
        ("restaurants", "restaurant_id", "restaurant"),
    ):
        links.append_constraint(
            sa.ForeignKeyConstraint(
                ["organization_id", column_name],
                [f"{parent_name}.organization_id", f"{parent_name}.id"],
                name=f"fk_group_link_{suffix}_org",
                ondelete="RESTRICT",
                postgresql_not_valid=True,
            )
        )
        sa.Index(
            f"ix_group_link_org_{suffix}", links.c.organization_id, links.c[column_name]
        )
    for table_name, prefix in (("owners", "owner"), ("admins", "admin")):
        table = metadata.tables[table_name]
        table.append_constraint(
            sa.ForeignKeyConstraint(
                ["identity_id"],
                ["identities.id"],
                name=f"fk_{prefix}_identity",
                ondelete="RESTRICT",
                postgresql_not_valid=True,
            )
        )
        table.append_constraint(
            sa.UniqueConstraint("identity_id", name=f"uq_{prefix}_identity")
        )


# ==============================================
# BUILD COMPLETE ALEMBIC TARGET METADATA
# ==============================================


def build_target_metadata(*, legacy_metadata: sa.MetaData) -> sa.MetaData:
    """Copy full legacy tables before adding E1; never mutate live ORM tables.

    Partial B1 reference metadata is deliberately not imported or concatenated.
    A missing or already-expanded prerequisite fails rather than hiding drift.
    """
    metadata = sa.MetaData(naming_convention=legacy_metadata.naming_convention)
    for table in legacy_metadata.tables.values():
        table.to_metadata(metadata)
    for table_name, _ in EXPANSIONS:
        if table_name not in metadata.tables:
            raise ValueError(f"E1 prerequisite absent: {table_name}")
    if any(name in metadata.tables for name in TENANT_TABLE_NAMES):
        raise ValueError("E1 tenant tables already present in source metadata")
    _expand_metadata(metadata=metadata)
    define_tenant_tables(metadata=metadata)
    return metadata


# ==============================================
# BUILD FROZEN OPERATION METADATA
# ==============================================


def operation_metadata() -> sa.MetaData:
    """Resolve FK targets for compilation, without creating reference tables."""
    metadata = sa.MetaData()
    for table_name, _ in EXPANSIONS:
        columns = [sa.Column("id", sa.Integer(), primary_key=True)]
        if table_name == "restaurant_branches":
            columns.extend(
                (
                    sa.Column("group_id", sa.Integer(), nullable=False),
                    sa.Column("restaurant_id", sa.Integer(), nullable=False),
                )
            )
        sa.Table(table_name, metadata, *columns, info={"external_reference": True})
    _expand_metadata(metadata=metadata)
    define_tenant_tables(metadata=metadata)
    return metadata


# ==============================================
# CONFIGURE TRANSACTIONAL DDL
# ==============================================


def _configure(*, operations: Operations) -> None:
    """Refuse other dialects/nontransactional DDL; bound lock waiting."""
    context = operations.get_context()
    if context.dialect.name != "postgresql" or not context.impl.transactional_ddl:
        raise RuntimeError("E1 requires PostgreSQL transactional DDL")
    if not context.as_sql:
        connection = operations.get_bind()
        if (
            connection is None
            or not connection.in_transaction()
            or connection.get_execution_options().get("isolation_level") == "AUTOCOMMIT"
        ):
            raise RuntimeError("E1 requires an active non-autocommit transaction")
    operations.execute("SET LOCAL search_path = public, pg_catalog")
    operations.execute("SET LOCAL lock_timeout = '5s'")
    operations.execute("SET LOCAL statement_timeout = '60s'")


# ==============================================
# CREATE NEW TABLE
# ==============================================


def _create_table(*, operations: Operations, table: sa.Table) -> None:
    """Emit one explicitly owned table and its deterministic indexes."""
    if table.name not in TENANT_TABLE_NAMES or table.info.get("external_reference"):
        raise ValueError("E1 cannot create an external reference table")
    create = ops.CreateTableOp.from_table(table)
    # Alembic otherwise copies the unordered constraint set. Stable ordering is
    # required for identical review SQL in both histories and across processes.
    create.columns = [
        *table.columns,
        *sorted(table.constraints, key=lambda constraint: str(constraint.name)),
    ]
    operations.invoke(create)
    for index in sorted(table.indexes, key=lambda item: str(item.name)):
        operations.invoke(ops.CreateIndexOp.from_index(index))


# ==============================================
# UPGRADE FOUNDATION
# ==============================================


def upgrade_e1(*, operations: Operations) -> None:
    """Emit the frozen expand contract and policy definitions, without backfill."""
    _configure(operations=operations)
    metadata = operation_metadata()
    for name in TENANT_TABLE_NAMES[:5]:
        _create_table(operations=operations, table=metadata.tables[name])
    for table_name, column_name in EXPANSIONS:
        operations.add_column(
            table_name, sa.Column(column_name, sa.Integer(), nullable=True)
        )
    for table_name, _ in EXPANSIONS:
        table = metadata.tables[table_name]
        for constraint in sorted(table.constraints, key=lambda item: str(item.name)):
            if isinstance(constraint, (sa.ForeignKeyConstraint, sa.UniqueConstraint)):
                operations.invoke(ops.AddConstraintOp.from_constraint(constraint))
        for index in sorted(table.indexes, key=lambda item: str(item.name)):
            operations.invoke(ops.CreateIndexOp.from_index(index))
    for name in TENANT_TABLE_NAMES[5:]:
        _create_table(operations=operations, table=metadata.tables[name])

    operations.bulk_insert(
        metadata.tables["tenant_roles"],
        [{"code": role, "policy_revision": 1} for role in sorted(ROLE_PERMISSIONS)],
    )
    operations.bulk_insert(
        metadata.tables["tenant_role_permissions"],
        [
            {"role_code": role, "permission_code": permission}
            for role in sorted(ROLE_PERMISSIONS)
            for permission in ROLE_PERMISSIONS[role]
        ],
    )
    for statement in FUNCTION_DEFINITIONS:
        operations.execute(sa.DDL(statement))
    for _, _, statement in TRIGGER_DEFINITIONS:
        operations.execute(sa.DDL(statement))
    for name in TENANT_TABLE_NAMES:
        operations.execute(f"REVOKE ALL ON TABLE public.{name} FROM PUBLIC")


# ==============================================
# BUILD GUARDED DOWNGRADE CHECK
# ==============================================


def downgrade_guard_sql() -> str:
    """Reject removal of any tenant data, links, cutover or changed policies."""
    checks = [
        f"EXISTS (SELECT 1 FROM public.{name})"
        for name in TENANT_TABLE_NAMES
        if name not in {"tenant_roles", "tenant_role_permissions"}
    ]
    checks.extend(
        f"EXISTS (SELECT 1 FROM public.{table} WHERE {column} IS NOT NULL)"
        for table, column in EXPANSIONS
    )
    role_values = ", ".join(
        f"('{role}', 1::bigint)" for role in sorted(ROLE_PERMISSIONS)
    )
    policy_values = ", ".join(
        f"('{role}', '{permission}')"
        for role in sorted(ROLE_PERMISSIONS)
        for permission in ROLE_PERMISSIONS[role]
    )
    for table, columns, values in (
        ("tenant_roles", "code, policy_revision", role_values),
        ("tenant_role_permissions", "role_code, permission_code", policy_values),
    ):
        actual = f"SELECT {columns} FROM public.{table}"
        expected = f"VALUES {values}"
        checks.append(
            f"EXISTS (({actual} EXCEPT {expected}) UNION ALL ({expected} EXCEPT {actual}))"
        )
    return (
        """DO $e1$
BEGIN
    IF """
        + "\n        OR ".join(checks)
        + """ THEN
        RAISE EXCEPTION 'E1 downgrade refused: retained data, links or policy drift'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_empty_downgrade';
    END IF;
END;
$e1$"""
    )


# ==============================================
# DOWNGRADE EMPTY FOUNDATION ONLY
# ==============================================


def downgrade_e1(*, operations: Operations) -> None:
    """Remove only unused E1 objects, after exclusive locks and fail-closed checks."""
    _configure(operations=operations)
    tables = sorted(set(TENANT_TABLE_NAMES) | {name for name, _ in EXPANSIONS})
    operations.execute(
        "LOCK TABLE "
        + ", ".join(f"public.{name}" for name in tables)
        + " IN ACCESS EXCLUSIVE MODE"
    )
    operations.execute(sa.DDL(downgrade_guard_sql()))
    for table_name, trigger_name, _ in reversed(TRIGGER_DEFINITIONS):
        operations.execute(f"DROP TRIGGER {trigger_name} ON public.{table_name}")
    for signature in reversed(FUNCTION_SIGNATURES):
        operations.execute(f"DROP FUNCTION public.{signature}")
    for name in reversed(TENANT_TABLE_NAMES[3:]):
        operations.drop_table(name)
    metadata = operation_metadata()
    for table_name, column_name in reversed(EXPANSIONS):
        table = metadata.tables[table_name]
        for index in sorted(table.indexes, key=lambda item: str(item.name)):
            operations.drop_index(str(index.name), table_name=table_name)
        for constraint in sorted(table.constraints, key=lambda item: str(item.name)):
            if isinstance(constraint, (sa.ForeignKeyConstraint, sa.UniqueConstraint)):
                operations.drop_constraint(
                    str(constraint.name),
                    table_name,
                    type_=(
                        "foreignkey"
                        if isinstance(constraint, sa.ForeignKeyConstraint)
                        else "unique"
                    ),
                )
        operations.drop_column(table_name, column_name)
    for name in reversed(TENANT_TABLE_NAMES[:3]):
        operations.drop_table(name)
