from app.repositories.orders_repo import lock_order
"""Order payments are separate from fulfillment status.

All writes share the order unit of work and payment transition policy.
"""
from sqlalchemy import select

from app.core.exceptions import NotFoundError, ValidationError
from app.models.order import Order
from app.repositories.order_payments_repo import OrderPaymentsRepository
from app.services.business.orders.transaction import transactional_order


async def _locked_order(order_id, session):
    order = await lock_order(order_id=order_id, session=session)
    if order is None:
        raise NotFoundError(message="Order not found")
    return order


@transactional_order
async def mark_order_paid(*, order_id: int, payment_id: int, session) -> None:
    from app.services.business.order_payments_service import OrderPaymentsService
    order = await _locked_order(order_id, session)
    payment = await OrderPaymentsRepository(session=session).get_by_id(id=payment_id)
    if payment is None:
        raise NotFoundError(message="Payment not found")
    if payment.order_id != order.id:
        raise ValidationError(message="Payment does not belong to this order")
    if payment.payment_status == "paid":
        return
    if order.status == "cancelled":
        raise ValidationError(message="Cannot pay a cancelled order")
    await OrderPaymentsService(session=session).confirm_payment(payment_id=payment_id)
    # No fulfillment transition: pending/confirmed/... remain governed by constants.


async def is_order_paid(*, order_id: int, session) -> bool:
    info = await get_order_payment_status(order_id=order_id, session=session)
    return info["is_paid"]


async def get_order_payment_status(*, order_id: int, session):
    order = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if order is None:
        return dict(order_id=order_id, exists=False, is_paid=False, status=None,
                    payment_count=0, total_paid_amount=0, remaining_amount=0,
                    paid_payment_id=None)
    payments = await OrderPaymentsRepository(session=session).get_by_order_id(
        order_id=order_id, limit=1000)
    paid = [p for p in payments if p.payment_status == "paid"]
    amount = round(sum(float(p.amount) for p in paid), 2)
    total = round(float(order.total_amount or 0), 2)
    return dict(order_id=order_id, exists=True, is_paid=total > 0 and amount >= total,
                status=order.status, payment_count=len(payments), total_paid_amount=amount,
                remaining_amount=round(max(0, total - amount), 2),
                paid_payment_id=paid[0].id if paid else None)


@transactional_order
async def unpay_order(*, order_id: int, session) -> None:
    from app.services.business.order_payments_service import OrderPaymentsService
    order = await _locked_order(order_id, session)
    if order.status in {"completed", "delivered", "cancelled"}:
        raise ValidationError(message="Cannot reverse payment in this order state")
    payments = await OrderPaymentsRepository(session=session).get_by_order_id(
        order_id=order_id, limit=1000)
    service = OrderPaymentsService(session=session)
    for payment in payments:
        if payment.payment_status == "paid":
            await service.refund_payment(payment_id=payment.id)


@transactional_order
async def process_order_payment(*, order_id: int, payment_method: str, amount: float, session) -> int:
    from app.schemas.order_payment import PaymentCreate
    from app.services.business.order_payments_service import OrderPaymentsService
    order = await _locked_order(order_id, session)
    if order.status == "cancelled" or order.is_paid:
        raise ValidationError(message="Order cannot accept another payment")
    service = OrderPaymentsService(session=session)
    payment = await service.create_payment(payment_data=PaymentCreate(
        order_id=order_id, payment_method=payment_method, amount=amount))
    await mark_order_paid(order_id=order_id, payment_id=payment.id, session=session)
    return payment.id


async def mark_order_paid_compat(**kwargs):
    return await mark_order_paid(**kwargs)


async def is_order_paid_compat(**kwargs):
    return await is_order_paid(**kwargs)
