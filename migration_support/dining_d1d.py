# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# D1D STAFF, PUBLIC DOCUMENTS AND CONTROLLED VISITS
# Extend the reviewed D1c graph without changing historical migrations or identity tables.
# ==============================================

"""Versioned additive schema; no accounts, tariffs or personal grants are seeded."""

from __future__ import annotations

# isort: split
# ==============================================
# DECLARATIVE SQL DEPENDENCIES
# Construct independent metadata; only an explicitly owned migration executes DDL.
# ==============================================

import hashlib
import json
import secrets
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection
from sqlalchemy.sql.schema import SchemaItem

from migration_support.dining_d1_schema import dining_schema
from migration_support.dining_d1c import CAPABILITY_CHECK as D1C_CAPABILITY_CHECK

# ==============================================
# EXACT VERSION AND OWNED RESOURCES
# New order powers remain branch-specific human grants, never role-name fallbacks.
# ==============================================

D1D_REVISION = "d1d20261105"
D1D_TABLES = (
    "dining_staff_profiles",
    "dining_staff_functions",
    "dining_staff_assignments",
    "dining_public_links",
    "dining_presence_signals",
    "dining_visits",
    "dining_visit_orders",
)
SERVICE_CAPABILITIES = (
    "orders.read",
    "orders.approve",
    "orders.prepare",
    "orders.complete",
    "documents.issue",
)
CAPABILITY_CHECK = (
    D1C_CAPABILITY_CHECK[:-1]
    + ","
    + ",".join(repr(value) for value in SERVICE_CAPABILITIES)
    + ")"
)


# ==============================================
# APPEND THE FROZEN SERVICE TABLE CONTRACT
# Every child retains composite restaurant/branch foreign keys and an explicit parent.
# ==============================================


def add_service_schema(*, metadata: MetaData) -> None:
    """Append independent tables to D1 metadata without I/O or implicit creation."""

    # ==============================================
    # SCOPED SQL RECORD FACTORY
    # Positional schema arguments are SQL helpers, not business service parameters.
    # ==============================================

    def record(name: str, *items: SchemaItem) -> Table:
        """Keep IDs globally unique and scope explicit on every extension record."""
        return Table(
            name,
            metadata,
            Column("id", Integer, Identity(), primary_key=True),
            Column("restaurant_id", Integer, nullable=False),
            Column("branch_id", Integer, nullable=False),
            Column(
                "created_at",
                DateTime(timezone=True),
                nullable=False,
                server_default=text("now()"),
            ),
            UniqueConstraint(
                "restaurant_id", "branch_id", "id", name=f"uq_{name}_scope"
            ),
            ForeignKeyConstraint(
                ["restaurant_id", "branch_id"],
                ["dining_policies.restaurant_id", "dining_policies.branch_id"],
                ondelete="RESTRICT",
                name=f"fk_{name}_scope",
            ),
            *items,
        )

    # ==============================================
    # COMPOSITE CHILD REFERENCE
    # A foreign identifier can never rebind a record to another establishment.
    # ==============================================

    def link(column: str, parent: str) -> ForeignKeyConstraint:
        """Preserve the scope of each optional or required resource relationship."""
        return ForeignKeyConstraint(
            ["restaurant_id", "branch_id", column],
            [f"{parent}.restaurant_id", f"{parent}.branch_id", f"{parent}.id"],
            ondelete="RESTRICT",
        )

    record(
        "dining_staff_profiles",
        Column("membership_id", Integer, nullable=False),
        Column("employee_code", String(50), nullable=False),
        Column("display_name", String(160), nullable=False),
        Column("enrollment_generation", Integer, nullable=False),
        Column("accepted_at", DateTime(timezone=True)),
        UniqueConstraint("restaurant_id", "branch_id", "membership_id"),
        UniqueConstraint("restaurant_id", "branch_id", "employee_code"),
        ForeignKeyConstraint(
            ["membership_id"], ["organization_memberships.id"], ondelete="RESTRICT"
        ),
    )
    record(
        "dining_staff_functions",
        Column("code", String(50), nullable=False),
        Column("labels", JSONB, nullable=False),
        Column("tasks", JSONB, nullable=False),
        Column("active", Boolean, nullable=False),
        UniqueConstraint("restaurant_id", "branch_id", "code"),
    )
    record(
        "dining_staff_assignments",
        Column("membership_id", Integer, nullable=False),
        Column("function_id", Integer, nullable=False),
        Column("active", Boolean, nullable=False),
        Column("assigned_by", Integer, nullable=False),
        UniqueConstraint("restaurant_id", "branch_id", "membership_id", "function_id"),
        ForeignKeyConstraint(
            ["membership_id"], ["organization_memberships.id"], ondelete="RESTRICT"
        ),
        link("function_id", "dining_staff_functions"),
    )
    record(
        "dining_public_links",
        Column("public_id", String(43), nullable=False, unique=True),
        Column("reference", String(80), nullable=False, unique=True),
        Column("kind", String(24), nullable=False),
        Column("version", Integer, nullable=False),
        Column("generation", Integer, nullable=False),
        Column("active", Boolean, nullable=False),
        Column("table_id", Integer),
        Column("request_id", Integer),
        Column("invoice_id", Integer),
        Column("receipt_id", Integer),
        Column("snapshot", JSONB, nullable=False),
        Column("digest", String(64), nullable=False),
        Column("invalidated_reason", String(100)),
        link("table_id", "dining_tables"),
        link("request_id", "dining_requests"),
        link("invoice_id", "dining_invoices"),
        link("receipt_id", "dining_receipts"),
        CheckConstraint(
            "version > 0 AND generation > 0 AND num_nonnulls(table_id,request_id,invoice_id,receipt_id)=1",
            name="ck_public_link_target",
        ),
        CheckConstraint(
            "(kind='table' AND table_id IS NOT NULL) OR (kind='reservation' AND request_id IS NOT NULL) OR (kind='food_invoice' AND invoice_id IS NOT NULL) OR (kind='receipt' AND receipt_id IS NOT NULL)",
            name="ck_public_link_kind",
        ),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "kind",
            "version",
            "generation",
            "table_id",
            "request_id",
            "invoice_id",
            "receipt_id",
            name="uq_public_link_generation",
            postgresql_nulls_not_distinct=True,
        ),
    )
    public_links = metadata.tables["dining_public_links"]
    Index(
        "uq_public_link_active_version",
        public_links.c.restaurant_id,
        public_links.c.branch_id,
        public_links.c.kind,
        public_links.c.version,
        public_links.c.table_id,
        public_links.c.request_id,
        public_links.c.invoice_id,
        public_links.c.receipt_id,
        unique=True,
        postgresql_where=text("active"),
        postgresql_nulls_not_distinct=True,
    )
    record(
        "dining_presence_signals",
        Column("public_link_id", Integer, nullable=False),
        Column("table_id", Integer, nullable=False),
        Column("token_hash", String(64), nullable=False, unique=True),
        Column("party_size", Integer, nullable=False),
        Column("status", String(16), nullable=False),
        Column("expires_at", DateTime(timezone=True), nullable=False),
        link("public_link_id", "dining_public_links"),
        link("table_id", "dining_tables"),
        CheckConstraint(
            "party_size > 0 AND status IN ('pending','installed','closed')",
            name="ck_presence_signal",
        ),
    )
    record(
        "dining_visits",
        Column("public_link_id", Integer, nullable=False),
        Column("presence_id", Integer, nullable=False, unique=True),
        Column("occupation_id", Integer, nullable=False),
        Column("table_id", Integer, nullable=False),
        Column("token_hash", String(64), nullable=False, unique=True),
        Column("status", String(16), nullable=False),
        Column("ended_at", DateTime(timezone=True)),
        link("public_link_id", "dining_public_links"),
        link("presence_id", "dining_presence_signals"),
        link("occupation_id", "dining_occupations"),
        link("table_id", "dining_tables"),
        CheckConstraint("status IN ('active','ended')", name="ck_visit_status"),
    )
    record(
        "dining_visit_orders",
        Column("visit_id", Integer, nullable=False),
        Column(
            "order_id", metadata.tables["orders"].c.id.type, nullable=False, unique=True
        ),
        Column("idempotency_key", String(80), nullable=False),
        Column("currency", String(3), nullable=False),
        Column("exact_lines", JSONB, nullable=False),
        Column("total", Numeric(24, 8), nullable=False),
        Column("digest", String(64), nullable=False),
        link("visit_id", "dining_visits"),
        ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        UniqueConstraint("visit_id", "idempotency_key"),
        CheckConstraint(
            "total >= 0 AND total <> 'NaN'::numeric", name="ck_visit_order_amount"
        ),
    )
    invoice = metadata.tables["dining_invoices"]
    table = metadata.tables["dining_tables"]
    table.append_column(Column("floor_label", String(160)))
    table.append_column(Column("room_label", String(160)))
    invoice.c.request_id.nullable = True
    invoice.append_column(Column("occupation_id", Integer))
    invoice.append_constraint(link("occupation_id", "dining_occupations"))
    invoice.append_constraint(
        UniqueConstraint("occupation_id", name="uq_dining_invoice_occupation")
    )
    invoice.append_constraint(
        CheckConstraint(
            "num_nonnulls(request_id,occupation_id)=1", name="ck_dining_invoice_context"
        )
    )


# ==============================================
# EXACT ADDITIVE UPGRADE
# Retain prior invoices and applied ancestry; do not infer any financial configuration.
# ==============================================


def upgrade_dining_d1d(*, connection: Connection) -> None:
    """Create owned additions and extend invoice context in one Alembic transaction."""
    if (
        connection.scalar(text("SELECT version_num FROM public.alembic_version"))
        != "d1c20261104"
    ):
        raise RuntimeError("dining_d1d_requires_exact_parent")
    metadata = dining_schema()
    add_service_schema(metadata=metadata)
    for name in D1D_TABLES:
        metadata.tables[name].create(connection)
    connection.execute(
        text(
            "ALTER TABLE public.dining_tables ADD COLUMN floor_label varchar(160), ADD COLUMN room_label varchar(160)"
        )
    )
    connection.execute(
        text("ALTER TABLE public.dining_grants DROP CONSTRAINT ck_dining_capability")
    )
    connection.execute(
        text(
            "ALTER TABLE public.dining_grants ADD CONSTRAINT ck_dining_capability CHECK ("
            + CAPABILITY_CHECK
            + ")"
        )
    )
    connection.execute(
        text(
            "ALTER TABLE public.dining_invoices ALTER COLUMN request_id DROP NOT NULL, ADD COLUMN occupation_id integer, ADD CONSTRAINT uq_dining_invoice_occupation UNIQUE (occupation_id), ADD CONSTRAINT fk_dining_invoice_occupation FOREIGN KEY (restaurant_id,branch_id,occupation_id) REFERENCES public.dining_occupations(restaurant_id,branch_id,id), ADD CONSTRAINT ck_dining_invoice_context CHECK (num_nonnulls(request_id,occupation_id)=1)"
        )
    )
    connection.execute(
        text(
            """CREATE FUNCTION public.dining_d1d_document_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    IF TG_OP='DELETE' OR ROW(NEW.public_id,NEW.reference,NEW.kind,NEW.version,NEW.generation,NEW.restaurant_id,NEW.branch_id,NEW.table_id,NEW.request_id,NEW.invoice_id,NEW.receipt_id,NEW.snapshot,NEW.digest) IS DISTINCT FROM ROW(OLD.public_id,OLD.reference,OLD.kind,OLD.version,OLD.generation,OLD.restaurant_id,OLD.branch_id,OLD.table_id,OLD.request_id,OLD.invoice_id,OLD.receipt_id,OLD.snapshot,OLD.digest) THEN RAISE EXCEPTION 'issued document identity is immutable' USING ERRCODE='23514'; END IF; RETURN NEW; END $$"""
        )
    )
    connection.execute(
        text(
            "CREATE TRIGGER tr_d1d_document_immutable BEFORE UPDATE OR DELETE ON public.dining_public_links FOR EACH ROW EXECUTE FUNCTION public.dining_d1d_document_immutable()"
        )
    )
    backfill_table_links(connection=connection)


# ==============================================
# EXISTING TABLE QR BACKFILL
# Give every historical table one opaque permanent menu target without publishing physical state.
# ==============================================


def backfill_table_links(*, connection: Connection) -> int:
    """Retain existing and revoked links; add only missing table identities, never prices or grants."""
    rows = tuple(
        connection.execute(
            text(
                "SELECT t.id,t.restaurant_id,t.branch_id,r.name restaurant,b.name branch FROM public.dining_tables t JOIN public.restaurants r ON r.id=t.restaurant_id JOIN public.branches b ON b.id=t.branch_id AND b.restaurant_id=t.restaurant_id WHERE NOT EXISTS (SELECT 1 FROM public.dining_public_links l WHERE l.restaurant_id=t.restaurant_id AND l.branch_id=t.branch_id AND l.table_id=t.id AND l.kind='table') ORDER BY t.restaurant_id,t.branch_id,t.id"
            )
        ).mappings()
    )
    for row in rows:
        snapshot = {
            "table_id": row["id"],
            "public_physical_state": False,
            "restaurant": row["restaurant"],
            "branch": row["branch"],
        }
        encoded = json.dumps(
            snapshot,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        connection.execute(
            text(
                "INSERT INTO public.dining_public_links(restaurant_id,branch_id,public_id,reference,kind,version,generation,active,table_id,snapshot,digest) VALUES (:restaurant,:branch,:public,:reference,'table',1,1,true,:table,CAST(:snapshot AS jsonb),:digest)"
            ),
            {
                "restaurant": row["restaurant_id"],
                "branch": row["branch_id"],
                "table": row["id"],
                "public": secrets.token_urlsafe(32),
                "reference": "DOC-" + uuid4().hex.upper(),
                "snapshot": encoded,
                "digest": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            },
        )
    return len(rows)
