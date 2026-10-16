# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# INTEGRATION TEST - PRICING DISCOUNT REPOSITORIES
# Verify persisted loyalty and multi-restaurant discount rules.
# ==============================================

"""Database integration coverage for SQLAlchemy discount repositories."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loyalty_discount import (
    LoyaltyDiscount,
    MultiRestaurantDiscount,
    Promotion,
)
from app.services.business.pricing_service import (
    calculate_loyalty_discount,
    calculate_multi_restaurant_discount,
    calculate_promotion_discount,
)

# ==============================================
# PERSISTED DISCOUNT RULES
# ==============================================


@pytest.mark.asyncio
async def test_pricing_uses_persisted_discount_rules(
    db_session: AsyncSession,
) -> None:
    """Select the highest eligible persisted rule for each discount category."""
    db_session.add_all(
        (
            LoyaltyDiscount(years_required=1, discount_percent=5),
            LoyaltyDiscount(years_required=3, discount_percent=12.5),
            MultiRestaurantDiscount(min_restaurants=2, discount_percent=10),
            MultiRestaurantDiscount(min_restaurants=4, discount_percent=18),
            Promotion(name="Integration promotion", discount_percent=7.5, active=True),
        )
    )
    await db_session.flush()

    amount = Decimal(200)

    loyalty_discount = await calculate_loyalty_discount(
        session=db_session,
        years_with_platform=4,
        amount=amount,
    )
    multi_restaurant_discount = await calculate_multi_restaurant_discount(
        session=db_session,
        restaurants_count=5,
        amount=amount,
    )
    promotion_discount = await calculate_promotion_discount(
        session=db_session,
        amount=amount,
    )

    assert loyalty_discount == Decimal("25.0")
    assert multi_restaurant_discount == Decimal("36.0")
    assert promotion_discount == Decimal("15.0")
