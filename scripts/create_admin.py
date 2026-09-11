# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 👑 CREATE INITIAL ADMIN
# ==============================================

import asyncio
import os
import sys

# إضافة مسار المشروع إلى sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import init_db, execute, fetchrow
from app.core.logger import logger


async def create_admin():
    """
    إنشاء المسؤول الأولي في قاعدة البيانات
    """
    await init_db()

    # ==========================================
    # 🔍 التحقق من وجود المسؤول
    # ==========================================

    existing = await fetchrow(
        """
        SELECT id, chat_id, username
        FROM admins
        WHERE username = 'admin'
        LIMIT 1
        """
    )

    if existing:
        logger.info(
            "admin_already_exists",
            extra={
                "admin_id": existing["id"],
                "chat_id": existing["chat_id"],
                "username": existing["username"],
            },
        )
        return

    # ==========================================
    # ➕ إنشاء المسؤول
    # ==========================================

    chat_id = int(input("أدخل رقم المحادثة الخاص بك في Telegram: "))

    await execute(
        """
        INSERT INTO admins (
            chat_id,
            username,
            full_name,
            role,
            is_active
        )
        VALUES (
            %s,
            'admin',
            'مدير النظام',
            'super_admin',
            TRUE
        )
        """,
        chat_id,
    )

    logger.info(
        "admin_created_successfully",
        extra={
            "chat_id": chat_id,
            "username": "admin",
        },
    )

    # ==========================================
    # ✅ عرض المسؤول المنشأ
    # ==========================================

    admin = await fetchrow(
        """
        SELECT id, chat_id, username, full_name, role, created_at
        FROM admins
        WHERE chat_id = %s
        """,
        chat_id,
    )

    print("\n✅ تم إنشاء المسؤول بنجاح!")
    print(f"🆔 معرف المسؤول: {admin['id']}")
    print(f"💬 معرف المحادثة: {admin['chat_id']}")
    print(f"👤 اسم المستخدم: {admin['username']}")
    print(f"📛 الاسم الكامل: {admin['full_name']}")
    print(f"🔑 الدور: {admin['role']}")


if __name__ == "__main__":
    asyncio.run(create_admin())