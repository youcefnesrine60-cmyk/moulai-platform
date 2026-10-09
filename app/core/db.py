# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🐘 PostgreSQL - Psycopg3 (Async)
# Production Ready
# ==============================================

"""MoulAI operational module for db.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.logger import logger

# ==============================================
# 🌍 LOAD ENVIRONMENT VARIABLES
# ==============================================

load_dotenv()

# ==============================================
# 🌍 DATABASE URL
# ==============================================

DATABASE_URL: str = os.getenv("DATABASE_SYNC_URL", "")

# ==============================================
# 🧩 TYPES
# ==============================================

DatabasePool = AsyncConnectionPool
RowType = Dict[str, Any]
RowsType = List[RowType]

# ==============================================
# 🔌 GLOBAL POOL
# ==============================================

db_pool: Optional[DatabasePool] = None

# ==============================================
# 🚀 INITIALIZE DATABASE POOL
# ==============================================


async def init_db() -> None:
    """
    تهيئة تجمع اتصالات قاعدة البيانات
    """
    global db_pool

    if db_pool is not None:
        return

    try:
        db_pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            min_size=2,
            max_size=10,
            timeout=120,
            kwargs={
                "row_factory": dict_row,
                "connect_timeout": 30,
                "keepalives": 1,
                "keepalives_idle": 10,
                "keepalives_interval": 5,
                "keepalives_count": 5,
            },
        )

        await db_pool.open()

        logger.info("postgresql_pool_initialized")

    except Exception as e:
        logger.exception(
            "postgresql_pool_init_failed",
            extra={"error": str(e)},
        )
        raise


# ==============================================
# 📥 GET POOL
# ==============================================


async def get_pool() -> DatabasePool:
    """
    الحصول على تجمع الاتصالات

    Returns:
        DatabasePool: تجمع الاتصالات
    """
    global db_pool

    if db_pool is None:
        await init_db()

    return db_pool


# ==============================================
# 📥 FETCH ONE
# ==============================================


async def fetchrow(
    query: str,
    *args: Any,
    retries: int = 3,
) -> Optional[RowType]:
    """
    تنفيذ استعلام وإعادة صف واحد مع إعادة المحاولة

    Args:
        query: استعلام SQL
        *args: معاملات الاستعلام
        retries: عدد محاولات إعادة المحاولة

    Returns:
        الصف المسترجع أو None
    """
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            pool = await get_pool()

            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, args)
                    return await cur.fetchone()

        except Exception as e:
            last_error = e
            logger.warning(
                f"fetchrow_attempt_{attempt + 1}_failed",
                extra={
                    "error": str(e),
                    "attempt": attempt + 1,
                    "query": query[:100],
                },
            )

            if attempt < retries - 1:
                wait_time = 2**attempt
                await asyncio.sleep(wait_time)

    logger.error(
        "fetchrow_all_attempts_failed",
        extra={
            "query": query[:100],
            "retries": retries,
            "last_error": str(last_error),
        },
    )
    raise last_error  # type: ignore


# ==============================================
# 📥 FETCH MANY
# ==============================================


async def fetch(
    query: str,
    *args: Any,
    retries: int = 3,
) -> RowsType:
    """
    تنفيذ استعلام وإعادة عدة صفوف مع إعادة المحاولة

    Args:
        query: استعلام SQL
        *args: معاملات الاستعلام
        retries: عدد محاولات إعادة المحاولة

    Returns:
        قائمة الصفوف المسترجعة
    """
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            pool = await get_pool()

            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, args)
                    return await cur.fetchall()

        except Exception as e:
            last_error = e
            logger.warning(
                f"fetch_attempt_{attempt + 1}_failed",
                extra={
                    "error": str(e),
                    "attempt": attempt + 1,
                    "query": query[:100],
                },
            )

            if attempt < retries - 1:
                wait_time = 2**attempt
                await asyncio.sleep(wait_time)

    logger.error(
        "fetch_all_attempts_failed",
        extra={
            "query": query[:100],
            "retries": retries,
            "last_error": str(last_error),
        },
    )
    raise last_error  # type: ignore


# ==============================================
# ✏️ EXECUTE
# ==============================================


async def execute(
    query: str,
    *args: Any,
    retries: int = 3,
) -> Optional[str]:
    """
    تنفيذ استعلام SQL مع إعادة المحاولة

    Args:
        query: استعلام SQL
        *args: معاملات الاستعلام
        retries: عدد محاولات إعادة المحاولة

    Returns:
        رسالة حالة التنفيذ
    """
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            pool = await get_pool()

            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, args)
                    return cur.statusmessage

        except Exception as e:
            last_error = e
            logger.warning(
                f"execute_attempt_{attempt + 1}_failed",
                extra={
                    "error": str(e),
                    "attempt": attempt + 1,
                    "query": query[:100],
                },
            )

            if attempt < retries - 1:
                wait_time = 2**attempt
                await asyncio.sleep(wait_time)

    logger.error(
        "execute_all_attempts_failed",
        extra={
            "query": query[:100],
            "retries": retries,
            "last_error": str(last_error),
        },
    )
    raise last_error  # type: ignore


# ==============================================
# ➕ INSERT RETURNING ID
# ==============================================


async def insert_returning_id(
    query: str,
    *args: Any,
    retries: int = 3,
) -> int:
    """
    إدراج صف وإرجاع المعرف مع إعادة المحاولة

    Args:
        query: استعلام SQL (يجب أن يحتوي على RETURNING id)
        *args: معاملات الاستعلام
        retries: عدد محاولات إعادة المحاولة

    Returns:
        المعرف المُدرج
    """
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            pool = await get_pool()

            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, args)
                    value = await cur.fetchone()
                    return int(value[0])  # type: ignore

        except Exception as e:
            last_error = e
            logger.warning(
                f"insert_returning_id_attempt_{attempt + 1}_failed",
                extra={
                    "error": str(e),
                    "attempt": attempt + 1,
                    "query": query[:100],
                },
            )

            if attempt < retries - 1:
                wait_time = 2**attempt
                await asyncio.sleep(wait_time)

    logger.error(
        "insert_returning_id_all_attempts_failed",
        extra={
            "query": query[:100],
            "retries": retries,
            "last_error": str(last_error),
        },
    )
    raise last_error  # type: ignore


# ==============================================
# 🔄 TRANSACTION CONTEXT
# ==============================================


@asynccontextmanager
async def transaction():
    """
    سياق تنفيذ المعاملات (Transaction)

    Yields:
        AsyncConnection: اتصال قاعدة البيانات
    """
    pool = await get_pool()

    async with pool.connection() as conn:
        async with conn.transaction():
            yield conn


# ==============================================
# 🔒 CLOSE DATABASE POOL
# ==============================================


async def close_db() -> None:
    """
    إغلاق تجمع اتصالات قاعدة البيانات
    """
    global db_pool

    if db_pool is None:
        return

    await db_pool.close()
    db_pool = None

    logger.info("postgresql_pool_closed")
