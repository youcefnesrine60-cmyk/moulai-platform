# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS SERVICE
# منطق الأعمال لإعدادات الدفع للمطعم
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
from app.repositories.restaurant.restaurant_payment_settings_repo import (
    RestaurantPaymentSettingsRepository,
)
from app.schemas.restaurant.restaurant_payment_setting import (
    RestaurantPaymentSettingCreate,
    RestaurantPaymentSettingResponse,
    RestaurantPaymentSettingUpdate,
    PaymentMethodsList,
    PaymentSettingsSummary,
)


# ==============================================
# 🧩 CONSTANTS
# ==============================================

ALL_PAYMENT_METHODS = ["cash", "card", "ccp", "baridimob", "stripe", "paypal"]
DEFAULT_PAYMENT_METHODS = ["cash", "card"]


# ==============================================
# 🧩 TYPES
# ==============================================

PaymentSettingsData = Dict[str, Any]
PaymentSettingsUpdateData = Dict[str, Any]
SettingsSummary = Dict[str, Any]


# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS SERVICE
# ==============================================

class RestaurantPaymentSettingsService:
    """
    خدمة إعدادات الدفع للمطعم - تدير منطق الأعمال لإعدادات الدفع.
    
    مسؤولة عن:
        - إنشاء إعدادات الدفع
        - قراءة إعدادات الدفع
        - تحديث إعدادات الدفع
        - حذف إعدادات الدفع
        - جلب طرق الدفع المسموح بها
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع إعدادات الدفع
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة إعدادات الدفع للمطعم.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = RestaurantPaymentSettingsRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET SETTINGS
    # ==============================================

    async def get_settings(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantPaymentSettingResponse:
        """
        الحصول على إعدادات الدفع لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            RestaurantPaymentSettingResponse: بيانات إعدادات الدفع
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الإعدادات
        """
        logger.info(
            "payment_settings_service_get_settings",
            extra={"restaurant_id": restaurant_id},
        )

        settings = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not settings:
            raise NotFoundError(
                message=f"إعدادات الدفع للمطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        return RestaurantPaymentSettingResponse.model_validate(settings)

    # ==============================================
    # GET ALLOWED METHODS
    # ==============================================

    async def get_allowed_methods(
        self,
        *,
        restaurant_id: int,
    ) -> PaymentMethodsList:
        """
        الحصول على قائمة طرق الدفع المسموح بها لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            PaymentMethodsList: قائمة طرق الدفع المسموح بها
        """
        logger.info(
            "payment_settings_service_get_allowed_methods",
            extra={"restaurant_id": restaurant_id},
        )

        return await self.repo.get_allowed_methods(
            restaurant_id=restaurant_id,
        )

    # ==============================================
    # IS METHOD ALLOWED
    # ==============================================

    async def is_method_allowed(
        self,
        *,
        restaurant_id: int,
        method: str,
    ) -> bool:
        """
        التحقق من أن طريقة دفع معينة مسموح بها لمطعم.
        
        Args:
            restaurant_id: معرف المطعم
            method: طريقة الدفع (cash, card, ccp, baridimob, stripe, paypal)
            
        Returns:
            bool: True إذا كانت مسموحة، False إذا لم تكن
        """
        if method.lower() not in ALL_PAYMENT_METHODS:
            raise ValidationError(
                message=f"طريقة الدفع '{method}' غير معروفة",
                details={
                    "method": method,
                    "valid_methods": ALL_PAYMENT_METHODS,
                },
            )

        logger.info(
            "payment_settings_service_is_method_allowed",
            extra={
                "restaurant_id": restaurant_id,
                "method": method,
            },
        )

        allowed_methods = await self.repo.get_allowed_methods(
            restaurant_id=restaurant_id,
        )

        return method.lower() in allowed_methods

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET SETTINGS SUMMARY
    # ==============================================

    async def get_settings_summary(
        self,
        *,
        restaurant_id: int,
    ) -> PaymentSettingsSummary:
        """
        الحصول على ملخص إعدادات الدفع لمطعم.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            PaymentSettingsSummary: ملخص إعدادات الدفع
        """
        logger.info(
            "payment_settings_service_get_summary",
            extra={"restaurant_id": restaurant_id},
        )

        settings = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not settings:
            return PaymentSettingsSummary(
                restaurant_id=restaurant_id,
                exists=False,
                total_enabled=0,
                total_disabled=len(ALL_PAYMENT_METHODS),
                enabled_methods=[],
                disabled_methods=ALL_PAYMENT_METHODS.copy(),
            )

        enabled_methods = []
        disabled_methods = []

        method_map = {
            "cash": settings.allow_cash,
            "card": settings.allow_card,
            "ccp": settings.allow_ccp,
            "baridimob": settings.allow_baridimob,
            "stripe": settings.allow_stripe,
            "paypal": settings.allow_paypal,
        }

        for method, enabled in method_map.items():
            if enabled:
                enabled_methods.append(method)
            else:
                disabled_methods.append(method)

        return PaymentSettingsSummary(
            restaurant_id=restaurant_id,
            exists=True,
            settings_id=settings.id,
            total_enabled=len(enabled_methods),
            total_disabled=len(disabled_methods),
            enabled_methods=enabled_methods,
            disabled_methods=disabled_methods,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE SETTINGS
    # ==============================================

    async def create_settings(
        self,
        *,
        settings_data: RestaurantPaymentSettingCreate,
    ) -> RestaurantPaymentSettingResponse:
        """
        إنشاء إعدادات دفع جديدة لمطعم.
        
        Args:
            settings_data: بيانات إعدادات الدفع
            
        Returns:
            RestaurantPaymentSettingResponse: بيانات إعدادات الدفع المنشأة
            
        Raises:
            ConflictError: إذا كانت الإعدادات موجودة مسبقاً
        """
        logger.info(
            "payment_settings_service_create",
            extra={
                "restaurant_id": settings_data.restaurant_id,
                "allow_cash": settings_data.allow_cash,
                "allow_card": settings_data.allow_card,
            },
        )

        existing = await self.repo.get_by_restaurant_id(
            restaurant_id=settings_data.restaurant_id,
        )

        if existing:
            raise ConflictError(
                message=f"إعدادات الدفع للمطعم بـ ID '{settings_data.restaurant_id}' موجودة مسبقاً",
            )

        settings = await self.repo.create_settings(
            restaurant_id=settings_data.restaurant_id,
            allow_cash=settings_data.allow_cash,
            allow_card=settings_data.allow_card,
            allow_ccp=settings_data.allow_ccp if settings_data.allow_ccp is not None else False,
            allow_baridimob=settings_data.allow_baridimob if settings_data.allow_baridimob is not None else False,
            allow_stripe=settings_data.allow_stripe if settings_data.allow_stripe is not None else False,
            allow_paypal=settings_data.allow_paypal if settings_data.allow_paypal is not None else False,
        )

        logger.info(
            "payment_settings_created_successfully",
            extra={
                "restaurant_id": settings_data.restaurant_id,
                "settings_id": settings.id,
            },
        )

        return RestaurantPaymentSettingResponse.model_validate(settings)

    # ==============================================
    # UPDATE SETTINGS
    # ==============================================

    async def update_settings(
        self,
        *,
        restaurant_id: int,
        update_data: RestaurantPaymentSettingUpdate,
    ) -> RestaurantPaymentSettingResponse:
        """
        تحديث إعدادات الدفع لمطعم.
        
        Args:
            restaurant_id: معرف المطعم
            update_data: بيانات التحديث
            
        Returns:
            RestaurantPaymentSettingResponse: بيانات إعدادات الدفع المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الإعدادات
        """
        logger.info(
            "payment_settings_service_update",
            extra={
                "restaurant_id": restaurant_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        settings = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not settings:
            raise NotFoundError(
                message=f"إعدادات الدفع للمطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        updates = update_data.model_dump(exclude_unset=True)

        updated = await self.repo.update(
            id=settings.id,
            data=updates,
        )

        if not updated:
            raise NotFoundError(
                message=f"إعدادات الدفع للمطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        logger.info(
            "payment_settings_updated_successfully",
            extra={"restaurant_id": restaurant_id},
        )

        return RestaurantPaymentSettingResponse.model_validate(updated)

    # ==============================================
    # UPDATE PAYMENT METHODS
    # ==============================================

    async def update_payment_methods(
        self,
        *,
        restaurant_id: int,
        allow_cash: Optional[bool] = None,
        allow_card: Optional[bool] = None,
        allow_ccp: Optional[bool] = None,
        allow_baridimob: Optional[bool] = None,
        allow_stripe: Optional[bool] = None,
        allow_paypal: Optional[bool] = None,
    ) -> RestaurantPaymentSettingResponse:
        """
        تحديث طرق الدفع المسموح بها لمطعم.
        """
        logger.info(
            "payment_settings_service_update_methods",
            extra={
                "restaurant_id": restaurant_id,
                "allow_cash": allow_cash,
                "allow_card": allow_card,
                "allow_ccp": allow_ccp,
                "allow_baridimob": allow_baridimob,
                "allow_stripe": allow_stripe,
                "allow_paypal": allow_paypal,
            },
        )

        settings = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not settings:
            raise NotFoundError(
                message=f"إعدادات الدفع للمطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        updated = await self.repo.update_payment_methods(
            restaurant_id=restaurant_id,
            allow_cash=allow_cash,
            allow_card=allow_card,
            allow_ccp=allow_ccp,
            allow_baridimob=allow_baridimob,
            allow_stripe=allow_stripe,
            allow_paypal=allow_paypal,
        )

        if not updated:
            raise NotFoundError(
                message=f"إعدادات الدفع للمطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        logger.info(
            "payment_methods_updated_successfully",
            extra={"restaurant_id": restaurant_id},
        )

        return RestaurantPaymentSettingResponse.model_validate(updated)

    # ==============================================
    # ENABLE PAYMENT METHOD
    # ==============================================

    async def enable_payment_method(
        self,
        *,
        restaurant_id: int,
        method: str,
    ) -> RestaurantPaymentSettingResponse:
        """
        تفعيل طريقة دفع معينة لمطعم.
        """
        if method.lower() not in ALL_PAYMENT_METHODS:
            raise ValidationError(
                message=f"طريقة الدفع '{method}' غير معروفة",
                details={
                    "method": method,
                    "valid_methods": ALL_PAYMENT_METHODS,
                },
            )

        logger.info(
            "payment_settings_service_enable_method",
            extra={
                "restaurant_id": restaurant_id,
                "method": method,
            },
        )

        updates = {method.lower(): True}

        return await self.update_payment_methods(
            restaurant_id=restaurant_id,
            **updates,
        )

    # ==============================================
    # DISABLE PAYMENT METHOD
    # ==============================================

    async def disable_payment_method(
        self,
        *,
        restaurant_id: int,
        method: str,
    ) -> RestaurantPaymentSettingResponse:
        """
        إلغاء تفعيل طريقة دفع معينة لمطعم.
        """
        if method.lower() not in ALL_PAYMENT_METHODS:
            raise ValidationError(
                message=f"طريقة الدفع '{method}' غير معروفة",
                details={
                    "method": method,
                    "valid_methods": ALL_PAYMENT_METHODS,
                },
            )

        logger.info(
            "payment_settings_service_disable_method",
            extra={
                "restaurant_id": restaurant_id,
                "method": method,
            },
        )

        updates = {method.lower(): False}

        return await self.update_payment_methods(
            restaurant_id=restaurant_id,
            **updates,
        )

    # ==============================================
    # DELETE SETTINGS
    # ==============================================

    async def delete_settings(
        self,
        *,
        restaurant_id: int,
    ) -> None:
        """
        حذف إعدادات الدفع لمطعم.
        """
        logger.info(
            "payment_settings_service_delete",
            extra={"restaurant_id": restaurant_id},
        )

        settings = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not settings:
            raise NotFoundError(
                message=f"إعدادات الدفع للمطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        deleted = await self.repo.delete(id=settings.id)

        if not deleted:
            raise NotFoundError(
                message=f"إعدادات الدفع للمطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        logger.info(
            "payment_settings_deleted_successfully",
            extra={"restaurant_id": restaurant_id},
        )

    # ==============================================
    # RESET TO DEFAULTS
    # ==============================================

    async def reset_to_defaults(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantPaymentSettingResponse:
        """
        إعادة تعيين إعدادات الدفع إلى القيم الافتراضية.
        """
        logger.info(
            "payment_settings_service_reset",
            extra={"restaurant_id": restaurant_id},
        )

        settings = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not settings:
            raise NotFoundError(
                message=f"إعدادات الدفع للمطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        updated = await self.repo.update_payment_methods(
            restaurant_id=restaurant_id,
            allow_cash=True,
            allow_card=True,
            allow_ccp=False,
            allow_baridimob=False,
            allow_stripe=False,
            allow_paypal=False,
        )

        if not updated:
            raise NotFoundError(
                message=f"إعدادات الدفع للمطعم بـ ID '{restaurant_id}' غير موجودة",
            )

        logger.info(
            "payment_settings_reset_successfully",
            extra={"restaurant_id": restaurant_id},
        )

        return RestaurantPaymentSettingResponse.model_validate(updated)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantPaymentSettingsService",
    "ALL_PAYMENT_METHODS",
    "DEFAULT_PAYMENT_METHODS",
    "PaymentSettingsData",
    "PaymentSettingsUpdateData",
    "SettingsSummary",
]