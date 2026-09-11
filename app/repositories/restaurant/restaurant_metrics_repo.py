# ==============================================
# 📊 RESTAURANT METRICS REPOSITORY
# عمليات قاعدة البيانات لمقاييس المطعم باستخدام SQLAlchemy
# ==============================================

from typing import (
    Any,
    Dict,
    Optional,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.restaurant_metric import RestaurantMetric
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

RestaurantMetricsData = Dict[str, Any]
RestaurantMetricsUpdateData = Dict[str, Any]

# ==============================================
# 📊 RESTAURANT METRICS REPOSITORY
# ==============================================


class RestaurantMetricsRepository(
    BaseRepository[
        RestaurantMetric,
        RestaurantMetricsData,
        RestaurantMetricsUpdateData,
    ]
):
    """
    مستودع مقاييس المطعم - يوفر عمليات خاصة بمقاييس المطاعم.
    
    مسؤول عن:
        - عمليات CRUD الأساسية لمقاييس المطعم
        - إنشاء مقاييس افتراضية للمطعم الجديد
        - تحديث عدد المنتجات والتصنيفات
        - تسجيل الطلبات وتحديث المقاييس
    
    Attributes:
        model: نموذج RestaurantMetric
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع مقاييس المطعم.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(RestaurantMetric, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY RESTAURANT ID
    # ==============================================

    async def get_by_restaurant_id(
        self,
        *,
        restaurant_id: int,
    ) -> Optional[RestaurantMetric]:
        """
        الحصول على مقاييس مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            كائن RestaurantMetric أو None
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(self.model.restaurant_id == restaurant_id)
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "restaurant_metrics_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE DEFAULT
    # ==============================================

    async def create_default(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantMetric:
        """
        إنشاء مقاييس افتراضية لمطعم جديد.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            كائن RestaurantMetric المنشأ
        """
        logger.info(
            "restaurant_metrics_repo_create_default",
            extra={"restaurant_id": restaurant_id},
        )

        # التحقق من وجود مقاييس مسبقة
        existing = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if existing:
            logger.info(
                "restaurant_metrics_already_exists",
                extra={"restaurant_id": restaurant_id},
            )
            return existing

        # إنشاء مقاييس جديدة
        data: RestaurantMetricsData = {
            "restaurant_id": restaurant_id,
            "products_count": 0,
            "categories_count": 0,
            "monthly_orders": 0,
            "average_order_value": 0,
        }

        metrics = await self.create(data=data)

        logger.info(
            "restaurant_metrics_created",
            extra={"restaurant_id": restaurant_id},
        )

        return metrics

    # ==============================================
    # INCREMENT PRODUCTS COUNT
    # ==============================================

    async def increment_products_count(
        self,
        *,
        restaurant_id: int,
        amount: int = 1,
    ) -> Optional[RestaurantMetric]:
        """
        زيادة عدد المنتجات.
        
        Args:
            restaurant_id: معرف المطعم
            amount: مقدار الزيادة
            
        Returns:
            كائن RestaurantMetric المحدث أو None
        """
        logger.info(
            "restaurant_metrics_repo_increment_products",
            extra={
                "restaurant_id": restaurant_id,
                "amount": amount,
            },
        )

        metrics = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not metrics:
            metrics = await self.create_default(
                restaurant_id=restaurant_id,
            )

        new_count = (metrics.products_count or 0) + amount

        return await self.update(
            id=metrics.restaurant_id,
            data={"products_count": new_count},
        )

    # ==============================================
    # DECREMENT PRODUCTS COUNT
    # ==============================================

    async def decrement_products_count(
        self,
        *,
        restaurant_id: int,
        amount: int = 1,
    ) -> Optional[RestaurantMetric]:
        """
        تقليل عدد المنتجات.
        
        Args:
            restaurant_id: معرف المطعم
            amount: مقدار النقصان
            
        Returns:
            كائن RestaurantMetric المحدث أو None
        """
        logger.info(
            "restaurant_metrics_repo_decrement_products",
            extra={
                "restaurant_id": restaurant_id,
                "amount": amount,
            },
        )

        metrics = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not metrics:
            metrics = await self.create_default(
                restaurant_id=restaurant_id,
            )

        new_count = max(0, (metrics.products_count or 0) - amount)

        return await self.update(
            id=metrics.restaurant_id,
            data={"products_count": new_count},
        )

    # ==============================================
    # INCREMENT CATEGORIES COUNT
    # ==============================================

    async def increment_categories_count(
        self,
        *,
        restaurant_id: int,
        amount: int = 1,
    ) -> Optional[RestaurantMetric]:
        """
        زيادة عدد التصنيفات.
        
        Args:
            restaurant_id: معرف المطعم
            amount: مقدار الزيادة
            
        Returns:
            كائن RestaurantMetric المحدث أو None
        """
        logger.info(
            "restaurant_metrics_repo_increment_categories",
            extra={
                "restaurant_id": restaurant_id,
                "amount": amount,
            },
        )

        metrics = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not metrics:
            metrics = await self.create_default(
                restaurant_id=restaurant_id,
            )

        new_count = (metrics.categories_count or 0) + amount

        return await self.update(
            id=metrics.restaurant_id,
            data={"categories_count": new_count},
        )

    # ==============================================
    # DECREMENT CATEGORIES COUNT
    # ==============================================

    async def decrement_categories_count(
        self,
        *,
        restaurant_id: int,
        amount: int = 1,
    ) -> Optional[RestaurantMetric]:
        """
        تقليل عدد التصنيفات.
        
        Args:
            restaurant_id: معرف المطعم
            amount: مقدار النقصان
            
        Returns:
            كائن RestaurantMetric المحدث أو None
        """
        logger.info(
            "restaurant_metrics_repo_decrement_categories",
            extra={
                "restaurant_id": restaurant_id,
                "amount": amount,
            },
        )

        metrics = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not metrics:
            metrics = await self.create_default(
                restaurant_id=restaurant_id,
            )

        new_count = max(0, (metrics.categories_count or 0) - amount)

        return await self.update(
            id=metrics.restaurant_id,
            data={"categories_count": new_count},
        )

    # ==============================================
    # REGISTER ORDER
    # ==============================================

    async def register_order(
        self,
        *,
        restaurant_id: int,
        order_total: float,
    ) -> Optional[RestaurantMetric]:
        """
        تسجيل طلب جديد وتحديث المقاييس.
        
        Args:
            restaurant_id: معرف المطعم
            order_total: إجمالي قيمة الطلب
            
        Returns:
            كائن RestaurantMetric المحدث أو None
        """
        logger.info(
            "restaurant_metrics_repo_register_order",
            extra={
                "restaurant_id": restaurant_id,
                "order_total": order_total,
            },
        )

        metrics = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not metrics:
            metrics = await self.create_default(
                restaurant_id=restaurant_id,
            )

        # حساب القيم الجديدة
        current_orders = metrics.monthly_orders or 0
        current_avg = metrics.average_order_value or 0

        new_orders = current_orders + 1

        # حساب المتوسط الجديد
        if current_orders > 0:
            new_avg = ((current_avg * current_orders) + order_total) / new_orders
        else:
            new_avg = order_total

        return await self.update(
            id=metrics.restaurant_id,
            data={
                "monthly_orders": new_orders,
                "average_order_value": new_avg,
            },
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET AVERAGE ORDER VALUE
    # ==============================================

    async def get_average_order_value(
        self,
        *,
        restaurant_id: int,
    ) -> float:
        """
        الحصول على متوسط قيمة الطلب لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            متوسط قيمة الطلب
        """
        metrics = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        return float(metrics.average_order_value) if metrics else 0.0

    # ==============================================
    # GET MONTHLY ORDERS
    # ==============================================

    async def get_monthly_orders(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        الحصول على عدد الطلبات الشهرية لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            عدد الطلبات الشهرية
        """
        metrics = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        return metrics.monthly_orders if metrics else 0

    # ==============================================
    # GET TOTAL PRODUCTS
    # ==============================================

    async def get_total_products(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        الحصول على عدد المنتجات لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            عدد المنتجات
        """
        metrics = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        return metrics.products_count if metrics else 0

    # ==============================================
    # GET TOTAL CATEGORIES
    # ==============================================

    async def get_total_categories(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        الحصول على عدد التصنيفات لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            عدد التصنيفات
        """
        metrics = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        return metrics.categories_count if metrics else 0


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# GET RESTAURANT METRICS (COMPATIBILITY)
# ==============================================

async def get_restaurant_metrics(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مقاييس مطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        مقاييس المطعم أو None
    """
    repo = RestaurantMetricsRepository(session=session)

    metrics = await repo.get_by_restaurant_id(
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
        "updated_at": metrics.updated_at,
    }


# ==============================================
# CREATE RESTAURANT METRICS (COMPATIBILITY)
# ==============================================

async def create_restaurant_metrics(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    إنشاء مقاييس افتراضية لمطعم جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = RestaurantMetricsRepository(session=session)

    await repo.create_default(restaurant_id=restaurant_id)

    logger.info(
        "restaurant_metrics_created",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# INCREMENT PRODUCTS COUNT (COMPATIBILITY)
# ==============================================

async def increment_products_count(
    *,
    restaurant_id: int,
    amount: int = 1,
    session: AsyncSession,
) -> None:
    """
    زيادة عدد المنتجات (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        amount: مقدار الزيادة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = RestaurantMetricsRepository(session=session)

    await repo.increment_products_count(
        restaurant_id=restaurant_id,
        amount=amount,
    )

    logger.info(
        "restaurant_metrics_products_incremented",
        extra={
            "restaurant_id": restaurant_id,
            "amount": amount,
        },
    )


# ==============================================
# DECREMENT PRODUCTS COUNT (COMPATIBILITY)
# ==============================================

async def decrement_products_count(
    *,
    restaurant_id: int,
    amount: int = 1,
    session: AsyncSession,
) -> None:
    """
    تقليل عدد المنتجات (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        amount: مقدار النقصان
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = RestaurantMetricsRepository(session=session)

    await repo.decrement_products_count(
        restaurant_id=restaurant_id,
        amount=amount,
    )

    logger.info(
        "restaurant_metrics_products_decremented",
        extra={
            "restaurant_id": restaurant_id,
            "amount": amount,
        },
    )


# ==============================================
# INCREMENT CATEGORIES COUNT (COMPATIBILITY)
# ==============================================

async def increment_categories_count(
    *,
    restaurant_id: int,
    amount: int = 1,
    session: AsyncSession,
) -> None:
    """
    زيادة عدد التصنيفات (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        amount: مقدار الزيادة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = RestaurantMetricsRepository(session=session)

    await repo.increment_categories_count(
        restaurant_id=restaurant_id,
        amount=amount,
    )

    logger.info(
        "restaurant_metrics_categories_incremented",
        extra={
            "restaurant_id": restaurant_id,
            "amount": amount,
        },
    )


# ==============================================
# DECREMENT CATEGORIES COUNT (COMPATIBILITY)
# ==============================================

async def decrement_categories_count(
    *,
    restaurant_id: int,
    amount: int = 1,
    session: AsyncSession,
) -> None:
    """
    تقليل عدد التصنيفات (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        amount: مقدار النقصان
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = RestaurantMetricsRepository(session=session)

    await repo.decrement_categories_count(
        restaurant_id=restaurant_id,
        amount=amount,
    )

    logger.info(
        "restaurant_metrics_categories_decremented",
        extra={
            "restaurant_id": restaurant_id,
            "amount": amount,
        },
    )


# ==============================================
# REGISTER ORDER METRICS (COMPATIBILITY)
# ==============================================

async def register_order_metrics(
    *,
    restaurant_id: int,
    order_total: float,
    session: AsyncSession,
) -> None:
    """
    تسجيل طلب جديد وتحديث المقاييس (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        order_total: إجمالي قيمة الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = RestaurantMetricsRepository(session=session)

    await repo.register_order(
        restaurant_id=restaurant_id,
        order_total=order_total,
    )

    logger.info(
        "restaurant_metrics_order_registered",
        extra={
            "restaurant_id": restaurant_id,
            "order_total": order_total,
        },
    )