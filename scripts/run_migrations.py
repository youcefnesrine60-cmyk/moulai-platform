# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📋 RUN MIGRATIONS SCRIPT
# سكريبت لتشغيل ترحيلات Alembic بسهولة
# ==============================================

"""Operational maintenance script for run migrations.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import subprocess
import sys
from typing import Optional

# ==============================================
# 📝 LOGGING (مع Fallback)
# ==============================================

try:
    from app.core.logger import logger

    HAS_LOGGER = True
except ImportError:
    HAS_LOGGER = False

    # دوال احتياطية إذا لم يوجد logger
    # ==============================================
    # LOGGER INFO
    # ==============================================

    def logger_info(msg, **kwargs):
        print(f"ℹ️ {msg}")

    # ==============================================
    # LOGGER SUCCESS
    # ==============================================

    def logger_success(msg, **kwargs):
        print(f"✅ {msg}")

    # ==============================================
    # LOGGER ERROR
    # ==============================================

    def logger_error(msg, **kwargs):
        print(f"❌ {msg}")

    # ==============================================
    # LOGGER EXCEPTION
    # ==============================================

    def logger_exception(msg, **kwargs):
        print(f"❌ {msg} - {kwargs.get('extra', {}).get('error', '')}")

    logger = type(
        "Logger",
        (),
        {
            "info": staticmethod(logger_info),
            "exception": staticmethod(logger_exception),
        },
    )()


# ==============================================
# 🚀 FUNCTIONS
# ==============================================


def run_command(command: str, description: str) -> bool:
    """
    تشغيل أمر في الطرفية

    Args:
        command: الأمر المراد تشغيله
        description: وصف الأمر

    Returns:
        bool: True إذا نجح، False إذا فشل
    """
    try:
        logger.info(f"running_{description}", extra={"command": command})
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"{description}_completed_successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.exception(
            f"{description}_failed",
            extra={"error": e.stderr},
        )
        print(f"❌ Error: {e.stderr}")
        return False


# ==============================================
# CREATE MIGRATION
# ==============================================


def create_migration(message: str) -> bool:
    """
    إنشاء ترحيلة جديدة

    Args:
        message: رسالة الترحيل

    Returns:
        bool: True إذا نجح، False إذا فشل
    """
    command = f'alembic revision --autogenerate -m "{message}"'
    return run_command(command, "create_migration")


# ==============================================
# UPGRADE MIGRATION
# ==============================================


def upgrade_migration(revision: Optional[str] = "head") -> bool:
    """
    تطبيق الترحيلات

    Args:
        revision: رقم الإصدار المطلوب (head = الأحدث)

    Returns:
        bool: True إذا نجح، False إذا فشل
    """
    command = f"alembic upgrade {revision}"
    return run_command(command, "upgrade_migration")


# ==============================================
# DOWNGRADE MIGRATION
# ==============================================


def downgrade_migration(revision: str = "-1") -> bool:
    """
    التراجع عن الترحيلات

    Args:
        revision: رقم الإصدار للتراجع إليه

    Returns:
        bool: True إذا نجح، False إذا فشل
    """
    command = f"alembic downgrade {revision}"
    return run_command(command, "downgrade_migration")


# ==============================================
# SHOW CURRENT REVISION
# ==============================================


def show_current_revision() -> bool:
    """
    عرض الإصدار الحالي

    Returns:
        bool: True إذا نجح، False إذا فشل
    """
    command = "alembic current"
    return run_command(command, "show_current_revision")


# ==============================================
# SHOW HISTORY
# ==============================================


def show_history() -> bool:
    """
    عرض تاريخ الترحيلات

    Returns:
        bool: True إذا نجح، False إذا فشل
    """
    command = "alembic history"
    return run_command(command, "show_history")


# ==============================================
# 📋 HELP
# ==============================================


def show_help() -> None:
    """عرض المساعدة"""
    print("""
    📋 استخدامات سكريبت الترحيلات:

    🚀 إنشاء ترحيلة جديدة:
        python scripts/run_migrations.py create "رسالة الترحيل"

    ⬆️ تطبيق الترحيلات:
        python scripts/run_migrations.py upgrade

    ⬇️ التراجع عن آخر ترحيلة:
        python scripts/run_migrations.py downgrade

    ⬇️ التراجع عن عدد محدد من الترحيلات:
        python scripts/run_migrations.py downgrade -3

    📊 عرض الإصدار الحالي:
        python scripts/run_migrations.py current

    📜 عرض تاريخ الترحيلات:
        python scripts/run_migrations.py history
    """)


# ==============================================
# 📋 MAIN
# ==============================================


def main() -> None:
    """الدالة الرئيسية"""
    args = sys.argv[1:]

    if not args:
        show_help()
        return

    command = args[0]

    if command == "create" and len(args) > 1:
        message = " ".join(args[1:])
        create_migration(message)

    elif command == "upgrade":
        revision = args[1] if len(args) > 1 else "head"
        upgrade_migration(revision)

    elif command == "downgrade":
        revision = args[1] if len(args) > 1 else "-1"
        downgrade_migration(revision)

    elif command == "current":
        show_current_revision()

    elif command == "history":
        show_history()

    else:
        print(f"❌ أمر غير معروف: {command}")
        show_help()


if __name__ == "__main__":
    main()
