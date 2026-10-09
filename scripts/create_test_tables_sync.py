# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MAINTENANCE SCRIPT - SCRIPTS / CREATE TEST TABLES SYNC
# Operational maintenance utility for the MoulAI platform.
# ==============================================

"""Operational maintenance script for create test tables sync.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# scripts/create_test_tables_sync.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import (
    create_engine,
    text,
)

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401  # Register every ORM model in Base.metadata.

# ✅ استخدام engine متزامن (ليس async)
dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://") + "_test"
engine = create_engine(dsn)

print("=" * 50)
print("📋 النماذج المسجلة:")
for table in Base.metadata.tables.values():
    print(f"   - {table.name}")
print("=" * 50)

# ✅ إنشاء الجداول باستخدام sync engine
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

print("✅ تم إنشاء جميع الجداول في قاعدة البيانات الاختبارية")

with engine.connect() as conn:
    result = conn.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    tables = [row[0] for row in result]
    if tables:
        print(f"📋 الجداول المنشأة ({len(tables)}):")
        for table in tables:
            print(f"   - {table}")
    else:
        print("❌ لا توجد جداول في قاعدة البيانات!")
