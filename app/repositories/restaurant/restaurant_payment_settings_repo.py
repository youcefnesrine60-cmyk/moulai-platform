# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS REPOSITORY
# عمليات قاعدة البيانات لإعدادات الدفع باستخدام SQLAlchemy
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.restaurant_payment_setting import RestaurantPaymentSetting
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

PaymentSettingsData = Dict[str, Any]
PaymentSettingsUpdateData = Dict[str, Any]
AllowedMethodsList = List[str]

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS REPOSITORY
# ==============================================


class RestaurantPaymentSettingsRepository(
    BaseRepository[
        RestaurantPaymentSetting,
        PaymentSettingsData,
        PaymentSettingsUpdateData,
    ]
):
    """
    مستودع إعدادات الدفع - يوفر عمليات خاصة بإعدادات الدفع للمطاعم.
    
    مسؤول عن:
        - عمليات CRUD الأساسية لإعدادات الدفع
        - إنشاء أو تحديث إعدادات الدفع
        - جلب طرق الدفع المسموح بها
    
    Attributes:
        model: نموذج RestaurantPaymentSetting
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع إعدادات الدفع.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(RestaurantPaymentSetting, session)

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
    ) -> Optional[RestaurantPaymentSetting]:
        """
        الحصول على إعدادات الدفع لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            كائن RestaurantPaymentSetting أو None
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
                "payment_settings_repo_get_by_restaurant_failed",
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
    # UPSERT
    # ==============================================

    async def upsert(
        self,
        *,
        restaurant_id: int,
        allow_cash: bool = True,
        allow_card: bool = True,
        allow_ccp: bool = False,
        allow_baridimob: bool = False,
        allow_stripe: bool = False,
        allow_paypal: bool = False,
    ) -> RestaurantPaymentSetting:
        """
        إنشاء أو تحديث إعدادات الدفع لمطعم.
        
        Args:
            restaurant_id: معرف المطعم
            allow_cash: السماح بالدفع نقداً
            allow_card: السماح بالدفع ببطاقة POS
            allow_ccp: السماح بالدفع عبر CCP
            allow_baridimob: السماح بالدفع عبر بريدي موب
            allow_stripe: السماح بالدفع عبر Stripe
            allow_paypal: السماح بالدفع عبر PayPal
            
        Returns:
            كائن RestaurantPaymentSetting المحدث
        """
        logger.info(
            "payment_settings_repo_upsert",
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

        # التحقق من وجود إعدادات مسبقة
        existing = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if existing:
            # تحديث الإعدادات الموجودة
            data: PaymentSettingsUpdateData = {
                "allow_cash": allow_cash,
                "allow_card": allow_card,
                "allow_ccp": allow_ccp,
                "allow_baridimob": allow_baridimob,
                "allow_stripe": allow_stripe,
                "allow_paypal": allow_paypal,
            }

            updated = await self.update(
                id=existing.id,
                data=data,
            )

            if not updated:
                raise ValueError("payment_settings_update_failed")

            logger.info(
                "payment_settings_updated",
                extra={"restaurant_id": restaurant_id},
            )

            return updated

        # إنشاء إعدادات جديدة
        data: PaymentSettingsData = {
            "restaurant_id": restaurant_id,
            "allow_cash": allow_cash,
            "allow_card": allow_card,
            "allow_ccp": allow_ccp,
            "allow_baridimob": allow_baridimob,
            "allow_stripe": allow_stripe,
            "allow_paypal": allow_paypal,
        }

        created = await self.create(data=data)

        logger.info(
            "payment_settings_created",
            extra={
                "payment_id": created.id,
                "restaurant_id": restaurant_id,
            },
        )

        return created

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
    ) -> Optional[RestaurantPaymentSetting]:
        """
        تحديث طرق الدفع المسموح بها لمطعم.
        
        Args:
            restaurant_id: معرف المطعم
            allow_cash: السماح بالدفع نقداً (اختياري)
            allow_card: السماح بالدفع ببطاقة POS (اختياري)
            allow_ccp: السماح بالدفع عبر CCP (اختياري)
            allow_baridimob: السماح بالدفع عبر بريدي موب (اختياري)
            allow_stripe: السماح بالدفع عبر Stripe (اختياري)
            allow_paypal: السماح بالدفع عبر PayPal (اختياري)
            
        Returns:
            كائن RestaurantPaymentSetting المحدث أو None
        """
        logger.info(
            "payment_settings_repo_update_methods",
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

        # الحصول على الإعدادات الحالية
        settings = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not settings:
            # إنشاء إعدادات جديدة إذا لم تكن موجودة
            return await self.upsert(
                restaurant_id=restaurant_id,
                allow_cash=allow_cash if allow_cash is not None else True,
                allow_card=allow_card if allow_card is not None else True,
                allow_ccp=allow_ccp if allow_ccp is not None else False,
                allow_baridimob=allow_baridimob if allow_baridimob is not None else False,
                allow_stripe=allow_stripe if allow_stripe is not None else False,
                allow_paypal=allow_paypal if allow_paypal is not None else False,
            )

        # تحديث الحقول المحددة فقط
        data: PaymentSettingsUpdateData = {}

        if allow_cash is not None:
            data["allow_cash"] = allow_cash
        if allow_card is not None:
            data["allow_card"] = allow_card
        if allow_ccp is not None:
            data["allow_ccp"] = allow_ccp
        if allow_baridimob is not None:
            data["allow_baridimob"] = allow_baridimob
        if allow_stripe is not None:
            data["allow_stripe"] = allow_stripe
        if allow_paypal is not None:
            data["allow_paypal"] = allow_paypal

        if not data:
            return settings

        return await self.update(
            id=settings.id,
            data=data,
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET ALLOWED METHODS
    # ==============================================

    async def get_allowed_methods(
        self,
        *,
        restaurant_id: int,
    ) -> AllowedMethodsList:
        """
        الحصول على قائمة طرق الدفع المسموح بها لمطعم.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            قائمة طرق الدفع المسموح بها
        """
        settings = await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if not settings:
            # القيم الافتراضية
            return ["cash", "card"]

        allowed: AllowedMethodsList = []

        if settings.allow_cash:
            allowed.append("cash")
        if settings.allow_card:
            allowed.append("card")
        if settings.allow_ccp:
            allowed.append("ccp")
        if settings.allow_baridimob:
            allowed.append("baridimob")
        if settings.allow_stripe:
            allowed.append("stripe")
        if settings.allow_paypal:
            allowed.append("paypal")

        # إذا لم تكن هناك طرق مسموحة، نعود للقيم الافتراضية
        if not allowed:
            return ["cash", "card"]

        return allowed


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# GET RESTAURANT PAYMENT SETTINGS (COMPATIBILITY)
# ==============================================

async def get_restaurant_payment_settings(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    جلب إعدادات الدفع لمطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        إعدادات الدفع أو None
    """
    repo = RestaurantPaymentSettingsRepository(session=session)

    settings = await repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
    )

    if not settings:
        return None

    return {
        "id": settings.id,
        "restaurant_id": settings.restaurant_id,
        "allow_cash": settings.allow_cash,
        "allow_card": settings.allow_card,
        "allow_ccp": settings.allow_ccp,
        "allow_baridimob": settings.allow_baridimob,
        "allow_stripe": settings.allow_stripe,
        "allow_paypal": settings.allow_paypal,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at,
    }


# ==============================================
# UPSERT RESTAURANT PAYMENT SETTINGS (COMPATIBILITY)
# ==============================================

async def upsert_restaurant_payment_settings(
    *,
    restaurant_id: int,
    allow_cash: bool = True,
    allow_card: bool = True,
    allow_ccp: bool = False,
    allow_baridimob: bool = False,
    allow_stripe: bool = False,
    allow_paypal: bool = False,
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    إنشاء أو تحديث إعدادات الدفع لمطعم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        allow_cash: السماح بالدفع نقداً
        allow_card: السماح بالدفع ببطاقة POS
        allow_ccp: السماح بالدفع عبر CCP
        allow_baridimob: السماح بالدفع عبر بريدي موب
        allow_stripe: السماح بالدفع عبر Stripe
        allow_paypal: السماح بالدفع عبر PayPal
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        إعدادات الدفع المحدثة
    """
    repo = RestaurantPaymentSettingsRepository(session=session)

    settings = await repo.upsert(
        restaurant_id=restaurant_id,
        allow_cash=allow_cash,
        allow_card=allow_card,
        allow_ccp=allow_ccp,
        allow_baridimob=allow_baridimob,
        allow_stripe=allow_stripe,
        allow_paypal=allow_paypal,
    )

    return {
        "id": settings.id,
        "restaurant_id": settings.restaurant_id,
        "allow_cash": settings.allow_cash,
        "allow_card": settings.allow_card,
        "allow_ccp": settings.allow_ccp,
        "allow_baridimob": settings.allow_baridimob,
        "allow_stripe": settings.allow_stripe,
        "allow_paypal": settings.allow_paypal,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at,
    }


# ==============================================
# GET ALLOWED PAYMENT METHODS (COMPATIBILITY)
# ==============================================

async def get_allowed_payment_methods(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> AllowedMethodsList:
    """
    الحصول على قائمة طرق الدفع المسموح بها لمطعم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قائمة طرق الدفع المسموح بها
    """
    repo = RestaurantPaymentSettingsRepository(session=session)

    return await repo.get_allowed_methods(
        restaurant_id=restaurant_id,
    )