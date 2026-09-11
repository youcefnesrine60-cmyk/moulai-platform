# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# scripts/check_test_db.py

import sys
from pathlib import Path

# إضافة مسار المشروع
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import asyncpg
from app.core.config import settings

async def check_test_db():
    """التحقق من وجود قاعدة البيانات الاختبارية."""
    
    # إزالة +asyncpg من الرابط
    dsn = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    
    print(f"📡 الاتصال بقاعدة البيانات الرئيسية...")
    
    try:
        # محاولة الاتصال بقاعدة البيانات الرئيسية
        conn = await asyncpg.connect(dsn)
        print('✅ الاتصال بقاعدة البيانات الرئيسية ناجح')
        
        # التحقق من وجود قاعدة البيانات الاختبارية
        result = await conn.fetch("SELECT 1 FROM pg_database WHERE datname = 'neondb_test'")
        
        if result:
            print('✅ قاعدة البيانات neondb_test موجودة')
        else:
            print('❌ قاعدة البيانات neondb_test غير موجودة')
            
            # محاولة إنشاء قاعدة البيانات
            try:
                await conn.execute('CREATE DATABASE neondb_test')
                print('✅ تم إنشاء قاعدة البيانات neondb_test بنجاح')
            except Exception as e:
                print(f'❌ فشل إنشاء قاعدة البيانات: {e}')
        
        await conn.close()
        
    except Exception as e:
        print(f'❌ خطأ: {e}')
        print('💡 تأكد من أن قاعدة البيانات الرئيسية موجودة وأن الرابط صحيح')

if __name__ == '__main__':
    asyncio.run(check_test_db())