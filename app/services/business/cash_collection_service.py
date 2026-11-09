# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# AUTHORIZED CASH COLLECTION SERVICE
# Verify collection authority and matching evidence, then settle once with durable
# auditing.
# ==============================================

"""Physical cash settlement, using independently committed attempt auditing.

Internal command only: a trusted authenticated adapter must supply admin_id.
No HTTP route or owner-upload path is registered by this module.
"""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from collections.abc import Mapping
from datetime import (
    datetime,
    timezone,
)
from uuid import uuid4

from pydantic import ValidationError as SchemaError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import raiseload

from app.core.exceptions import (
    AppException,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.logger import logger
from app.models.admin import Admin
from app.models.cash_collection import (
    CashCollection,
    CashCollectionAttempt,
)
from app.models.payment import Payment
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)
from app.models.subscription import Subscription
from app.repositories.subscription_queries import base_select
from app.schemas.cash_collection import CashConfirmation
from app.services.business.manual_payment_service import normalize_transfer_reference
from app.services.business.payment_service import PaymentService
from app.services.business.subscription_types import (
    CashCollectionResult,
    SessionFactory,
)

# ==============================================
# CASH COLLECTION SERVICE
# Own sessions so a caller rollback cannot erase refused collection attempts.
# ==============================================


class CashCollectionService:
    """Own sessions so a caller rollback cannot erase refused collection attempts."""

    # ==============================================
    # INIT
    # Bind the explicit dependencies without performing external operations.
    # ==============================================

    def __init__(self, *, session_factory: SessionFactory) -> None:
        """Bind the explicit dependencies without performing external operations."""

        self.sessions = session_factory

    # ==============================================
    # AUDIT
    # Commit an attempt record independently so caller rollback cannot erase it.
    # ==============================================

    async def _audit(
        self, *, attempt: str, payment: int, admin: int, result: str
    ) -> None:
        """Commit an attempt record independently so caller rollback cannot erase it."""

        async with self.sessions() as session, session.begin():
            session.add(
                CashCollectionAttempt(
                    attempt_id=attempt,
                    payment_id=payment,
                    attempted_admin_id=admin,
                    result=result,
                    details={},
                )
            )

    # ==============================================
    # CONFIRM
    # Authorize and lock cash settlement; commit matching evidence and activation once.
    # ==============================================

    async def confirm(
        self,
        *,
        payment_id: int,
        admin_id: int,
        data: CashConfirmation | Mapping[str, object],
    ) -> CashCollectionResult:
        """Authorize and lock cash settlement; commit matching evidence and activation once."""

        attempt = uuid4().hex
        # Persist before parsing or authorization; a crash leaves an explicit attempt.
        await self._audit(
            attempt=attempt, payment=payment_id, admin=admin_id, result="requested"
        )
        try:
            facts = CashConfirmation.model_validate(data)
            reference = normalize_transfer_reference(value=facts.receipt_reference)
            collected = facts.collected_at.astimezone(timezone.utc).replace(tzinfo=None)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if collected > now:
                raise ValidationError(message="Cash collection date is in the future")
            async with self.sessions() as session, session.begin():
                # Require an explicit cash grant, including for wildcard/review roles.
                authorized = (
                    await session.execute(
                        base_select(Admin)
                        .with_only_columns(Admin.id)
                        .join(Role, Role.id == Admin.role_id)
                        .join(role_permissions, role_permissions.c.role_id == Role.id)
                        .join(
                            Permission,
                            Permission.id == role_permissions.c.permission_id,
                        )
                        .where(
                            Admin.id == admin_id,
                            Admin.is_active.is_(True),
                            Role.is_active.is_(True),
                            Permission.code == "payments.cash.collect",
                        )
                    )
                ).scalar_one_or_none()
                if authorized is None:
                    raise UnauthorizedError(
                        message="Explicit cash collection permission required"
                    )
                payment = (
                    await session.execute(
                        base_select(Payment)
                        .options(raiseload("*"))
                        .where(Payment.id == payment_id)
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                ).scalar_one_or_none()
                if payment is None:
                    raise NotFoundError(message="Cash payment not found")
                if (
                    payment.payment_provider != "manual_cash"
                    or payment.payment_method != "cash"
                ):
                    raise ValidationError(
                        message="Payment is not a cash collection request"
                    )
                if (
                    payment.amount != facts.received_amount
                    or payment.currency != facts.currency
                ):
                    raise ValidationError(message="Cash amount or currency mismatch")
                existing = (
                    await session.execute(
                        base_select(CashCollection).where(
                            CashCollection.payment_id == payment_id
                        )
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    if (
                        existing.receipt_reference != reference
                        or existing.collected_at != collected
                        or existing.received_amount != facts.received_amount
                        or existing.currency != facts.currency
                        or payment.status != "paid"
                    ):
                        raise ConflictError(
                            message="Cash payment already confirmed with different evidence"
                        )
                    outcome = "idempotent"
                    receipt = existing
                else:
                    if payment.status != "pending":
                        raise ValidationError(message="Cash payment is not pending")
                    subscription = (
                        await session.execute(
                            base_select(Subscription)
                            .options(raiseload("*"))
                            .where(Subscription.id == payment.subscription_id)
                        )
                    ).scalar_one_or_none()
                    if subscription is None or (
                        subscription.owner_id,
                        subscription.restaurant_id,
                        subscription.amount,
                        subscription.currency,
                    ) != (
                        payment.owner_id,
                        payment.restaurant_id,
                        payment.amount,
                        payment.currency,
                    ):
                        raise ValidationError(
                            message="Cash subscription terms mismatch"
                        )
                    receipt = CashCollection(
                        payment_id=payment.id,
                        subscription_id=subscription.id,
                        admin_id=admin_id,
                        expected_amount=payment.amount,
                        received_amount=facts.received_amount,
                        currency=facts.currency,
                        collected_at=collected,
                        confirmed_at=now,
                        receipt_reference=reference,
                    )
                    session.add(receipt)
                    await session.flush()
                    await PaymentService(session=session).confirm_payment(
                        payment_id=payment_id
                    )
                    outcome = "confirmed"
                session.add(
                    CashCollectionAttempt(
                        attempt_id=attempt,
                        payment_id=payment_id,
                        attempted_admin_id=admin_id,
                        result=outcome,
                        details={"collection_id": receipt.id},
                    )
                )
                result: CashCollectionResult = {
                    "payment_id": payment_id,
                    "collection_id": receipt.id,
                    "result": outcome,
                }
            logger.info(
                "cash_collection_settled",
                extra={
                    "payment_id": payment_id,
                    "collection_id": result["collection_id"],
                    "result": outcome,
                },
            )
            return result
        except (AppException, SchemaError, ValueError, IntegrityError) as exc:
            await self._audit(
                attempt=attempt,
                payment=payment_id,
                admin=admin_id,
                result=type(exc).__name__,
            )
            logger.warning(
                "cash_collection_refused",
                extra={
                    "payment_id": payment_id,
                    "admin_id": admin_id,
                    "error_type": type(exc).__name__,
                },
            )
            raise
        except Exception:
            await self._audit(
                attempt=attempt,
                payment=payment_id,
                admin=admin_id,
                result="unexpected_error",
            )
            raise
