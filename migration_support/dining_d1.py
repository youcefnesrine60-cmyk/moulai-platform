# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ADDITIVE D1 MIGRATION EXECUTOR
# Apply frozen dining DDL after S1a and preserve immutable financial evidence.
# ==============================================

"""Execute versioned dining schema statements, never application metadata DDL."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND FROZEN TRIGGERS
# Database constraints complement scoped services and concurrent claim exclusion.
# ==============================================

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.schema import (
    CreateIndex,
    CreateTable,
)

from migration_support.dining_d1_schema import (
    D1_PARENT,
    D1_TABLES,
    dining_schema,
)

TRIGGER_DDL = (
    """CREATE FUNCTION public.dining_d1_retain() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
    BEGIN RAISE EXCEPTION 'dining_evidence_is_append_only' USING ERRCODE='23514'; END $$""",
    """CREATE FUNCTION public.dining_d1_reference_kind() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
    DECLARE item record; expected text; actual text;
    BEGIN
      IF TG_TABLE_NAME='dining_tables' THEN
        FOR item IN SELECT * FROM (VALUES
          (NEW.shape_id,'shape'),(NEW.category_id,'category'),
          (NEW.zone_id,'zone'),(NEW.location_id,'location')) AS x(id,kind)
        LOOP
          SELECT kind INTO actual FROM public.dining_references
          WHERE id=item.id AND restaurant_id=NEW.restaurant_id AND branch_id=NEW.branch_id;
          IF actual IS DISTINCT FROM item.kind THEN
            RAISE EXCEPTION 'dining_reference_kind_mismatch' USING ERRCODE='23514';
          END IF;
        END LOOP;
      ELSIF TG_TABLE_NAME='dining_traits' THEN
        SELECT kind INTO actual FROM public.dining_references
        WHERE id=NEW.reference_id AND restaurant_id=NEW.restaurant_id AND branch_id=NEW.branch_id;
        IF actual IS DISTINCT FROM NEW.kind THEN
          RAISE EXCEPTION 'dining_reference_kind_mismatch' USING ERRCODE='23514';
        END IF;
      ELSIF TG_TABLE_NAME='dining_blackouts' AND NEW.zone_id IS NOT NULL THEN
        SELECT kind INTO actual FROM public.dining_references
        WHERE id=NEW.zone_id AND restaurant_id=NEW.restaurant_id AND branch_id=NEW.branch_id;
        IF actual IS DISTINCT FROM 'zone' THEN
          RAISE EXCEPTION 'dining_reference_kind_mismatch' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$""",
    """CREATE FUNCTION public.dining_d1_grant_scope() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
    DECLARE company integer; member_company integer; author_company integer; author_role text; member_role text;
    BEGIN
      SELECT organization_id INTO company FROM public.restaurants WHERE id=NEW.restaurant_id;
      SELECT organization_id,role_code INTO member_company,member_role FROM public.organization_memberships WHERE id=NEW.membership_id;
      SELECT organization_id,role_code INTO author_company,author_role FROM public.organization_memberships WHERE id=NEW.granted_by;
      IF company IS NULL OR member_company IS DISTINCT FROM company
        OR author_company IS DISTINCT FROM company OR author_role IS DISTINCT FROM 'owner'
        OR (NEW.actor_kind='assistant' AND member_role='owner') THEN
        RAISE EXCEPTION 'dining_grant_scope_mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$""",
    """CREATE FUNCTION public.dining_d1_paid_request_guard() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
    BEGIN
      IF EXISTS (SELECT 1 FROM public.dining_receipts WHERE request_id=OLD.id)
        AND ROW(NEW.restaurant_id,NEW.branch_id,NEW.customer_issuer,NEW.customer_subject,
          NEW.starts_at,NEW.ends_at,NEW.party_size,NEW.event_id,NEW.preparation,NEW.menu)
        IS DISTINCT FROM ROW(OLD.restaurant_id,OLD.branch_id,OLD.customer_issuer,OLD.customer_subject,
          OLD.starts_at,OLD.ends_at,OLD.party_size,OLD.event_id,OLD.preparation,OLD.menu) THEN
        RAISE EXCEPTION 'dining_post_payment_change_requires_policy' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$""",
    """CREATE FUNCTION public.dining_d1_paid_assignment_guard() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
    DECLARE request_identifier integer;
    BEGIN
      IF TG_OP='DELETE' THEN request_identifier=OLD.request_id;
      ELSE request_identifier=NEW.request_id; END IF;
      IF EXISTS (SELECT 1 FROM public.dining_receipts WHERE request_id=request_identifier) THEN
        RAISE EXCEPTION 'dining_paid_assignment_is_retained' USING ERRCODE='23514';
      END IF;
      IF TG_OP='UPDATE' AND EXISTS (SELECT 1 FROM public.dining_receipts WHERE request_id=OLD.request_id) THEN
        RAISE EXCEPTION 'dining_paid_assignment_is_retained' USING ERRCODE='23514';
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$""",
    """CREATE FUNCTION public.dining_d1_invoice_retain() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
    BEGIN
      IF TG_OP='DELETE' OR OLD.status='finalized' THEN
        RAISE EXCEPTION 'dining_invoice_finalized_or_retained' USING ERRCODE='23514';
      END IF;
      IF ROW(NEW.id,NEW.restaurant_id,NEW.branch_id,NEW.request_id,NEW.currency,NEW.precision)
        IS DISTINCT FROM ROW(OLD.id,OLD.restaurant_id,OLD.branch_id,OLD.request_id,OLD.currency,OLD.precision) THEN
        RAISE EXCEPTION 'dining_invoice_identity_is_immutable' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$""",
)


# ==============================================
# REAL POST-S1A UPGRADE
# Require the recorded parent revision and fail atomically on any existing drift.
# ==============================================


def upgrade_dining(connection: Connection) -> None:
    """Execute actual D1 CREATE/constraint/trigger statements in Alembic's transaction.

    btree_gist is trusted in PostgreSQL 18, but requires CREATE privilege on the
    current database. This function does not change roles or grant privileges.
    """
    if (
        connection.scalar(text("SELECT version_num FROM public.alembic_version"))
        != D1_PARENT
    ):
        raise RuntimeError("dining_migration_requires_exact_s1a_parent")
    existing = set(
        connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        ).scalars()
    )
    if existing.intersection(D1_TABLES):
        raise RuntimeError("dining_migration_existing_schema_drift")
    connection.execute(
        text("CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public")
    )
    extension_schema = connection.scalar(
        text(
            "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='btree_gist'"
        )
    )
    if extension_schema != "public":
        raise RuntimeError("dining_btree_gist_schema_requires_review")
    connection.execute(
        text(
            "CREATE UNIQUE INDEX uq_d1_branch_restaurant ON public.branches(id,restaurant_id)"
        )
    )
    metadata = dining_schema()
    for name in D1_TABLES:
        table = metadata.tables[name]
        connection.execute(CreateTable(table))
        for index in sorted(table.indexes, key=lambda item: str(item.name)):
            connection.execute(CreateIndex(index))
    for statement in TRIGGER_DDL:
        connection.execute(text(statement))
    connection.execute(
        text(
            "CREATE TRIGGER tr_dining_paid_assignment_guard BEFORE INSERT OR UPDATE OR DELETE ON public.dining_request_tables FOR EACH ROW EXECUTE FUNCTION public.dining_d1_paid_assignment_guard()"
        )
    )
    for name in (
        "dining_quotes",
        "dining_acceptances",
        "dining_receipts",
        "dining_allocations",
        "dining_events",
        "dining_confirmations",
        "dining_tariffs",
        "dining_invoice_orders",
    ):
        connection.execute(
            text(
                f"CREATE TRIGGER tr_{name}_retain BEFORE UPDATE OR DELETE ON public.{name} FOR EACH ROW EXECUTE FUNCTION public.dining_d1_retain()"
            )
        )
        connection.execute(
            text(
                f"CREATE TRIGGER tr_{name}_retain_truncate BEFORE TRUNCATE ON public.{name} FOR EACH STATEMENT EXECUTE FUNCTION public.dining_d1_retain()"
            )
        )
    for name in ("dining_tables", "dining_traits", "dining_blackouts"):
        connection.execute(
            text(
                f"CREATE TRIGGER tr_{name}_reference_kind BEFORE INSERT OR UPDATE ON public.{name} FOR EACH ROW EXECUTE FUNCTION public.dining_d1_reference_kind()"
            )
        )
    connection.execute(
        text(
            "CREATE TRIGGER tr_dining_grant_scope BEFORE INSERT OR UPDATE ON public.dining_grants FOR EACH ROW EXECUTE FUNCTION public.dining_d1_grant_scope()"
        )
    )
    connection.execute(
        text(
            "CREATE TRIGGER tr_dining_paid_request BEFORE UPDATE ON public.dining_requests FOR EACH ROW EXECUTE FUNCTION public.dining_d1_paid_request_guard()"
        )
    )
    connection.execute(
        text(
            "CREATE TRIGGER tr_dining_invoice_retain BEFORE UPDATE OR DELETE ON public.dining_invoices FOR EACH ROW EXECUTE FUNCTION public.dining_d1_invoice_retain()"
        )
    )
    connection.execute(
        text(
            "CREATE TRIGGER tr_dining_invoice_truncate BEFORE TRUNCATE ON public.dining_invoices FOR EACH STATEMENT EXECUTE FUNCTION public.dining_d1_retain()"
        )
    )
