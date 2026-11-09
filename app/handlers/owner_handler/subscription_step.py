# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNER SUBSCRIPTION PRESENTATION
# Read owner subscription context and present the existing plan and quotation workflow.
# ==============================================

"""Read owner subscription context and present the existing plan and quotation workflow."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from datetime import (
    datetime,
    timezone,
)

from app.core.database import get_session
from app.core.logger import logger
from app.helpers.ui_manager import UIManager

# ✅ إضافة استيراد orders_repo
from app.repositories.state_repo import (
    get_state,
    set_state,
)
from app.repositories.subscription_plan_repo import SubscriptionPlanRepository
from app.services.business.pricing_service import calculate_subscription_pricing
from app.views.subscription_ui import subscription_ui
from app.views.ui import button

# ==============================================
# 💳 SHOW SUBSCRIPTION PLANS (OWNER)
# عرض الباقات المتاحة لصاحب المحل
# ==============================================

# ==============================================
# SHOW SUBSCRIPTION PLANS FOR OWNER
# عرض الباقات المتاحة للاشتراك لصاحب المحل
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

    # ==============================================
    # 1️⃣ جلب الباقات النشطة
    # Read active persisted plans and report explicitly when no plan is available.
    # ==============================================

    async with await get_session() as session:
        plans = await SubscriptionPlanRepository(session=session).get_active()

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

    # ==============================================
    # 2️⃣ حفظ بيانات المالك والمطعم في الحالة
    # Retain the selected owner and restaurant for the subsequent subscription step.
    # ==============================================

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

    # ==============================================
    # 3️⃣ عرض واجهة الباقات
    # Render the selected plan instructions using the existing owner conversation
    # interface.
    # ==============================================

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
# حساب سعر الاشتراك لباقة معينة لصاحب المحل
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

    # ==============================================
    # 1️⃣ جلب حالة المستخدم
    # Require existing owner and restaurant context before requesting a quotation.
    # ==============================================

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

    # ==============================================
    # 2️⃣ جلب بيانات المطعم وحجمه
    # Read verified historical metrics and calculate the owned restaurant quotation.
    # ==============================================

    # 🔢 عدد المنتجات
    from app.services.business import subscription_metrics

    async with await get_session() as session:
        _ref, inputs = await subscription_metrics.pricing_inputs(
            session=session,
            owner_id=owner_id,
            restaurant_id=restaurant_id,
            now=datetime.now(timezone.utc),
        )
        pricing = await calculate_subscription_pricing(
            session=session,
            plan_id=plan_id,
            billing_cycle="monthly",
            payment_method="electronic",
            owner_id=owner_id,
            restaurant_id=restaurant_id,
            **inputs,
        )
    products_count = inputs["products_count"]
    categories_count = inputs["categories_count"]
    branches_count = inputs["branches_count"]
    restaurants_count = inputs["restaurants_count"]
    years_with_platform = inputs["years_with_platform"]
    monthly_orders = inputs["monthly_orders"]
    average_order_value = inputs["average_order_value"]

    state["selected_plan_id"] = plan_id
    state["pricing_result"] = pricing

    await set_state(
        chat_id=chat_id,
        state=state,
    )

    # ==============================================
    # 5️⃣ عرض تفاصيل السعر
    # Present the retained metrics, discounts and final amount without recalculating
    # them.
    # ==============================================

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
