# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 RESTAURANT METRICS EVENT HANDLERS
# معالجات أحداث مقاييس المطعم
# ==============================================

"""MoulAI operational module for handlers.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.services.business.restaurant.metrics.service import RestaurantMetricsService

# ==============================================
# 📊 METRICS EVENT HANDLERS
# ==============================================


class MetricsEventHandlers:
    """
    معالجات أحداث مقاييس المطعم.

    تتعامل مع تحديث المقاييس عند حدوث أحداث:
        - إنشاء/حذف منتج
        - إنشاء/حذف تصنيف
        - تسجيل طلب

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        service: خدمة مقاييس المطعم
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة معالجات الأحداث.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.service = RestaurantMetricsService(session)

    # ==========================================
    # 📦 PRODUCT EVENTS
    # ==========================================

    # ==============================================
    # ON PRODUCT CREATED
    # ==============================================

    async def on_product_created(
        self,
        *,
        restaurant_id: int,
        amount: int = 1,
    ) -> None:
        """
        معالج حدث إنشاء منتج جديد.

        Args:
            restaurant_id: معرف المطعم
            amount: عدد المنتجات المضافة

        Raises:
            NotFoundError: إذا لم يتم العثور على المقاييس
            ValidationError: إذا كان العدد غير صالح
        """
        if amount <= 0:
            raise ValidationError(
                message="العدد يجب أن يكون أكبر من الصفر",
            )

        logger.info(
            "metrics_handler_product_created",
            extra={
                "restaurant_id": restaurant_id,
                "amount": amount,
            },
        )

        metrics = await self.service.repo.increment_products_count(
            restaurant_id=restaurant_id,
            amount=amount,
        )

        if not metrics:
            raise NotFoundError(
                message=f"مقاييس المطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        logger.info(
            "metrics_product_created_updated",
            extra={
                "restaurant_id": restaurant_id,
                "products_count": metrics.products_count,
            },
        )

    # ==============================================
    # ON PRODUCT DELETED
    # ==============================================

    async def on_product_deleted(
        self,
        *,
        restaurant_id: int,
        amount: int = 1,
    ) -> None:
        """
        معالج حدث حذف منتج.

        Args:
            restaurant_id: معرف المطعم
            amount: عدد المنتجات المحذوفة

        Raises:
            NotFoundError: إذا لم يتم العثور على المقاييس
            ValidationError: إذا كان العدد غير صالح
        """
        if amount <= 0:
            raise ValidationError(
                message="العدد يجب أن يكون أكبر من الصفر",
            )

        logger.info(
            "metrics_handler_product_deleted",
            extra={
                "restaurant_id": restaurant_id,
                "amount": amount,
            },
        )

        metrics = await self.service.repo.decrement_products_count(
            restaurant_id=restaurant_id,
            amount=amount,
        )

        if not metrics:
            raise NotFoundError(
                message=f"مقاييس المطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        logger.info(
            "metrics_product_deleted_updated",
            extra={
                "restaurant_id": restaurant_id,
                "products_count": metrics.products_count,
            },
        )

    # ==========================================
    # 📂 CATEGORY EVENTS
    # ==========================================

    # ==============================================
    # ON CATEGORY CREATED
    # ==============================================

    async def on_category_created(
        self,
        *,
        restaurant_id: int,
        amount: int = 1,
    ) -> None:
        """
        معالج حدث إنشاء تصنيف جديد.

        Args:
            restaurant_id: معرف المطعم
            amount: عدد التصنيفات المضافة

        Raises:
            NotFoundError: إذا لم يتم العثور على المقاييس
            ValidationError: إذا كان العدد غير صالح
        """
        if amount <= 0:
            raise ValidationError(
                message="العدد يجب أن يكون أكبر من الصفر",
            )

        logger.info(
            "metrics_handler_category_created",
            extra={
                "restaurant_id": restaurant_id,
                "amount": amount,
            },
        )

        metrics = await self.service.repo.increment_categories_count(
            restaurant_id=restaurant_id,
            amount=amount,
        )

        if not metrics:
            raise NotFoundError(
                message=f"مقاييس المطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        logger.info(
            "metrics_category_created_updated",
            extra={
                "restaurant_id": restaurant_id,
                "categories_count": metrics.categories_count,
            },
        )

    # ==============================================
    # ON CATEGORY DELETED
    # ==============================================

    async def on_category_deleted(
        self,
        *,
        restaurant_id: int,
        amount: int = 1,
    ) -> None:
        """
        معالج حدث حذف تصنيف.

        Args:
            restaurant_id: معرف المطعم
            amount: عدد التصنيفات المحذوفة

        Raises:
            NotFoundError: إذا لم يتم العثور على المقاييس
            ValidationError: إذا كان العدد غير صالح
        """
        if amount <= 0:
            raise ValidationError(
                message="العدد يجب أن يكون أكبر من الصفر",
            )

        logger.info(
            "metrics_handler_category_deleted",
            extra={
                "restaurant_id": restaurant_id,
                "amount": amount,
            },
        )

        metrics = await self.service.repo.decrement_categories_count(
            restaurant_id=restaurant_id,
            amount=amount,
        )

        if not metrics:
            raise NotFoundError(
                message=f"مقاييس المطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        logger.info(
            "metrics_category_deleted_updated",
            extra={
                "restaurant_id": restaurant_id,
                "categories_count": metrics.categories_count,
            },
        )

    # ==========================================
    # 📦 ORDER EVENTS
    # ==========================================

    # ==============================================
    # ON ORDER REGISTERED
    # ==============================================

    async def on_order_registered(
        self,
        *,
        restaurant_id: int,
        order_total: float,
    ) -> None:
        """
        معالج حدث تسجيل طلب جديد.

        Args:
            restaurant_id: معرف المطعم
            order_total: إجمالي قيمة الطلب

        Raises:
            NotFoundError: إذا لم يتم العثور على المقاييس
            ValidationError: إذا كانت قيمة الطلب غير صالحة
        """
        if order_total <= 0:
            raise ValidationError(
                message="قيمة الطلب يجب أن تكون أكبر من الصفر",
            )

        logger.info(
            "metrics_handler_order_registered",
            extra={
                "restaurant_id": restaurant_id,
                "order_total": order_total,
            },
        )

        metrics = await self.service.repo.register_order(
            restaurant_id=restaurant_id,
            order_total=order_total,
        )

        if not metrics:
            raise NotFoundError(
                message=f"مقاييس المطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        logger.info(
            "metrics_order_registered_updated",
            extra={
                "restaurant_id": restaurant_id,
                "monthly_orders": metrics.monthly_orders,
                "average_order_value": metrics.average_order_value,
            },
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "MetricsEventHandlers",
]
