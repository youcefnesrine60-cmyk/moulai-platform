# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER SERVICE
# منطق الأعمال لعداد طلبات المطعم
# ==============================================

from typing import (
    Any,
    Dict,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.repositories.restaurant.restaurant_order_counters_repo import (
    RestaurantOrderCountersRepository,
)
from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.schemas.restaurant.restaurant_order_counter import (
    RestaurantOrderCounterResponse,
    RestaurantOrderCounterUpdate,
    NextOrderNumberResponse,
    OrderCounterSummary,
)


# ==============================================
# 🧩 TYPES
# ==============================================

OrderCounterData = Dict[str, Any]
OrderCounterUpdateData = Dict[str, Any]
CounterSummary = Dict[str, Any]


# ==============================================
# 🔢 RESTAURANT ORDER COUNTER SERVICE
# ==============================================

class RestaurantOrderCounterService:
    """
    خدمة عداد طلبات المطعم - تدير منطق الأعمال لعداد الطلبات.
    
    مسؤولة عن:
        - إنشاء عداد طلبات
        - قراءة عداد طلبات
        - تحديث عداد طلبات
        - زيادة عداد طلبات
        - توليد رقم طلب
        - إعادة تعيين عداد طلبات
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع عداد الطلبات
        restaurant_repo: مستودع المطاعم
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة عداد طلبات المطعم.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = RestaurantOrderCountersRepository(session)
        self.restaurant_repo = RestaurantRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET COUNTER
    # ==============================================

    async def get_counter(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantOrderCounterResponse:
        """
        الحصول على عداد طلبات مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            RestaurantOrderCounterResponse: بيانات عداد الطلبات
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العداد
        """
        logger.info(
            "order_counter_service_get_counter",
            extra={"restaurant_id": restaurant_id},
        )

        counter = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not counter:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        return RestaurantOrderCounterResponse.model_validate(counter)

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
            int: آخر رقم طلب
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العداد
        """
        logger.info(
            "order_counter_service_get_current_number",
            extra={"restaurant_id": restaurant_id},
        )

        number = await self.repo.get_current_number(
            restaurant_id=restaurant_id,
        )

        if number < 0:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        return number

    # ==============================================
    # GET NEXT ORDER NUMBER
    # ==============================================

    async def get_next_order_number(
        self,
        *,
        restaurant_id: int,
    ) -> NextOrderNumberResponse:
        """
        الحصول على رقم الطلب التالي لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            NextOrderNumberResponse: رقم الطلب التالي
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العداد
        """
        logger.info(
            "order_counter_service_get_next_order_number",
            extra={"restaurant_id": restaurant_id},
        )

        counter = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not counter:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        next_number = counter.last_number + 1
        formatted_number = self.build_order_number(
            restaurant_id=restaurant_id,
            sequence=next_number,
        )

        return NextOrderNumberResponse(
            restaurant_id=restaurant_id,
            next_number=next_number,
            formatted_number=formatted_number,
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET COUNTER SUMMARY
    # ==============================================

    async def get_counter_summary(
        self,
        *,
        restaurant_id: int,
    ) -> OrderCounterSummary:
        """
        الحصول على ملخص عداد طلبات مطعم.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            OrderCounterSummary: ملخص العداد
        """
        logger.info(
            "order_counter_service_get_summary",
            extra={"restaurant_id": restaurant_id},
        )

        counter = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not counter:
            return OrderCounterSummary(
                restaurant_id=restaurant_id,
                exists=False,
                total_orders=0,
                last_order_number=None,
                next_order_number=None,
            )

        last_order_number = self.build_order_number(
            restaurant_id=restaurant_id,
            sequence=counter.last_number,
        )

        next_order_number = self.build_order_number(
            restaurant_id=restaurant_id,
            sequence=counter.last_number + 1,
        )

        return OrderCounterSummary(
            restaurant_id=restaurant_id,
            exists=True,
            total_orders=counter.last_number,
            last_order_number=last_order_number,
            next_order_number=next_order_number,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # INITIALIZE COUNTER
    # ==============================================

    async def initialize_counter(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantOrderCounterResponse:
        """
        تهيئة عداد طلبات جديد لمطعم.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            RestaurantOrderCounterResponse: بيانات العداد المنشأ
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المطعم
            ConflictError: إذا كان العداد موجوداً مسبقاً
        """
        logger.info(
            "order_counter_service_initialize",
            extra={"restaurant_id": restaurant_id},
        )

        # التحقق من وجود المطعم
        restaurant = await self.restaurant_repo.get_by_id(
            id=restaurant_id,
        )

        if not restaurant:
            raise NotFoundError(
                message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        # التحقق من عدم وجود عداد مسبق
        existing = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if existing:
            raise ConflictError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' موجود مسبقاً",
            )

        # إنشاء عداد جديد
        counter = await self.repo.create_counter(
            restaurant_id=restaurant_id,
        )

        logger.info(
            "order_counter_service_initialized_successfully",
            extra={
                "restaurant_id": restaurant_id,
                "counter_id": counter.restaurant_id,
            },
        )

        return RestaurantOrderCounterResponse.model_validate(counter)

    # ==============================================
    # UPDATE COUNTER
    # ==============================================

    async def update_counter(
        self,
        *,
        restaurant_id: int,
        update_data: RestaurantOrderCounterUpdate,
    ) -> RestaurantOrderCounterResponse:
        """
        تحديث عداد طلبات مطعم.
        
        Args:
            restaurant_id: معرف المطعم
            update_data: بيانات التحديث
            
        Returns:
            RestaurantOrderCounterResponse: بيانات العداد المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العداد
            ValidationError: إذا كانت البيانات غير صالحة
        """
        logger.info(
            "order_counter_service_update",
            extra={
                "restaurant_id": restaurant_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود العداد
        counter = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not counter:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        updates = update_data.model_dump(exclude_unset=True)

        # التحقق من صحة القيمة
        if "last_number" in updates:
            if updates["last_number"] < 0:
                raise ValidationError(
                    message="رقم الطلب لا يمكن أن يكون سالباً",
                )

        # تحديث العداد
        updated = await self.repo.update(
            id=counter.restaurant_id,
            data=updates,
        )

        if not updated:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        logger.info(
            "order_counter_service_updated_successfully",
            extra={"restaurant_id": restaurant_id},
        )

        return RestaurantOrderCounterResponse.model_validate(updated)

    # ==============================================
    # INCREMENT COUNTER
    # ==============================================

    async def increment_counter(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantOrderCounterResponse:
        """
        زيادة عداد طلبات مطعم بمقدار 1.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            RestaurantOrderCounterResponse: بيانات العداد المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العداد
        """
        logger.info(
            "order_counter_service_increment",
            extra={"restaurant_id": restaurant_id},
        )

        # التحقق من وجود العداد
        counter = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not counter:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        # زيادة العداد
        await self.repo.increment_counter(
            restaurant_id=restaurant_id,
        )

        # جلب العداد المحدث
        updated = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not updated:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        logger.info(
            "order_counter_service_incremented_successfully",
            extra={
                "restaurant_id": restaurant_id,
                "new_number": updated.last_number,
            },
        )

        return RestaurantOrderCounterResponse.model_validate(updated)

    # ==============================================
    # RESET COUNTER
    # ==============================================

    async def reset_counter(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantOrderCounterResponse:
        """
        إعادة تعيين عداد طلبات مطعم إلى الصفر.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            RestaurantOrderCounterResponse: بيانات العداد المعاد تعيينه
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العداد
        """
        logger.info(
            "order_counter_service_reset",
            extra={"restaurant_id": restaurant_id},
        )

        # التحقق من وجود العداد
        counter = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not counter:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        # إعادة تعيين العداد
        updated = await self.repo.update(
            id=counter.restaurant_id,
            data={"last_number": 0},
        )

        if not updated:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        logger.info(
            "order_counter_service_reset_successfully",
            extra={"restaurant_id": restaurant_id},
        )

        return RestaurantOrderCounterResponse.model_validate(updated)

    # ==============================================
    # GENERATE NEXT ORDER NUMBER
    # ==============================================

    async def generate_next_order_number(
        self,
        *,
        restaurant_id: int,
    ) -> NextOrderNumberResponse:
        """
        توليد رقم الطلب التالي لمطعم (يزيد العداد ويعيد الرقم المنسق).
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            NextOrderNumberResponse: رقم الطلب التالي
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العداد
        """
        logger.info(
            "order_counter_service_generate_next",
            extra={"restaurant_id": restaurant_id},
        )

        # التحقق من وجود العداد
        counter = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not counter:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        # توليد الرقم التالي (يزيد العداد تلقائياً)
        order_number = await self.repo.generate_next_order_number(
            restaurant_id=restaurant_id,
        )

        logger.info(
            "order_counter_service_generated_successfully",
            extra={
                "restaurant_id": restaurant_id,
                "order_number": order_number,
            },
        )

        # الحصول على الرقم الحالي
        updated = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not updated:
            raise NotFoundError(
                message=f"عداد طلبات المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        return NextOrderNumberResponse(
            restaurant_id=restaurant_id,
            next_number=updated.last_number,
            formatted_number=order_number,
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
            str: رقم الطلب المنسق
        """
        return RestaurantOrderCountersRepository.build_order_number(
            restaurant_id=restaurant_id,
            sequence=sequence,
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantOrderCounterService",
    "OrderCounterData",
    "OrderCounterUpdateData",
    "CounterSummary",
]