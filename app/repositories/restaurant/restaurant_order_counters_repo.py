# ==============================================
# 🔢 RESTAURANT ORDER COUNTERS REPOSITORY
# عمليات قاعدة البيانات لعدادات الطلبات باستخدام SQLAlchemy
# ==============================================

from typing import (
    Any,
    Dict,
    Optional,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.restaurant_order_counter import RestaurantOrderCounter
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

RestaurantOrderCounterData = Dict[str, Any]

# ==============================================
# 🔢 RESTAURANT ORDER COUNTERS REPOSITORY
# ==============================================


class RestaurantOrderCountersRepository(
    BaseRepository[
        RestaurantOrderCounter,
        RestaurantOrderCounterData,
        RestaurantOrderCounterData,
    ]
):
    """
    مستودع عداد الطلبات - يوفر عمليات خاصة بعدادات الطلبات.
    
    مسؤول عن:
        - عمليات CRUD الأساسية لعدادات الطلبات
        - إنشاء عداد جديد للمطعم
        - زيادة العداد وإرجاع الرقم الجديد
        - توليد رقم طلب منسق
    
    Attributes:
        model: نموذج RestaurantOrderCounter
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع عداد الطلبات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(RestaurantOrderCounter, session)

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
    ) -> Optional[RestaurantOrderCounter]:
        """
        الحصول على عداد طلبات مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            كائن RestaurantOrderCounter أو None
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
                "order_counter_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET CURRENT NUMBER
    # ==============================================

    async def get_current_number(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        الحصول على رقم الطلب الحالي لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            آخر رقم طلب
        """
        counter = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not counter:
            return 0

        return counter.last_number

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE COUNTER
    # ==============================================

    async def create_counter(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantOrderCounter:
        """
        إنشاء عداد طلبات جديد لمطعم.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            كائن RestaurantOrderCounter المنشأ
        """
        logger.info(
            "order_counter_repo_create",
            extra={"restaurant_id": restaurant_id},
        )

        # التحقق من وجود عداد مسبق
        existing = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if existing:
            logger.info(
                "order_counter_already_exists",
                extra={"restaurant_id": restaurant_id},
            )
            return existing

        # إنشاء عداد جديد
        data: RestaurantOrderCounterData = {
            "restaurant_id": restaurant_id,
            "last_number": 0,
        }

        counter = await self.create(data=data)

        logger.info(
            "order_counter_created",
            extra={"restaurant_id": restaurant_id},
        )

        return counter

    # ==============================================
    # INCREMENT COUNTER
    # ==============================================

    async def increment_counter(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        زيادة عداد الطلبات وإرجاع الرقم الجديد.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            رقم الطلب الجديد
        """
        logger.info(
            "order_counter_repo_increment",
            extra={"restaurant_id": restaurant_id},
        )

        # الحصول على العداد الحالي
        counter = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not counter:
            # إنشاء عداد جديد إذا لم يكن موجوداً
            counter = await self.create_counter(
                restaurant_id=restaurant_id,
            )

        # زيادة الرقم
        new_number = counter.last_number + 1

        # تحديث العداد
        await self.update(
            id=counter.restaurant_id,
            data={"last_number": new_number},
        )

        logger.info(
            "order_counter_incremented",
            extra={
                "restaurant_id": restaurant_id,
                "new_number": new_number,
            },
        )

        return new_number

    # ==============================================
    # RESET COUNTER
    # ==============================================

    async def reset_counter(
        self,
        *,
        restaurant_id: int,
    ) -> Optional[RestaurantOrderCounter]:
        """
        إعادة تعيين عداد الطلبات إلى الصفر.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            كائن RestaurantOrderCounter المعاد تعيينه أو None
        """
        logger.info(
            "order_counter_repo_reset",
            extra={"restaurant_id": restaurant_id},
        )

        counter = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not counter:
            return None

        return await self.update(
            id=counter.restaurant_id,
            data={"last_number": 0},
        )

    # ==========================================
    # 🏷️ HELPERS
    # ==========================================

    # ==============================================
    # BUILD ORDER NUMBER
    # ==============================================

    @staticmethod
    def build_order_number(
        restaurant_id: int,
        sequence: int,
    ) -> str:
        """
        بناء رقم طلب منسق.
        
        Args:
            restaurant_id: معرف المطعم
            sequence: رقم التسلسل
            
        Returns:
            رقم الطلب المنسق
        """
        return f"RST{restaurant_id}-{sequence:06d}"

    # ==============================================
    # GENERATE NEXT ORDER NUMBER
    # ==============================================

    async def generate_next_order_number(
        self,
        *,
        restaurant_id: int,
    ) -> str:
        """
        توليد رقم الطلب التالي.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            رقم الطلب التالي
        """
        sequence = await self.increment_counter(
            restaurant_id=restaurant_id,
        )

        return self.build_order_number(
            restaurant_id=restaurant_id,
            sequence=sequence,
        )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE ORDER COUNTER (COMPATIBILITY)
# ==============================================

async def create_order_counter(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    إنشاء عداد طلبات جديد لمطعم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = RestaurantOrderCountersRepository(session=session)

    await repo.create_counter(restaurant_id=restaurant_id)

    logger.info(
        "order_counter_created",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# GET ORDER COUNTER (COMPATIBILITY)
# ==============================================

async def get_order_counter(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على عداد طلبات مطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        عداد الطلبات أو None
    """
    repo = RestaurantOrderCountersRepository(session=session)

    counter = await repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
    )

    if not counter:
        return None

    return {
        "restaurant_id": counter.restaurant_id,
        "last_number": counter.last_number,
        "created_at": counter.created_at,
        "updated_at": counter.updated_at,
    }


# ==============================================
# GET CURRENT ORDER NUMBER (COMPATIBILITY)
# ==============================================

async def get_current_order_number(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> int:
    """
    الحصول على رقم الطلب الحالي لمطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        آخر رقم طلب
    """
    repo = RestaurantOrderCountersRepository(session=session)

    return await repo.get_current_number(
        restaurant_id=restaurant_id,
    )


# ==============================================
# INCREMENT ORDER COUNTER TX (COMPATIBILITY)
# ==============================================

async def increment_order_counter_tx(
    *,
    conn: AsyncSession,
    restaurant_id: int,
) -> int:
    """
    زيادة عداد الطلبات وإرجاع الرقم الجديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        conn: جلسة قاعدة البيانات (AsyncSession)
        restaurant_id: معرف المطعم
        
    Returns:
        رقم الطلب الجديد
    """
    repo = RestaurantOrderCountersRepository(conn)

    return await repo.increment_counter(
        restaurant_id=restaurant_id,
    )


# ==============================================
# BUILD ORDER NUMBER (COMPATIBILITY)
# ==============================================

def build_order_number(
    *,
    restaurant_id: int,
    sequence: int,
) -> str:
    """
    بناء رقم طلب منسق (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        sequence: رقم التسلسل
        
    Returns:
        رقم الطلب المنسق
    """
    return RestaurantOrderCountersRepository.build_order_number(
        restaurant_id=restaurant_id,
        sequence=sequence,
    )


# ==============================================
# GENERATE NEXT ORDER NUMBER TX (COMPATIBILITY)
# ==============================================

async def generate_next_order_number_tx(
    *,
    conn: AsyncSession,
    restaurant_id: int,
) -> str:
    """
    توليد رقم الطلب التالي (دالة متوافقة مع الإصدار القديم).
    
    Args:
        conn: جلسة قاعدة البيانات (AsyncSession)
        restaurant_id: معرف المطعم
        
    Returns:
        رقم الطلب التالي
    """
    repo = RestaurantOrderCountersRepository(conn)

    return await repo.generate_next_order_number(
        restaurant_id=restaurant_id,
    )