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
from datetime import datetime
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
)
from sqlalchemy import or_, select

from app.core.exceptions import NotFoundError, ValidationError
from app.core.database import AsyncSessionLocal
from app.core.logger import logger
from app.models.loyalty_discount import Promotion
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.repositories.products_repo import ProductRepository
from app.repositories.user_repo import UserRepository
from app.services.business.orders.placement import quote_customer_order, place_customer_order
from app.services.business.orders.customer import (
    cancel_customer_order,
    change_customer_order_item_quantity,
    get_customer_order,
)
from app.services.business.complaints import create_customer_complaint


def _request_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not context:
        return {}
    return context.get("request_context", {})


def _restaurant_id(
    *,
    params: Dict[str, Any],
    context: Optional[Dict[str, Any]],
) -> Optional[int]:
    value = params.get("restaurant_id") or _request_context(context).get("restaurant_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None



def _order_restaurant_scope(params, context):
    """The channel's restaurant takes precedence over extracted entities.

    A missing scope denotes the global customer account; an invalid supplied
    scope fails closed by matching no restaurant.
    """
    request = _request_context(context)
    value = request.get("restaurant_id", params.get("restaurant_id"))
    if value is None:
        return None
    try:
        return int(value) if not isinstance(value, bool) and int(value) > 0 else 0
    except (TypeError, ValueError):
        return 0


def _chat_id(context: Optional[Dict[str, Any]]) -> Optional[int]:
    if not context:
        return None
    value = context.get("user_id") or _request_context(context).get("chat_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def _find_products(
    *,
    product_name: Optional[str],
    restaurant_id: Optional[int],
) -> list[Any]:
    if not product_name:
        return []
    async with AsyncSessionLocal() as session:
        repository = ProductRepository(session=session)
        products = await repository.search(
            query=str(product_name).strip(),
            restaurant_id=restaurant_id,
            limit=20,
        )
        return [
            product for product in products
            if product.restaurant and product.restaurant.is_active
        ]


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

    def _order_arguments(self, params, context):
        return dict(chat_id=_chat_id(context), product_name=params.get("product_name"),
                    product_id=params.get("product_id"), quantity=params.get("quantity", 1),
                    restaurant_id=_order_restaurant_scope(params, context))

    async def prepare(self, *, params, context=None):
        try:
            async with AsyncSessionLocal() as session:
                quote = await quote_customer_order(
                    **self._order_arguments(params, context), session=session)
        except (NotFoundError, ValidationError) as error:
            return ActionResponse(False, error.message, error=error.error_code)
        return ActionResponse(True,
            f"{quote['quantity']} x {quote['product_name']} : {quote['quoted_total']:.2f} DZD",
            data=quote)

    async def execute(self, *, params, context=None):
        try:
            async with AsyncSessionLocal() as session:
                result = await place_customer_order(
                    **self._order_arguments(params, context), session=session,
                    quoted_unit_price=params.get("quoted_unit_price"),
                    order_type=params.get("order_type", "takeaway"),
                    delivery_address=params.get("delivery_address"),
                    customer_note=params.get("customer_note"))
        except (NotFoundError, ValidationError) as error:
            return ActionResponse(False, error.message, error=error.error_code)
        return ActionResponse(True,
            f"Order {result['order_number']}: {result['quantity']} x {result['product_name']}, {result['total_price']:.2f} DZD",
            data=result)


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

        restaurant_id = _restaurant_id(params=params, context=context)
        async with AsyncSessionLocal() as session:
            if not restaurant_id:
                result = await session.execute(
                    select(Restaurant).where(Restaurant.is_active == True).order_by(Restaurant.name),
                )
                restaurants = result.scalars().all()
                if not restaurants:
                    return ActionResponse(False, "لا توجد مطاعم متاحة حالياً.", error="restaurants_not_found")
                lines = [f"{restaurant.id}. {restaurant.name} - {restaurant.wilaya}" for restaurant in restaurants]
                return ActionResponse(
                    True,
                    "اختر مطعماً لعرض قائمته:\n" + "\n".join(lines),
                    data={"restaurants": [{"id": r.id, "name": r.name} for r in restaurants]},
                )
            repository = ProductRepository(session=session)
            products = await repository.get_by_restaurant_id(
                restaurant_id=restaurant_id,
                only_available=True,
                category_id=params.get("category_id"),
                limit=100,
            )
            if params.get("search"):
                products = [
                    product for product in products
                    if str(params["search"]).casefold() in str(product.name).casefold()
                ]
            if not products:
                return ActionResponse(False, "لا توجد منتجات متاحة في هذا المطعم حالياً.", error="menu_empty")
            items = [{"id": p.id, "name": p.name, "price": p.price} for p in products]
            message = "📋 القائمة الفعلية:\n" + "\n".join(
                f"{item['id']}. {item['name']} - {item['price']:.2f} دج"
                for item in items
            )
            return ActionResponse(True, message, data={"items": items})


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

        async with AsyncSessionLocal() as session:
            statement = select(Restaurant).where(Restaurant.is_active == True)
            if params.get("location"):
                statement = statement.where(Restaurant.wilaya.ilike(f"%{params['location']}%"))
            restaurants = (await session.execute(statement.order_by(Restaurant.name))).scalars().all()
        data = [
            {"id": restaurant.id, "name": restaurant.name, "location": restaurant.wilaya}
            for restaurant in restaurants
        ]
        if not data:
            return ActionResponse(False, "لا توجد مطاعم متاحة حالياً.", error="restaurants_not_found")
        return ActionResponse(
            True,
            "🏪 المطاعم المتاحة:\n" + "\n".join(
                f"{r['id']}. {r['name']} - {r['location']}" for r in data
            ),
            data={"restaurants": data},
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

        chat_id = _chat_id(context)
        if not chat_id:
            return ActionResponse(False, "تعذر التحقق من ملكية الطلب.", error="user_not_found")
        order_reference = params.get("order_id")
        if order_reference is None or not str(order_reference).strip():
            return ActionResponse(False, "أرسل رقم الطلب الذي تريد تعديله.", error="missing_order_id")
        try:
            quantity = int(params.get("quantity"))
        except (TypeError, ValueError):
            quantity = 0
        if quantity <= 0:
            return ActionResponse(False, "أرسل الكمية الجديدة المطلوبة.", error="invalid_order_quantity")

        async with AsyncSessionLocal() as session:
            try:
                order, item = await change_customer_order_item_quantity(
                    chat_id=chat_id,
                    restaurant_id=_order_restaurant_scope(params, context),
                    order_reference=order_reference,
                    product_name=params.get("product_name"),
                    quantity=quantity,
                    session=session,
                )
            except NotFoundError:
                return ActionResponse(
                    False,
                    "لم أجد هذا الطلب ضمن طلبات حسابك.",
                    error="order_not_found",
                )
            except ValidationError as error:
                error_codes = {
                    "ORDER_NOT_MODIFIABLE": "order_not_modifiable",
                    "ORDER_ITEM_NOT_FOUND": "order_item_not_found",
                    "ORDER_ITEM_AMBIGUOUS": "order_item_ambiguous",
                    "INVALID_ORDER_QUANTITY": "invalid_order_quantity",
                }
                error_code = error_codes.get(error.error_code or "", "action_failed")
                return ActionResponse(False, error.message, error=error_code)

        return ActionResponse(
            True,
            f"تم تحديث كمية {item.product_name} في الطلب رقم {order.order_number} إلى {item.quantity}. الإجمالي الجديد: {order.total_amount:.2f} دج.",
            data={
                "order_id": order.id,
                "order_number": order.order_number,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "total_amount": order.total_amount,
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

        chat_id = _chat_id(context)
        if not chat_id:
            return ActionResponse(False, "تعذر التحقق من ملكية الطلب.", error="user_not_found")
        order_number = params.get("order_id")
        if order_number is None or not str(order_number).strip():
            return ActionResponse(
                False,
                "أرسل رقم الطلب الذي تريد إلغاءه.",
                error="missing_order_id",
            )
        async with AsyncSessionLocal() as session:
            try:
                order, previous_status = await cancel_customer_order(
                    chat_id=chat_id,
                    restaurant_id=_order_restaurant_scope(params, context),
                    order_reference=order_number,
                    reason=params.get("reason"),
                    session=session,
                )
            except NotFoundError:
                return ActionResponse(
                    False,
                    "لم أجد هذا الطلب ضمن طلبات حسابك.",
                    error="order_not_found",
                )
            except ValidationError:
                return ActionResponse(
                    False,
                    "لا يمكن إلغاء الطلب في حالته الحالية.",
                    error="order_not_cancellable",
                )
        return ActionResponse(
            True,
            f"تم إلغاء الطلب رقم {order.order_number}.",
            data={"order_id": order.id, "order_number": order.order_number, "previous_status": previous_status},
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

        chat_id = _chat_id(context)
        if not chat_id:
            return ActionResponse(False, "تعذر التحقق من طلبات هذا الحساب.", error="user_not_found")
        order_number = params.get("order_id")
        if order_number is None or not str(order_number).strip():
            return ActionResponse(
                False,
                "أرسل رقم الطلب الذي تريد تتبعه.",
                error="missing_order_id",
            )
        async with AsyncSessionLocal() as session:
            order = await get_customer_order(
                chat_id=chat_id,
                restaurant_id=_order_restaurant_scope(params, context),
                order_reference=order_number,
                session=session,
            )
        if not order:
            return ActionResponse(False, "لم أجد طلباً مطابقاً ضمن طلبات حسابك.", error="order_not_found")
        return ActionResponse(
            True,
            f"📦 الطلب رقم {order.order_number}\nالحالة الفعلية: {order.status}\nالإجمالي: {order.total_amount:.2f} دج",
            data={
                "order_id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": order.total_amount,
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

        restaurant_id = _restaurant_id(params=params, context=context)
        products = await _find_products(
            product_name=params.get("product_name"),
            restaurant_id=restaurant_id,
        )
        if not products:
            return ActionResponse(False, "لم أجد هذا المنتج في القائمة المتاحة.", error="product_not_found")
        if len(products) > 1:
            return ActionResponse(
                False,
                "يوجد أكثر من منتج مطابق. حدّد المطعم أو الاسم الكامل.",
                error="ambiguous_product",
            )
        product = products[0]
        return ActionResponse(
            True,
            f"سعر {product.name} هو {product.price:.2f} دج.",
            data={"product_id": product.id, "product_name": product.name, "price": product.price},
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

        restaurant_id = _restaurant_id(params=params, context=context)
        now = datetime.now()
        statement = select(Promotion).where(Promotion.active == True)
        if restaurant_id:
            statement = statement.where(
                or_(Promotion.restaurant_id == restaurant_id, Promotion.restaurant_id.is_(None)),
            )
        async with AsyncSessionLocal() as session:
            promotions = (await session.execute(statement.order_by(Promotion.name))).scalars().all()
        promotions = [
            promotion for promotion in promotions
            if (promotion.starts_at is None or promotion.starts_at <= now)
            and (promotion.expires_at is None or promotion.expires_at >= now)
        ]
        if not promotions:
            return ActionResponse(False, "لا توجد عروض سارية حالياً.", error="offers_not_found")
        offers = [
            {"id": p.id, "name": p.name, "discount_percent": p.discount_percent}
            for p in promotions
        ]
        return ActionResponse(
            True,
            "🎁 العروض السارية:\n" + "\n".join(
                f"- {offer['name']}: خصم {offer['discount_percent']:.2f}%"
                for offer in offers
            ),
            data={"offers": offers},
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
4. **تعديل الكمية** - اكتب "تعديل الكمية" + رقم الطلب + اسم المنتج + الكمية الجديدة (للطلبات قيد الانتظار)
5. **إلغاء طلب** - اكتب "إلغاء الطلب" + رقم الطلب
6. **تتبع طلب** - اكتب "تتبع الطلب" + رقم الطلب
7. **الأسعار** - اكتب "سعر" + اسم المنتج
8. **العروض** - اكتب "العروض"

9. **تقديم شكوى** - اكتب وصف المشكلة، ثم اختر المطعم أو أرفق رقم الطلب.
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
            description="تسجيل شكوى",
            requires_confirmation=True,
            priority=9,
        )

    async def prepare(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        description = (
            params.get("description")
            or params.get("issue")
            or params.get("message")
            or (context.get("message") if context else None)
        )
        if not isinstance(description, str) or not description.strip():
            return ActionResponse(
                False,
                "اكتب وصفاً مختصراً للمشكلة قبل تسجيل الشكوى.",
                error="complaint_description_required",
            )

        description = description.strip()
        if len(description) > 5000:
            return ActionResponse(
                False,
                "يجب ألا يتجاوز وصف الشكوى 5000 حرف.",
                error="invalid_complaint_description",
            )
        order_reference = params.get("order_id")
        restaurant_id = _restaurant_id(params={}, context=context)
        if restaurant_id is None and not order_reference:
            return ActionResponse(
                False,
                "اختر المطعم أو أرفق رقم طلبك حتى أتمكن من توجيه الشكوى.",
                error="complaint_restaurant_required",
            )

        language = params.get("language", "ar")
        preview = description if len(description) <= 300 else description[:297] + "..."
        confirmation_messages = {
            "ar": f"سأسجل شكوى بهذا الوصف:\n{preview}\n\nهل تؤكد؟ (نعم/لا)",
            "en": f"I will register this complaint:\n{preview}\n\nConfirm? (Yes/No)",
            "fr": f"Je vais enregistrer cette réclamation :\n{preview}\n\nConfirmer ? (Oui/Non)",
        }
        return ActionResponse(
            True,
            confirmation_messages.get(language, confirmation_messages["en"]),
            data={"description": description},
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
                "restaurant_id": _restaurant_id(params={}, context=context),
            },
        )
        chat_id = _chat_id(context)
        if not chat_id:
            return ActionResponse(False, "تعذر التحقق من حسابك.", error="user_not_found")

        description = (
            params.get("description")
            or params.get("issue")
            or params.get("message")
            or (context.get("message") if context else None)
        )
        if not isinstance(description, str) or not description.strip():
            return ActionResponse(
                False,
                "اكتب وصفاً مختصراً للمشكلة قبل تسجيل الشكوى.",
                error="complaint_description_required",
            )

        async with AsyncSessionLocal() as session:
            try:
                complaint = await create_customer_complaint(
                    chat_id=chat_id,
                    restaurant_id=_restaurant_id(params={}, context=context),
                    order_reference=params.get("order_id"),
                    description=description,
                    session=session,
                )
            except NotFoundError as error:
                error_code = (
                    "order_not_found"
                    if error.error_code == "ORDER_NOT_FOUND"
                    else "user_not_found"
                    if error.error_code == "USER_NOT_FOUND"
                    else "complaint_restaurant_not_found"
                )
                return ActionResponse(False, error.message, error=error_code)
            except ValidationError as error:
                error_codes = {
                    "CUSTOMER_CONSENT_REQUIRED": "customer_consent_required",
                    "INVALID_COMPLAINT_DESCRIPTION": "invalid_complaint_description",
                    "COMPLAINT_ORDER_RESTAURANT_MISMATCH": "complaint_order_restaurant_mismatch",
                    "COMPLAINT_RESTAURANT_REQUIRED": "complaint_restaurant_required",
                }
                return ActionResponse(
                    False,
                    error.message,
                    error=error_codes.get(error.error_code or "", "action_failed"),
                )

        complaint_messages = {
            "ar": f"تم تسجيل الشكوى بنجاح. رقم البلاغ: {complaint.id}.",
            "en": f"Your complaint has been registered. Ticket number: {complaint.id}.",
            "fr": f"Votre réclamation a été enregistrée. Numéro du ticket : {complaint.id}.",
        }
        language = params.get("language", "ar")
        return ActionResponse(
            True,
            complaint_messages.get(language, complaint_messages["en"]),
            data={"complaint_id": complaint.id},
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
