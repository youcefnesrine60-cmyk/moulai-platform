# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / OWNER_HANDLER / SUBSCRIPTION STEP
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for subscription step.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from datetime import datetime, timezone

from app.core.database import get_session
from app.core.logger import logger
from app.helpers.ui_manager import UIManager
from app.repositories.branches_repo import BranchesRepository
from app.repositories.categories_repo import CategoriesRepository

# ✅ إضافة استيراد orders_repo
from app.repositories.orders_repo import OrdersRepository
from app.repositories.products_repo import ProductRepository
from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.repositories.state_repo import get_state, set_state
from app.repositories.subscription_plan_repo import SubscriptionPlanRepository
from app.services.business.owner_service import OwnerService
from app.services.business.pricing_service import calculate_subscription_pricing
from app.views.subscription_ui import (
    subscription_ui,
)
from app.views.ui import button

# ==============================================
# 💳 SHOW SUBSCRIPTION PLANS (OWNER)
# عرض الباقات المتاحة لصاحب المحل
# ==============================================


# ==============================================
# SHOW SUBSCRIPTION PLANS FOR OWNER
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

    async with await get_session() as session:
        plans = await SubscriptionPlanRepository(session).get_active()

    if not plans:
        logger.warning(
            "no_active_plans_for_owner",
            extra={
                "chat_id": chat_id,
                "owner_id": owner_id,
            },
        )

        await UIManager.send_new_message(
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

    await UIManager.send_new_message(
        chat_id=chat_id,
        text=plans_ui.get("text", "💳 باقات الاشتراك"),
        reply_markup=plans_ui.get("inline_keyboard"),
    )


# ==============================================
# 💳 CALCULATE SUBSCRIPTION PRICE (OWNER)
# حساب سعر الاشتراك لصاحب المحل
# ==============================================


# ==============================================
# CALCULATE SUBSCRIPTION PRICE FOR OWNER
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
    async with await get_session() as session:
        products_count = await ProductRepository(session).count_by_restaurant(
            restaurant_id=restaurant_id,
        )

    # 🔢 عدد الأقسام
    async with await get_session() as session:
        categories = await CategoriesRepository(session).get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )
    categories_count = len(categories)

    # 🔢 عدد الفروع
    async with await get_session() as session:
        branches_count = await BranchesRepository(session).count_by_restaurant(
            restaurant_id=restaurant_id,
        )

    # 🔢 عدد المطاعم المملوكة لنفس المالك
    async with await get_session() as session:
        restaurants = await RestaurantRepository(session).get_by_owner_id(
            owner_id=owner_id,
        )
    restaurants_count = len(restaurants)

    # 🔢 عدد سنوات التواجد في المنصة
    async with await get_session() as session:
        created_at = await OwnerService(session=session).get_created_at(
            owner_id=owner_id,
        )

    now = datetime.now(timezone.utc)
    if created_at:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        years_with_platform = max(0, (now - created_at).days // 365)
    else:
        years_with_platform = 0

    # ==========================================
    # 📦 جلب عدد الطلبات الشهرية
    # ==========================================

    # ✅ جلب جميع طلبات المطعم
    async with await get_session() as session:
        order_models = await OrdersRepository(session).get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )
    orders = [
        {
            "created_at": order.created_at,
            "status": order.status,
            "total_amount": order.total_amount,
        }
        for order in order_models
    ]

    # ✅ حساب عدد الطلبات الشهرية (آخر 30 يوماً)
    from datetime import timedelta

    thirty_days_ago = now - timedelta(days=30)

    monthly_orders = sum(
        1
        for order in orders
        if order.get("created_at")
        and (
            order["created_at"].replace(tzinfo=timezone.utc)
            if order["created_at"].tzinfo is None
            else order["created_at"]
        )
        >= thirty_days_ago
    )

    # ==========================================
    # 💰 حساب متوسط قيمة الطلب
    # ==========================================

    # ✅ حساب متوسط قيمة الطلبات المكتملة
    completed_orders = [order for order in orders if order.get("status") == "completed"]

    if completed_orders:
        total_amount = sum(
            float(order.get("total_amount", 0)) for order in completed_orders
        )
        average_order_value = total_amount / len(completed_orders)
    else:
        average_order_value = 0

    # ==========================================
    # 3️⃣ حساب السعر
    # ==========================================

    async with await get_session() as session:
        pricing = await calculate_subscription_pricing(
            session=session,
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
        f"📌 تفعيل الاشتراك يتطلب التحقق من وصول مبلغ التحويل."
    )

    buttons = [[await button(text="🔙 القائمة الرئيسية", callback="back_main")]]

    await UIManager.send_new_message(
        chat_id=chat_id,
        text=text,
        reply_markup={
            "inline_keyboard": buttons,
        },
    )
