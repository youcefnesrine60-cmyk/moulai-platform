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

from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logger import logger

# ==============================================
# 🌍 LOAD ENVIRONMENT VARIABLES
# ==============================================

load_dotenv()

# ==============================================
# ✅ استيراد Base من النماذج (مصدر واحد فقط)
# ==============================================

from app.models.base import Base


# ==============================================
# 🚀 CREATE ENGINE
# ==============================================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_recycle=settings.DB_POOL_RECYCLE,
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
# 📥 GET ASYNC SESSION
# ==============================================

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    الحصول على جلسة قاعدة البيانات (مولد غير متزامن).
    
    تستخدم في Dependency Injection مع FastAPI.
    
    Yields:
        AsyncSession: جلسة قاعدة البيانات
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.exception(
                "get_async_session_error",
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

async def init_db() -> None:
    """
    تهيئة قاعدة البيانات وإنشاء الجداول
    
    يتم استدعاؤها عند بدء التشغيل
    """
    try:
        # ✅ استيراد جميع النماذج لضمان تسجيلها في Base.metadata
        import app.models

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info(
            "database_initialized_successfully",
            extra={
                "environment": settings.APP_ENV,
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
        import app.models

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
            await conn.execute("SELECT 1")
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
    "get_async_session",
    "get_session",
    "init_db",
    "drop_db",
    "close_db",
    "check_db_connection",
]