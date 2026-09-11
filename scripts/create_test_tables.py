# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# scripts/create_test_tables.py

import sys
from pathlib import Path

# إضافة مسار المشروع
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

# ✅ استيراد Base من النماذج
from app.models.base import Base

async def create_tables():
    """إنشاء جميع الجداول في قاعدة البيانات الاختبارية."""
    
    print("=" * 60)
    print("📋 إنشاء الجداول في قاعدة البيانات الاختبارية")
    print("=" * 60)
    
    # ✅ استيراد جميع النماذج لضمان تسجيلها في Base.metadata
    import app.models
    
    # عرض النماذج المسجلة
    print(f"\n📊 عدد النماذج المسجلة: {len(Base.metadata.tables)}")
    if Base.metadata.tables:
        print("📋 النماذج المسجلة:")
        for table in Base.metadata.tables.values():
            print(f"   - {table.name}")
    else:
        print("❌ لا توجد نماذج مسجلة!")
        return
    
    print("\n" + "=" * 60)
    print("🔄 إنشاء الجداول...")
    print("=" * 60)
    
    engine = create_async_engine(settings.DATABASE_URL + "_test")
    
    try:
        async with engine.begin() as conn:
            # ✅ حذف الجداول أولاً (للتأكد من بيئة نظيفة)
            await conn.run_sync(Base.metadata.drop_all)
            # ✅ إنشاء جميع الجداول
            await conn.run_sync(Base.metadata.create_all)
        
        print("\n✅ تم إنشاء جميع الجداول في قاعدة البيانات الاختبارية")
        
        # عرض الجداول التي تم إنشاؤها
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
            tables = [row[0] for row in result]
            if tables:
                print(f"\n📋 الجداول المنشأة ({len(tables)}):")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("\n❌ لا توجد جداول في قاعدة البيانات!")
                
    except Exception as e:
        print(f"\n❌ خطأ أثناء إنشاء الجداول: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_tables())