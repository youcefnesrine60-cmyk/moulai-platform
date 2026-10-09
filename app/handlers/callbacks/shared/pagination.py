# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / SHARED / PAGINATION
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for pagination.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger

# ==============================================
# 📄 PAGINATION HELPER
# ==============================================


async def paginate(
    *,
    items: list,
    page: int = 0,
    page_size: int = 5,
) -> dict:
    """
    تقسيم القائمة إلى صفحات

    Args:
        items: القائمة الكاملة
        page: رقم الصفحة الحالية (تبدأ من 0)
        page_size: عدد العناصر في كل صفحة

    Returns:
        dict: {
            "items": قائمة العناصر في الصفحة الحالية,
            "total": إجمالي عدد العناصر,
            "page": رقم الصفحة الحالية,
            "total_pages": إجمالي عدد الصفحات,
            "has_next": هل توجد صفحة تالية,
            "has_prev": هل توجد صفحة سابقة,
        }
    """
    total = len(items)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    # التأكد من أن الصفحة ضمن النطاق
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    start = page * page_size
    end = min(start + page_size, total)

    page_items = items[start:end] if total > 0 else []

    logger.debug(
        "pagination_calculated",
        extra={
            "page": page,
            "total_pages": total_pages,
            "start": start,
            "end": end,
            "items_count": len(page_items),
        },
    )

    return {
        "items": page_items,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "has_next": page < total_pages - 1,
        "has_prev": page > 0,
    }


# ==============================================
# 📄 FORMAT PAGINATION TEXT
# ==============================================


async def format_pagination_text(
    *,
    page: int,
    total_pages: int,
    total_items: int,
) -> str:
    """
    تنسيق نص معلومات الصفحة

    Args:
        page: رقم الصفحة الحالية
        total_pages: إجمالي عدد الصفحات
        total_items: إجمالي عدد العناصر

    Returns:
        str: نص معلومات الصفحة
    """
    return f"\n\n📊 الصفحة {page + 1} من {total_pages} " f"(إجمالي {total_items} عنصر)"
