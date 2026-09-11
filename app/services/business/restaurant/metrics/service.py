# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 📊 RESTAURANT METRICS SERVICE
# منطق الأعمال لمقاييس المطعم
# ==============================================

from typing import (
    Any,
    Dict,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.repositories.restaurant.restaurant_metrics_repo import RestaurantMetricsRepository
from app.schemas.restaurant.restaurant_metric import (
    RestaurantMetricResponse,
    RestaurantMetricUpdate,
    RestaurantMetricSummary,
)


# ==============================================
# 🧩 TYPES
# ==============================================

MetricsDict = Dict[str, Any]


# ==============================================
# 📊 RESTAURANT METRICS SERVICE
# ==============================================

class RestaurantMetricsService:
    """
    خدمة مقاييس المطعم - تدير منطق الأعمال لمقاييس المطاعم.
    
    مسؤولة عن:
        - تهيئة مقاييس المطعم الجديد
        - جلب المقاييس
        - تحديث المقاييس
        - إعادة تعيين المقاييس
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع مقاييس المطعم
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة مقاييس المطعم.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = RestaurantMetricsRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET METRICS
    # ==============================================

    async def get_metrics(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantMetricResponse:
        """
        الحصول على مقاييس مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            RestaurantMetricResponse: بيانات المقاييس
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المقاييس
        """
        logger.info(
            "metrics_service_get_metrics",
            extra={"restaurant_id": restaurant_id},
        )

        metrics = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not metrics:
            raise NotFoundError(
                message=f"مقاييس المطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        return RestaurantMetricResponse.model_validate(metrics)

    # ==============================================
    # GET METRICS DICT
    # ==============================================

    async def get_metrics_dict(
        self,
        *,
        restaurant_id: int,
    ) -> Optional[MetricsDict]:
        """
        الحصول على مقاييس مطعم معين كقاموس.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            Optional[MetricsDict]: قاموس مقاييس المطعم أو None
        """
        logger.info(
            "metrics_service_get_metrics_dict",
            extra={"restaurant_id": restaurant_id},
        )

        metrics = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not metrics:
            return None

        return {
            "restaurant_id": metrics.restaurant_id,
            "products_count": metrics.products_count,
            "categories_count": metrics.categories_count,
            "monthly_orders": metrics.monthly_orders,
            "average_order_value": metrics.average_order_value,
            "created_at": metrics.created_at,
            "updated_at": metrics.updated_at,
        }

    # ==============================================
    # GET METRICS SUMMARY
    # ==============================================

    async def get_metrics_summary(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantMetricSummary:
        """
        الحصول على ملخص مقاييس المطعم.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            RestaurantMetricSummary: ملخص المقاييس
        """
        logger.info(
            "metrics_service_get_metrics_summary",
            extra={"restaurant_id": restaurant_id},
        )

        metrics = await self.get_metrics(
            restaurant_id=restaurant_id,
        )

        return RestaurantMetricSummary(
            restaurant_id=metrics.restaurant_id,
            products_count=metrics.products_count,
            categories_count=metrics.categories_count,
            monthly_orders=metrics.monthly_orders,
            average_order_value=metrics.average_order_value,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # INITIALIZE METRICS
    # ==============================================

    async def initialize_metrics(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantMetricResponse:
        """
        تهيئة مقاييس مطعم جديد.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            RestaurantMetricResponse: بيانات المقاييس المنشأة
            
        Raises:
            ValidationError: إذا كانت المقاييس موجودة مسبقاً
        """
        logger.info(
            "metrics_service_initialize",
            extra={"restaurant_id": restaurant_id},
        )

        existing = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if existing:
            raise ValidationError(
                message=f"مقاييس المطعم بـ ID '{restaurant_id}' موجودة مسبقاً",
            )

        metrics = await self.repo.create_default(
            restaurant_id=restaurant_id,
        )

        logger.info(
            "metrics_initialized_successfully",
            extra={"restaurant_id": restaurant_id},
        )

        return RestaurantMetricResponse.model_validate(metrics)

    # ==============================================
    # UPDATE METRICS
    # ==============================================

    async def update_metrics(
        self,
        *,
        restaurant_id: int,
        update_data: RestaurantMetricUpdate,
    ) -> RestaurantMetricResponse:
        """
        تحديث مقاييس المطعم.
        
        Args:
            restaurant_id: معرف المطعم
            update_data: بيانات التحديث
            
        Returns:
            RestaurantMetricResponse: بيانات المقاييس المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المقاييس
            ValidationError: إذا كانت البيانات غير صالحة
        """
        logger.info(
            "metrics_service_update",
            extra={
                "restaurant_id": restaurant_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        metrics = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not metrics:
            raise NotFoundError(
                message=f"مقاييس المطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        updates = update_data.model_dump(exclude_unset=True)

        # التحقق من صحة القيم
        self._validate_metrics_values(updates)

        updated = await self.repo.update(
            id=metrics.restaurant_id,
            data=updates,
        )

        if not updated:
            raise NotFoundError(
                message=f"مقاييس المطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        logger.info(
            "metrics_updated_successfully",
            extra={
                "restaurant_id": restaurant_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return RestaurantMetricResponse.model_validate(updated)

    # ==============================================
    # RESET METRICS
    # ==============================================

    async def reset_metrics(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantMetricResponse:
        """
        إعادة تعيين مقاييس المطعم إلى الصفر.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            RestaurantMetricResponse: بيانات المقاييس المعاد تعيينها
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المقاييس
        """
        logger.info(
            "metrics_service_reset",
            extra={"restaurant_id": restaurant_id},
        )

        return await self.update_metrics(
            restaurant_id=restaurant_id,
            update_data=RestaurantMetricUpdate(
                products_count=0,
                categories_count=0,
                monthly_orders=0,
                average_order_value=0,
            ),
        )

    # ==========================================
    # 🔒 PRIVATE METHODS
    # ==========================================

    # ==============================================
    # VALIDATE METRICS VALUES
    # ==============================================

    def _validate_metrics_values(
        self,
        updates: Dict[str, Any],
    ) -> None:
        """
        التحقق من صحة قيم المقاييس.
        
        Args:
            updates: قاموس القيم المراد تحديثها
            
        Raises:
            ValidationError: إذا كانت أي قيمة غير صالحة
        """
        if "products_count" in updates and updates["products_count"] < 0:
            raise ValidationError(
                message="عدد المنتجات لا يمكن أن يكون سالباً",
            )

        if "categories_count" in updates and updates["categories_count"] < 0:
            raise ValidationError(
                message="عدد التصنيفات لا يمكن أن يكون سالباً",
            )

        if "monthly_orders" in updates and updates["monthly_orders"] < 0:
            raise ValidationError(
                message="عدد الطلبات الشهرية لا يمكن أن يكون سالباً",
            )

        if "average_order_value" in updates and updates["average_order_value"] < 0:
            raise ValidationError(
                message="متوسط قيمة الطلب لا يمكن أن يكون سالباً",
            )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantMetricsService",
    "MetricsDict",
]