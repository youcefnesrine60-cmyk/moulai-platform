-- Generated from executed main Alembic history; apply with ON_ERROR_STOP and a single transaction.
-- Never stamp, auto-retry or apply to the historical project.
DO $attest$ BEGIN
IF current_database() IS DISTINCT FROM 'moulai_staging_rehearsal'
OR current_user IS DISTINCT FROM 'moulai_staging_migrator'
OR current_setting('neon.project_id',true) IS DISTINCT FROM 'sparkling-rice-23028300'
OR current_setting('neon.branch_id',true) IS DISTINCT FROM 'br-lucky-smoke-b9edyxoe'
OR current_setting('neon.endpoint_id',true) IS DISTINCT FROM 'ep-odd-wildflower-b9wacgg0'
THEN RAISE EXCEPTION 'staging_migration_target_refused'; END IF;
END $attest$;
SET LOCAL statement_timeout='120s';
SET LOCAL lock_timeout='5s';
DO $state$ BEGIN IF (SELECT version_num FROM public.alembic_version) IS DISTINCT FROM 'o420261108' THEN RAISE EXCEPTION 'staging_o4_required'; END IF; END $state$;
DO $marker$ BEGIN IF (SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()) IS DISTINCT FROM 'moulai-staging:bf4de394885f4d208b018f5056366f59' THEN RAISE EXCEPTION 'staging_marker_mismatch'; END IF; END $marker$;

CREATE TABLE subscription_documents(
          id bigserial PRIMARY KEY,public_id varchar(43) NOT NULL UNIQUE CHECK(public_id ~ '^[A-Za-z0-9_-]{43}$'),
          organization_id integer NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
          restaurant_id integer NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
          payment_id integer NOT NULL REFERENCES payments(id) ON DELETE RESTRICT,
          subscription_id integer NOT NULL REFERENCES subscriptions(id) ON DELETE RESTRICT,
          snapshot_id integer NOT NULL REFERENCES subscription_pricing_snapshots(id) ON DELETE RESTRICT,
          version integer NOT NULL CHECK(version>0),replaces_id bigint UNIQUE REFERENCES subscription_documents(id) ON DELETE RESTRICT,
          content jsonb NOT NULL CHECK(jsonb_typeof(content)='object'),sha256 varchar(64) NOT NULL CHECK(sha256 ~ '^[a-f0-9]{64}$'),
          author_admin_id integer NOT NULL,author_name varchar(255) NOT NULL,
          issued_at timestamptz NOT NULL DEFAULT now(),UNIQUE(payment_id,version));

CREATE INDEX ix_subscription_documents_scope ON subscription_documents(organization_id,restaurant_id,id);

CREATE TABLE subscription_document_events(
          id bigserial PRIMARY KEY,document_id bigint NOT NULL REFERENCES subscription_documents(id) ON DELETE RESTRICT,
          event varchar(16) NOT NULL CHECK(event IN ('issued','invalidated')),
          author_admin_id integer NOT NULL,author_name varchar(255) NOT NULL,
          reason text NOT NULL CHECK(length(btrim(reason))>=3),occurred_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE(document_id,event));

CREATE FUNCTION guard_subscription_document_history() RETURNS trigger LANGUAGE plpgsql AS $body$
        BEGIN RAISE EXCEPTION 'subscription_document_history_immutable' USING ERRCODE='23514'; END $body$;

CREATE TRIGGER retain_subscription_documents BEFORE UPDATE OR DELETE ON subscription_documents FOR EACH ROW EXECUTE FUNCTION guard_subscription_document_history();

CREATE TRIGGER retain_subscription_documents_truncate BEFORE TRUNCATE ON subscription_documents FOR EACH STATEMENT EXECUTE FUNCTION guard_subscription_document_history();

CREATE TRIGGER retain_subscription_document_events BEFORE UPDATE OR DELETE ON subscription_document_events FOR EACH ROW EXECUTE FUNCTION guard_subscription_document_history();

CREATE TRIGGER retain_subscription_document_events_truncate BEFORE TRUNCATE ON subscription_document_events FOR EACH STATEMENT EXECUTE FUNCTION guard_subscription_document_history();

UPDATE alembic_version SET version_num='o520261111' WHERE alembic_version.version_num = 'o420261108';
