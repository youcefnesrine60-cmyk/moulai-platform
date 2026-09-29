# ==============================================
# 💳 PAYMENT CALLBACK
# Payment Gateway Callback Handler
# معالجة ردود بوابات الدفع الخارجية (Webhook)
# Stripe, PayPal, CCP, BaridiMob
# Production Ready (Atomic Transaction)
# ==============================================

from datetime import datetime, timedelta, timezone

from app.core.db import transaction
from app.core.logger import logger

from app.repositories.payment_repo import (
    get_payment_by_reference,
    confirm_payment_tx,
    fail_payment_tx,
)

from app.repositories.subscription_repo import (
    get_subscription_by_id,
    activate_subscription_tx,
)

from app.repositories.subscription_features_repo import (
    SubscriptionFeatureRepository,
)

from app.repositories.subscription_feature_requests_repo import (
    SubscriptionFeatureRequestRepository,
)


# ==============================================
# ✅ PAYMENT SUCCESS CALLBACK
# ==============================================

async def handle_payment_success(
    *,
    external_reference: str,
) -> None:
    """
    معالجة رد نجاح الدفع من بوابة خارجية
    
    Args:
        external_reference: مرجع الدفع الخارجي
        
    Raises:
        ValueError: إذا لم يتم العثور على الدفع أو الاشتراك
    """
    payment = await get_payment_by_reference(
        external_reference=external_reference,
    )

    if not payment:
        logger.error(
            "payment_not_found",
            extra={
                "external_reference": external_reference,
            },
        )
        raise ValueError("payment_not_found")

    subscription_id = payment.get("subscription_id")

    if not subscription_id:
        logger.warning(
            "payment_without_subscription",
            extra={
                "payment_id": payment["id"],
            },
        )
        return

    subscription = await get_subscription_by_id(
        subscription_id=subscription_id,
    )

    if not subscription:
        logger.error(
            "subscription_not_found",
            extra={
                "subscription_id": subscription_id,
            },
        )
        raise ValueError("subscription_not_found")

    starts_at = datetime.now(timezone.utc)
    billing_cycle = subscription["billing_cycle"]

    if billing_cycle == "yearly":
        expires_at = starts_at + timedelta(days=365)
    elif billing_cycle == "monthly":
        expires_at = starts_at + timedelta(days=30)
    else:
        logger.error(
            "unsupported_billing_cycle",
            extra={
                "billing_cycle": billing_cycle,
            },
        )
        raise ValueError(f"unsupported_billing_cycle: {billing_cycle}")

    # ==========================================
    # 🔒 ATOMIC TRANSACTION
    # ==========================================

    async with transaction() as conn:
        updated_rows = await confirm_payment_tx(
            conn=conn,
            payment_id=payment["id"],
        )

        if updated_rows == 0:
            logger.warning(
                "payment_already_confirmed",
                extra={
                    "payment_id": payment["id"],
                },
            )
            return

        updated_rows = await activate_subscription_tx(
            conn=conn,
            subscription_id=subscription_id,
            starts_at=starts_at,
            expires_at=expires_at,
        )

        if updated_rows == 0:
            logger.warning(
                "subscription_already_active",
                extra={
                    "subscription_id": subscription_id,
                },
            )
            return

        feature_repo = SubscriptionFeatureRepository(session=conn)
        request_repo = SubscriptionFeatureRequestRepository(session=conn)

        requests = await request_repo.get_by_subscription(
            subscription_id=subscription_id,
        )

        for request in requests:
            await feature_repo.create_subscription_feature(
                subscription_id=subscription_id,
                feature_id=request.feature_id,
            )

        await request_repo.delete_by_subscription(
            subscription_id=subscription_id,
        )

    logger.info(
        "payment_callback_success",
        extra={
            "payment_id": payment["id"],
            "subscription_id": subscription_id,
        },
    )


# ==============================================
# ❌ PAYMENT FAILED CALLBACK
# ==============================================

async def handle_payment_failure(
    *,
    external_reference: str,
) -> None:
    """
    معالجة رد فشل الدفع من بوابة خارجية
    
    Args:
        external_reference: مرجع الدفع الخارجي
        
    Raises:
        ValueError: إذا لم يتم العثور على الدفع
    """
    payment = await get_payment_by_reference(
        external_reference=external_reference,
    )

    if not payment:
        logger.error(
            "payment_not_found",
            extra={
                "external_reference": external_reference,
            },
        )
        raise ValueError("payment_not_found")

    async with transaction() as conn:
        await fail_payment_tx(
            conn=conn,
            payment_id=payment["id"],
        )

    logger.warning(
        "payment_callback_failed",
        extra={
            "payment_id": payment["id"],
        },
    )