# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🐘 DATABASE - SQLAlchemy ORM
# اتصال بقاعدة البيانات باستخدام SQLAlchemy مع Async
# Production Ready
# ==============================================

"""MoulAI operational module for database.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from collections.abc import AsyncGenerator
from dataclasses import (
    dataclass,
    field,
)
from functools import partial
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import (
    inspect,
    text,
)
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import (
    DatabaseTarget,
    Settings,
    settings,
)
from app.core.health_only import (
    HealthOnlyDatabasePolicy,
    health_only_database_policy,
    install_health_only_database_guard,
)
from app.core.logger import logger
from app.core.test_database import (
    UnsafeTestDatabaseError,
    isolated_connection_arguments,
    read_test_database_identity,
    validate_test_branch_configuration,
    validated_test_database_url,
)

# ==============================================
# 🌍 LOAD ENVIRONMENT VARIABLES
# ==============================================

load_dotenv()

# ==============================================
# ✅ استيراد Base من النماذج (مصدر واحد فقط)
# ==============================================

from app.models.base import Base

# ==============================================
# EXPLICIT ORM CONNECTION TARGET
# ==============================================


@dataclass(frozen=True)
class DatabaseEngineConfiguration:
    """Capture the selected target and expected identity without exposing URLs.

    The snapshot remains paired with its engine even if a caller later changes
    the mutable Settings object. Production migration tools retain DATABASE_URL.
    """

    target: DatabaseTarget
    database_url: str = field(repr=False)
    connect_arguments: dict[str, Any] = field(repr=False)
    endpoint_id: str | None = None
    branch_id: str | None = None
    project_id: str | None = None
    protected_branch_id: str | None = None
    health_only_policy: HealthOnlyDatabasePolicy | None = None


def _engine_configuration(*, configuration: Settings) -> DatabaseEngineConfiguration:
    """Resolve an explicit ORM target and validate development before creation."""
    health_policy = health_only_database_policy(configuration=configuration)
    if configuration.DATABASE_TARGET == "primary":
        return DatabaseEngineConfiguration(
            target="primary",
            database_url=configuration.DATABASE_URL,
            connect_arguments={},
        )
    if configuration.DATABASE_TARGET != "development":
        raise UnsafeTestDatabaseError("DATABASE_TARGET is not a supported ORM target")
    if configuration.APP_ENV not in {"development", "test"}:
        raise UnsafeTestDatabaseError(
            "The development database target requires APP_ENV=development or test"
        )
    validate_test_branch_configuration(
        branch_id=configuration.TEST_DATABASE_BRANCH_ID,
        project_id=configuration.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=configuration.PROTECTED_DATABASE_BRANCH_ID,
    )
    url = validated_test_database_url(
        test_database_url=configuration.TEST_DATABASE_URL,
        test_endpoint_id=configuration.TEST_DATABASE_ENDPOINT_ID,
        protected_endpoint_id=configuration.PROTECTED_DATABASE_ENDPOINT_ID,
    )
    arguments = isolated_connection_arguments()
    if health_policy is not None:
        arguments["server_settings"] = {
            **arguments["server_settings"],
            "default_transaction_read_only": "on",
        }
    return DatabaseEngineConfiguration(
        target="development",
        database_url=url,
        connect_arguments=arguments,
        endpoint_id=configuration.TEST_DATABASE_ENDPOINT_ID,
        branch_id=configuration.TEST_DATABASE_BRANCH_ID,
        project_id=configuration.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=configuration.PROTECTED_DATABASE_BRANCH_ID,
        health_only_policy=health_policy,
    )


# ==============================================
# CREATE ENGINE AND CAPTURE ITS IDENTITY CONTRACT
# ==============================================

_DATABASE_CONFIGURATION = _engine_configuration(configuration=settings)

engine = create_async_engine(
    _DATABASE_CONFIGURATION.database_url,
    connect_args=_DATABASE_CONFIGURATION.connect_arguments,
    echo=settings.DB_ECHO,
    hide_parameters=_DATABASE_CONFIGURATION.health_only_policy is not None,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

if _DATABASE_CONFIGURATION.health_only_policy is not None:
    install_health_only_database_guard(
        engine=engine, policy=_DATABASE_CONFIGURATION.health_only_policy
    )


# ==============================================
# 🔌 SESSION FACTORY
# ==============================================

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ==============================================
# 📥 GET DATABASE SESSION (Dependency Injection)
# ==============================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    الحصول على جلسة قاعدة البيانات (Dependency Injection)

    تستخدم في FastAPI Dependency Injection

    Yields:
        AsyncSession: جلسة قاعدة البيانات
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.exception(
                "db_session_error",
                extra={"error": str(e)},
            )
            await session.rollback()
            raise
        finally:
            await session.close()


# ==============================================
# 📥 GET SESSION (للاستخدام المباشر)
# ==============================================


async def get_session() -> AsyncSession:
    """
    الحصول على جلسة قاعدة البيانات للاستخدام المباشر

    تستخدم في الـ Repositories والـ Services

    Returns:
        AsyncSession: جلسة قاعدة البيانات
    """
    return AsyncSessionLocal()


# ==============================================
# 🚀 INITIALIZE DATABASE
# ==============================================


def _validate_schema(connection: Connection) -> None:
    """Require migrated tables and columns; startup never performs schema writes."""
    inspector = inspect(connection)
    installed_tables = set(inspector.get_table_names())
    missing: list[str] = []
    for table in Base.metadata.sorted_tables:
        if table.name not in installed_tables:
            missing.append(table.name)
            continue
        installed_columns = {
            column["name"] for column in inspector.get_columns(table.name)
        }
        missing.extend(
            f"{table.name}.{column.name}"
            for column in table.columns
            if column.name not in installed_columns
        )
    if missing:
        logger.error(
            "database_schema_requires_migration", extra={"missing_objects": missing}
        )
        raise RuntimeError("Database schema requires an explicit Alembic migration")


# ==============================================
# INITIALIZE MIGRATED DATABASE
# ==============================================


async def init_db() -> None:
    """Verify connectivity and migrated schema without silently creating tables."""
    try:
        # ✅ استيراد جميع النماذج لضمان تسجيلها في Base.metadata
        import app.models  # noqa: F401  # Registers SQLAlchemy models in Base.metadata.

        async with engine.connect() as conn:
            try:
                if _DATABASE_CONFIGURATION.target == "development":
                    if _DATABASE_CONFIGURATION.health_only_policy is None:
                        await conn.execute(text("SET TRANSACTION READ ONLY"))
                    await conn.run_sync(
                        partial(
                            read_test_database_identity,
                            endpoint_id=_DATABASE_CONFIGURATION.endpoint_id,
                            branch_id=_DATABASE_CONFIGURATION.branch_id,
                            project_id=_DATABASE_CONFIGURATION.project_id,
                            protected_branch_id=(
                                _DATABASE_CONFIGURATION.protected_branch_id
                            ),
                        )
                    )
                await conn.run_sync(_validate_schema)
            finally:
                if _DATABASE_CONFIGURATION.target == "development":
                    await conn.rollback()

        logger.info(
            "database_initialized_successfully",
            extra={
                "environment": settings.APP_ENV,
                "database_target": _DATABASE_CONFIGURATION.target,
                "echo_enabled": settings.DB_ECHO,
            },
        )
    except Exception as e:
        logger.exception(
            "database_init_failed",
            extra={"error": str(e)},
        )
        raise


# ==============================================
# 🗑️ DROP DATABASE (للاختبار فقط)
# ==============================================


async def drop_db() -> None:
    """
    حذف جميع الجداول (للاختبار فقط)

    ⚠️ تحذير: هذه الدالة تحذف جميع البيانات!
    تستخدم فقط في بيئة الاختبار
    """
    try:
        # ✅ استيراد جميع النماذج لضمان تسجيلها في Base.metadata
        import app.models  # noqa: F401  # Registers SQLAlchemy models in Base.metadata.

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        logger.warning("database_dropped_successfully")
    except Exception as e:
        logger.exception(
            "database_drop_failed",
            extra={"error": str(e)},
        )
        raise


# ==============================================
# 🔒 CLOSE DATABASE
# ==============================================


async def close_db() -> None:
    """
    إغلاق اتصال قاعدة البيانات

    يتم استدعاؤها عند إيقاف التشغيل
    """
    try:
        await engine.dispose()
        logger.info("database_connection_closed")
    except Exception as e:
        logger.exception(
            "database_close_failed",
            extra={"error": str(e)},
        )
        raise


# ==============================================
# ✅ CHECK DATABASE CONNECTION
# ==============================================


async def check_db_connection() -> bool:
    """
    التحقق من اتصال قاعدة البيانات

    Returns:
        True إذا كان الاتصال ناجحاً، False إذا فشل
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connection_check_successful")
        return True
    except Exception as e:
        logger.exception(
            "database_connection_check_failed",
            extra={"error": str(e)},
        )
        return False


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Base
    "Base",
    # Engine
    "engine",
    # Session
    "AsyncSessionLocal",
    # Functions
    "get_db",
    "get_session",
    "init_db",
    "drop_db",
    "close_db",
    "check_db_connection",
]
