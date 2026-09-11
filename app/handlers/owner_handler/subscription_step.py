# ==============================================
# 💳 SUBSCRIPTION STEP
# عرض الباقات وحساب سعر الاشتراك لصاحب المحل
# (بعد موافقة المسؤول على طلب التسجيل)
# ==============================================

from datetime import datetime, timezone

from app.core.logger import logger

from app.views.ui import button

from app.helpers.ui_manager import UIManager
from app.repositories.state_repo import get_state, set_state
from app.repositories.subscription_plan_repo import get_active_subscription_plans

from app.repositories.products_repo import count_restaurant_products
from app.repositories.categories_repo import get_restaurant_categories
from app.repositories.branches_repo import count_restaurant_branches
from app.repositories.restaurant.restaurant_repo import get_restaurants_by_owner
from app.repositories.owner_repo import get_owner_created_at

# ✅ إضافة استيراد orders_repo
from app.repositories.orders_repo import get_restaurant_orders

from app.services.business.pricing_service import calculate_subscription_pricing

from app.views.subscription_ui import (
    subscription_ui,
)


# ==============================================
# 💳 SHOW SUBSCRIPTION PLANS (OWNER)
# عرض الباقات المتاحة لصاحب المحل
# ==============================================

async def show_subscription_plans_for_owner(
    *,
    chat_id: int,
    owner_id: int,
    restaurant_id: int,
) -> None:
    """
    عرض الباقات المتاحة للاشتراك لصاحب المحل
    بعد موافقة المسؤول على طلب التسجيل
    
    Args:
        chat_id: معرف المستخدم
        owner_id: معرف المالك
        restaurant_id: معرف المطعم
    """
    logger.info(
        "show_subscription_plans_for_owner",
        extra={
            "chat_id": chat_id,
            "owner_id": owner_id,
            "restaurant_id": restaurant_id,
        },
    )

    # ==========================================
    # 1️⃣ جلب الباقات النشطة
    # ==========================================

    plans = await get_active_subscription_plans()

    if not plans:
        logger.warning(
            "no_active_plans_for_owner",
            extra={
                "chat_id": chat_id,
                "owner_id": owner_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text="⚠️ لا توجد باقات متاحة حالياً. يرجى التواصل مع الدعم.",
            reply_markup=None,
        )
        return

    # ==========================================
    # 2️⃣ حفظ بيانات المالك والمطعم في الحالة
    # ==========================================

    state = await get_state(chat_id=chat_id)

    if not state:
        state = {}

    state["owner_id"] = owner_id
    state["restaurant_id"] = restaurant_id
    state["step"] = "subscription"

    await set_state(
        chat_id=chat_id,
        state=state,
    )

    # ==========================================
    # 3️⃣ عرض واجهة الباقات
    # ==========================================

    plans_ui = await subscription_ui(
        plans=plans,
        current_plan_id=None,
    )

    await UIManager.update(
        chat_id=chat_id,
        text=plans_ui.get("text", "💳 باقات الاشتراك"),
        reply_markup=plans_ui.get("inline_keyboard"),
    )


# ==============================================
# 💳 CALCULATE SUBSCRIPTION PRICE (OWNER)
# حساب سعر الاشتراك لصاحب المحل
# ==============================================

async def calculate_subscription_price_for_owner(
    *,
    chat_id: int,
    plan_id: int,
) -> None:
    """
    حساب سعر الاشتراك لباقة معينة لصاحب المحل
    
    Args:
        chat_id: معرف المستخدم
        plan_id: معرف الباقة
    """
    logger.info(
        "calculate_subscription_price_for_owner",
        extra={
            "chat_id": chat_id,
            "plan_id": plan_id,
        },
    )

    # ==========================================
    # 1️⃣ جلب حالة المستخدم
    # ==========================================

    state = await get_state(chat_id=chat_id)

    if not state:
        logger.warning(
            "state_not_found_price_calculation",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    restaurant_id = state.get("restaurant_id")
    owner_id = state.get("owner_id")

    if not restaurant_id or not owner_id:
        logger.warning(
            "missing_restaurant_or_owner",
            extra={
                "chat_id": chat_id,
                "restaurant_id": restaurant_id,
                "owner_id": owner_id,
            },
        )
        return

    # ==========================================
    # 2️⃣ جلب بيانات المطعم وحجمه
    # ==========================================

    # 🔢 عدد المنتجات
    products_count = await count_restaurant_products(
        restaurant_id=restaurant_id,
    )

    # 🔢 عدد الأقسام
    categories = await get_restaurant_categories(
        restaurant_id=restaurant_id,
    )
    categories_count = len(categories)

    # 🔢 عدد الفروع
    branches_count = await count_restaurant_branches(
        restaurant_id=restaurant_id,
    )

    # 🔢 عدد المطاعم المملوكة لنفس المالك
    restaurants = await get_restaurants_by_owner(
        owner_id=owner_id,
    )
    restaurants_count = len(restaurants)

    # 🔢 عدد سنوات التواجد في المنصة
    created_at = await get_owner_created_at(
        owner_id=owner_id,
    )

    if created_at:
        years_with_platform = (datetime.now(timezone.utc) - created_at).days // 365
    else:
        years_with_platform = 0

    # ==========================================
    # 📦 جلب عدد الطلبات الشهرية 
    # ==========================================

    # ✅ جلب جميع طلبات المطعم
    orders = await get_restaurant_orders(
        restaurant_id=restaurant_id,
    )

    # ✅ حساب عدد الطلبات الشهرية (آخر 30 يوماً)
    from datetime import timedelta
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    monthly_orders = sum(
        1 for order in orders
        if order.get("created_at") and order["created_at"] >= thirty_days_ago
    )

    # ==========================================
    # 💰 حساب متوسط قيمة الطلب
    # ==========================================

    # ✅ حساب متوسط قيمة الطلبات المكتملة
    completed_orders = [
        order for order in orders
        if order.get("status") == "completed"
    ]

    if completed_orders:
        total_amount = sum(
            float(order.get("total_amount", 0))
            for order in completed_orders
        )
        average_order_value = total_amount / len(completed_orders)
    else:
        average_order_value = 0

    # ==========================================
    # 3️⃣ حساب السعر
    # ==========================================

    pricing = await calculate_subscription_pricing(
        plan_id=plan_id,
        billing_cycle="monthly",
        payment_method="electronic",
        restaurants_count=restaurants_count,
        branches_count=branches_count,
        years_with_platform=years_with_platform,
        products_count=products_count,
        categories_count=categories_count,
        monthly_orders=monthly_orders,
        average_order_value=average_order_value,
        additional_feature_ids=None,
    )

    # ==========================================
    # 4️⃣ حفظ خطة الاشتراك المختارة في الحالة
    # ==========================================

    state["selected_plan_id"] = plan_id
    state["pricing_result"] = pricing

    await set_state(
        chat_id=chat_id,
        state=state,
    )

    # ==========================================
    # 5️⃣ عرض تفاصيل السعر
    # ==========================================

    text = (
        f"💳 **تفاصيل سعر الاشتراك**\n\n"
        f"📊 **حجم المطعم:**\n"
        f"🍔 عدد المنتجات: {products_count}\n"
        f"📂 عدد الأقسام: {categories_count}\n"
        f"🏢 عدد الفروع: {branches_count}\n"
        f"🏪 عدد المطاعم: {restaurants_count}\n"
        f"📅 سنوات التواجد: {years_with_platform} سنة\n"
        f"📦 الطلبات الشهرية: {monthly_orders}\n"
        f"💰 متوسط قيمة الطلب: {average_order_value:.2f} دج\n\n"
        f"💰 **تفاصيل السعر:**\n"
        f"السعر الأساسي: {pricing.get('base_price', 0):.2f} دج\n"
        f"نقاط الحجم: {pricing.get('restaurant_score', 0):.2f}\n"
        f"القيمة قبل الخصومات: {pricing.get('value_before_discounts', 0):.2f} دج\n\n"
        f"🎁 **الخصومات:**\n"
        f"خصم الولاء: -{pricing.get('loyalty_discount', 0):.2f} دج\n"
        f"خصم تعدد المطاعم: -{pricing.get('multi_restaurant_discount', 0):.2f} دج\n"
        f"خصم ترويجي: -{pricing.get('promotion_discount', 0):.2f} دج\n"
        f"إجمالي الخصومات: -{pricing.get('discount_price', 0):.2f} دج\n\n"
        f"🏢 **تكلفة الفروع:** +{pricing.get('multi_branch_cost', 0):.2f} دج\n\n"
        f"💰 **السعر النهائي: {pricing.get('final_price', 0):.2f} دج**\n"
        f"💳 تعديل الدفع: {pricing.get('payment_adjustment', 0):.2f} دج\n"
        f"💰 **المبلغ المستحق: {pricing.get('final_amount_due', 0):.2f} دج**\n\n"
        f"📌 هل تريد المتابعة إلى الدفع؟"
    )

    buttons = [
        [
            await button(
                text="💳 متابعة إلى الدفع",
                callback=f"payment_confirm_{plan_id}",
            ),
        ],
        [
            await button(
                text="🔙 رجوع إلى الباقات",
                callback="back_to_plans",
            ),
        ],
    ]

    await UIManager.update(
        chat_id=chat_id,
        text=text,
        reply_markup={
            "inline_keyboard": buttons,
        },
    )