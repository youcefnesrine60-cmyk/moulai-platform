# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDERS / PRICING
# Operational component of the MoulAI platform.
# ==============================================

"""Catalog validation and pricing used by API and customer order creation."""

import math

from typing import Any, TypeAlias

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories.products_repo import ProductRepository

MIN_QUANTITY = 1
MAX_QUANTITY = 100
MAX_ITEMS_PER_ORDER = 50

OrderAmount: TypeAlias = float | int | str
CatalogItemData: TypeAlias = dict[str, Any]


# ==============================================
# VALIDATE QUANTITY
# ==============================================


def validate_quantity(quantity: object) -> None:
    """Validate an order-line quantity against the supported business range."""
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or not 1 <= quantity <= MAX_QUANTITY
    ):
        raise ValidationError(
            message="Quantity must be between 1 and 100",
            error_code="INVALID_ORDER_QUANTITY",
        )


# ==============================================
# ITEM TOTAL
# ==============================================


def item_total(unit_price: OrderAmount, quantity: int) -> float:
    """Return the rounded line total after validating price and quantity."""
    validate_quantity(quantity)
    if not math.isfinite(float(unit_price)) or float(unit_price) < 0:
        raise ValidationError(message="Invalid unit price")
    return round(float(unit_price) * quantity, 2)


# ==============================================
# CATALOG ITEM
# ==============================================


async def catalog_item(
    *,
    restaurant_id: int,
    payload: dict[str, Any],
    session: AsyncSession,
) -> CatalogItemData:
    """Validate a restaurant-scoped product payload and create trusted pricing data."""
    product_id = payload.get("product_id")
    if not product_id:
        raise ValidationError(message="معرف المنتج مطلوب لكل عنصر")
    validate_quantity(payload.get("quantity"))
    product = await ProductRepository(session=session).get_for_order(
        product_id=product_id, restaurant_id=restaurant_id
    )
    if product is None or product.restaurant_id != restaurant_id:
        raise NotFoundError(message="Product not found in this restaurant")
    if not product.is_available:
        raise ValidationError(message="Product is unavailable")
    price = float(product.price)
    if (
        payload.get("quoted_unit_price") is not None
        and float(payload["quoted_unit_price"]) != price
    ):
        raise ValidationError(
            message="Price changed; review a new quote",
            error_code="product_price_changed",
        )
    return dict(
        product_id=product.id,
        product_name=product.name,
        unit_price=price,
        quantity=payload["quantity"],
        total_price=item_total(price, payload["quantity"]),
        options=payload.get("options") or [],
    )
