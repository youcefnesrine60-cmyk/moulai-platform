# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# ⚡ ACTIONS
# تعريف الإجراءات التي يمكن للوكيل تنفيذها
# ==============================================

from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
)

from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

ActionResult = Dict[str, Any]
ActionHandler = Callable[..., Awaitable[ActionResult]]
ActionMap = Dict[str, ActionHandler]

# ==============================================
# 📦 ACTION RESULT
# ==============================================


@dataclass
class ActionResponse:
    """
    نتيجة تنفيذ الإجراء.
    
    Attributes:
        success: هل نجح الإجراء؟
        message: رسالة للمستخدم
        data: بيانات إضافية
        error: رسالة خطأ (في حالة الفشل)
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==============================================
# ⚡ BASE ACTION
# ==============================================

class BaseAction:
    """
    الفئة الأساسية لجميع الإجراءات.
    
    Attributes:
        name: اسم الإجراء
        description: وصف الإجراء
        requires_confirmation: هل يتطلب تأكيداً؟
        priority: أولوية الإجراء
    """

    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        requires_confirmation: bool = False,
        priority: int = 0,
    ) -> None:
        """
        تهيئة الإجراء.
        
        Args:
            name: اسم الإجراء
            description: وصف الإجراء
            requires_confirmation: هل يتطلب تأكيداً؟
            priority: أولوية الإجراء
        """
        self.name: str = name
        self.description: str = description
        self.requires_confirmation: bool = requires_confirmation
        self.priority: int = priority

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ الإجراء.
        
        Args:
            params: معاملات الإجراء
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
            
        Raises:
            NotImplementedError: يجب تنفيذ هذه الدالة في الفئة الفرعية
        """
        raise NotImplementedError(
            f"Action '{self.name}' must implement execute() method"
        )


# ==============================================
# 🍔 ORDER FOOD ACTION
# ==============================================

class OrderFoodAction(BaseAction):
    """
    إجراء طلب طعام.
    """

    def __init__(self) -> None:
        super().__init__(
            name="order_food",
            description="طلب وجبة أو منتج",
            requires_confirmation=True,
            priority=10,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ طلب طعام.
        
        Args:
            params: معاملات الطلب (product_name, quantity, options, etc.)
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info(
            "action_order_food_executed",
            extra={
                "product_name": params.get("product_name"),
                "quantity": params.get("quantity"),
                "options": params.get("options"),
            },
        )

        # TODO: تنفيذ منطق الطلب الفعلي
        # - التحقق من توفر المنتج
        # - إنشاء الطلب
        # - إضافة العناصر

        return ActionResponse(
            success=True,
            message=f"تم طلب {params.get('quantity', 1)} × {params.get('product_name', 'المنتج')} بنجاح",
            data={
                "order_id": "ORDER-12345",
                "product_name": params.get("product_name"),
                "quantity": params.get("quantity"),
                "total_price": 100.00,
            },
        )


# ==============================================
# 📋 VIEW MENU ACTION
# ==============================================

class ViewMenuAction(BaseAction):
    """
    إجراء عرض القائمة.
    """

    def __init__(self) -> None:
        super().__init__(
            name="view_menu",
            description="عرض قائمة الطعام",
            requires_confirmation=False,
            priority=5,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ عرض القائمة.
        
        Args:
            params: معاملات العرض (category, search, etc.)
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info(
            "action_view_menu_executed",
            extra={
                "category": params.get("category"),
                "search": params.get("search"),
            },
        )

        # TODO: تنفيذ منطق عرض القائمة الفعلي
        # - جلب المنتجات من قاعدة البيانات
        # - تصفية حسب التصنيف أو البحث

        return ActionResponse(
            success=True,
            message="📋 **القائمة**\n\n1. بيتزا مارغريتا - 1500 دج\n2. برجر لحم - 1200 دج\n3. شاورما - 800 دج",
            data={
                "items": [
                    {"name": "بيتزا مارغريتا", "price": 1500},
                    {"name": "برجر لحم", "price": 1200},
                    {"name": "شاورما", "price": 800},
                ],
            },
        )


# ==============================================
# 🏪 VIEW RESTAURANTS ACTION
# ==============================================

class ViewRestaurantsAction(BaseAction):
    """
    إجراء عرض المطاعم.
    """

    def __init__(self) -> None:
        super().__init__(
            name="view_restaurants",
            description="عرض المطاعم المتاحة",
            requires_confirmation=False,
            priority=5,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ عرض المطاعم.
        
        Args:
            params: معاملات العرض (location, type, etc.)
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info(
            "action_view_restaurants_executed",
            extra={
                "location": params.get("location"),
                "type": params.get("type"),
            },
        )

        # TODO: تنفيذ منطق عرض المطاعم الفعلي

        return ActionResponse(
            success=True,
            message="🏪 **المطاعم المتاحة**\n\n1. مطعم البيتزا السريعة - الجزائر\n2. برجر هاوس - وهران\n3. شاورما الشام - قسنطينة",
            data={
                "restaurants": [
                    {"name": "مطعم البيتزا السريعة", "location": "الجزائر"},
                    {"name": "برجر هاوس", "location": "وهران"},
                    {"name": "شاورما الشام", "location": "قسنطينة"},
                ],
            },
        )


# ==============================================
# ✏️ MODIFY ORDER ACTION
# ==============================================

class ModifyOrderAction(BaseAction):
    """
    إجراء تعديل طلب.
    """

    def __init__(self) -> None:
        super().__init__(
            name="modify_order",
            description="تعديل طلب موجود",
            requires_confirmation=True,
            priority=8,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ تعديل الطلب.
        
        Args:
            params: معاملات التعديل (order_id, changes, etc.)
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info(
            "action_modify_order_executed",
            extra={
                "order_id": params.get("order_id"),
                "changes": params.get("changes"),
            },
        )

        # TODO: تنفيذ منطق تعديل الطلب الفعلي

        return ActionResponse(
            success=True,
            message=f"تم تعديل الطلب #{params.get('order_id', 'غير معروف')} بنجاح",
            data={
                "order_id": params.get("order_id"),
                "changes": params.get("changes"),
            },
        )


# ==============================================
# ❌ CANCEL ORDER ACTION
# ==============================================

class CancelOrderAction(BaseAction):
    """
    إجراء إلغاء طلب.
    """

    def __init__(self) -> None:
        super().__init__(
            name="cancel_order",
            description="إلغاء طلب",
            requires_confirmation=True,
            priority=8,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ إلغاء الطلب.
        
        Args:
            params: معاملات الإلغاء (order_id, reason, etc.)
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info(
            "action_cancel_order_executed",
            extra={
                "order_id": params.get("order_id"),
                "reason": params.get("reason"),
            },
        )

        # TODO: تنفيذ منطق إلغاء الطلب الفعلي

        return ActionResponse(
            success=True,
            message=f"تم إلغاء الطلب #{params.get('order_id', 'غير معروف')} بنجاح",
            data={
                "order_id": params.get("order_id"),
                "reason": params.get("reason"),
            },
        )


# ==============================================
# 🔍 TRACK ORDER ACTION
# ==============================================

class TrackOrderAction(BaseAction):
    """
    إجراء تتبع طلب.
    """

    def __init__(self) -> None:
        super().__init__(
            name="track_order",
            description="تتبع طلب",
            requires_confirmation=False,
            priority=7,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ تتبع الطلب.
        
        Args:
            params: معاملات التتبع (order_id, etc.)
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info(
            "action_track_order_executed",
            extra={"order_id": params.get("order_id")},
        )

        # TODO: تنفيذ منطق تتبع الطلب الفعلي

        return ActionResponse(
            success=True,
            message=f"📦 **حالة الطلب #{params.get('order_id', 'غير معروف')}**\n\nالحالة: قيد التحضير\nالوقت المتوقع: 15 دقيقة",
            data={
                "order_id": params.get("order_id"),
                "status": "preparing",
                "estimated_time": "15 دقيقة",
            },
        )


# ==============================================
# 💰 ASK PRICE ACTION
# ==============================================

class AskPriceAction(BaseAction):
    """
    إجراء الاستفسار عن السعر.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ask_price",
            description="الاستفسار عن السعر",
            requires_confirmation=False,
            priority=6,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ الاستفسار عن السعر.
        
        Args:
            params: معاملات الاستفسار (product_name, etc.)
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info(
            "action_ask_price_executed",
            extra={"product_name": params.get("product_name")},
        )

        # TODO: تنفيذ منطق الاستفسار عن السعر الفعلي

        return ActionResponse(
            success=True,
            message=f"💰 **سعر {params.get('product_name', 'المنتج')}**\n\nالسعر: 1500 دج",
            data={
                "product_name": params.get("product_name"),
                "price": 1500.00,
            },
        )


# ==============================================
# 🎁 ASK OFFER ACTION
# ==============================================

class AskOfferAction(BaseAction):
    """
    إجراء الاستفسار عن العروض.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ask_offer",
            description="الاستفسار عن العروض",
            requires_confirmation=False,
            priority=6,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ الاستفسار عن العروض.
        
        Args:
            params: معاملات الاستفسار
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info("action_ask_offer_executed")

        # TODO: تنفيذ منطق الاستفسار عن العروض الفعلي

        return ActionResponse(
            success=True,
            message="🎁 **العروض الحالية**\n\n1. عرض العائلة: 2 بيتزا + مشروب = 2500 دج\n2. عرض الغداء: برجر + مشروب = 1200 دج",
            data={
                "offers": [
                    {"name": "عرض العائلة", "price": 2500},
                    {"name": "عرض الغداء", "price": 1200},
                ],
            },
        )


# ==============================================
# 💬 HELP ACTION
# ==============================================

class HelpAction(BaseAction):
    """
    إجراء المساعدة.
    """

    def __init__(self) -> None:
        super().__init__(
            name="help",
            description="عرض المساعدة",
            requires_confirmation=False,
            priority=1,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ عرض المساعدة.
        
        Args:
            params: معاملات المساعدة
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info("action_help_executed")

        return ActionResponse(
            success=True,
            message="""
📚 **المساعدة المتاحة:**

1. **طلب طعام** - اكتب "أريد طلب" أو "اطلب"
2. **عرض القائمة** - اكتب "القائمة" أو "المنيو"
3. **عرض المطاعم** - اكتب "المطاعم"
4. **تعديل طلب** - اكتب "تعديل الطلب" + رقم الطلب
5. **إلغاء طلب** - اكتب "إلغاء الطلب" + رقم الطلب
6. **تتبع طلب** - اكتب "تتبع الطلب" + رقم الطلب
7. **الأسعار** - اكتب "سعر" + اسم المنتج
8. **العروض** - اكتب "العروض"
""",
            data={},
        )


# ==============================================
# 👋 GREETING ACTION
# ==============================================

class GreetingAction(BaseAction):
    """
    إجراء التحية.
    """

    def __init__(self) -> None:
        super().__init__(
            name="greeting",
            description="التحية والترحيب",
            requires_confirmation=False,
            priority=2,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ التحية.
        
        Args:
            params: معاملات التحية
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info("action_greeting_executed")

        return ActionResponse(
            success=True,
            message="مرحباً بك! 🌟 كيف يمكنني مساعدتك اليوم؟ يمكنك طلب الطعام، عرض القائمة، أو الاستفسار عن العروض.",
            data={},
        )


# ==============================================
# 👋 GOODBYE ACTION
# ==============================================

class GoodbyeAction(BaseAction):
    """
    إجراء الوداع.
    """

    def __init__(self) -> None:
        super().__init__(
            name="goodbye",
            description="الوداع",
            requires_confirmation=False,
            priority=2,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ الوداع.
        
        Args:
            params: معاملات الوداع
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info("action_goodbye_executed")

        return ActionResponse(
            success=True,
            message="مع السلامة! 👋 نتمنى أن نراك مجدداً، في أي وقت تحتاج مساعدة نحن هنا.",
            data={},
        )


# ==============================================
# 😤 COMPLAINT ACTION
# ==============================================

class ComplaintAction(BaseAction):
    """
    إجراء التعامل مع الشكوى.
    """

    def __init__(self) -> None:
        super().__init__(
            name="complaint",
            description="معالجة شكوى",
            requires_confirmation=False,
            priority=9,
        )

    async def execute(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        """
        تنفيذ معالجة الشكوى.
        
        Args:
            params: معاملات الشكوى (order_id, issue, etc.)
            context: سياق التنفيذ
            
        Returns:
            ActionResponse: نتيجة التنفيذ
        """
        logger.info(
            "action_complaint_executed",
            extra={
                "order_id": params.get("order_id"),
                "issue": params.get("issue"),
            },
        )

        # TODO: تنفيذ منطق معالجة الشكوى الفعلي

        return ActionResponse(
            success=True,
            message="تم تسجيل شكواك وسيتم التواصل معك قريباً لحل المشكلة. 🙏",
            data={
                "complaint_id": "CMP-12345",
                "order_id": params.get("order_id"),
                "issue": params.get("issue"),
            },
        )


# ==============================================
# 📋 ACTION REGISTRY
# ==============================================

class ActionRegistry:
    """
    سجل الإجراءات - يدير جميع الإجراءات المتاحة.
    """

    def __init__(self) -> None:
        """
        تهيئة سجل الإجراءات.
        """
        self._actions: Dict[str, BaseAction] = {}
        self._register_default_actions()

    def _register_default_actions(self) -> None:
        """
        تسجيل الإجراءات الافتراضية.
        """
        actions = [
            OrderFoodAction(),
            ViewMenuAction(),
            ViewRestaurantsAction(),
            ModifyOrderAction(),
            CancelOrderAction(),
            TrackOrderAction(),
            AskPriceAction(),
            AskOfferAction(),
            ComplaintAction(),
            HelpAction(),
            GreetingAction(),
            GoodbyeAction(),
        ]

        for action in actions:
            self.register(action)

        logger.info(
            "action_registry_initialized",
            extra={"action_count": len(self._actions)},
        )

    def register(self, action: BaseAction) -> None:
        """
        تسجيل إجراء.
        
        Args:
            action: الإجراء المراد تسجيله
        """
        self._actions[action.name] = action
        logger.debug(
            "action_registered",
            extra={
                "actions_name": action.name,
                "priority": action.priority,
            },
        )

    def get(self, name: str) -> Optional[BaseAction]:
        """
        الحصول على إجراء بالاسم.
        
        Args:
            name: اسم الإجراء
            
        Returns:
            الإجراء أو None
        """
        return self._actions.get(name)

    def get_all(self) -> List[BaseAction]:
        """
        الحصول على جميع الإجراءات.
        
        Returns:
            قائمة الإجراءات
        """
        return sorted(
            self._actions.values(),
            key=lambda a: -a.priority,  # ترتيب تنازلي حسب الأولوية
        )

    def get_names(self) -> List[str]:
        """
        الحصول على أسماء جميع الإجراءات.
        
        Returns:
            قائمة الأسماء
        """
        return list(self._actions.keys())

    def get_by_intent(self, intent: str) -> Optional[BaseAction]:
        """
        الحصول على الإجراء المناسب لنية معينة.
        
        Args:
            intent: اسم النية
            
        Returns:
            الإجراء المناسب أو None
        """
        # خريطة النوايا إلى الإجراءات
        intent_to_action = {
            "order_food": "order_food",
            "view_menu": "view_menu",
            "view_restaurants": "view_restaurants",
            "modify_order": "modify_order",
            "cancel_order": "cancel_order",
            "track_order": "track_order",
            "ask_price": "ask_price",
            "ask_offer": "ask_offer",
            "complaint": "complaint",
            "help": "help",
            "greeting": "greeting",
            "goodbye": "goodbye",
        }

        action_name = intent_to_action.get(intent)
        if action_name:
            return self.get(action_name)

        return None


# ==============================================
# 🌍 GLOBAL REGISTRY
# ==============================================

# إنشاء سجل إجراءات عالمي
action_registry = ActionRegistry()


# ==============================================
# 🔍 UTILITY FUNCTIONS
# ==============================================

# ==============================================
# GET ACTION
# ==============================================

def get_action(name: str) -> Optional[BaseAction]:
    """
    الحصول على إجراء بالاسم (دالة مساعدة).
    
    Args:
        name: اسم الإجراء
        
    Returns:
        الإجراء أو None
    """
    logger.debug(
        "get_action_called",
        extra={"actions_name": name},
    )

    return action_registry.get(name)


# ==============================================
# GET ACTION BY INTENT
# ==============================================

def get_action_by_intent(intent: str) -> Optional[BaseAction]:
    """
    الحصول على إجراء حسب النية (دالة مساعدة).
    
    Args:
        intent: اسم النية
        
    Returns:
        الإجراء أو None
    """
    logger.debug(
        "get_action_by_intent_called",
        extra={"intent": intent},
    )

    return action_registry.get_by_intent(intent)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [

    # Base
    "BaseAction",
    "ActionResponse",
    "ActionResult",
    "ActionHandler",
    "ActionMap",

    # Actions
    "OrderFoodAction",
    "ViewMenuAction",
    "ViewRestaurantsAction",
    "ModifyOrderAction",
    "CancelOrderAction",
    "TrackOrderAction",
    "AskPriceAction",
    "AskOfferAction",
    "ComplaintAction",
    "HelpAction",
    "GreetingAction",
    "GoodbyeAction",

    # Registry
    "ActionRegistry",
    "action_registry",

    # Utilities
    "get_action",
    "get_action_by_intent",
]