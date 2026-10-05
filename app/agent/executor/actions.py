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

from app.core.database import AsyncSessionLocal
from app.core.logger import logger
from app.models.loyalty_discount import Promotion
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.models.user import User
from app.repositories.order_status_history_repo import OrderStatusHistoryRepository
from app.repositories.orders_repo import OrdersRepository
from app.repositories.products_repo import ProductRepository
from app.repositories.user_repo import UserRepository
from app.services.business.orders.create import create_order_with_items


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


async def _find_owned_order(
    *,
    chat_id: int,
    order_number: Optional[Any],
    session: Any,
) -> Optional[Order]:
    statement = (
        select(Order)
        .join(User, Order.user_id == User.id)
        .where(User.chat_id == chat_id)
    )
    if order_number is not None:
        reference = str(order_number).strip()
        conditions = [Order.order_number == reference]
        if reference.isdigit():
            conditions.append(Order.id == int(reference))
        statement = statement.where(or_(*conditions))
    return (await session.execute(
        statement.order_by(Order.created_at.desc()).limit(1),
    )).scalar_one_or_none()

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

    async def prepare(
        self,
        *,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionResponse:
        chat_id = _chat_id(context)
        restaurant_id = _restaurant_id(params=params, context=context)
        product_name = params.get("product_name")
        try:
            quantity = int(params.get("quantity", 1))
        except (TypeError, ValueError):
            quantity = 0
        if not chat_id or quantity <= 0 or (not product_name and not params.get("product_id")):
            return ActionResponse(False, "أحتاج إلى المنتج والكمية قبل إعداد الطلب.", error="missing_order_details")

        async with AsyncSessionLocal() as session:
            user = await UserRepository(session=session).get_by_chat_id(chat_id=chat_id)
            if not user or not user.consent:
                return ActionResponse(
                    False,
                    "يرجى الموافقة على شروط الاستخدام قبل إنشاء طلب.",
                    error="customer_consent_required",
                )

        if params.get("product_id"):
            async with AsyncSessionLocal() as session:
                product = await ProductRepository(session=session).get_by_id(id=int(params["product_id"]))
                products = [product] if product and product.is_available else []
                if product and restaurant_id and product.restaurant_id != restaurant_id:
                    products = []
                if product:
                    restaurant = await session.get(Restaurant, product.restaurant_id)
                    if not restaurant or not restaurant.is_active:
                        products = []
        else:
            products = await _find_products(
                product_name=str(product_name),
                restaurant_id=restaurant_id,
            )
        if not products:
            return ActionResponse(False, "لم أجد منتجاً متاحاً بهذا الاسم.", error="product_not_found")
        if len(products) > 1:
            return ActionResponse(False, "يوجد أكثر من منتج مطابق. حدّد المنتج والمطعم.", error="ambiguous_product")

        product = products[0]
        unit_price = float(product.price)
        total = unit_price * quantity
        return ActionResponse(
            True,
            f"الطلب: {quantity} × {product.name}\nسعر الوحدة: {unit_price:.2f} دج\nالإجمالي: {total:.2f} دج",
            data={
                "product_id": product.id,
                "product_name": product.name,
                "restaurant_id": product.restaurant_id,
                "user_id": user.id,
                "quantity": quantity,
                "quoted_unit_price": unit_price,
                "quoted_total": total,
            },
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

        chat_id = _chat_id(context)
        product_name = params.get("product_name")
        restaurant_id = _restaurant_id(params=params, context=context)
        try:
            quantity = int(params.get("quantity", 1))
        except (TypeError, ValueError):
            quantity = 0
        if not chat_id or quantity <= 0 or (not product_name and not params.get("product_id")):
            return ActionResponse(
                success=False,
                message="لا أملك معلومات كافية لإنشاء الطلب. اذكر المنتج والكمية أولاً.",
                error="missing_order_details",
            )

        async with AsyncSessionLocal() as session:
            repository = ProductRepository(session=session)
            if params.get("product_id"):
                product = await repository.get_by_id(id=int(params["product_id"]))
                products = [product] if product and product.is_available else []
                if product and restaurant_id and product.restaurant_id != restaurant_id:
                    products = []
                if product:
                    restaurant = await session.get(Restaurant, product.restaurant_id)
                    if not restaurant or not restaurant.is_active:
                        products = []
            else:
                products = await repository.search(
                    query=str(product_name).strip(),
                    restaurant_id=restaurant_id,
                    limit=20,
                )
            if not products:
                return ActionResponse(
                    success=False,
                    message="لم أجد منتجاً متاحاً بهذا الاسم. تحقق من الاسم أو اختر مطعماً أولاً.",
                    error="product_not_found",
                )
            if len(products) > 1:
                choices = "\n".join(
                    f"- {product.name} ({product.price:.2f} دج)"
                    for product in products[:8]
                )
                return ActionResponse(
                    success=False,
                    message=f"وجدت أكثر من منتج مطابق. حدّد المنتج والمطعم:\n{choices}",
                    error="ambiguous_product",
                )

            product = products[0]
            quoted_price = params.get("quoted_unit_price")
            if quoted_price is not None and abs(float(quoted_price) - float(product.price)) > 0.000001:
                return ActionResponse(
                    success=False,
                    message="تغير سعر المنتج منذ إعداد الطلب. لم يتم إنشاء الطلب؛ أعد المحاولة لمراجعة السعر الجديد.",
                    error="product_price_changed",
                )
            user = await UserRepository(session=session).get_by_chat_id(chat_id=chat_id)
            if not user or not user.consent:
                return ActionResponse(
                    success=False,
                    message="يرجى الموافقة على شروط الاستخدام قبل إنشاء طلب.",
                    error="customer_consent_required",
                )

            order_type = params.get("order_type", "takeaway")
            delivery_address = params.get("delivery_address")
            if order_type == "delivery" and not delivery_address:
                return ActionResponse(
                    success=False,
                    message="أرسل عنوان التوصيل قبل تأكيد طلب التوصيل.",
                    error="missing_delivery_address",
                )

            unit_price = float(product.price)
            subtotal = unit_price * quantity
            order_id = await create_order_with_items(
                restaurant_id=product.restaurant_id,
                branch_id=None,
                table_id=None,
                employee_id=None,
                user_id=user.id,
                order_type=order_type,
                customer_name=None,
                customer_phone=None,
                delivery_address=delivery_address,
                customer_note=params.get("customer_note"),
                subtotal_amount=subtotal,
                discount_amount=0,
                tax_amount=0,
                delivery_amount=0,
                total_amount=subtotal,
                items=[{
                    "product_id": product.id,
                    "product_name": product.name,
                    "unit_price": unit_price,
                    "quantity": quantity,
                    "total_price": subtotal,
                }],
                session=session,
            )
            order = await session.get(Order, order_id)
            order_number = order.order_number if order else str(order_id)

        return ActionResponse(
            success=True,
            message=f"تم إنشاء الطلب رقم {order_number}: {quantity} × {product.name}، الإجمالي {subtotal:.2f} دج.",
            data={
                "order_id": order_id,
                "order_number": order_number,
                "product_id": product.id,
                "product_name": product.name,
                "quantity": quantity,
                "total_price": subtotal,
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
            requires_confirmation=False,
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

        return ActionResponse(
            success=False,
            message="تعديل عناصر الطلب عبر المحادثة غير متاح حالياً. لم يتم تغيير الطلب.",
            error="order_modification_not_supported",
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
        async with AsyncSessionLocal() as session:
            order = await _find_owned_order(
                chat_id=chat_id,
                order_number=params.get("order_id"),
                session=session,
            )
            if not order:
                return ActionResponse(False, "لم أجد هذا الطلب ضمن طلبات حسابك.", error="order_not_found")
            if order.status not in {"pending", "confirmed"}:
                return ActionResponse(
                    False,
                    f"لا يمكن إلغاء الطلب في حالته الحالية ({order.status}).",
                    error="order_not_cancellable",
                )
            previous_status = order.status
            await OrdersRepository(session=session).update(
                id=order.id,
                data={"status": "cancelled"},
            )
            await OrderStatusHistoryRepository(session=session).create(
                data={
                    "order_id": order.id,
                    "status": "cancelled",
                    "employee_id": None,
                    "note": params.get("reason") or "تم الإلغاء بواسطة العميل عبر الوكيل",
                },
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
        async with AsyncSessionLocal() as session:
            order = await _find_owned_order(
                chat_id=chat_id,
                order_number=params.get("order_id"),
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
4. **إلغاء طلب** - اكتب "إلغاء الطلب" + رقم الطلب
5. **تتبع طلب** - اكتب "تتبع الطلب" + رقم الطلب
6. **الأسعار** - اكتب "سعر" + اسم المنتج
7. **العروض** - اكتب "العروض"

تعديل الطلبات وتسجيل الشكاوى غير متاحين حالياً؛ لم يتم تنفيذ تعديل أو إنشاء بلاغ.
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

        return ActionResponse(
            success=False,
            message="تسجيل الشكاوى غير متاح حالياً. لم يتم إنشاء بلاغ.",
            error="complaint_registration_not_supported",
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