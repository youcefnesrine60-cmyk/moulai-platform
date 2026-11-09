# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# FROZEN D1 DINING SCHEMA CONTRACT
# Define the additive post-S1a schema independently of application ORM changes.
# ==============================================

"""Versioned D1 table definitions; only its migration executes these definitions.

The factory returns independent metadata copies for migration and ORM use. It
does not import application models, inspect an environment, or perform I/O.
Existing prerequisite tables are references only and must never be created here.
Future schema changes require a new revision, not edits to this D1 contract.
"""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND CLOSED TECHNICAL VOCABULARY
# Use native SQLAlchemy DDL constructs and PostgreSQL range exclusion support.
# ==============================================

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import (
    JSONB,
    ExcludeConstraint,
)
from sqlalchemy.sql.schema import SchemaItem

D1_REVISION = "d1a20261102"
D1_PARENT = "s1a20261028"
D1_TABLES = (
    "dining_policies",
    "dining_references",
    "dining_grants",
    "dining_calendar",
    "dining_tables",
    "dining_traits",
    "dining_combinations",
    "dining_members",
    "dining_blackouts",
    "dining_requests",
    "dining_request_tables",
    "dining_confirmations",
    "dining_tariffs",
    "dining_quotes",
    "dining_acceptances",
    "dining_claims",
    "dining_occupations",
    "dining_occupation_tables",
    "dining_receipts",
    "dining_invoices",
    "dining_invoice_orders",
    "dining_allocations",
    "dining_events",
    "dining_outbox",
)
REFERENCE_KINDS = (
    "'shape','category','zone','location','view','proximity','feature','event'"
)
CAPABILITIES = "'read','service','clean','collect','assistant'"


# ==============================================
# FRESH METADATA WITH EXTERNAL PREREQUISITE REFERENCES
# Scope every dining row and preserve existing primary keys and financial data.
# ==============================================


def dining_schema() -> MetaData:
    """Build the exact D1 contract without executing CREATE TABLE or create_all.

    External reference definitions contain only columns needed for D1 foreign
    keys. They are not historical baseline reconstructions or ORM replacements.
    """
    metadata = MetaData()
    for name in ("restaurants", "branches", "organization_memberships", "products"):
        columns = [Column("id", Integer, primary_key=True)]
        if name == "branches":
            columns.append(Column("restaurant_id", Integer))
        Table(name, metadata, *columns)
    Table("orders", metadata, Column("id", BigInteger, primary_key=True))

    # ==============================================
    # SCOPED RECORD FACTORY
    # Give every resource a stable key, technical timestamp and composite scope.
    # ==============================================

    def record(name: str, *items: SchemaItem) -> Table:
        """Declare one table; positional arguments are SQL schema items."""
        scoped = (
            []
            if name == "dining_policies"
            else [
                ForeignKeyConstraint(
                    ["restaurant_id", "branch_id"],
                    ["dining_policies.restaurant_id", "dining_policies.branch_id"],
                    name=f"fk_{name}_scope",
                    ondelete="RESTRICT",
                )
            ]
        )
        declared = Table(
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
                "restaurant_id", "branch_id", "id", name=f"uq_{name}_scope_id"
            ),
            *scoped,
            *items,
        )
        for column in declared.columns:
            if isinstance(column.type, Numeric):
                # PostgreSQL Numeric NaN otherwise sorts above ordinary money
                # and can satisfy an apparently nonnegative CHECK condition.
                declared.append_constraint(
                    CheckConstraint(
                        f"\"{column.name}\" <> 'NaN'::numeric",
                        name=f"ck_d1_finite_{name}_{column.name}",
                    )
                )
        return declared

    # ==============================================
    # SCOPED FOREIGN KEY FACTORY
    # A child key can never point into a different restaurant or branch.
    # ==============================================

    def link(name: str, column: str, parent: str) -> ForeignKeyConstraint:
        """Return an exact composite SQL FK; never infer ownership from an ID."""
        return ForeignKeyConstraint(
            ["restaurant_id", "branch_id", column],
            [f"{parent}.restaurant_id", f"{parent}.branch_id", f"{parent}.id"],
            name=f"fk_{name}_{column}",
            ondelete="RESTRICT",
        )

    # ==============================================
    # BRANCH CONFIGURATION AND HUMAN CAPABILITIES
    # Store owner-supplied policies; no timing, price or personal-grant seeds.
    # ==============================================

    record(
        "dining_policies",
        Column("timezone", String(100), nullable=False),
        Column("settings", JSONB, nullable=False),
        UniqueConstraint("restaurant_id", "branch_id", name="uq_dining_policy_scope"),
        ForeignKeyConstraint(
            ["branch_id", "restaurant_id"],
            ["branches.id", "branches.restaurant_id"],
            name="fk_dining_policy_branch",
            ondelete="RESTRICT",
        ),
    )
    record(
        "dining_references",
        Column("kind", String(30), nullable=False),
        Column("code", String(80), nullable=False),
        Column("labels", JSONB, nullable=False),
        Column("active", Boolean, nullable=False),
        Column("pricing_ref", String(100)),
        CheckConstraint(
            f"kind IN ({REFERENCE_KINDS})", name="ck_dining_reference_kind"
        ),
        CheckConstraint(
            "kind <> 'shape' OR code IN ('round','rectangular','square','oval')",
            name="ck_dining_shape",
        ),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "kind",
            "code",
            name="uq_dining_reference_code",
        ),
    )
    record(
        "dining_grants",
        Column("membership_id", Integer, nullable=False),
        Column("capability", String(30), nullable=False),
        Column("actor_kind", String(20), nullable=False),
        Column("active", Boolean, nullable=False),
        Column("granted_by", Integer, nullable=False),
        ForeignKeyConstraint(
            ["membership_id"],
            ["organization_memberships.id"],
            name="fk_dining_grant_member",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["granted_by"],
            ["organization_memberships.id"],
            name="fk_dining_grant_author",
            ondelete="RESTRICT",
        ),
        CheckConstraint(f"capability IN ({CAPABILITIES})", name="ck_dining_capability"),
        CheckConstraint(
            "actor_kind IN ('human','assistant') AND (actor_kind='human' OR capability IN ('read','assistant'))",
            name="ck_dining_assistant_ceiling",
        ),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "membership_id",
            "capability",
            name="uq_dining_grant",
        ),
    )
    calendar = record(
        "dining_calendar",
        Column("weekday", Integer),
        Column("service_date", Date),
        Column("windows", JSONB, nullable=False),
        CheckConstraint(
            "(weekday BETWEEN 0 AND 6 AND service_date IS NULL) OR (weekday IS NULL AND service_date IS NOT NULL)",
            name="ck_dining_calendar_target",
        ),
    )
    Index(
        "uq_dining_weekday",
        calendar.c.restaurant_id,
        calendar.c.branch_id,
        calendar.c.weekday,
        unique=True,
        postgresql_where=text("service_date IS NULL"),
    )
    Index(
        "uq_dining_calendar_date",
        calendar.c.restaurant_id,
        calendar.c.branch_id,
        calendar.c.service_date,
        unique=True,
        postgresql_where=text("service_date IS NOT NULL"),
    )

    # ==============================================
    # DESCRIPTIVE TABLES AND AUTHORIZED COMBINATIONS
    # Keep physical state independent of planning, references and retirement.
    # ==============================================

    record(
        "dining_tables",
        Column("code", String(80), nullable=False),
        Column("name", String(200)),
        Column("min_capacity", Integer, nullable=False),
        Column("max_capacity", Integer, nullable=False),
        Column("shape_id", Integer, nullable=False),
        Column("category_id", Integer, nullable=False),
        Column("zone_id", Integer, nullable=False),
        Column("location_id", Integer, nullable=False),
        Column("description", Text, nullable=False),
        Column("photos", JSONB, nullable=False),
        Column("pricing_ref", String(100), nullable=False),
        Column("in_service", Boolean, nullable=False),
        Column("physical_state", String(30), nullable=False),
        Column("revision", BigInteger, nullable=False, server_default=text("1")),
        CheckConstraint(
            "min_capacity > 0 AND max_capacity >= min_capacity",
            name="ck_dining_capacity",
        ),
        CheckConstraint(
            "physical_state IN ('available','occupied','dirty','maintenance','out_of_service')",
            name="ck_dining_physical_state",
        ),
        UniqueConstraint(
            "restaurant_id", "branch_id", "code", name="uq_dining_table_code"
        ),
        *(
            link("dining_table", f"{kind}_id", "dining_references")
            for kind in ("shape", "category", "zone", "location")
        ),
    )
    record(
        "dining_traits",
        Column("table_id", Integer, nullable=False),
        Column("reference_id", Integer, nullable=False),
        Column("kind", String(30), nullable=False),
        CheckConstraint(
            "kind IN ('view','proximity','feature')", name="ck_dining_trait_kind"
        ),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "table_id",
            "reference_id",
            name="uq_dining_trait",
        ),
        link("dining_trait", "table_id", "dining_tables"),
        link("dining_trait", "reference_id", "dining_references"),
    )
    record(
        "dining_combinations",
        Column("code", String(80), nullable=False),
        Column("min_capacity", Integer, nullable=False),
        Column("max_capacity", Integer, nullable=False),
        Column("pricing_ref", String(100), nullable=False),
        Column("active", Boolean, nullable=False),
        CheckConstraint(
            "min_capacity > 0 AND max_capacity >= min_capacity",
            name="ck_dining_combination_capacity",
        ),
        UniqueConstraint(
            "restaurant_id", "branch_id", "code", name="uq_dining_combination_code"
        ),
    )
    record(
        "dining_members",
        Column("combination_id", Integer, nullable=False),
        Column("table_id", Integer, nullable=False),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "combination_id",
            "table_id",
            name="uq_dining_combination_member",
        ),
        link("dining_member", "combination_id", "dining_combinations"),
        link("dining_member", "table_id", "dining_tables"),
    )
    record(
        "dining_blackouts",
        Column("table_id", Integer),
        Column("zone_id", Integer),
        Column("starts_at", DateTime(timezone=True), nullable=False),
        Column("ends_at", DateTime(timezone=True), nullable=False),
        Column("kind", String(30), nullable=False),
        Column("reason", String(500), nullable=False),
        Column("active", Boolean, nullable=False),
        CheckConstraint(
            "ends_at > starts_at AND (table_id IS NULL OR zone_id IS NULL)",
            name="ck_dining_blackout_interval",
        ),
        CheckConstraint(
            "kind IN ('closure','maintenance','preparation','cleaning')",
            name="ck_dining_blackout_kind",
        ),
        link("dining_blackout", "table_id", "dining_tables"),
        link("dining_blackout", "zone_id", "dining_references"),
    )

    # ==============================================
    # REQUESTS, HUMAN EVIDENCE AND EXCLUSIVE PLANNING
    # Store immutable time bounds and protect claims even against concurrent SQL.
    # ==============================================

    record(
        "dining_requests",
        Column("reference", String(64), nullable=False, unique=True),
        Column("customer_issuer", String(500), nullable=False),
        Column("customer_subject", String(255), nullable=False),
        Column("customer_name", String(200), nullable=False),
        Column("contact", String(300), nullable=False),
        Column("starts_at", DateTime(timezone=True), nullable=False),
        Column("ends_at", DateTime(timezone=True), nullable=False),
        Column("party_size", Integer, nullable=False),
        Column("event_id", Integer),
        Column("preparation", Boolean, nullable=False),
        Column("criteria", JSONB, nullable=False),
        Column("menu", JSONB, nullable=False),
        Column("status", String(30), nullable=False),
        Column("transmitted_at", DateTime(timezone=True)),
        Column("confirmed_at", DateTime(timezone=True)),
        Column("qr_token", String(100)),
        Column("qr_hash", String(64), unique=True),
        CheckConstraint(
            "ends_at > starts_at AND party_size > 0", name="ck_dining_request_period"
        ),
        CheckConstraint(
            "status IN ('pending','held','confirmed','arrived','served','cancelled','manual_review')",
            name="ck_dining_request_status",
        ),
        link("dining_request", "event_id", "dining_references"),
    )
    record(
        "dining_request_tables",
        Column("request_id", Integer, nullable=False),
        Column("table_id", Integer, nullable=False),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "request_id",
            "table_id",
            name="uq_dining_request_table",
        ),
        link("dining_request_table", "request_id", "dining_requests"),
        link("dining_request_table", "table_id", "dining_tables"),
    )
    record(
        "dining_confirmations",
        Column("request_id", Integer),
        Column("starts_at", DateTime(timezone=True), nullable=False),
        Column("ends_at", DateTime(timezone=True), nullable=False),
        Column("valid_until", DateTime(timezone=True), nullable=False),
        Column("table_versions", JSONB, nullable=False),
        Column("membership_id", Integer, nullable=False),
        Column("origin", String(20), nullable=False),
        CheckConstraint(
            "ends_at > starts_at AND origin='human'",
            name="ck_dining_human_confirmation",
        ),
        link("dining_confirmation", "request_id", "dining_requests"),
        ForeignKeyConstraint(
            ["membership_id"],
            ["organization_memberships.id"],
            name="fk_dining_confirmation_author",
            ondelete="RESTRICT",
        ),
    )
    record(
        "dining_claims",
        Column("request_id", Integer),
        Column("table_id", Integer, nullable=False),
        Column("starts_at", DateTime(timezone=True), nullable=False),
        Column("ends_at", DateTime(timezone=True), nullable=False),
        Column("kind", String(20), nullable=False),
        Column("expires_at", DateTime(timezone=True)),
        Column("active", Boolean, nullable=False),
        CheckConstraint(
            "ends_at > starts_at AND kind IN ('hold','reservation','occupation') AND (kind <> 'hold' OR expires_at IS NOT NULL)",
            name="ck_dining_claim_period",
        ),
        link("dining_claim", "request_id", "dining_requests"),
        link("dining_claim", "table_id", "dining_tables"),
        ExcludeConstraint(
            ("table_id", "="),
            (text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=text("active"),
            name="ex_dining_active_table_period",
            using="gist",
        ),
    )

    # ==============================================
    # VERSIONED TARIFFS AND EXACT-DECIMAL ACCEPTED QUOTES
    # Preserve accepted contents and reject ambiguous price validity intervals.
    # ==============================================

    record(
        "dining_tariffs",
        Column("reference", String(100), nullable=False),
        Column("component", String(20), nullable=False),
        Column("currency", String(3), nullable=False),
        Column("unit", String(20), nullable=False),
        Column("unit_price", Numeric(24, 8), nullable=False),
        Column("valid_from", DateTime(timezone=True), nullable=False),
        Column("valid_until", DateTime(timezone=True)),
        CheckConstraint(
            "unit_price >= 0 AND (valid_until IS NULL OR valid_until > valid_from)",
            name="ck_dining_tariff_validity",
        ),
        CheckConstraint(
            "(component='table' AND unit='per_hour') OR (component='preparation' AND unit IN ('flat','per_person','per_hour')) OR (component='menu' AND unit='per_item')",
            name="ck_dining_tariff_unit",
        ),
        ExcludeConstraint(
            ("branch_id", "="),
            ("reference", "="),
            ("component", "="),
            ("currency", "="),
            (text("tstzrange(valid_from,valid_until,'[)')"), "&&"),
            name="ex_dining_tariff_validity",
            using="gist",
        ),
    )
    record(
        "dining_quotes",
        Column("request_id", Integer, nullable=False),
        Column("version", Integer, nullable=False),
        Column("currency", String(3), nullable=False),
        Column("amount", Numeric(24, 8), nullable=False),
        Column("components", JSONB, nullable=False),
        Column("terms", Text, nullable=False),
        Column("menu_digest", String(64), nullable=False),
        Column("digest", String(64), nullable=False),
        Column("expires_at", DateTime(timezone=True), nullable=False),
        CheckConstraint("version > 0 AND amount >= 0", name="ck_dining_quote_amount"),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "request_id",
            "version",
            name="uq_dining_quote_version",
        ),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "id",
            "request_id",
            name="uq_dining_quote_request",
        ),
        link("dining_quote", "request_id", "dining_requests"),
    )
    record(
        "dining_acceptances",
        Column("quote_id", Integer, nullable=False),
        Column("party", String(20), nullable=False),
        Column("digest", String(64), nullable=False),
        Column("author", JSONB, nullable=False),
        CheckConstraint(
            "party IN ('customer','restaurant')", name="ck_dining_acceptance_party"
        ),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "quote_id",
            "party",
            name="uq_dining_acceptance",
        ),
        link("dining_acceptance", "quote_id", "dining_quotes"),
    )

    # ==============================================
    # REAL OCCUPATION AND CLEANING TIMESTAMPS
    # Predicted ends never free the physical table; explicit completion does.
    # ==============================================

    record(
        "dining_occupations",
        Column("request_id", Integer),
        Column("party_size", Integer, nullable=False),
        Column("arrived_at", DateTime(timezone=True), nullable=False),
        Column("expected_end", DateTime(timezone=True), nullable=False),
        Column("departed_at", DateTime(timezone=True)),
        Column("cleaning_expected_start", DateTime(timezone=True), nullable=False),
        Column("cleaning_actual_start", DateTime(timezone=True)),
        Column("cleaning_expected_end", DateTime(timezone=True), nullable=False),
        Column("cleaning_actual_end", DateTime(timezone=True)),
        Column("status", String(20), nullable=False),
        Column("installed_by", Integer, nullable=False),
        Column("departure_by", Integer),
        Column("cleaned_by", Integer),
        CheckConstraint(
            "party_size > 0 AND expected_end > arrived_at AND cleaning_expected_end >= cleaning_expected_start",
            name="ck_dining_occupation_period",
        ),
        CheckConstraint(
            "status IN ('occupied','dirty','cleaning','closed')",
            name="ck_dining_occupation_status",
        ),
        link("dining_occupation", "request_id", "dining_requests"),
    )
    occupation_tables = record(
        "dining_occupation_tables",
        Column("occupation_id", Integer, nullable=False),
        Column("table_id", Integer, nullable=False),
        Column("active", Boolean, nullable=False),
        link("dining_occupation_table", "occupation_id", "dining_occupations"),
        link("dining_occupation_table", "table_id", "dining_tables"),
    )
    Index(
        "uq_dining_live_occupation",
        occupation_tables.c.table_id,
        unique=True,
        postgresql_where=text("active"),
    )

    # ==============================================
    # RESTAURANT ADVANCE FACTS AND SINGLE INVOICE APPLICATION
    # Receipt facts survive subsequent reservation failures and cannot be reused.
    # ==============================================

    record(
        "dining_receipts",
        Column("request_id", Integer, nullable=False),
        Column("quote_id", Integer, nullable=False),
        Column("expected_amount", Numeric(24, 8), nullable=False),
        Column("received_amount", Numeric(24, 8), nullable=False),
        Column("currency", String(3), nullable=False),
        Column("mode", String(30), nullable=False),
        Column("reference", String(120), nullable=False),
        Column("received_at", DateTime(timezone=True), nullable=False),
        Column("validated_by", Integer, nullable=False),
        Column("status", String(30), nullable=False),
        Column("review_reason", String(100)),
        CheckConstraint(
            "received_amount > 0 AND expected_amount >= 0 AND status IN ('verified','manual_review')",
            name="ck_dining_receipt_facts",
        ),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "mode",
            "reference",
            name="uq_dining_receipt_reference",
        ),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "id",
            "request_id",
            name="uq_dining_receipt_request",
        ),
        ForeignKeyConstraint(
            ["restaurant_id", "branch_id", "quote_id", "request_id"],
            [
                "dining_quotes.restaurant_id",
                "dining_quotes.branch_id",
                "dining_quotes.id",
                "dining_quotes.request_id",
            ],
            name="fk_dining_receipt_quote",
            ondelete="RESTRICT",
        ),
    )
    record(
        "dining_invoices",
        Column("request_id", Integer, nullable=False, unique=True),
        Column("status", String(20), nullable=False),
        Column("currency", String(3), nullable=False),
        Column("precision", Integer, nullable=False),
        Column("revision", BigInteger, nullable=False),
        Column("lines", JSONB, nullable=False),
        Column("provenance", JSONB, nullable=False),
        Column("total", Numeric(24, 8), nullable=False),
        Column("finalized_by", Integer),
        Column("finalized_at", DateTime(timezone=True)),
        CheckConstraint(
            "status IN ('draft','finalized') AND total >= 0 AND precision BETWEEN 0 AND 8 AND revision > 0",
            name="ck_dining_invoice",
        ),
        CheckConstraint(
            "(status='draft' AND finalized_at IS NULL AND finalized_by IS NULL) OR (status='finalized' AND finalized_at IS NOT NULL AND finalized_by IS NOT NULL)",
            name="ck_dining_invoice_finalization",
        ),
        link("dining_invoice", "request_id", "dining_requests"),
    )
    record(
        "dining_invoice_orders",
        Column("invoice_id", Integer, nullable=False),
        Column("order_id", BigInteger, nullable=False, unique=True),
        Column("source_snapshot", JSONB, nullable=False),
        link("dining_invoice_order", "invoice_id", "dining_invoices"),
        ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name="fk_dining_invoice_order_source",
            ondelete="RESTRICT",
        ),
    )
    record(
        "dining_allocations",
        Column("request_id", Integer, nullable=False),
        Column("receipt_id", Integer, nullable=False, unique=True),
        Column("invoice_id", Integer, nullable=False),
        Column("invoice_revision", BigInteger, nullable=False),
        Column("invoice_total", Numeric(24, 8), nullable=False),
        Column("other_paid", Numeric(24, 8), nullable=False),
        Column("amount", Numeric(24, 8), nullable=False),
        Column("currency", String(3), nullable=False),
        Column("balance", Numeric(24, 8), nullable=False),
        CheckConstraint(
            "amount > 0 AND invoice_total >= 0 AND other_paid >= 0 AND balance >= 0 AND invoice_total=amount+other_paid+balance",
            name="ck_dining_allocation_balance",
        ),
        ForeignKeyConstraint(
            ["restaurant_id", "branch_id", "receipt_id", "request_id"],
            [
                "dining_receipts.restaurant_id",
                "dining_receipts.branch_id",
                "dining_receipts.id",
                "dining_receipts.request_id",
            ],
            name="fk_dining_allocation_receipt",
            ondelete="RESTRICT",
        ),
        link("dining_allocation", "invoice_id", "dining_invoices"),
    )

    # ==============================================
    # APPEND-ONLY EVENT HISTORY AND TRANSACTIONAL OUTBOX
    # Publish only committed evidence through explicitly injected transports.
    # ==============================================

    record(
        "dining_events",
        Column("request_id", Integer),
        Column("kind", String(80), nullable=False),
        Column("author", JSONB, nullable=False),
        Column("details", JSONB, nullable=False),
        Column("occurred_at", DateTime(timezone=True), nullable=False),
        link("dining_event", "request_id", "dining_requests"),
    )
    record(
        "dining_outbox",
        Column("request_id", Integer),
        Column("event_key", String(160), nullable=False),
        Column("target", String(160), nullable=False),
        Column("payload", JSONB, nullable=False),
        Column("due_at", DateTime(timezone=True), nullable=False),
        Column("status", String(20), nullable=False),
        Column("attempts", Integer, nullable=False, server_default=text("0")),
        Column("delivery_reference", String(200)),
        UniqueConstraint(
            "restaurant_id",
            "branch_id",
            "event_key",
            "target",
            name="uq_dining_outbox_delivery",
        ),
        CheckConstraint(
            "status IN ('pending','sending','delivered','failed','uncertain','cancelled') AND attempts >= 0",
            name="ck_dining_outbox_status",
        ),
        link("dining_outbox", "request_id", "dining_requests"),
    )
    return metadata
