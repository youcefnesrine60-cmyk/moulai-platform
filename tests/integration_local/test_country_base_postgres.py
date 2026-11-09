# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# COUNTRY BASE POSTGRESQL REHEARSAL PROOFS
# Verify the real O3 chain, exact resolution, retained history and publication safety in a separate owned cluster.
# ==============================================

"""No shared destructive fixtures, permanent target, Keycloak call or commercial tariff seed."""

from __future__ import annotations

# isort: split
# ==============================================
# STRICT LOCAL TEST DEPENDENCIES
# Every connection is reattested against the dedicated test database and marker.
# ==============================================

import asyncio
import json
import os
from collections.abc import AsyncIterator
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import (
    insert,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security.oidc import OIDCPrincipal
from app.models.admin import Admin
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)
from app.services.business.pricing_service import (
    base_breakdown,
    calculate_subscription_pricing,
)
from app.services.business.subscription_country_base import (
    CountryBaseSelection,
    publish_country_base,
    resolve_country_base,
    validate_context,
)
from migration_support.country_base_o3 import upgrade as apply_country_base

# ==============================================
# DEDICATED HISTORICAL SCHEMA
# Shared collection keeps pure tests offline; factory-dependent cases require the runner's independently attested disposable target.
# ==============================================

pytestmark = pytest.mark.country_rehearsal

# ==============================================
# ATTESTED SESSION FACTORY
# An environment variable alone cannot admit an existing review or remote database.
# ==============================================


@pytest.fixture(scope="module")
async def factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Require the new marked cluster and actual Alembic O3 revision before any test write."""
    url = make_url(os.environ["COUNTRY_BASE_TEST_URL"])
    assert (url.host, url.port, url.database, url.username) == (
        "127.0.0.1",
        55434,
        "moulai_base_rehearsal",
        "moulai_base_rehearsal",
    )
    engine = create_async_engine(url, hide_parameters=True, connect_args={"ssl": False})
    async with engine.connect() as connection:
        assert (
            await connection.scalar(
                text(
                    "SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"
                )
            )
            == "moulai-country-base:" + os.environ["COUNTRY_BASE_TEST_MARKER"]
        )
        assert await connection.scalar(
            text("SELECT version_num FROM alembic_version")
        ) in {"o320261108", "o420261108"}
    try:
        yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    finally:
        await engine.dispose()


# ==============================================
# SOURCE TRANSFER AND COUNTRY ADOPTION
# DZD is imported only for approved Algeria; no other price is invented.
# ==============================================


@pytest.mark.asyncio
async def test_forward_migration_has_one_authoritative_price(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Inspect the final catalogue and retain the actual imported value and legacy revision."""
    async with factory() as session:
        row = await resolve_country_base(
            session=session,
            country_code="DZ",
            currency="DZD",
            at=datetime.now(timezone.utc),
        )
        assert (
            row.amount == 3000
            and row.revision == "legacy:subscription_pricing_config:1"
        )
        assert (
            await session.scalar(text("SELECT count(*) FROM subscription_base_prices"))
            == 1
        )
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='subscription_pricing_config' AND column_name='base_price'"
                )
            )
            == 0
        )
        policy = await session.scalar(
            text("SELECT policies FROM subscription_pricing_config WHERE id=1")
        )
        assert "currency_bases" not in policy and "base_revision" not in policy
        assert row.policies["reminder_days"] == [14, 7, 1, 0]


# ==============================================
# MISSING CONTEXT HAS NO TARIFF FALLBACK
# A common currency never authorizes reuse of another country's price.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "country,currency", [("FR", "EUR"), ("FR", "DZD"), ("DZ", "USD")]
)
async def test_unconfigured_country_currency_refused(
    factory: async_sessionmaker[AsyncSession], country: str, currency: str
) -> None:
    """Require an exact configured pair instead of conversion or a silent DZ default."""
    async with factory() as session:
        with pytest.raises(ValueError, match="country_base_missing"):
            await resolve_country_base(
                session=session,
                country_code=country,
                currency=currency,
                at=datetime.now(timezone.utc),
            )


# ==============================================
# HISTORICAL DATES ARE NOT INVENTED
# The adoption timestamp does not assert a tariff history that was never recorded.
# ==============================================


@pytest.mark.asyncio
async def test_before_adoption_is_not_backfilled(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Older retained JSON remains readable, while a new date lookup before adoption is refused."""
    async with factory() as session:
        start = await session.scalar(
            text("SELECT min(effective_from) FROM subscription_base_prices")
        )
        with pytest.raises(ValueError, match="country_base_missing"):
            await resolve_country_base(
                session=session,
                country_code="DZ",
                currency="DZD",
                at=start - timedelta(microseconds=1),
            )


# ==============================================
# COUNTRY INPUT VALIDATION
# Codes and time must be explicit before any database query can run.
# ==============================================


@pytest.mark.parametrize(
    "country,currency,at",
    [
        ("dz", "DZD", datetime.now(timezone.utc)),
        ("DZ", "dzd", datetime.now(timezone.utc)),
        (
            "DZ",
            "DZD",
            datetime(2026, 1, 1, tzinfo=timezone.utc).replace(tzinfo=None),
        ),
    ],
)
def test_ambiguous_input_refused(country: str, currency: str, at: datetime) -> None:
    """Reject implicit normalization and naive timezone interpretation."""
    with pytest.raises(ValueError, match="country_base_context_required"):
        validate_context(country_code=country, currency=currency, at=at)


# ==============================================
# DATABASE INTEGRITY IS INDEPENDENT OF THE SERVICE
# Direct SQL cannot rewrite amounts, delete history or restore a second live base store.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE subscription_base_prices SET amount=1 WHERE id=1",
        "DELETE FROM subscription_base_prices WHERE id=1",
        "TRUNCATE subscription_base_prices",
        "UPDATE subscription_pricing_config SET policies=jsonb_set(policies::jsonb,'{currency_bases}','{}')::json WHERE id=1",
        "INSERT INTO subscription_base_prices(country_code,currency,amount,revision,effective_from,source_reference) SELECT country_code,currency,amount,'overlap-test',effective_from,'isolated test' FROM subscription_base_prices WHERE id=1",
    ],
)
async def test_direct_sql_integrity(
    factory: async_sessionmaker[AsyncSession], statement: str
) -> None:
    """Rollback each refused SQL transaction and inspect the unchanged price separately."""
    with pytest.raises(IntegrityError):
        async with factory() as session, session.begin():
            await session.execute(text(statement))
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT amount FROM subscription_base_prices WHERE id=1")
            )
            == 3000
        )


# ==============================================
# EXPLICIT STORED PLATFORM AUTHORITY
# A descriptive administrator label or another permission cannot publish a base price.
# ==============================================


@pytest.fixture(scope="module")
async def actors(
    factory: async_sessionmaker[AsyncSession],
) -> tuple[OIDCPrincipal, OIDCPrincipal]:
    """Prepare only local synthetic administrators; no grant is written outside this cluster."""
    async with factory() as session, session.begin():
        principals = []
        for index, code in enumerate(["subscriptions.pricing.manage", "admins.manage"]):
            role = (
                await session.execute(
                    insert(Role)
                    .values(
                        code="o3-role-" + str(index),
                        name="O3 local test",
                        is_active=True,
                    )
                    .returning(Role.id)
                )
            ).scalar_one()
            permission = await session.scalar(
                text("SELECT id FROM permissions WHERE code=:code"), {"code": code}
            )
            if permission is None:
                permission = (
                    await session.execute(
                        insert(Permission)
                        .values(code=code, name="O3 local test")
                        .returning(Permission.id)
                    )
                ).scalar_one()
            await session.execute(
                insert(role_permissions).values(role_id=role, permission_id=permission)
            )
            await session.execute(
                insert(Admin).values(
                    chat_id=-830001 - index,
                    role_id=role,
                    is_active=True,
                    full_name="O3 local author",
                    auth_subject="o3-author-" + str(index),
                )
            )
            principals.append(
                OIDCPrincipal(
                    subject="o3-author-" + str(index),
                    issuer="https://local-test.invalid",
                    realm_roles=frozenset(),
                )
            )
    return principals[0], principals[1]


# ==============================================
# PUBLICATION REFUSAL BEFORE ANY PRICE CHANGE
# The exact permission is checked inside the service's own transaction.
# ==============================================


@pytest.mark.asyncio
async def test_unprivileged_publication_refused(
    factory: async_sessionmaker[AsyncSession],
    actors: tuple[OIDCPrincipal, OIDCPrincipal],
) -> None:
    """Inspect the committed row count after the refused call from another session."""
    async with factory() as session:
        with pytest.raises(HTTPException) as error:
            await publish_country_base(
                session=session,
                principal=actors[1],
                country_code="DZ",
                currency="DZD",
                amount=Decimal("3000.01"),
                expected_revision="legacy:subscription_pricing_config:1",
                source_reference="Isolated test, no commercial approval",
            )
    assert error.value.status_code == 403
    async with factory() as observer:
        assert (
            await observer.scalar(text("SELECT count(*) FROM subscription_base_prices"))
            == 1
        )


# ==============================================
# VERSIONED CONCURRENT PUBLICATION AND BOUNDARIES
# One intent commits; stale competitors fail, while the old interval remains queryable.
# ==============================================


@pytest.mark.asyncio
async def test_concurrent_publication_preserves_history(
    factory: async_sessionmaker[AsyncSession],
    actors: tuple[OIDCPrincipal, OIDCPrincipal],
) -> None:
    """Use independent service transactions and observers; no fixture rollback creates the proof."""

    async def publish() -> CountryBaseSelection:
        """Attempt the same old version in a distinct committed session."""
        async with factory() as session:
            return await publish_country_base(
                session=session,
                principal=actors[0],
                country_code="DZ",
                currency="DZD",
                amount=Decimal("3000.01"),
                expected_revision="legacy:subscription_pricing_config:1",
                source_reference="Disposable regression only, not a commercial increase",
            )

    results = await asyncio.gather(publish(), publish(), return_exceptions=True)
    accepted = [r for r in results if isinstance(r, CountryBaseSelection)]
    assert len(accepted) == 1 and sum(isinstance(r, ValueError) for r in results) == 1
    selected = accepted[0]
    evidence = json.loads(os.environ["COUNTRY_BASE_TEST_EVIDENCE"])
    async with factory() as observer:
        old = await resolve_country_base(
            session=observer,
            country_code="DZ",
            currency="DZD",
            at=selected.effective_from - timedelta(microseconds=1),
        )
        new = await resolve_country_base(
            session=observer,
            country_code="DZ",
            currency="DZD",
            at=selected.effective_from,
        )
        assert (
            old.identifier == 1
            and old.amount == 3000
            and new.amount == Decimal("3000.01")
        )
        assert old.effective_until == new.effective_from
        snapshot = (
            await observer.execute(
                text(
                    "SELECT pricing,parameters FROM subscription_pricing_snapshots WHERE id=:id"
                ),
                {"id": evidence["snapshot"]},
            )
        ).one()
        assert (
            snapshot.pricing == {"final_amount_due": "3000.00"}
            and snapshot.parameters["B"] == "3000.00"
        )
        assert (
            await observer.scalar(
                text("SELECT amount FROM subscriptions WHERE id=:id"),
                {"id": evidence["subscription"]},
            )
            == 3000
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM admin_logs WHERE action='pricing.base.country.change'"
                )
            )
            == 1
        )


# ==============================================
# SINGLE EXISTING CALCULATOR WITH COUNTRY INPUT
# Do not copy the layered arithmetic or derive a new price from a currency conversion.
# ==============================================


@pytest.mark.asyncio
async def test_existing_engine_retains_country_source(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verify the actual engine reads O3 and emits country, amount and version evidence."""
    evidence = json.loads(os.environ["COUNTRY_BASE_TEST_EVIDENCE"])
    async with factory() as session:
        value, parameters = await base_breakdown(
            session=session,
            plan_id=evidence["plan"],
            billing_cycle="monthly",
            currency="DZD",
            country_code="DZ",
        )
        assert (
            value == Decimal("3000.01")
            and parameters["base_selection"]["country_code"] == "DZ"
        )
        result = await calculate_subscription_pricing(
            session=session,
            plan_id=evidence["plan"],
            billing_cycle="monthly",
            payment_method="electronic",
            restaurants_count=1,
            branches_count=1,
            years_with_platform=0,
            products_count=0,
            categories_count=0,
            monthly_orders=0,
            average_order_value=0,
            currency="DZD",
            country_code="DZ",
        )
        assert result["parameters"]["B"] == "3000.01000000"
        assert result["parameters"]["base_revision"] == parameters["base_revision"]
        assert result["final_amount_due"] == Decimal("2940.01")


# ==============================================
# LEGACY FOREIGN CURRENCIES REQUIRE COUNTRY DECISIONS
# A populated currency_bases map cannot silently be assigned to an invented country.
# ==============================================


@pytest.mark.asyncio
async def test_unclassified_legacy_prices_block_migration(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Exercise the migration's real precondition in a transaction-local test schema."""
    with pytest.raises(DBAPIError, match="legacy_currency_country_mapping_required"):
        async with factory() as session, session.begin():
            await session.execute(text("CREATE SCHEMA o3_legacy_mapping_test"))
            await session.execute(
                text(
                    "CREATE TABLE o3_legacy_mapping_test.subscription_pricing_config(id integer,base_price numeric,policies json)"
                )
            )
            await session.execute(
                text(
                    'INSERT INTO o3_legacy_mapping_test.subscription_pricing_config VALUES(1,3000,\'{"currency_bases":{"XTS":"1"}}\')'
                )
            )
            await session.execute(
                text("SET LOCAL search_path=o3_legacy_mapping_test,public")
            )
            connection = await session.connection()
            await connection.run_sync(lambda sync: apply_country_base(connection=sync))
    async with factory() as observer:
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM information_schema.schemata WHERE schema_name='o3_legacy_mapping_test'"
                )
            )
            == 0
        )


# ==============================================
# LATE AUDIT FAILURE ROLLS BACK BOTH VERSIONS
# Closing an interval is part of the same transaction as its replacement and retained decision.
# ==============================================


@pytest.mark.asyncio
async def test_publication_failure_leaves_no_partial_version(
    factory: async_sessionmaker[AsyncSession],
    actors: tuple[OIDCPrincipal, OIDCPrincipal],
) -> None:
    """Inject a database audit failure and inspect committed price history independently."""
    async with factory() as session:
        before = await resolve_country_base(
            session=session,
            country_code="DZ",
            currency="DZD",
            at=datetime.now(timezone.utc),
        )
    async with factory() as session, session.begin():
        await session.execute(
            text(
                "CREATE FUNCTION o3_test_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'o3_test_audit_failure' USING ERRCODE='23514'; END $$"
            )
        )
        await session.execute(
            text(
                "CREATE TRIGGER o3_test_fail_audit BEFORE INSERT ON admin_logs FOR EACH ROW WHEN (NEW.action='pricing.base.country.change') EXECUTE FUNCTION o3_test_fail_audit()"
            )
        )
    try:
        async with factory() as session:
            with pytest.raises(IntegrityError, match="o3_test_audit_failure"):
                await publish_country_base(
                    session=session,
                    principal=actors[0],
                    country_code="DZ",
                    currency="DZD",
                    amount=Decimal("3000.02"),
                    expected_revision=before.revision,
                    source_reference="Disposable rollback test only",
                )
        async with factory() as observer:
            current = await resolve_country_base(
                session=observer,
                country_code="DZ",
                currency="DZD",
                at=datetime.now(timezone.utc),
            )
            assert (
                current.revision == before.revision and current.amount == before.amount
            )
            assert (
                await observer.scalar(
                    text(
                        "SELECT count(*) FROM subscription_base_prices WHERE country_code='DZ' AND currency='DZD'"
                    )
                )
                == 2
            )
    finally:
        async with factory() as session, session.begin():
            await session.execute(text("DROP TRIGGER o3_test_fail_audit ON admin_logs"))
            await session.execute(text("DROP FUNCTION o3_test_fail_audit()"))


# ==============================================
# INDEPENDENT COUNTRY AND CURRENCY DIMENSIONS
# ZZ and XTS identify disposable test fixtures, never approved prices for a real foreign market.
# ==============================================


@pytest.mark.asyncio
async def test_country_and_currency_are_selected_independently(
    factory: async_sessionmaker[AsyncSession],
    actors: tuple[OIDCPrincipal, OIDCPrincipal],
) -> None:
    """Configure testing pairs only in this disposable cluster and prove no cross-context fallback."""
    async with factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE subscription_pricing_config SET policies=jsonb_set(policies::jsonb,'{currencies,XTS}',CAST(:policy AS jsonb))::json WHERE id=1"
            ),
            {"policy": json.dumps({"decimals": 8})},
        )
    for currency, amount in [("DZD", Decimal(1)), ("XTS", Decimal(2))]:
        async with factory() as session:
            await publish_country_base(
                session=session,
                principal=actors[0],
                country_code="ZZ",
                currency=currency,
                amount=amount,
                expected_revision=None,
                source_reference="Reserved testing context; disposable fixture, not commercial approval",
            )
    async with factory() as observer:
        now = datetime.now(timezone.utc)
        first = await resolve_country_base(
            session=observer, country_code="ZZ", currency="DZD", at=now
        )
        second = await resolve_country_base(
            session=observer, country_code="ZZ", currency="XTS", at=now
        )
        dz = await resolve_country_base(
            session=observer, country_code="DZ", currency="DZD", at=now
        )
        assert (
            first.amount == 1 and second.amount == 2 and dz.amount == Decimal("3000.01")
        )
        with pytest.raises(ValueError, match="country_base_missing"):
            await resolve_country_base(
                session=observer, country_code="DZ", currency="XTS", at=now
            )
