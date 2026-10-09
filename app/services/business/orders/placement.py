# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDERS / PLACEMENT
# Operational component of the MoulAI platform.
# ==============================================

"""Customer order quotation and placement; actions only adapt messages."""

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories.products_repo import ProductRepository
from app.repositories.user_repo import UserRepository
from app.models.restaurant import Restaurant
from app.repositories.orders_repo import OrdersRepository
from app.services.business.orders.create import create_order_with_items
from app.services.business.orders.pricing import item_total, validate_quantity
from app.services.business.orders.transaction import transactional_order

# ==============================================
# QUOTE CUSTOMER ORDER
# ==============================================


async def quote_customer_order(
    *,
    chat_id,
    product_name=None,
    product_id=None,
    quantity=1,
    restaurant_id=None,
    session
):
    validate_quantity(quantity)
    if not chat_id or not (product_name or product_id):
        raise ValidationError(
            message="Product and customer are required",
            error_code="missing_order_details",
        )
    user = await UserRepository(session=session).get_by_chat_id(chat_id=chat_id)
    if user is None or not user.consent:
        raise ValidationError(
            message="Please accept the terms before ordering",
            error_code="customer_consent_required",
        )
    repository = ProductRepository(session=session)
    if product_id:
        product = await repository.get_by_id(id=product_id)
        products = [product] if product and product.is_available else []
    else:
        products = await repository.search(
            query=str(product_name).strip(), restaurant_id=restaurant_id, limit=20
        )
    candidates = []
    for product in products:
        if restaurant_id is not None and product.restaurant_id != restaurant_id:
            continue
        restaurant = await session.get(Restaurant, product.restaurant_id)
        if restaurant and restaurant.is_active and product.is_available:
            candidates.append(product)
    if not candidates:
        raise NotFoundError(message="Product not found", error_code="product_not_found")
    if len(candidates) != 1:
        raise ValidationError(
            message="Specify the product and restaurant", error_code="ambiguous_product"
        )
    product = candidates[0]
    price = float(product.price)
    return dict(
        product_id=product.id,
        product_name=product.name,
        restaurant_id=product.restaurant_id,
        user_id=user.id,
        quantity=quantity,
        quoted_unit_price=price,
        quoted_total=item_total(price, quantity),
    )


# ==============================================
# PLACE CUSTOMER ORDER
# ==============================================


@transactional_order
async def place_customer_order(
    *,
    session,
    quoted_unit_price=None,
    order_type="takeaway",
    delivery_address=None,
    customer_note=None,
    **kwargs
):
    quote = await quote_customer_order(session=session, **kwargs)
    if (
        quoted_unit_price is not None
        and float(quoted_unit_price) != quote["quoted_unit_price"]
    ):
        raise ValidationError(
            message="Price changed; review a new quote",
            error_code="product_price_changed",
        )
    if order_type == "delivery" and not delivery_address:
        raise ValidationError(
            message="Delivery address is required",
            error_code="missing_delivery_address",
        )
    order_id = await create_order_with_items(
        restaurant_id=quote["restaurant_id"],
        user_id=quote["user_id"],
        branch_id=None,
        table_id=None,
        employee_id=None,
        order_type=order_type,
        customer_name=None,
        customer_phone=None,
        delivery_address=delivery_address,
        customer_note=customer_note,
        subtotal_amount=quote["quoted_total"],
        discount_amount=0,
        tax_amount=0,
        delivery_amount=0,
        total_amount=quote["quoted_total"],
        items=[
            dict(
                product_id=quote["product_id"],
                quantity=quote["quantity"],
                quoted_unit_price=quote["quoted_unit_price"],
            )
        ],
        session=session,
    )
    order = await OrdersRepository(session=session).get_by_id(id=order_id)
    return dict(
        order_id=order.id,
        order_number=order.order_number,
        product_id=quote["product_id"],
        product_name=quote["product_name"],
        quantity=quote["quantity"],
        total_price=order.total_amount,
    )
