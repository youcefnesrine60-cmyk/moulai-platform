# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🔄 RESTAURANT METRICS COMPATIBILITY
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.services.business.restaurant.metrics.service import (
    RestaurantMetricsService,
    MetricsDict,
)
from app.services.business.restaurant.metrics.handlers import MetricsEventHandlers


# ==============================================
# 📊 COMPATIBILITY FUNCTIONS
# ==============================================

# ==============================================
# INITIALIZE METRICS
# ==============================================

async def initialize_metrics(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    تهيئة مقاييس مطعم جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    service = RestaurantMetricsService(session=session)
    await service.initialize_metrics(restaurant_id=restaurant_id)

    logger.info("metrics_initialized", extra={"restaurant_id": restaurant_id})


# ==============================================
# PRODUCT CREATED
# ==============================================

async def product_created(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    تحديث المقاييس عند إنشاء منتج جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    handlers = MetricsEventHandlers(session=session)
    await handlers.on_product_created(restaurant_id=restaurant_id)

    logger.info("metrics_product_created", extra={"restaurant_id": restaurant_id})


# ==============================================
# PRODUCT DELETED
# ==============================================

async def product_deleted(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    تحديث المقاييس عند حذف منتج (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    handlers = MetricsEventHandlers(session=session)
    await handlers.on_product_deleted(restaurant_id=restaurant_id)

    logger.info("metrics_product_deleted", extra={"restaurant_id": restaurant_id})


# ==============================================
# CATEGORY CREATED
# ==============================================

async def category_created(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    تحديث المقاييس عند إنشاء تصنيف جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    handlers = MetricsEventHandlers(session=session)
    await handlers.on_category_created(restaurant_id=restaurant_id)

    logger.info("metrics_category_created", extra={"restaurant_id": restaurant_id})


# ==============================================
# CATEGORY DELETED
# ==============================================

async def category_deleted(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    تحديث المقاييس عند حذف تصنيف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    handlers = MetricsEventHandlers(session=session)
    await handlers.on_category_deleted(restaurant_id=restaurant_id)

    logger.info("metrics_category_deleted", extra={"restaurant_id": restaurant_id})


# ==============================================
# ORDER REGISTERED
# ==============================================

async def order_registered(
    *,
    restaurant_id: int,
    order_total: float,
    session: AsyncSession,
) -> None:
    """
    تحديث المقاييس عند تسجيل طلب جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        order_total: إجمالي قيمة الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    handlers = MetricsEventHandlers(session=session)
    await handlers.on_order_registered(
        restaurant_id=restaurant_id,
        order_total=order_total,
    )

    logger.info(
        "metrics_order_registered",
        extra={
            "restaurant_id": restaurant_id,
            "order_total": order_total,
        },
    )


# ==============================================
# GET METRICS
# ==============================================

async def get_metrics(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Optional[MetricsDict]:
    """
    الحصول على مقاييس مطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[MetricsDict]: قاموس مقاييس المطعم أو None
    """
    service = RestaurantMetricsService(session=session)
    return await service.get_metrics_dict(restaurant_id=restaurant_id)


# ==============================================
# GET METRICS SUMMARY
# ==============================================

async def get_metrics_summary(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Optional[MetricsDict]:
    """
    الحصول على ملخص مقاييس المطعم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[MetricsDict]: قاموس ملخص المقاييس أو None
    """
    service = RestaurantMetricsService(session=session)

    try:
        summary = await service.get_metrics_summary(restaurant_id=restaurant_id)
        return summary.model_dump()
    except Exception:
        return None


# ==============================================
# RESET METRICS
# ==============================================

async def reset_metrics(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    إعادة تعيين مقاييس المطعم إلى الصفر (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    service = RestaurantMetricsService(session=session)
    await service.reset_metrics(restaurant_id=restaurant_id)

    logger.info("metrics_reset", extra={"restaurant_id": restaurant_id})


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "initialize_metrics",
    "product_created",
    "product_deleted",
    "category_created",
    "category_deleted",
    "order_registered",
    "get_metrics",
    "get_metrics_summary",
    "reset_metrics",
]