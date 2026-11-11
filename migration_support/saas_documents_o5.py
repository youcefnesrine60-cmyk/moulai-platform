# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# O5 RETAINED SAAS DOCUMENT EVIDENCE
# Keep issued content and subsequent invalidation decisions append-only, independently of administrative accounts.
# ==============================================

"""Add documentary evidence without changing funds, subscription periods or personal grants."""

from sqlalchemy.engine import Connection

# ==============================================
# ADDITIVE TRANSACTIONAL STORAGE
# Referential restrictions retain financial sources; immutable rows prevent silent replacement or erasure.
# ==============================================


def upgrade(*, connection: Connection) -> None:
    """Create the distinct SaaS circuit inside the caller's attested Alembic transaction."""
    statements = (
        """CREATE TABLE subscription_documents(
          id bigserial PRIMARY KEY,public_id varchar(43) NOT NULL UNIQUE CHECK(public_id ~ '^[A-Za-z0-9_-]{43}$'),
          organization_id integer NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
          restaurant_id integer NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
          payment_id integer NOT NULL REFERENCES payments(id) ON DELETE RESTRICT,
          subscription_id integer NOT NULL REFERENCES subscriptions(id) ON DELETE RESTRICT,
          snapshot_id integer NOT NULL REFERENCES subscription_pricing_snapshots(id) ON DELETE RESTRICT,
          version integer NOT NULL CHECK(version>0),replaces_id bigint UNIQUE REFERENCES subscription_documents(id) ON DELETE RESTRICT,
          content jsonb NOT NULL CHECK(jsonb_typeof(content)='object'),sha256 varchar(64) NOT NULL CHECK(sha256 ~ '^[a-f0-9]{64}$'),
          author_admin_id integer NOT NULL,author_name varchar(255) NOT NULL,
          issued_at timestamptz NOT NULL DEFAULT now(),UNIQUE(payment_id,version))""",
        "CREATE INDEX ix_subscription_documents_scope ON subscription_documents(organization_id,restaurant_id,id)",
        """CREATE TABLE subscription_document_events(
          id bigserial PRIMARY KEY,document_id bigint NOT NULL REFERENCES subscription_documents(id) ON DELETE RESTRICT,
          event varchar(16) NOT NULL CHECK(event IN ('issued','invalidated')),
          author_admin_id integer NOT NULL,author_name varchar(255) NOT NULL,
          reason text NOT NULL CHECK(length(btrim(reason))>=3),occurred_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE(document_id,event))""",
        """CREATE FUNCTION guard_subscription_document_history() RETURNS trigger LANGUAGE plpgsql AS $body$
        BEGIN RAISE EXCEPTION 'subscription_document_history_immutable' USING ERRCODE='23514'; END $body$""",
    )
    for statement in statements:
        connection.exec_driver_sql(statement)
    for table in ("subscription_documents", "subscription_document_events"):
        connection.exec_driver_sql(
            f"CREATE TRIGGER retain_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION guard_subscription_document_history()"
        )
        connection.exec_driver_sql(
            f"CREATE TRIGGER retain_{table}_truncate BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION guard_subscription_document_history()"
        )


# ==============================================
# EVIDENCE-PRESERVING RECOVERY
# Reversing documentary history requires a separately verified backup rather than destructive automatic downgrade.
# ==============================================


def downgrade() -> None:
    """Refuse erasure of issued documents and their invalidation audit."""
    raise RuntimeError("subscription_document_history_preservation_required")
