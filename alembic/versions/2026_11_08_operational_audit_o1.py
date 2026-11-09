# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# O1 RETAINED ADMINISTRATIVE DECISIONS
# Preserve committed audit records and their original actor after administrator deletion.
# ==============================================

"""Additive audit retention; existing migration files and business prices stay unchanged."""

# isort: split
# ==============================================
# MIGRATION DEPENDENCIES
# Execute only on the connection explicitly supplied to the migration runner.
# ==============================================

from alembic import op

revision = "o120261108"
down_revision = "d1d20261105"
branch_labels = None
depends_on = None

# ==============================================
# ADD ACTOR EVIDENCE AND RETENTION GUARDS
# Backfill the currently available actor identity without claiming unavailable historical names.
# ==============================================


def upgrade() -> None:
    """Retain old rows, replace cascade with SET NULL and freeze committed audit contents."""
    statements = (
        """
ALTER TABLE public.admin_logs
          ADD COLUMN actor_admin_id integer,
          ADD COLUMN actor_name varchar(255),
          ADD COLUMN actor_subject varchar(255);
        """,
        """
UPDATE public.admin_logs AS l SET
          actor_admin_id=l.admin_id, actor_name=a.full_name, actor_subject=a.auth_subject
        FROM public.admins AS a WHERE a.id=l.admin_id;
        """,
        """
ALTER TABLE public.admin_logs
          ALTER COLUMN actor_admin_id SET NOT NULL,
          ALTER COLUMN admin_id DROP NOT NULL;
        """,
        """
DO $migration$
        DECLARE fk record;
        BEGIN
          FOR fk IN SELECT c.conname FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=ANY(c.conkey)
            WHERE c.conrelid='public.admin_logs'::regclass AND c.contype='f'
              AND a.attname='admin_id'
          LOOP EXECUTE format('ALTER TABLE public.admin_logs DROP CONSTRAINT %I',fk.conname);
          END LOOP;
        END $migration$;
        """,
        """
ALTER TABLE public.admin_logs ADD CONSTRAINT fk_admin_log_retained_actor
          FOREIGN KEY(admin_id) REFERENCES public.admins(id) ON DELETE SET NULL;
        """,
        """
CREATE FUNCTION public.capture_admin_log_actor() RETURNS trigger
          LANGUAGE plpgsql SET search_path=pg_catalog,public AS $body$
        BEGIN
          IF NEW.admin_id IS NULL THEN RAISE EXCEPTION 'audit_author_required'; END IF;
          SELECT a.id,a.full_name,a.auth_subject
            INTO NEW.actor_admin_id,NEW.actor_name,NEW.actor_subject
            FROM public.admins a WHERE a.id=NEW.admin_id;
          IF NOT FOUND THEN RAISE EXCEPTION 'audit_author_unavailable'; END IF;
          RETURN NEW;
        END $body$;
        """,
        """
CREATE TRIGGER capture_admin_log_actor BEFORE INSERT ON public.admin_logs
          FOR EACH ROW EXECUTE FUNCTION public.capture_admin_log_actor();
        """,
        """
CREATE FUNCTION public.protect_admin_log_history() RETURNS trigger
          LANGUAGE plpgsql SET search_path=pg_catalog,public AS $body$
        BEGIN
          IF TG_OP='UPDATE' THEN
            IF OLD.admin_id IS NOT NULL AND NEW.admin_id IS NULL
              AND (to_jsonb(NEW)-'admin_id')=(to_jsonb(OLD)-'admin_id')
            THEN RETURN NEW; END IF;
          END IF;
          RAISE EXCEPTION 'audit_history_immutable' USING ERRCODE='23514';
        END $body$;
        """,
        """
CREATE TRIGGER protect_admin_log_history BEFORE UPDATE OR DELETE ON public.admin_logs
          FOR EACH ROW EXECUTE FUNCTION public.protect_admin_log_history();
        """,
        """
CREATE TRIGGER protect_admin_log_truncate BEFORE TRUNCATE ON public.admin_logs
          FOR EACH STATEMENT EXECUTE FUNCTION public.protect_admin_log_history();
        """,
    )
    for statement in statements:
        op.execute(statement)


# ==============================================
# NO AUTOMATIC LOSS OF RETAINED EVIDENCE
# Reintroducing a destructive cascade would require a separately reviewed data policy.
# ==============================================


def downgrade() -> None:
    """Refuse destructive restoration of cascade semantics and loss of actor snapshots."""
    raise RuntimeError("audit_retention_downgrade_requires_review")
