# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# O4 VERIFIED BILLING COUNTRY AND ENROLLMENT CONTRACT
# Persist private evidence, explicit administrative decisions and versioned enrollment without personal grants.
# ==============================================

"""Additive operations after O3; no commercial foreign tariffs, legal texts or account grants are seeded."""

from sqlalchemy.engine import Connection

# ==============================================
# PREPARED TRANSACTIONAL SCHEMA
# Retain decisions and documents independently of account deletion and keep legacy history unmodified.
# ==============================================


def upgrade(*, connection: Connection) -> None:
    """Create owned evidence and decision records; the attested Alembic caller owns commit."""
    statements = (
        """UPDATE subscription_pricing_config SET policies=(policies::jsonb ||
          '{"base_storage":"country_versions","policy_revision":"o4-initial-policy"}'::jsonb)::json WHERE id=1""",
        """ALTER TABLE subscription_pricing_config ADD CONSTRAINT ck_country_base_storage
          CHECK((policies->>'base_storage') IS NOT DISTINCT FROM 'country_versions')""",
        """CREATE TABLE billing_country_profiles(
          organization_id integer PRIMARY KEY REFERENCES organizations(id) ON DELETE RESTRICT,
          revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
          created_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE TABLE billing_country_evidence(
          id varchar(32) PRIMARY KEY, organization_id integer NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
          submitted_identity_id integer NOT NULL REFERENCES identities(id) ON DELETE RESTRICT,
          filename varchar(180) NOT NULL,media_type varchar(80) NOT NULL,
          content bytea NOT NULL CHECK(octet_length(content)>0 AND octet_length(content)<=2097152),
          sha256 varchar(64) NOT NULL,synthetic boolean NOT NULL CHECK(synthetic),
          created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(organization_id,id))""",
        """CREATE TABLE billing_country_requests(
          id bigserial PRIMARY KEY,organization_id integer NOT NULL REFERENCES billing_country_profiles(organization_id),
          submitted_identity_id integer NOT NULL REFERENCES identities(id),declared_country varchar(2) NOT NULL CHECK(declared_country ~ '^[A-Z]{2}$'),
          legal_entity_reference varchar(180) NOT NULL,reason text NOT NULL,
          evidence_id varchar(32) NOT NULL,expected_revision bigint NOT NULL,
          status varchar(24) NOT NULL CHECK(status IN ('pending','needs_information','approved','rejected','superseded')),
          idempotency_key varchar(80) NOT NULL,submitted_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY(organization_id,evidence_id) REFERENCES billing_country_evidence(organization_id,id),
          UNIQUE(organization_id,idempotency_key),UNIQUE(organization_id,id))""",
        """CREATE UNIQUE INDEX uq_country_pending_request ON billing_country_requests(organization_id)
          WHERE status IN ('pending','needs_information')""",
        """CREATE TABLE billing_country_decisions(
          id bigserial PRIMARY KEY,organization_id integer NOT NULL REFERENCES billing_country_profiles(organization_id),
          request_id bigint NOT NULL UNIQUE,previous_country varchar(2),validated_country varchar(2) NOT NULL,
          legal_entity_reference varchar(180) NOT NULL,evidence_id varchar(32) NOT NULL,
          author_admin_id integer NOT NULL,justification text NOT NULL,decided_at timestamptz NOT NULL,
          effective_at timestamptz NOT NULL,profile_revision bigint NOT NULL,
          FOREIGN KEY(organization_id,request_id) REFERENCES billing_country_requests(organization_id,id),
          FOREIGN KEY(organization_id,evidence_id) REFERENCES billing_country_evidence(organization_id,id),
          UNIQUE(organization_id,profile_revision))""",
        "CREATE INDEX ix_country_effective ON billing_country_decisions(organization_id,effective_at,id)",
        """CREATE TABLE enrollment_documents(
          id bigserial PRIMARY KEY,purpose varchar(40) NOT NULL,version varchar(80) NOT NULL,
          response_kind varchar(30) NOT NULL CHECK(response_kind IN ('acceptance','information','optional_consent')),
          contents jsonb NOT NULL,sha256 varchar(64) NOT NULL,
          required boolean NOT NULL,synthetic boolean NOT NULL CHECK(synthetic),
          published_at timestamptz NOT NULL,retired_at timestamptz,
          UNIQUE(purpose,version),CHECK(NOT(required AND response_kind='optional_consent')),
          CHECK(contents ?& ARRAY['fr','en','ar']))""",
        """CREATE UNIQUE INDEX uq_enrollment_current_document ON enrollment_documents(purpose)
          WHERE retired_at IS NULL""",
        """CREATE TABLE enrollment_dossiers(
          id bigserial PRIMARY KEY,identity_id integer NOT NULL UNIQUE REFERENCES identities(id),
          organization_id integer NOT NULL UNIQUE REFERENCES organizations(id),
          registration_request_id integer NOT NULL UNIQUE REFERENCES registration_requests(id),
          legal_entity_reference varchar(180) NOT NULL,branch_name varchar(180) NOT NULL,
          status varchar(30) NOT NULL CHECK(status IN ('draft','country_pending','ready','completed')),
          revision bigint NOT NULL DEFAULT 1,created_at timestamptz NOT NULL DEFAULT now(),
          completed_at timestamptz,restaurant_id integer REFERENCES restaurants(id),
          UNIQUE(organization_id,identity_id))""",
        """CREATE TABLE enrollment_document_events(
          id bigserial PRIMARY KEY,dossier_id bigint NOT NULL REFERENCES enrollment_dossiers(id),
          identity_id integer NOT NULL REFERENCES identities(id),document_id bigint NOT NULL REFERENCES enrollment_documents(id),
          locale varchar(2) NOT NULL CHECK(locale IN ('fr','en','ar')),document_sha256 varchar(64) NOT NULL,
          event varchar(16) NOT NULL CHECK(event IN ('presented','accepted','acknowledged','declined')),
          occurred_at timestamptz NOT NULL DEFAULT now(),UNIQUE(dossier_id,document_id,event,locale))""",
        """CREATE FUNCTION guard_enrollment_document_version() RETURNS trigger LANGUAGE plpgsql AS $body$
        BEGIN
          IF TG_OP <> 'UPDATE' THEN RAISE EXCEPTION 'enrollment_document_version_immutable' USING ERRCODE='23514'; END IF;
          IF (to_jsonb(NEW)-'retired_at') IS DISTINCT FROM (to_jsonb(OLD)-'retired_at')
            OR OLD.retired_at IS NOT NULL OR NEW.retired_at IS NULL OR NEW.retired_at < OLD.published_at
          THEN RAISE EXCEPTION 'enrollment_document_version_immutable' USING ERRCODE='23514'; END IF;
          RETURN NEW;
        END $body$""",
        """CREATE TRIGGER retain_enrollment_document_version BEFORE UPDATE OR DELETE ON enrollment_documents
          FOR EACH ROW EXECUTE FUNCTION guard_enrollment_document_version()""",
        """CREATE TRIGGER retain_enrollment_document_truncate BEFORE TRUNCATE ON enrollment_documents
          FOR EACH STATEMENT EXECUTE FUNCTION guard_enrollment_document_version()""",
        """ALTER TABLE subscriptions ADD COLUMN billing_country_code varchar(2),
          ADD COLUMN billing_country_decision_id bigint REFERENCES billing_country_decisions(id) ON DELETE RESTRICT""",
        """CREATE FUNCTION guard_billing_retained_country() RETURNS trigger LANGUAGE plpgsql AS $body$
        BEGIN IF (NEW.billing_country_code,NEW.billing_country_decision_id) IS DISTINCT FROM
          (OLD.billing_country_code,OLD.billing_country_decision_id)
          AND EXISTS(SELECT 1 FROM subscription_pricing_snapshots WHERE subscription_id=OLD.id)
        THEN RAISE EXCEPTION 'retained_country_context_immutable' USING ERRCODE='23514'; END IF;
        RETURN NEW; END $body$""",
        """CREATE TRIGGER guard_billing_retained_country BEFORE UPDATE ON subscriptions
          FOR EACH ROW EXECUTE FUNCTION guard_billing_retained_country()""",
        """CREATE FUNCTION guard_billing_evidence_history() RETURNS trigger LANGUAGE plpgsql AS $body$
        BEGIN RAISE EXCEPTION 'billing_evidence_history_immutable' USING ERRCODE='23514'; END $body$""",
    )
    for statement in statements:
        connection.exec_driver_sql(statement)
    for table in (
        "billing_country_evidence",
        "billing_country_decisions",
        "enrollment_document_events",
    ):
        connection.exec_driver_sql(
            f"CREATE TRIGGER retain_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION guard_billing_evidence_history()"
        )
        connection.exec_driver_sql(
            f"CREATE TRIGGER retain_{table}_truncate BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION guard_billing_evidence_history()"
        )


# ==============================================
# NONDESTRUCTIVE RECOVERY REQUIREMENT
# Country decisions and consent evidence cannot be discarded by an automatic downgrade.
# ==============================================


def downgrade() -> None:
    """Require independently verified restoration instead of erasing retained evidence."""
    raise RuntimeError("billing_country_history_preservation_required")
