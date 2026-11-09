# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# O3 COUNTRY AND CURRENCY BASE PRICE STORAGE
# Replace the old scalar price with retained, nonoverlapping country/currency versions.
# ==============================================

"""Prepared migration operations only; no configuration discovery or connection.

The existing singleton retains shared policies. Its price is transferred, never
copied into a second writable source. Unknown legacy currency bases block adoption.
"""

from sqlalchemy.engine import Connection

# ==============================================
# TRANSACTIONAL SOURCE REPLACEMENT
# Refuse unclassified legacy prices and retain snapshots without rewriting their JSON.
# ==============================================


def upgrade(*, connection: Connection) -> None:
    """Transfer the observed DZD scalar to DZ and remove competing live price stores.

    The Alembic caller owns the transaction. The migration imports the value it
    finds, not a hard-coded new tariff, and records the time of adoption only.
    """
    statements = (
        "LOCK TABLE subscription_pricing_config IN ACCESS EXCLUSIVE MODE",
        """DO $body$ BEGIN
          IF (SELECT count(*) FROM subscription_pricing_config WHERE id=1)<>1
            THEN RAISE EXCEPTION 'base_singleton_missing'; END IF;
          IF EXISTS(SELECT 1 FROM subscription_pricing_config
            WHERE coalesce(policies::jsonb->'currency_bases','{}'::jsonb)<>'{}'::jsonb)
            THEN RAISE EXCEPTION 'legacy_currency_country_mapping_required'; END IF;
        END $body$""",
        "CREATE EXTENSION IF NOT EXISTS btree_gist",
        """CREATE TABLE subscription_base_prices (
          id BIGSERIAL PRIMARY KEY,
          country_code varchar(2) NOT NULL CHECK(country_code ~ '^[A-Z]{2}$'),
          currency varchar(3) NOT NULL CHECK(currency ~ '^[A-Z]{3}$'),
          amount numeric(24,8) NOT NULL CHECK(amount>=0 AND amount::text NOT IN ('NaN','Infinity','-Infinity')),
          revision varchar(128) NOT NULL UNIQUE,
          effective_from timestamptz NOT NULL,
          effective_until timestamptz,
          recorded_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
          author_admin_id integer,
          source_reference text NOT NULL CHECK(length(btrim(source_reference))>0),
          CHECK(effective_until IS NULL OR effective_until>effective_from),
          EXCLUDE USING gist(country_code WITH =,currency WITH =,
            tstzrange(effective_from,effective_until,'[)') WITH &&)
        )""",
        """INSERT INTO subscription_base_prices(country_code,currency,amount,revision,effective_from,source_reference)
          SELECT 'DZ','DZD',base_price,
            coalesce(policies->>'base_revision','legacy:subscription_pricing_config:1'),
            transaction_timestamp(),'migration:subscription_pricing_config:1; observed value, no retroactive tariff assertion'
          FROM subscription_pricing_config WHERE id=1""",
        """CREATE FUNCTION guard_subscription_base_version() RETURNS trigger LANGUAGE plpgsql AS $body$
        BEGIN
          IF TG_OP='UPDATE' AND OLD.effective_until IS NULL AND NEW.effective_until IS NOT NULL
            AND NEW.effective_until>OLD.effective_from
            AND (to_jsonb(NEW)-'effective_until')=(to_jsonb(OLD)-'effective_until')
          THEN RETURN NEW; END IF;
          RAISE EXCEPTION 'subscription_base_version_immutable' USING ERRCODE='23514';
        END $body$""",
        """CREATE TRIGGER guard_subscription_base_version BEFORE UPDATE OR DELETE
          ON subscription_base_prices FOR EACH ROW EXECUTE FUNCTION guard_subscription_base_version()""",
        """CREATE TRIGGER guard_subscription_base_truncate BEFORE TRUNCATE
          ON subscription_base_prices FOR EACH STATEMENT EXECUTE FUNCTION guard_subscription_base_version()""",
        "ALTER TABLE subscription_pricing_config DROP COLUMN base_price",
        """UPDATE subscription_pricing_config
          SET policies=((policies::jsonb-'currency_bases')-'base_revision')::json""",
        """CREATE FUNCTION refuse_legacy_base_policy() RETURNS trigger LANGUAGE plpgsql AS $body$
        BEGIN
          IF NEW.policies::jsonb ?| ARRAY['currency_bases','base_revision']
          THEN RAISE EXCEPTION 'legacy_base_policy_store_refused' USING ERRCODE='23514'; END IF;
          RETURN NEW;
        END $body$""",
        """CREATE TRIGGER refuse_legacy_base_policy BEFORE INSERT OR UPDATE
          ON subscription_pricing_config FOR EACH ROW EXECUTE FUNCTION refuse_legacy_base_policy()""",
    )
    for statement in statements:
        connection.exec_driver_sql(statement)


# ==============================================
# RETAINED HISTORY RECOVERY BOUNDARY
# A singleton cannot represent several countries or retained versions without loss.
# ==============================================


def downgrade() -> None:
    """Reject a destructive collapse; recovery requires an explicitly reviewed backup plan."""
    raise RuntimeError("country_base_history_preservation_required")
