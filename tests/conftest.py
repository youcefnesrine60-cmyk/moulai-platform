# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PYTEST OFFLINE AND DATABASE BOUNDARIES
# Install the offline guard and require explicit authorization for destructive database
# fixtures.
# ==============================================

"""Keep offline tests independent of explicitly authorized PostgreSQL fixtures."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

import asyncio
import os
import sys
import time
from collections.abc import (
    AsyncGenerator,
    Generator,
)
from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from scripts.run_offline_api_tests import OfflineNetworkGuard
from test_support.offline_storage import reserve_pytest_directory

# ==============================================
# 🔧 TEST DATABASE
# Identify the explicit test schema and keep it separate from application data.
# ==============================================

TEST_ALEMBIC_DIRECTORY = Path(__file__).resolve().parents[1] / "alembic_test"
OFFLINE_GUARD: pytest.StashKey[OfflineNetworkGuard] = pytest.StashKey()
AUDIT_ACTIVE: pytest.StashKey[bool] = pytest.StashKey()
SEPARATE_REHEARSALS: pytest.StashKey[dict[str, int]] = pytest.StashKey()


# ==============================================
# EXPLICIT LIVE-DATABASE OPT-IN AND OFFLINE NETWORK GUARD
# Require an explicit CLI choice before destructive database fixtures run.
# ==============================================


def pytest_addoption(parser: pytest.Parser) -> None:
    """Require an explicit CLI choice before destructive database fixtures run."""
    parser.getgroup("moulai").addoption(
        "--run-database-tests",
        action="store_true",
        default=False,
        help="Enable approved PostgreSQL tests; fixtures truncate the test dataset.",
    )
    parser.getgroup("moulai").addoption(
        "--local-postgres-tests",
        action="store_true",
        default=False,
        help="Use only the isolated loopback database prepared by the local launcher.",
    )


# ==============================================
# CONFIGURE DEFAULT OFFLINE EXECUTION
# Reuse the socket guard before collecting application test modules.
# ==============================================


def pytest_configure(config: pytest.Config) -> None:
    """Reuse the socket guard before collecting application test modules."""
    # Reserve a unique workspace path before pytest constructs its tmp_path factory.
    # An explicitly supplied --basetemp remains under the caller's control.
    if config.option.basetemp is None:
        config.option.basetemp = str(reserve_pytest_directory())
    config.stash[SEPARATE_REHEARSALS] = {}
    config.addinivalue_line(
        "markers", "database: requires explicit live PostgreSQL test authorization"
    )
    config.addinivalue_line(
        "markers", "k10_postgres: requires the dedicated isolated local E1 profile"
    )
    config.addinivalue_line(
        "markers",
        "dining_postgres: requires the dedicated post-S1a local dining profile",
    )
    config.addinivalue_line(
        "markers", "country_rehearsal: requires the dedicated disposable O3/O4 runner"
    )
    config.addinivalue_line(
        "markers", "operational_rehearsal: requires the dedicated disposable O2 runner"
    )
    local_mode = config.getoption("--local-postgres-tests")
    if local_mode and config.getoption("--run-database-tests"):
        raise pytest.UsageError(
            "Choose local PostgreSQL or the remote test path, not both."
        )
    if config.getoption("--run-database-tests"):
        return
    os.environ["REDIS_URL"] = ""
    if local_mode:
        from pydantic import ValidationError

        from test_support.local_postgres import (
            LocalPostgresNetworkGuard,
            LocalPostgresSettings,
        )

        try:
            local_configuration = LocalPostgresSettings()
        except ValidationError:
            raise pytest.UsageError(
                "Local PostgreSQL configuration is incomplete or unsafe. "
                "Use python scripts/run_local_postgres_tests.py; no Neon fallback exists."
            ) from None
        guard = LocalPostgresNetworkGuard(client_port=local_configuration.CLIENT_PORT)
    else:
        guard = OfflineNetworkGuard()
    config.stash[OFFLINE_GUARD] = guard
    config.stash[AUDIT_ACTIVE] = True

    # ==============================================
    # DISPATCH AUDIT EVENTS ONLY DURING THIS PYTEST SESSION
    # Limit the hook to this run, including embedded pytest invocations.
    # ==============================================

    def audit_network(event: str, arguments: tuple[Any, ...]) -> None:
        """Limit the hook to this run, including embedded pytest invocations."""
        if config.stash.get(AUDIT_ACTIVE, False):
            guard(event, arguments)

    sys.addaudithook(audit_network)


# ==============================================
# CLASSIFY LIVE FIXTURE DEPENDENCIES
# Skip only live fixture consumers, including their transitive dependents.
# ==============================================


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip only live fixture consumers, including their transitive dependents."""
    for item in items:
        # ==============================================
        # SEPARATE HISTORICAL SCHEMAS FROM THE GENERAL DATABASE PROFILE
        # These runners use --noconftest and attest their own fresh databases; neither a remote opt-in nor ambient credentials admit them here.
        # ==============================================

        for marker, command in (
            ("country_rehearsal", "scripts/rehearse_country_base.py --billing-country"),
            (
                "operational_rehearsal",
                "scripts/rehearse_country_base.py --operational-history",
            ),
        ):
            if item.get_closest_marker(marker) is not None and "factory" in getattr(
                item, "fixturenames", ()
            ):
                separate = config.stash[SEPARATE_REHEARSALS]
                separate[command] = separate.get(command, 0) + 1
                item.add_marker(
                    pytest.mark.skip(
                        reason="Separate disposable-schema test: run python "
                        + command
                        + ". Not executed in this general run; no database connection opened."
                    )
                )
        if item.get_closest_marker("dining_postgres") is not None and (
            not config.getoption("--local-postgres-tests")
            or os.environ.get("LOCAL_POSTGRES_TEST_PROFILE") != "dining"
        ):
            item.add_marker(
                pytest.mark.skip(
                    reason="Dining requires the isolated launcher --profile dining."
                )
            )
        if item.get_closest_marker("k10_postgres") is not None and (
            not config.getoption("--local-postgres-tests")
            or os.environ.get("LOCAL_POSTGRES_TEST_PROFILE") != "k10"
        ):
            item.add_marker(
                pytest.mark.skip(
                    reason="K10 requires the isolated E1 launcher --profile k10."
                )
            )
        if "test_database_engine" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.database)
        if (
            item.get_closest_marker("database") is not None
            and not config.getoption("--run-database-tests")
            and not config.getoption("--local-postgres-tests")
        ):
            item.add_marker(
                pytest.mark.skip(
                    reason="PostgreSQL tests require separate authorization and "
                    "an explicit database mode; use scripts/run_local_postgres_tests.py "
                    "for isolated local execution. No database connection was opened."
                )
            )


# ==============================================
# REPORT UNEXPECTED NETWORK ATTEMPTS
# A caught forbidden network attempt must not produce a successful run.
# ==============================================


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """A caught forbidden network attempt must not produce a successful run."""
    guard = session.config.stash.get(OFFLINE_GUARD, None)
    if guard is not None and guard.denied and exitstatus == 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


# ==============================================
# EXPLAIN NETWORK POLICY FAILURES WITHOUT DESTINATION DETAILS
# Make a rejected network event visible even if the test caught its error.
# ==============================================


def pytest_terminal_summary(terminalreporter: Any, config: pytest.Config) -> None:
    """Make a rejected network event visible even if the test caught its error."""
    guard = config.stash.get(OFFLINE_GUARD, None)
    if guard is not None and guard.denied:
        terminalreporter.write_sep(
            "=", f"Offline network guard rejected {sum(guard.denied.values())} event(s)"
        )
    separate = config.stash.get(SEPARATE_REHEARSALS, {})
    if separate:
        terminalreporter.write_sep(
            "-", "Separate PostgreSQL scenarios NOT RUN in this campaign"
        )
        for command, count in sorted(separate.items()):
            terminalreporter.write_line(f"{count} scenario(s): python {command}")


# ==============================================
# CLOSE THE SESSION AUDIT BOUNDARY
# Deactivate this run's audit callback when pytest releases its config.
# ==============================================


def pytest_unconfigure(config: pytest.Config) -> None:
    """Deactivate this run's audit callback when pytest releases its config."""
    config.stash[AUDIT_ACTIVE] = False


# ==============================================
# LAZY GUARDED POSTGRESQL ENGINE
# Validate the approved target only when a live fixture is requested.
# ==============================================


@pytest.fixture(scope="session")
async def test_database_engine(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncEngine, None]:
    """Validate the approved target only when a live fixture is requested."""
    local_mode = request.config.getoption("--local-postgres-tests")
    if local_mode:
        from test_support.local_postgres import LocalPostgresSettings

        configuration = LocalPostgresSettings()
        engine = create_async_engine(
            configuration.URL.get_secret_value(),
            echo=False,
            pool_size=5,
            max_overflow=0,
            connect_args={
                "ssl": False,
                "timeout": 20,
                "command_timeout": 60,
                "server_settings": {"search_path": "public", "lock_timeout": "5000"},
            },
            execution_options={"moulai_local_configuration": configuration},
        )
        try:
            yield engine
        finally:
            await engine.dispose()
        return
    if not request.config.getoption("--run-database-tests"):
        pytest.skip("Live PostgreSQL fixtures require --run-database-tests.")

    from app.core.config import settings
    from app.core.test_database import (
        isolated_connection_arguments,
        validate_test_branch_configuration,
        validated_test_database_url,
    )

    validate_test_branch_configuration(
        branch_id=settings.TEST_DATABASE_BRANCH_ID,
        project_id=settings.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
    )
    test_url = validated_test_database_url(
        test_database_url=settings.TEST_DATABASE_URL,
        test_endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
        protected_endpoint_id=settings.PROTECTED_DATABASE_ENDPOINT_ID,
    )
    connection_arguments = isolated_connection_arguments()
    connection_arguments.update({"timeout": 60, "command_timeout": 60})
    connection_arguments["server_settings"].update(
        {"lock_timeout": "5000", "idle_in_transaction_session_timeout": "0"}
    )
    engine = create_async_engine(
        test_url,
        echo=False,
        pool_size=5,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args=connection_arguments,
    )
    try:
        yield engine
    finally:
        await engine.dispose()


# ==============================================
# TEST SCHEMA REVISION GUARD
# Return the head revision from the dedicated test Alembic history.
# ==============================================


def get_expected_test_schema_revision() -> str:
    """Return the head revision from the dedicated test Alembic history."""
    alembic_config = Config()
    alembic_config.set_main_option("script_location", str(TEST_ALEMBIC_DIRECTORY))
    expected_revision = (
        ScriptDirectory.from_config(alembic_config)
        .get_revision("e1b92b200001")
        .revision
    )
    if expected_revision is None:
        raise RuntimeError("The dedicated test Alembic history has no head revision.")

    return expected_revision


# ==============================================
# VERIFY TEST SCHEMA REVISION
# Refuse cleanup on a mismatched schema without prescribing a migration.
# ==============================================


@pytest.fixture(scope="session")
async def verify_test_schema_revision(test_database_engine: AsyncEngine) -> None:
    """Refuse cleanup on a mismatched schema without prescribing a migration."""
    from test_support.local_postgres import (
        LOCAL_MAIN_REVISION,
        LOCAL_REVISION,
        LOCAL_S1_REVISION,
        LocalPostgresSettings,
        read_local_test_identity,
    )

    local_configuration = test_database_engine.sync_engine.get_execution_options().get(
        "moulai_local_configuration"
    )
    local_mode = isinstance(local_configuration, LocalPostgresSettings)
    expected_revision = (
        (
            {"subscription": LOCAL_S1_REVISION, "main": LOCAL_MAIN_REVISION}.get(
                local_configuration.PROFILE, LOCAL_REVISION
            )
        )
        if local_mode
        else get_expected_test_schema_revision()
    )

    try:
        async with test_database_engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            if local_mode:
                await connection.run_sync(
                    lambda sync: read_local_test_identity(
                        sync, configuration=local_configuration
                    )
                )
            else:
                from app.core.config import settings
                from app.core.test_database import read_test_database_identity

                await connection.run_sync(
                    lambda sync: read_test_database_identity(
                        sync,
                        endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
                        branch_id=settings.TEST_DATABASE_BRANCH_ID,
                        project_id=settings.TEST_DATABASE_PROJECT_ID,
                        protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
                    )
                )
            installed_revisions = (
                (
                    await connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    )
                )
                .scalars()
                .all()
            )
    except SQLAlchemyError as error:
        raise RuntimeError(
            "The test schema is unavailable; database tests stopped before cleanup. "
            "Review the isolated target and obtain separate migration authorization."
        ) from error

    if installed_revisions != [expected_revision]:
        raise RuntimeError(
            "The test schema is not at the dedicated Alembic head "
            f"(expected {expected_revision}). Database tests stopped before cleanup. "
            "No migration is authorized or performed by pytest. "
            "Run offline tests without --run-database-tests."
        )


# ==============================================
# 🔧 ASYNCIO FIXTURE
# إنشاء event loop للاختبارات غير المتزامنة.
# ==============================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    إنشاء event loop للاختبارات غير المتزامنة.

    Returns:
        Generator[asyncio.AbstractEventLoop, None, None]: Event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==============================================
# ✅ DB SESSION FIXTURE
# إنشاء جلسة قاعدة بيانات اختبارية.
# ==============================================


@pytest.fixture(scope="function")
async def db_session(
    test_database_engine: AsyncEngine, cleanup_test_database: None
) -> AsyncGenerator[AsyncSession, None]:
    """
    إنشاء جلسة قاعدة بيانات اختبارية.

    ✅ rollback بعد كل اختبار لضمان عزل البيانات

    Yields:
        AsyncGenerator[AsyncSession, None]: جلسة قاعدة البيانات
    """
    session_factory = async_sessionmaker(
        test_database_engine, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ==============================================
# ✅ CLIENT FIXTURE
# إنشاء عميل اختبار HTTP مع جلسة قاعدة بيانات مستقلة لكل طلب.
# ==============================================


@pytest.fixture(scope="function")
async def client(
    test_database_engine: AsyncEngine, cleanup_test_database: None
) -> AsyncGenerator[AsyncClient, None]:
    """
    إنشاء عميل اختبار HTTP مع جلسة قاعدة بيانات مستقلة لكل طلب.

    ✅ كل طلب HTTP يحصل على جلسة DB جديدة
    ✅ rollback بعد كل طلب لضمان عزل البيانات

    Yields:
        AsyncGenerator[AsyncClient, None]: عميل HTTP
    """

    from app.core.database import get_db
    from app.main import app

    session_factory = async_sessionmaker(
        test_database_engine, expire_on_commit=False, autoflush=False
    )

    # ==============================================
    # OVERRIDE GET DB
    # Yield the explicitly selected test session to the dependency override.
    # ==============================================

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        """Yield the explicitly selected test session to the dependency override."""

        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.rollback()
                await session.close()

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


# ==============================================
# 🔧 TEST DATABASE CLEANUP FIXTURE
# تنظيف قاعدة البيانات التجريبية قبل وبعد كل اختبار.
# ==============================================


@pytest.fixture(scope="function")
async def cleanup_test_database(
    test_database_engine: AsyncEngine, verify_test_schema_revision: None
) -> AsyncGenerator[None, None]:
    """
    تنظيف قاعدة البيانات التجريبية قبل وبعد كل اختبار.

    تستخدم واجهات API عمليات commit مستقلة؛ لذلك rollback الجلسة
    وحده لا يعزل الاختبارات.
    """
    import app.models  # noqa: F401  # Register ORM models in Base.metadata.
    from app.models.base import Base

    table_names = ", ".join(
        f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)
    )

    # ==============================================
    # TRUNCATE ALL TABLES
    # Clear only the verified test tables through the explicitly authorized fixture
    # connection.
    # ==============================================

    async def truncate_all_tables() -> None:
        """Clear only the verified test tables through the explicitly authorized fixture connection."""

        if not table_names:
            return

        async with test_database_engine.begin() as connection:
            from test_support.local_postgres import (
                LocalPostgresSettings,
                read_local_test_identity,
            )

            local_configuration = (
                test_database_engine.sync_engine.get_execution_options().get(
                    "moulai_local_configuration"
                )
            )
            if isinstance(local_configuration, LocalPostgresSettings):
                await connection.run_sync(
                    lambda sync: read_local_test_identity(
                        sync, configuration=local_configuration
                    )
                )
                actual_tables = set(
                    (
                        await connection.execute(
                            text(
                                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
                            )
                        )
                    ).scalars()
                )
                expected_tables = set(Base.metadata.tables) | {"alembic_version"}
                if local_configuration.PROFILE not in {"subscription", "main"}:
                    expected_tables -= {
                        "subscription_pricing_config",
                        "subscription_pricing_snapshots",
                        "subscription_reminders",
                        "cash_collections",
                        "cash_collection_attempts",
                    }
                if local_configuration.PROFILE == "main":
                    from migration_support.tenant_e1_schema import TENANT_TABLE_NAMES

                    expected_tables |= set(TENANT_TABLE_NAMES)
                if actual_tables != expected_tables:
                    raise RuntimeError("local_cleanup_catalog_not_allowlisted")
                local_tables = ", ".join(
                    f'public."{name}"'
                    for name in sorted(expected_tables - {"alembic_version"})
                )
                if local_configuration.PROFILE == "main":
                    # E1 retention triggers intentionally reject TRUNCATE. Keep
                    # them active; subscription fixtures own untagged legacy rows
                    # only and must never create tenant governance records.
                    for name in set(TENANT_TABLE_NAMES) - {
                        "tenant_roles",
                        "tenant_role_permissions",
                    }:
                        if (
                            await connection.execute(
                                text(f'SELECT count(*) FROM public."{name}"')
                            )
                        ).scalar_one():
                            raise RuntimeError(
                                "main_subscription_cleanup_contains_retained_tenant_data"
                            )
                    # These five ancestors are referenced by retained E1 tables.
                    # Delete their untagged fixture rows after truncating their
                    # business dependants; never disable any retention trigger.
                    delete_only = {
                        "admins",
                        "owners",
                        "restaurant_groups",
                        "restaurants",
                        "roles",
                    }
                    truncate_names = (
                        expected_tables
                        - {"alembic_version"}
                        - set(TENANT_TABLE_NAMES)
                        - delete_only
                    )
                    quoted_tables = ", ".join(
                        f'public."{name}"' for name in sorted(truncate_names)
                    )
                    await connection.execute(
                        text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY")
                    )
                    for table in reversed(Base.metadata.sorted_tables):
                        if table.name not in delete_only:
                            continue
                        await connection.execute(table.delete())
                        sequence = (
                            await connection.execute(
                                text("SELECT pg_get_serial_sequence(:name, 'id')"),
                                {"name": table.name},
                            )
                        ).scalar_one()
                        if sequence:
                            # Server-derived identifier belongs to this exact
                            # allowlisted table; quote each namespace part.
                            quoted = ".".join(
                                '"' + part.replace('"', '""') + '"'
                                for part in sequence.split(".")
                            )
                            await connection.execute(
                                text(f"ALTER SEQUENCE {quoted} RESTART WITH 1")
                            )
                else:
                    await connection.execute(
                        text(f"TRUNCATE TABLE {local_tables} RESTART IDENTITY")
                    )
                if local_configuration.PROFILE in {"subscription", "main"}:
                    from sqlalchemy import insert

                    from app.models.subscription_pricing_legacy import LegacySubscriptionPricingConfig as SubscriptionPricingConfig  # isort: skip  # fmt: skip

                    await connection.execute(
                        insert(SubscriptionPricingConfig).values(
                            id=1,
                            base_price=3000,
                            policies={
                                "currencies": {"DZD": {"decimals": 2}},
                                "reminder_days": [14, 7, 1, 0],
                            },
                        )
                    )

                return
            await connection.execute(
                text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"),
            )

    await truncate_all_tables()
    try:
        yield
    finally:
        await truncate_all_tables()


# ==============================================
# 📦 DATA FACTORIES - SAMPLE DATA
# بيانات مالك نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_owner_data() -> dict[str, Any]:
    """
    بيانات مالك نموذجية للاختبار.

    Returns:
        Dict[str, Any]: بيانات المالك
    """
    unique_id: int = int(time.time() * 1000) % 1000000000

    return {
        "chat_id": unique_id,
        "full_name": f"أحمد محمد {unique_id}",
        "phone": "0555123456",
        "email": f"ahmed_{unique_id}@example.com",
        "registration_status": "pending",
    }


# ==============================================
# SAMPLE RESTAURANT DATA
# بيانات مطعم نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_restaurant_data() -> dict[str, Any]:
    """
    بيانات مطعم نموذجية للاختبار.

    Returns:
        Dict[str, Any]: بيانات المطعم
    """
    return {
        "name": "مطعم البيتزا الذهبية",
        "type": "restaurant",
        "phone": "+213551234567",
        "wilaya": "الجزائر",
        "lat": 36.7538,
        "lng": 3.0588,
        "is_active": True,
    }


# ==============================================
# SAMPLE RESTAURANT GROUP DATA
# بيانات مجموعة مطاعم نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_restaurant_group_data() -> dict[str, Any]:
    """
    بيانات مجموعة مطاعم نموذجية للاختبار.

    ✅ لا يحتوي على is_active لأن RestaurantGroup لا يدعمه

    Returns:
        Dict[str, Any]: بيانات المجموعة
    """
    return {
        "name": "مجموعة المطاعم الذهبية",
    }


# ==============================================
# SAMPLE RESTAURANT BRANCH DATA
# بيانات فرع مطعم نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_restaurant_branch_data() -> dict[str, Any]:
    """
    بيانات فرع مطعم نموذجية للاختبار.

    Returns:
        Dict[str, Any]: بيانات الفرع
    """
    return {
        "group_id": 1,
        "restaurant_id": 1,
    }


# ==============================================
# SAMPLE BULK BRANCHES DATA
# بيانات فروع متعددة نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_bulk_branches_data() -> dict[str, Any]:
    """
    بيانات فروع متعددة نموذجية للاختبار.

    Returns:
        Dict[str, Any]: بيانات الفروع المتعددة
    """
    return {
        "group_id": 1,
        "restaurant_ids": [1, 2, 3],
    }


# ==============================================
# SAMPLE METRIC DATA
# بيانات مقاييس نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_metric_data() -> dict[str, Any]:
    """
    بيانات مقاييس نموذجية للاختبار.

    Returns:
        Dict[str, Any]: بيانات المقاييس
    """
    return {
        "products_count": 10,
        "categories_count": 5,
        "monthly_orders": 100,
        "average_order_value": 1500.00,
    }


# ==============================================
# SAMPLE ORDER COUNTER DATA
# بيانات عداد طلبات نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_order_counter_data() -> dict[str, Any]:
    """
    بيانات عداد طلبات نموذجية للاختبار.

    Returns:
        Dict[str, Any]: بيانات عداد الطلبات
    """
    return {
        "last_number": 0,
    }


# ==============================================
# SAMPLE PAYMENT SETTINGS DATA
# بيانات إعدادات دفع نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_payment_settings_data() -> dict[str, Any]:
    """
    بيانات إعدادات دفع نموذجية للاختبار.

    Returns:
        Dict[str, Any]: بيانات إعدادات الدفع
    """
    return {
        "allow_cash": True,
        "allow_card": True,
        "allow_ccp": False,
        "allow_baridimob": False,
        "allow_stripe": False,
        "allow_paypal": False,
    }


# ==============================================
# SAMPLE ORDER DATA
# بيانات طلب نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_order_data() -> dict[str, Any]:
    """
    بيانات طلب نموذجية للاختبار.

    Returns:
        Dict[str, Any]: بيانات الطلب
    """
    return {
        "order_number": "RST1-000001",
        "order_type": "dine_in",
        "customer_name": "علي أحمد",
        "customer_phone": "0555123456",
        "delivery_address": None,
        "customer_note": "بدون بصل",
        "subtotal_amount": 100.00,
        "discount_amount": 0.00,
        "tax_amount": 0.00,
        "delivery_amount": 0.00,
        "total_amount": 100.00,
        "status": "pending",
    }


# ==============================================
# SAMPLE PRODUCT DATA
# بيانات منتج نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_product_data() -> dict[str, Any]:
    """
    بيانات منتج نموذجية للاختبار.

    Returns:
        Dict[str, Any]: بيانات المنتج
    """
    return {
        "name": "بيتزا مارجريتا",
        "description": "بيتزا كلاسيكية بصلصة الطماطم والجبن",
        "price": 800.00,
        "image_url": None,
        "sort_order": 0,
        "is_available": True,
        "is_active": True,
    }


# ==============================================
# SAMPLE CATEGORY DATA
# بيانات تصنيف نموذجية للاختبار.
# ==============================================


@pytest.fixture
def sample_category_data() -> dict[str, Any]:
    """
    بيانات تصنيف نموذجية للاختبار.

    Returns:
        Dict[str, Any]: بيانات التصنيف
    """
    return {
        "name": "بيتزا",
        "description": "جميع أنواع البيتزا",
        "sort_order": 0,
        "is_active": True,
    }


# ==============================================
# SAMPLE GROUP DATA
# بيانات مجموعة نموذجية للاختبار (متوافقة مع الاختبارات القديمة).
# ==============================================


@pytest.fixture
def sample_group_data() -> dict[str, Any]:
    """
    بيانات مجموعة نموذجية للاختبار (متوافقة مع الاختبارات القديمة).

    ✅ لا يحتوي على is_active

    Returns:
        Dict[str, Any]: بيانات المجموعة
    """
    return {
        "name": "مجموعة المطاعم الذهبية",
    }


# ==============================================
# 🏗️ HELPER FUNCTIONS
# إنشاء مالك للاختبارات باستخدام DB مباشر.
# ==============================================


async def create_test_owner(
    db_session: AsyncSession,
    owner_data: dict[str, Any],
) -> Any:
    """
    إنشاء مالك للاختبارات باستخدام DB مباشر.

    ⚠️ تستخدم فقط في إعدادات الاختبارات (setup)

    Args:
        db_session: جلسة قاعدة البيانات
        owner_data: بيانات المالك

    Returns:
        Any: كائن المالك المنشأ
    """
    from app.models.owner import Owner

    owner = Owner(**owner_data)
    db_session.add(owner)
    await db_session.flush()
    await db_session.refresh(owner)
    return owner


# ==============================================
# CREATE TEST RESTAURANT
# إنشاء مطعم للاختبارات باستخدام DB مباشر.
# ==============================================


async def create_test_restaurant(
    db_session: AsyncSession,
    restaurant_data: dict[str, Any],
    owner_id: int,
) -> Any:
    """
    إنشاء مطعم للاختبارات باستخدام DB مباشر.

    ⚠️ تستخدم فقط في إعدادات الاختبارات (setup)

    Args:
        db_session: جلسة قاعدة البيانات
        restaurant_data: بيانات المطعم
        owner_id: معرف المالك

    Returns:
        Any: كائن المطعم المنشأ
    """
    from app.models.restaurant import Restaurant

    restaurant = Restaurant(**{**restaurant_data, "owner_id": owner_id})
    db_session.add(restaurant)
    await db_session.flush()
    await db_session.refresh(restaurant)
    return restaurant


# ==============================================
# CREATE TEST GROUP
# إنشاء مجموعة مطاعم للاختبارات باستخدام DB مباشر.
# ==============================================


async def create_test_group(
    db_session: AsyncSession,
    group_data: dict[str, Any],
    owner_id: int,
) -> Any:
    """
    إنشاء مجموعة مطاعم للاختبارات باستخدام DB مباشر.

    ⚠️ تستخدم فقط في إعدادات الاختبارات (setup)

    Args:
        db_session: جلسة قاعدة البيانات
        group_data: بيانات المجموعة
        owner_id: معرف المالك

    Returns:
        Any: كائن المجموعة المنشأ
    """
    from app.models.restaurant_group import RestaurantGroup

    group = RestaurantGroup(**{**group_data, "owner_id": owner_id})
    db_session.add(group)
    await db_session.flush()
    await db_session.refresh(group)
    return group


# ==============================================
# CREATE TEST BRANCH
# إنشاء فرع مطعم للاختبارات باستخدام DB مباشر.
# ==============================================


async def create_test_branch(
    db_session: AsyncSession,
    group_id: int,
    restaurant_id: int,
) -> Any:
    """
    إنشاء فرع مطعم للاختبارات باستخدام DB مباشر.

    ⚠️ تستخدم فقط في إعدادات الاختبارات (setup)

    Args:
        db_session: جلسة قاعدة البيانات
        group_id: معرف المجموعة
        restaurant_id: معرف المطعم

    Returns:
        Any: كائن الفرع المنشأ
    """
    from app.models.restaurant_group import RestaurantBranch

    branch = RestaurantBranch(
        group_id=group_id,
        restaurant_id=restaurant_id,
    )
    db_session.add(branch)
    await db_session.flush()
    await db_session.refresh(branch)
    return branch


# ==============================================
# 📋 EXPORTS
# Declare the public names intentionally exposed to importing modules.
# ==============================================

__all__ = [
    "client",
    "create_test_branch",
    "create_test_group",
    "create_test_owner",
    "create_test_restaurant",
    "db_session",
    "event_loop",
    "sample_bulk_branches_data",
    "sample_category_data",
    "sample_group_data",
    "sample_metric_data",
    "sample_order_counter_data",
    "sample_order_data",
    "sample_owner_data",
    "sample_payment_settings_data",
    "sample_product_data",
    "sample_restaurant_branch_data",
    "sample_restaurant_data",
    "sample_restaurant_group_data",
]
