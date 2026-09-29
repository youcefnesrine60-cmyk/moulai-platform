# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💰 PRICING SERVICE
# MoulAI Pricing Engine
#
# Async SQLAlchemy Version
# ==============================================

from decimal import Decimal
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.repositories.branch_pricing_repo import (
    BranchPricingRepository,
)
from app.repositories.feature_pricing_repo import (
    FeaturePricingRepository,
)
from app.repositories.loyalty_discount_repo import (
    LoyaltyDiscountRepository,
)
from app.repositories.multi_restaurant_discount_repo import (
    MultiRestaurantDiscountRepository,
)
from app.repositories.promotion_repo import (
    PromotionRepository,
)
from app.repositories.subscription_plan_repo import (
    SubscriptionPlanRepository,
)

# ==============================================
# 🧩 TYPES
# ==============================================

PricingResult = Dict[str, Any]
FeatureIdsList = List[int]

# ==============================================
# 🧩 CONSTANTS
# ==============================================

PAYMENT_CASH = "cash"
PAYMENT_ELECTRONIC = "electronic"

MONTHLY = "monthly"
YEARLY = "yearly"


# ==============================================
# 📊 RESTAURANT SCORE
# ==============================================

def calculate_restaurant_score(
    *,
    products_count: int,
    categories_count: int,
    monthly_orders: int,
    average_order_value: float,
) -> Decimal:
    """
    حساب نقاط المطعم (Restaurant Score) المستخدمة في التسعير.

    Args:
        products_count: عدد المنتجات
        categories_count: عدد التصنيفات
        monthly_orders: عدد الطلبات الشهرية
        average_order_value: متوسط قيمة الطلب

    Returns:
        نقاط المطعم كـ Decimal
    """
    score = (
        (
            products_count * 1
            + categories_count * 3
            + monthly_orders * 0.1
            + (average_order_value / 100)
        )
        * 10
    )

    return Decimal(str(round(score, 2)))


# ==============================================
# 💲 ADDITIONAL FEATURES PRICE
# ==============================================

async def calculate_additional_features_price(
    *,
    session: AsyncSession,
    feature_ids: FeatureIdsList,
    billing_cycle: str,
) -> Decimal:
    """
    حساب السعر الإجمالي للميزات الإضافية.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        feature_ids: قائمة معرفات الميزات الإضافية
        billing_cycle: دورة الفوترة (monthly, yearly)

    Returns:
        السعر الإجمالي للميزات الإضافية
    """
    total = Decimal("0")

    if not feature_ids:
        return total

    repo = FeaturePricingRepository(session=session)

    for feature_id in feature_ids:
        feature_pricing = await repo.get_by_feature_and_cycle(
            feature_id=feature_id,
            billing_cycle=billing_cycle,
            only_active=True,
        )

        if not feature_pricing:
            continue

        total += Decimal(str(feature_pricing.price))

    return total


# ==============================================
# 💰 PLAN BASE PRICE
# ==============================================

async def calculate_plan_base_price(
    *,
    session: AsyncSession,
    plan_id: int,
    billing_cycle: str,
    additional_feature_ids: Optional[FeatureIdsList] = None,
) -> Decimal:
    """
    حساب السعر الأساسي للخطة (بما في ذلك الميزات الإضافية بعد الخصم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        plan_id: معرف الخطة
        billing_cycle: دورة الفوترة
        additional_feature_ids: قائمة معرفات الميزات الإضافية

    Returns:
        السعر الأساسي للخطة

    Raises:
        ValueError: إذا لم يتم العثور على الخطة
    """
    additional_feature_ids = additional_feature_ids or []

    plan_repo = SubscriptionPlanRepository(session=session)

    plan = await plan_repo.get_by_id(id=plan_id)

    if not plan:
        raise ValueError("plan_not_found")

    base_price = Decimal(str(plan.base_price))
    discount_percent = Decimal(str(plan.plan_discount_percent))

    additional_features_price = await calculate_additional_features_price(
        session=session,
        feature_ids=additional_feature_ids,
        billing_cycle=billing_cycle,
    )

    discounted_features_price = (
        additional_features_price
        * (Decimal("100") - discount_percent)
        / Decimal("100")
    )

    return base_price + discounted_features_price


# ==============================================
# 🎖️ LOYALTY DISCOUNT
# ==============================================

async def calculate_loyalty_discount(
    *,
    session: AsyncSession,
    years_with_platform: int,
    amount: Decimal,
) -> Decimal:
    """
    حساب خصم الولاء بناءً على عدد سنوات التعامل مع المنصة.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        years_with_platform: عدد سنوات التعامل
        amount: المبلغ قبل الخصم

    Returns:
        قيمة خصم الولاء
    """
    repo = LoyaltyDiscountRepository(session=session)

    percent = await repo.get_discount_for_years(years=years_with_platform)

    if not percent:
        return Decimal("0")

    return amount * Decimal(str(percent)) / Decimal("100")


# ==============================================
# 🏢 MULTI RESTAURANT DISCOUNT
# ==============================================

async def calculate_multi_restaurant_discount(
    *,
    session: AsyncSession,
    restaurants_count: int,
    amount: Decimal,
) -> Decimal:
    """
    حساب خصم المطاعم المتعددة.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurants_count: عدد المطاعم
        amount: المبلغ قبل الخصم

    Returns:
        قيمة خصم المطاعم المتعددة
    """
    repo = MultiRestaurantDiscountRepository(session=session)

    rule = await repo.get_discount_for_count(
        restaurants_count=restaurants_count,
    )

    if not rule:
        return Decimal("0")

    return amount * Decimal(str(rule.discount_percent)) / Decimal("100")


# ==============================================
# 🎉 PROMOTION DISCOUNT
# ==============================================

async def calculate_promotion_discount(
    *,
    session: AsyncSession,
    amount: Decimal,
) -> Decimal:
    """
    حساب خصم العرض الترويجي النشط (أحدث عرض).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        amount: المبلغ قبل الخصم

    Returns:
        قيمة خصم العرض الترويجي
    """
    repo = PromotionRepository(session=session)

    promotions = await repo.get_active_promotions(limit=1)

    if not promotions:
        return Decimal("0")

    promotion = promotions[0]

    return amount * Decimal(str(promotion.discount_percent)) / Decimal("100")


# ==============================================
# 🏢 MULTI BRANCH COST
# ==============================================

async def calculate_multi_branch_cost(
    *,
    session: AsyncSession,
    branches_count: int,
) -> Decimal:
    """
    حساب تكلفة الفروع الإضافية.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        branches_count: عدد الفروع

    Returns:
        تكلفة الفروع الإضافية
    """
    if branches_count <= 1:
        return Decimal("0")

    repo = BranchPricingRepository(session=session)

    rule = await repo.get_rule_for_branches(
        branches_count=branches_count,
    )

    if not rule:
        return Decimal("0")

    price_per_branch = Decimal(str(rule.price_per_branch))
    additional_branches = branches_count - 1

    return price_per_branch * additional_branches


# ==============================================
# 📅 BILLING CYCLE MULTIPLIER
# ==============================================

def calculate_billing_cycle_price(
    *,
    amount: Decimal,
    billing_cycle: str,
) -> Decimal:
    """
    حساب السعر النهائي حسب دورة الفوترة (monthly, yearly).

    Args:
        amount: السعر الأساسي
        billing_cycle: دورة الفوترة

    Returns:
        السعر بعد التطبيق حسب الدورة

    Raises:
        ValueError: إذا كانت دورة الفوترة غير صالحة
    """
    if billing_cycle == MONTHLY:
        return amount

    if billing_cycle == YEARLY:
        # ✅ السنة = 10 أشهر (شهران مجانيان)
        return amount * Decimal("10")

    raise ValueError("invalid_billing_cycle")


# ==============================================
# 💳 PAYMENT ADJUSTMENT
# ==============================================

def calculate_payment_adjustment(
    *,
    amount: Decimal,
    payment_method: str,
) -> Decimal:
    """
    حساب تعديل السعر حسب طريقة الدفع (خصم للدفع الإلكتروني، رسوم للنقدي).

    Args:
        amount: السعر قبل التعديل
        payment_method: طريقة الدفع

    Returns:
        قيمة التعديل (موجبة أو سالبة)
    """
    if payment_method == PAYMENT_ELECTRONIC:
        # ✅ خصم 2% للدفع الإلكتروني
        return amount * Decimal("-2") / Decimal("100")

    if payment_method == PAYMENT_CASH:
        # ✅ رسوم 2% للدفع النقدي
        return amount * Decimal("2") / Decimal("100")

    return Decimal("0")


# ==============================================
# 🧮 FINAL PRICING
# ==============================================

async def calculate_subscription_pricing(
    *,
    session: AsyncSession,
    plan_id: int,
    billing_cycle: str,
    payment_method: str,
    restaurants_count: int,
    branches_count: int,
    years_with_platform: int,
    products_count: int,
    categories_count: int,
    monthly_orders: int,
    average_order_value: float,
    additional_feature_ids: Optional[FeatureIdsList] = None,
) -> PricingResult:
    """
    حساب التسعير النهائي للاشتراك بشكل كامل.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        plan_id: معرف الخطة
        billing_cycle: دورة الفوترة
        payment_method: طريقة الدفع
        restaurants_count: عدد المطاعم
        branches_count: عدد الفروع
        years_with_platform: عدد سنوات التعامل مع المنصة
        products_count: عدد المنتجات
        categories_count: عدد التصنيفات
        monthly_orders: عدد الطلبات الشهرية
        average_order_value: متوسط قيمة الطلب
        additional_feature_ids: قائمة معرفات الميزات الإضافية

    Returns:
        قاموس تفاصيل التسعير الكامل
    """
    additional_feature_ids = additional_feature_ids or []

    # 1️⃣ السعر الأساسي للخطة
    base_price = await calculate_plan_base_price(
        session=session,
        plan_id=plan_id,
        billing_cycle=billing_cycle,
        additional_feature_ids=additional_feature_ids,
    )

    # 2️⃣ نقاط المطعم
    restaurant_score = calculate_restaurant_score(
        products_count=products_count,
        categories_count=categories_count,
        monthly_orders=monthly_orders,
        average_order_value=average_order_value,
    )

    value_before_discounts = base_price + restaurant_score

    # 3️⃣ الخصومات
    loyalty_discount = await calculate_loyalty_discount(
        session=session,
        years_with_platform=years_with_platform,
        amount=value_before_discounts,
    )

    multi_restaurant_discount = await calculate_multi_restaurant_discount(
        session=session,
        restaurants_count=restaurants_count,
        amount=value_before_discounts,
    )

    promotion_discount = await calculate_promotion_discount(
        session=session,
        amount=value_before_discounts,
    )

    total_discount = (
        loyalty_discount
        + multi_restaurant_discount
        + promotion_discount
    )

    # 4️⃣ تكلفة الفروع الإضافية
    branch_cost = await calculate_multi_branch_cost(
        session=session,
        branches_count=branches_count,
    )

    final_price = value_before_discounts - total_discount + branch_cost

    # 5️⃣ تعديل دورة الفوترة
    final_price = calculate_billing_cycle_price(
        amount=final_price,
        billing_cycle=billing_cycle,
    )

    # 6️⃣ تعديل طريقة الدفع
    payment_adjustment = calculate_payment_adjustment(
        amount=final_price,
        payment_method=payment_method,
    )

    final_amount_due = final_price + payment_adjustment

    # ✅ نتيجة كاملة
    return {
        "base_price": float(base_price),
        "restaurant_score": float(restaurant_score),
        "value_before_discounts": float(value_before_discounts),
        "loyalty_discount": float(loyalty_discount),
        "multi_restaurant_discount": float(multi_restaurant_discount),
        "promotion_discount": float(promotion_discount),
        "discount_price": float(total_discount),
        "multi_branch_cost": float(branch_cost),
        "final_price": float(final_price),
        "payment_adjustment": float(payment_adjustment),
        "final_amount_due": float(final_amount_due),
    }


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "PricingResult",
    "FeatureIdsList",
    "PAYMENT_CASH",
    "PAYMENT_ELECTRONIC",
    "MONTHLY",
    "YEARLY",
    "calculate_restaurant_score",
    "calculate_additional_features_price",
    "calculate_plan_base_price",
    "calculate_loyalty_discount",
    "calculate_multi_restaurant_discount",
    "calculate_promotion_discount",
    "calculate_multi_branch_cost",
    "calculate_billing_cycle_price",
    "calculate_payment_adjustment",
    "calculate_subscription_pricing",
]