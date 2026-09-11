# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🗑️ CLEAR TEST DATABASE
# حذف جميع البيانات من قاعدة البيانات الاختبارية
# ==============================================

import sys
from pathlib import Path

# إضافة مسار المشروع
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings


async def clear_test_data():
    """
    حذف جميع البيانات من قاعدة البيانات الاختبارية.
    """
    print("=" * 60)
    print("🗑️  حذف البيانات من قاعدة البيانات الاختبارية")
    print("=" * 60)

    engine = create_async_engine(settings.DATABASE_URL + "_test")

    try:
        async with engine.begin() as conn:
            # قائمة الجداول المراد تفريغها (بترتيب عكسي حسب العلاقات)
            tables = [
                "restaurant_branches",
                "restaurant_groups",
                "restaurants",
                "owners",
                "admin_logs",
                "admin_sessions",
                "admins",
                "agents",
                "categories",
                "products",
                "orders",
                "order_items",
                "payments",
                "subscriptions",
                "subscription_plans",
            ]

            for table in tables:
                try:
                    await conn.execute(
                        text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;')
                    )
                    print(f"   ✅ حذف البيانات من: {table}")
                except Exception as e:
                    print(f"   ⚠️  جدول {table} غير موجود أو حدث خطأ: {e}")

        print("\n✅ تم حذف جميع البيانات بنجاح!")

    except Exception as e:
        print(f"\n❌ خطأ أثناء حذف البيانات: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(clear_test_data())