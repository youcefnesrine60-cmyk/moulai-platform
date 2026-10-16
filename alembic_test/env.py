# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DATABASE MIGRATION - ALEMBIC / ENV
# Database migration and schema management component.
# ==============================================

"""Database migration for env.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ==============================================
# 📦 IMPORT MODELS
# ==============================================

from app.core.config import settings
from app.core.test_database import (
    isolated_connection_arguments,
    read_test_database_identity,
    validate_test_branch_configuration,
    validated_test_database_url,
)
from app.models import Base

# ==============================================
# 🔧 ALEMBIC CONFIG
# ==============================================

config = context.config

# ==============================================
# 🗂️ SET ISOLATED TEST DATABASE URL
# ==============================================

TEST_DATABASE_NAME = "neondb_test"


def get_test_database_url() -> str:
    """Return the explicitly configured, isolated test database URL.

    Alembic test migrations must never infer a test database from the runtime
    URL.  Requiring the configured test database name prevents an accidental
    schema operation against the development or production database.
    """
    validate_test_branch_configuration(
        branch_id=settings.TEST_DATABASE_BRANCH_ID,
        project_id=settings.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
    )
    return validated_test_database_url(
        test_database_url=settings.TEST_DATABASE_URL,
        test_endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
        protected_endpoint_id=settings.PROTECTED_DATABASE_ENDPOINT_ID,
    )


config.set_main_option("sqlalchemy.url", get_test_database_url())

# ==============================================
# 📝 LOGGING
# ==============================================

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ==============================================
# 🎯 TARGET METADATA
# ==============================================

target_metadata = Base.metadata


# ==============================================
# 🚀 RUN MIGRATIONS OFFLINE
# ==============================================


def run_migrations_offline() -> None:
    """تشغيل الترحيلات في وضع Offline"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ==============================================
# 🔄 DO RUN MIGRATIONS (SYNC)
# ==============================================


def do_run_migrations(connection: Connection) -> None:
    """تنفيذ الترحيلات (النسخة المتزامنة)"""
    read_test_database_identity(
        connection,
        endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
        branch_id=settings.TEST_DATABASE_BRANCH_ID,
        project_id=settings.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
    )
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ==============================================
# 🚀 RUN MIGRATIONS ONLINE (ASYNC)
# ==============================================


async def run_async_migrations() -> None:
    """تشغيل الترحيلات في وضع Online (غير متزامن)"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=isolated_connection_arguments(),
    )

    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# ==============================================
# RUN MIGRATIONS ONLINE
# ==============================================


def run_migrations_online() -> None:
    """تشغيل الترحيلات في وضع Online (الواجهة العامة)"""
    asyncio.run(run_async_migrations())


# ==============================================
# 🎯 ENTRY POINT
# ==============================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
