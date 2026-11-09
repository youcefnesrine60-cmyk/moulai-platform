# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SHARED S1 MIGRATION OPERATIONS
# Define S1 schema changes and refuse downgrade without a history-preservation plan.
# ==============================================

"""Frozen S1 DDL, shared by permanent and disposable migration histories.

No application models, settings, environment or connections are imported here.
"""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from sqlalchemy.engine import Connection

# ==============================================
# CONFIGURATION AND CONSTANTS
# Group the existing configuration values without changing their defaults.
# ==============================================

DDL = (
    "ALTER TABLE subscriptions ADD COLUMN calendar_anchor TIMESTAMP, ADD COLUMN cancelled_at TIMESTAMP, ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'DZD', ADD COLUMN market VARCHAR(10)",
    "ALTER TABLE subscriptions ALTER COLUMN amount TYPE NUMERIC(24,8) USING amount::numeric",
    "ALTER TABLE payments ALTER COLUMN amount TYPE NUMERIC(24,8) USING amount::numeric",
    "ALTER TABLE feature_pricing ALTER COLUMN price TYPE NUMERIC(24,8) USING price::numeric, ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'DZD'",
    "ALTER TABLE branch_pricing ALTER COLUMN price_per_branch TYPE NUMERIC(24,8) USING price_per_branch::numeric, ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'DZD', ADD COLUMN market VARCHAR(10), ADD COLUMN grid_code VARCHAR(80) NOT NULL DEFAULT 'legacy-review-required', ADD COLUMN starts_at TIMESTAMP, ADD COLUMN expires_at TIMESTAMP",
    "UPDATE branch_pricing SET active=false",
    "INSERT INTO branch_pricing(min_branches,max_branches,price_per_branch,active,currency,grid_code) VALUES(2,5,500,true,'DZD','approved-dzd-20261029'),(6,20,400,true,'DZD','approved-dzd-20261029'),(21,NULL,300,true,'DZD','approved-dzd-20261029')",
    "ALTER TABLE loyalty_discounts ALTER COLUMN discount_percent TYPE NUMERIC(12,8) USING discount_percent::numeric",
    "ALTER TABLE multi_restaurant_discounts ALTER COLUMN discount_percent TYPE NUMERIC(12,8) USING discount_percent::numeric",
    "ALTER TABLE promotions ALTER COLUMN discount_percent TYPE NUMERIC(12,8) USING discount_percent::numeric, ADD COLUMN owner_id INTEGER REFERENCES owners(id), ADD COLUMN plan_id INTEGER REFERENCES subscription_plans(id), ADD COLUMN priority INTEGER NOT NULL DEFAULT 0",
    "CREATE TABLE subscription_reminders(id SERIAL PRIMARY KEY, subscription_id INTEGER NOT NULL REFERENCES subscriptions(id), expires_at TIMESTAMP NOT NULL, offset_days INTEGER NOT NULL CHECK(offset_days>=0), recipient VARCHAR(30) NOT NULL, target_chat_id VARCHAR(40), due_at TIMESTAMP NOT NULL, status VARCHAR(20) NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, sent_at TIMESTAMP, attempt_log JSON NOT NULL DEFAULT '[]', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, CONSTRAINT uq_subscription_reminder UNIQUE(subscription_id,expires_at,offset_days,recipient))",
    "ALTER TABLE subscription_features ADD CONSTRAINT uq_subscription_feature UNIQUE(subscription_id,feature_id)",
    "ALTER TABLE subscription_feature_requests ADD CONSTRAINT uq_subscription_feature_request UNIQUE(subscription_id,feature_id)",
    """CREATE TABLE subscription_pricing_config (
      id INTEGER PRIMARY KEY CHECK (id=1), base_price NUMERIC(14,2) NOT NULL CHECK(base_price>=0),
      policies JSON NOT NULL DEFAULT '{}', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """INSERT INTO subscription_pricing_config(id,base_price,policies) VALUES(1,3000,'{"currencies":{"DZD":{"decimals":2}},"reminder_days":[14,7,1,0]}')""",
    """CREATE TABLE subscription_pricing_snapshots (
      id SERIAL PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES owners(id),
      restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
      subscription_id INTEGER UNIQUE REFERENCES subscriptions(id),
      source_subscription_id INTEGER NOT NULL REFERENCES subscriptions(id),
      reference_start TIMESTAMP NOT NULL, reference_end TIMESTAMP NOT NULL,
      context VARCHAR(30) NOT NULL, products_count INTEGER NOT NULL CHECK(products_count>=0),
      categories_count INTEGER NOT NULL CHECK(categories_count>=0),
      monthly_orders INTEGER NOT NULL CHECK(monthly_orders>=0),
      average_order_value NUMERIC(20,8) NOT NULL CHECK(average_order_value>=0 AND average_order_value::text NOT IN ('NaN','Infinity','-Infinity')),
      calculated_at TIMESTAMP NOT NULL, pricing JSON NOT NULL, parameters JSON NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT ck_snapshot_period CHECK(reference_end-reference_start=INTERVAL '30 days'),
      CONSTRAINT ck_snapshot_context CHECK(context IN ('active_month','trial_end','renewal','return')))""",
    "CREATE UNIQUE INDEX uq_subscription_metric_period ON subscription_pricing_snapshots(source_subscription_id,reference_end) WHERE context='active_month' AND subscription_id IS NULL",
    """CREATE FUNCTION moulai_snapshot_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'subscription_snapshot_immutable'; END IF;
      IF NOT EXISTS(SELECT 1 FROM restaurants WHERE id=NEW.restaurant_id AND owner_id=NEW.owner_id)
        THEN RAISE EXCEPTION 'snapshot_owner_mismatch'; END IF;
      IF NEW.subscription_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM subscriptions
        WHERE id=NEW.subscription_id AND owner_id=NEW.owner_id AND restaurant_id=NEW.restaurant_id)
        THEN RAISE EXCEPTION 'snapshot_subscription_mismatch'; END IF;
      IF NEW.source_subscription_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM subscriptions
        WHERE id=NEW.source_subscription_id AND owner_id=NEW.owner_id AND restaurant_id=NEW.restaurant_id)
        THEN RAISE EXCEPTION 'snapshot_source_mismatch'; END IF;
      RETURN NEW;
    END $$""",
    "CREATE TRIGGER subscription_snapshot_guard BEFORE INSERT OR UPDATE OR DELETE ON subscription_pricing_snapshots FOR EACH ROW EXECUTE FUNCTION moulai_snapshot_guard()",
    """CREATE FUNCTION moulai_retained_price_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS(SELECT 1 FROM subscription_pricing_snapshots WHERE subscription_id=OLD.id) THEN
        IF (NEW.amount,NEW.currency,NEW.plan_id,NEW.billing_cycle,NEW.owner_id,NEW.restaurant_id)
           IS DISTINCT FROM (OLD.amount,OLD.currency,OLD.plan_id,OLD.billing_cycle,OLD.owner_id,OLD.restaurant_id)
          THEN RAISE EXCEPTION 'retained_subscription_price_immutable'; END IF;
        IF OLD.starts_at IS NOT NULL AND (NEW.starts_at,NEW.expires_at,NEW.calendar_anchor)
           IS DISTINCT FROM (OLD.starts_at,OLD.expires_at,OLD.calendar_anchor)
          THEN RAISE EXCEPTION 'purchased_subscription_period_immutable'; END IF;
      END IF;
      RETURN NEW;
    END $$""",
    "CREATE TRIGGER retained_subscription_price BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION moulai_retained_price_guard()",
)

DDL += (
    """CREATE TABLE cash_collections (
      id SERIAL PRIMARY KEY, payment_id INTEGER NOT NULL UNIQUE REFERENCES payments(id),
      subscription_id INTEGER NOT NULL REFERENCES subscriptions(id), admin_id INTEGER NOT NULL REFERENCES admins(id),
      expected_amount NUMERIC(24,8) NOT NULL CHECK(expected_amount>0),
      received_amount NUMERIC(24,8) NOT NULL CHECK(received_amount=expected_amount),
      currency VARCHAR(3) NOT NULL, collected_at TIMESTAMP NOT NULL, confirmed_at TIMESTAMP NOT NULL,
      receipt_reference VARCHAR(120) NOT NULL UNIQUE,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE cash_collection_attempts (
      id SERIAL PRIMARY KEY, attempt_id VARCHAR(32) NOT NULL, payment_id INTEGER NOT NULL,
      attempted_admin_id INTEGER NOT NULL, result VARCHAR(40) NOT NULL, details JSON NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    "CREATE INDEX ix_cash_collection_attempts_attempt_id ON cash_collection_attempts(attempt_id)",
    "INSERT INTO permissions(code,name) VALUES('payments.cash.collect','Confirm physical cash collection') ON CONFLICT(code) DO NOTHING",
    """CREATE FUNCTION moulai_cash_evidence_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'cash_evidence_immutable'; END IF;
      IF TG_TABLE_NAME='cash_collections' THEN
        IF NOT EXISTS(SELECT 1 FROM payments p JOIN subscriptions s ON s.id=p.subscription_id
          WHERE p.id=NEW.payment_id AND p.subscription_id=NEW.subscription_id
            AND p.payment_method='cash' AND p.payment_provider='manual_cash' AND p.status='pending'
            AND p.amount=NEW.expected_amount AND p.currency=NEW.currency
            AND s.amount=p.amount AND s.currency=p.currency AND s.owner_id=p.owner_id AND s.restaurant_id=p.restaurant_id)
          THEN RAISE EXCEPTION 'cash_payment_terms_mismatch'; END IF;
        IF NEW.collected_at>NEW.confirmed_at THEN RAISE EXCEPTION 'cash_date_invalid'; END IF;
      END IF;
      RETURN NEW;
    END $$""",
    "CREATE TRIGGER cash_evidence_guard BEFORE INSERT OR UPDATE OR DELETE ON cash_collections FOR EACH ROW EXECUTE FUNCTION moulai_cash_evidence_guard()",
    "CREATE TRIGGER cash_attempt_guard BEFORE INSERT OR UPDATE OR DELETE ON cash_collection_attempts FOR EACH ROW EXECUTE FUNCTION moulai_cash_evidence_guard()",
    """CREATE FUNCTION moulai_cash_payment_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS(SELECT 1 FROM cash_collections WHERE payment_id=OLD.id) AND
        (NEW.amount,NEW.currency,NEW.subscription_id,NEW.owner_id,NEW.restaurant_id,NEW.payment_method,NEW.payment_provider)
        IS DISTINCT FROM (OLD.amount,OLD.currency,OLD.subscription_id,OLD.owner_id,OLD.restaurant_id,OLD.payment_method,OLD.payment_provider)
        THEN RAISE EXCEPTION 'cash_payment_terms_immutable'; END IF;
      RETURN NEW;
    END $$""",
    "CREATE TRIGGER cash_payment_guard BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION moulai_cash_payment_guard()",
)


# ==============================================
# UPGRADE
# Apply the prepared S1 operations using the connection explicitly supplied by the
# caller.
# ==============================================


def upgrade(connection: Connection) -> None:
    # Existing payable amounts must survive conversion exactly at their DZD precision.
    """Apply the prepared S1 operations using the connection explicitly supplied by the caller."""

    for table in ("subscriptions", "payments"):
        bad = connection.exec_driver_sql(
            f"SELECT count(*) FROM {table} WHERE amount IS NULL OR amount<0 OR amount::text IN ('NaN','Infinity','-Infinity') OR amount::numeric<>round(amount::numeric,2)"
        ).scalar_one()
        if bad:
            raise RuntimeError("legacy_amounts_require_review")
    if connection.exec_driver_sql(
        "SELECT count(*) FROM payments WHERE currency<>'DZD'"
    ).scalar_one():
        raise RuntimeError("legacy_currencies_require_review")
    # Unexpected legacy global tariffs require review, never automatic deletion.
    loyalty = {1: 2, 2: 5, 3: 8, 4: 11, 5: 15, 10: 20, 15: 25}
    multi = {1: 0, 3: 5, 10: 15}
    for table, key, expected, where in [
        ("loyalty_discounts", "years_required", loyalty, " WHERE owner_id IS NULL"),
        ("multi_restaurant_discounts", "min_restaurants", multi, ""),
    ]:
        rows = connection.exec_driver_sql(
            f"SELECT {key},discount_percent FROM {table}{where}"
        ).all()
        if len({row[0] for row in rows}) != len(rows) or any(
            key not in expected or value != expected[key] for key, value in rows
        ):
            raise RuntimeError("legacy_global_pricing_rules_require_review")
    for statement in DDL:
        connection.exec_driver_sql(statement)
    for key, rate in loyalty.items():
        connection.exec_driver_sql(
            f"INSERT INTO loyalty_discounts(years_required,discount_percent) SELECT {key},{rate} WHERE NOT EXISTS(SELECT 1 FROM loyalty_discounts WHERE years_required={key} AND owner_id IS NULL)"
        )
    for key, rate in multi.items():
        connection.exec_driver_sql(
            f"INSERT INTO multi_restaurant_discounts(min_restaurants,discount_percent) SELECT {key},{rate} WHERE NOT EXISTS(SELECT 1 FROM multi_restaurant_discounts WHERE min_restaurants={key})"
        )


# ==============================================
# DOWNGRADE
# Refuse destructive downgrade until an explicit history-preservation plan is approved.
# ==============================================


def downgrade(connection: Connection) -> None:
    # Intentionally refuse data loss: rollback requires an explicit preservation plan.
    """Refuse destructive downgrade until an explicit history-preservation plan is approved."""

    raise RuntimeError("subscription_history_downgrade_requires_preservation_plan")
