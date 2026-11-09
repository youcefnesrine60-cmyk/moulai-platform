# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# O2 EXACT FINAL FOOD INVOICE SETTLEMENT
# Record a verified remaining balance once, without changing sales or reusing an advance.
# ==============================================

"""Add a scoped immutable receipt ledger; no money transfer, price seed or permission grant."""

# ==============================================
# CHECKED MIGRATION CONNECTION
# Alembic supplies the already attested transaction; no URL is read here.
# ==============================================

from alembic import op

revision = "o220261108"
down_revision = "o120261108"
branch_labels = None
depends_on = None

# ==============================================
# EXACT SCOPED LEDGER AND DATABASE GUARANTEES
# Serialize with advances on the same invoice and refuse edits, deletion or duplicate receipt references.
# ==============================================


def upgrade() -> None:
    """Add retained full-balance receipts while leaving historical Float order payments unchanged."""
    statements = (
        """CREATE TABLE dining_settlements(
          id SERIAL PRIMARY KEY, restaurant_id integer NOT NULL, branch_id integer NOT NULL,
          invoice_id integer NOT NULL UNIQUE, invoice_revision bigint NOT NULL,
          invoice_total numeric(24,8) NOT NULL, advance_amount numeric(24,8) NOT NULL,
          amount numeric(24,8) NOT NULL CHECK(amount>0 AND amount<>'NaN'::numeric),
          currency varchar(3) NOT NULL, mode varchar(40) NOT NULL,
          reference varchar(160) NOT NULL, received_at timestamptz NOT NULL,
          author_membership_id integer NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE(restaurant_id,branch_id,reference),
          FOREIGN KEY(restaurant_id,branch_id,invoice_id)
            REFERENCES dining_invoices(restaurant_id,branch_id,id) ON DELETE RESTRICT,
          CHECK(invoice_total=advance_amount+amount AND advance_amount>=0)
        )""",
        """CREATE FUNCTION check_food_settlement() RETURNS trigger LANGUAGE plpgsql
          SET search_path=pg_catalog,public AS $body$
        DECLARE bill public.dining_invoices%ROWTYPE; advances numeric;
        BEGIN
          SELECT * INTO bill FROM public.dining_invoices WHERE id=NEW.invoice_id FOR UPDATE;
          SELECT coalesce(sum(amount),0) INTO advances FROM public.dining_allocations WHERE invoice_id=NEW.invoice_id;
          IF bill.id IS NULL OR bill.status<>'finalized' OR bill.currency<>NEW.currency
            OR bill.revision<>NEW.invoice_revision OR bill.total<>NEW.invoice_total
            OR advances<>NEW.advance_amount OR NEW.amount<>bill.total-advances
          THEN RAISE EXCEPTION 'food_settlement_mismatch' USING ERRCODE='23514'; END IF;
          RETURN NEW;
        END $body$""",
        """CREATE TRIGGER check_food_settlement BEFORE INSERT ON dining_settlements
          FOR EACH ROW EXECUTE FUNCTION check_food_settlement()""",
        """CREATE FUNCTION protect_food_settlement() RETURNS trigger LANGUAGE plpgsql AS $body$
        BEGIN RAISE EXCEPTION 'food_settlement_immutable' USING ERRCODE='23514'; END $body$""",
        """CREATE TRIGGER protect_food_settlement BEFORE UPDATE OR DELETE ON dining_settlements
          FOR EACH ROW EXECUTE FUNCTION protect_food_settlement()""",
        """CREATE TRIGGER protect_food_settlement_truncate BEFORE TRUNCATE ON dining_settlements
          FOR EACH STATEMENT EXECUTE FUNCTION protect_food_settlement()""",
        """CREATE FUNCTION refuse_advance_after_settlement() RETURNS trigger LANGUAGE plpgsql
          SET search_path=pg_catalog,public AS $body$
        BEGIN
          PERFORM id FROM public.dining_invoices WHERE id=NEW.invoice_id FOR UPDATE;
          IF EXISTS(SELECT 1 FROM public.dining_settlements WHERE invoice_id=NEW.invoice_id)
          THEN RAISE EXCEPTION 'food_invoice_already_settled' USING ERRCODE='23514'; END IF;
          RETURN NEW;
        END $body$""",
        """CREATE TRIGGER refuse_advance_after_settlement BEFORE INSERT ON dining_allocations
          FOR EACH ROW EXECUTE FUNCTION refuse_advance_after_settlement()""",
    )
    for statement in statements:
        op.execute(statement)


# ==============================================
# RETAIN RECORDED FINANCIAL FACTS
# An automatic downgrade must never erase receipts or enable duplicate allocation.
# ==============================================


def downgrade() -> None:
    """Require a separately reviewed reconciliation before removing settlement guarantees."""
    raise RuntimeError("food_settlement_downgrade_requires_review")
