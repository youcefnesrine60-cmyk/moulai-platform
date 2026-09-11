# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# scripts/create_test_tables_sync.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from app.core.config import settings
from app.core.database import Base

# ✅ استيراد جميع النماذج بشكل صريح
from app.models.owner import Owner
from app.models.restaurant import Restaurant
from app.models.restaurant_group import RestaurantGroup, RestaurantBranch
from app.models.restaurant_metric import RestaurantMetric
from app.models.restaurant_order_counter import RestaurantOrderCounter
from app.models.restaurant_payment_setting import RestaurantPaymentSetting
from app.models.admin import Admin
from app.models.admin_log import AdminLog
from app.models.admin_session import AdminSession
from app.models.agent import Agent, Channel, Conversation, Message
from app.models.user import User

# ✅ استخدام engine متزامن (ليس async)
dsn = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://') + "_test"
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

# عرض الجداول
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
    tables = [row[0] for row in result]
    if tables:
        print(f"📋 الجداول المنشأة ({len(tables)}):")
        for table in tables:
            print(f"   - {table}")
    else:
        print("❌ لا توجد جداول في قاعدة البيانات!")