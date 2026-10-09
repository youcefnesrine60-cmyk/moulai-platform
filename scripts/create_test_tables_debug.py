# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MAINTENANCE SCRIPT - SCRIPTS / CREATE TEST TABLES DEBUG
# Operational maintenance utility for the MoulAI platform.
# ==============================================

"""Operational maintenance script for create test tables debug.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# scripts/create_test_tables_debug.py

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base

# ==============================================
# CREATE TABLES
# ==============================================


async def create_tables():
    # Register every ORM model before reading or creating Base.metadata tables.
    import app.models  # noqa: F401

    # ✅ عرض النماذج المسجلة قبل الإنشاء
    print("=" * 50)
    print("📋 النماذج المسجلة قبل الإنشاء:")
    for table in Base.metadata.tables.values():
        print(f"   - {table.name}")
    print("=" * 50)

    engine = create_async_engine(settings.DATABASE_URL + "_test")

    async with engine.begin() as conn:
        # ✅ حذف الجداول أولاً
        await conn.run_sync(Base.metadata.drop_all)
        # ✅ إنشاء جميع الجداول
        await conn.run_sync(Base.metadata.create_all)

    print("✅ تم إنشاء جميع الجداول في قاعدة البيانات الاختبارية")

    # عرض الجداول التي تم إنشاؤها
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        tables = [row[0] for row in result]
        if tables:
            print(f"📋 الجداول المنشأة ({len(tables)}):")
            for table in tables:
                print(f"   - {table}")
        else:
            print("❌ لا توجد جداول في قاعدة البيانات!")


if __name__ == "__main__":
    asyncio.run(create_tables())
