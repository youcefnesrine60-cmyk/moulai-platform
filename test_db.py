# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - TEST DB
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for test db.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import asyncio
import sys
import selectors
from typing import Any, Dict

from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.db import fetchrow, get_pool, close_db
from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

TestResult = Dict[str, Any]


# ==============================================
# 🧪 TEST SQLALCHEMY CONNECTION
# ==============================================


async def test_sqlalchemy_connection() -> TestResult:
    """
    اختبار اتصال SQLAlchemy بقاعدة البيانات

    Returns:
        نتيجة الاختبار
    """
    result: TestResult = {
        "name": "SQLAlchemy Connection",
        "status": "failed",
        "message": "",
    }

    try:
        async with AsyncSessionLocal() as session:
            # تنفيذ استعلام بسيط
            stmt = text("SELECT 1 as test, NOW() as time, version() as version")
            db_result = await session.execute(stmt)
            row = db_result.first()

            if row:
                result["status"] = "success"
                result["message"] = "Connected successfully"
                result["data"] = {
                    "test": row.test,
                    "time": str(row.time),
                    "version": row.version,
                }

                logger.info(
                    "test_sqlalchemy_connection_success",
                    extra={"result": result},
                )
            else:
                result["message"] = "No data returned from SQLAlchemy"

    except Exception as e:
        result["message"] = str(e)
        logger.exception(
            "test_sqlalchemy_connection_failed",
            extra={"error": str(e)},
        )

    return result


# ==============================================
# 🧪 TEST PSYCOPG3 CONNECTION
# ==============================================


async def test_psycopg3_connection() -> TestResult:
    """
    اختبار اتصال Psycopg3 بقاعدة البيانات

    Returns:
        نتيجة الاختبار
    """
    result: TestResult = {
        "name": "Psycopg3 Connection",
        "status": "failed",
        "message": "",
    }

    try:
        # اختبار fetchrow
        row = await fetchrow("SELECT 1 as test, NOW() as time, version() as version")

        if row:
            result["status"] = "success"
            result["message"] = "Connected successfully"
            result["data"] = {
                "test": row.get("test"),
                "time": str(row.get("time")),
                "version": row.get("version"),
            }

            logger.info(
                "test_psycopg3_connection_success",
                extra={"result": result},
            )
        else:
            result["message"] = "No data returned"

    except Exception as e:
        result["message"] = str(e)
        logger.exception(
            "test_psycopg3_connection_failed",
            extra={"error": str(e)},
        )

    return result


# ==============================================
# 🧪 TEST POOL STATUS
# ==============================================


async def test_pool_status() -> TestResult:
    """
    اختبار حالة تجمع الاتصالات

    Returns:
        نتيجة الاختبار
    """
    result: TestResult = {
        "name": "Pool Status",
        "status": "failed",
        "message": "",
    }

    try:
        pool = await get_pool()

        if pool:
            result["status"] = "success"
            result["message"] = "Pool is active"

            result["data"] = {
                "min_size": getattr(pool, "min_size", "N/A"),
                "max_size": getattr(pool, "max_size", "N/A"),
                "timeout": getattr(pool, "timeout", "N/A"),
            }

            logger.info(
                "test_pool_status_success",
                extra={"result": result},
            )
        else:
            result["message"] = "Pool is None"

    except Exception as e:
        result["message"] = str(e)
        logger.exception(
            "test_pool_status_failed",
            extra={"error": str(e)},
        )

    return result


# ==============================================
# 🧪 TEST DATABASE URL
# ==============================================


async def test_database_url() -> TestResult:
    """
    اختبار صيغة رابط قاعدة البيانات

    Returns:
        نتيجة الاختبار
    """
    result: TestResult = {
        "name": "Database URL",
        "status": "failed",
        "message": "",
    }

    try:
        url = settings.DATABASE_URL
        sync_url = getattr(settings, "DATABASE_SYNC_URL", None)

        result["status"] = "success"
        result["message"] = "URLs are configured"
        result["data"] = {
            "has_async_url": bool(url),
            "has_sync_url": bool(sync_url),
            "async_url_prefix": url.split("://")[0] if url else None,
            "sync_url_prefix": sync_url.split("://")[0] if sync_url else None,
        }

        logger.info(
            "test_database_url_success",
            extra={"result": result},
        )

    except Exception as e:
        result["message"] = str(e)
        logger.exception(
            "test_database_url_failed",
            extra={"error": str(e)},
        )

    return result


# ==============================================
# 🧪 RUN ALL TESTS
# ==============================================


async def run_all_tests() -> None:
    """
    تشغيل جميع الاختبارات وعرض النتائج
    """
    print("\n" + "=" * 60)
    print("🧪 DATABASE CONNECTION TESTS")
    print("=" * 60)

    # 1️⃣ اختبار الرابط
    url_result = await test_database_url()
    print(f"\n📌 {url_result['name']}")
    print(f"   Status: {url_result['status']}")
    print(f"   Message: {url_result['message']}")
    if url_result.get("data"):
        for key, value in url_result["data"].items():
            print(f"   {key}: {value}")

    # 2️⃣ اختبار SQLAlchemy
    sqlalchemy_result = await test_sqlalchemy_connection()
    print(f"\n📌 {sqlalchemy_result['name']}")
    print(f"   Status: {sqlalchemy_result['status']}")
    print(f"   Message: {sqlalchemy_result['message']}")
    if sqlalchemy_result.get("data"):
        print(f"   Data: {sqlalchemy_result['data']}")

    # 3️⃣ اختبار Psycopg3
    psycopg3_result = await test_psycopg3_connection()
    print(f"\n📌 {psycopg3_result['name']}")
    print(f"   Status: {psycopg3_result['status']}")
    print(f"   Message: {psycopg3_result['message']}")
    if psycopg3_result.get("data"):
        print(f"   Data: {psycopg3_result['data']}")

    # 4️⃣ اختبار تجمع الاتصالات
    pool_result = await test_pool_status()
    print(f"\n📌 {pool_result['name']}")
    print(f"   Status: {pool_result['status']}")
    print(f"   Message: {pool_result['message']}")
    if pool_result.get("data"):
        for key, value in pool_result["data"].items():
            print(f"   {key}: {value}")

    print("\n" + "=" * 60)

    # التحقق من النجاح الكلي
    all_success = all(
        [
            url_result["status"] == "success",
            sqlalchemy_result["status"] == "success",
            psycopg3_result["status"] == "success",
            pool_result["status"] == "success",
        ]
    )

    if all_success:
        print("✅ ALL TESTS PASSED! Database is working correctly.")
    else:
        print("❌ SOME TESTS FAILED. Please check the errors above.")

    print("=" * 60 + "\n")


# ==============================================
# 🚀 MAIN
# ==============================================


async def main() -> None:
    """
    النقطة الرئيسية لتشغيل الاختبارات
    """
    try:
        await run_all_tests()
    except Exception as e:
        logger.exception(
            "test_main_failed",
            extra={"error": str(e)},
        )
        print(f"\n❌ Test execution failed: {e}")
    finally:
        # إغلاق اتصالات كلا التجمعين
        try:
            await close_db()
        except Exception:
            pass

        try:
            await engine.dispose()
        except Exception:
            pass


# ==============================================
# 🏁 ENTRY POINT
# ==============================================

if __name__ == "__main__":
    # دعم Windows
    if sys.platform == "win32":
        asyncio.run(
            main(),
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    else:
        asyncio.run(main())  # الدالة الرئيسية لتشغيل الكود غير المتزامن
