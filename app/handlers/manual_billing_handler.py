# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Private Telegram checkout and evidence upload; settlement requires OIDC API authentication."""

# ==============================================
# IMPORTS
# ==============================================

import re
import time
from html import escape
from typing import (
    Any,
    TypeAlias,
    cast,
)

from pydantic import ValidationError as SchemaValidationError

from app.core.database import get_session
from app.core.exceptions import (
    AppException,
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.repositories.state_repo import (
    delete_state,
    get_state,
    set_state,
)
from app.schemas.manual_payment import (
    ManualPaymentMethod,
    ManualSubscriptionCheckout,
    SubscriptionBillingCycle,
)
from app.services.business.manual_payment_service import (
    MAX_RECEIPT_BYTES,
    ManualPaymentService,
    normalize_transfer_reference,
)

from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip
from app.services.business.telegram_billing_service import (
    TelegramBillingService,
    transfer_instructions,
)
from app.services.telegram import send_message
from app.services.telegram.files import download_receipt

# ==============================================
# TYPES AND CONSTANTS
# ==============================================

TelegramPayload: TypeAlias = dict[str, Any]
KeyboardRows: TypeAlias = list[list[dict[str, str]]]
BILLING_FLOW = "manual_billing"
FLOW_TTL_SECONDS = 900


# ==============================================
# VIEW AND STATE HELPERS
# ==============================================


async def _say(*, chat_id: int, text: str, rows: KeyboardRows | None = None) -> None:
    """Send a private flow response without logging bank references or content."""
    await send_message(
        chat_id=chat_id,
        text=escape(text),
        reply_markup={"inline_keyboard": rows} if rows else None,
    )


def _button(*, text: str, data: str) -> dict[str, str]:
    """Build a Bot API callback button with compact, scoped identifiers."""
    return {"text": text, "callback_data": data}


async def _stage(*, chat_id: int, step: str, payment_id: int, **data: Any) -> None:
    """Keep only workflow data; ownership and permissions remain database facts."""
    await set_state(
        chat_id=chat_id,
        state={
            "flow": BILLING_FLOW,
            "step": step,
            "payment_id": payment_id,
            "expires_at": time.time() + FLOW_TTL_SECONDS,
            **data,
        },
    )


def is_private_actor(*, message: TelegramPayload, actor: TelegramPayload) -> bool:
    """Require the signed update's private chat to match its human sender."""
    chat = message.get("chat", {})
    if not isinstance(chat, dict) or not isinstance(actor, dict):
        return False
    return (
        chat.get("type") == "private"
        and type(chat.get("id")) is int
        and type(actor.get("id")) is int
        and chat["id"] > 0
        and chat["id"] == actor.get("id")
        and actor.get("is_bot") is False
    )


# ==============================================
# OWNER ENTRY AND INVOICE
# ==============================================


async def _owner_menu(*, chat_id: int) -> None:
    """List only persisted owned restaurants and resumable pending invoices."""
    async with await get_session() as session:
        billing = TelegramBillingService(session=session)
        owner_id = await billing.owner_id(chat_id=chat_id)
        restaurants = await billing.repo.restaurants(owner_id=owner_id)
        payments = await billing.repo.pending_payments(owner_id=owner_id)
    rows = [
        [_button(text=name[:60], data=f"mb:plans:{restaurant_id}")]
        for restaurant_id, name in restaurants[:20]
    ]
    rows.extend(
        [
            [
                _button(
                    text=f"فاتورة معلقة #{payment_id}", data=f"mb:invoice:{payment_id}"
                )
            ]
            for payment_id in payments
        ]
    )
    await _say(
        chat_id=chat_id,
        text="الاشتراكات والتحويلات اليدوية: اختر المطعم أو استأنف فاتورة معلقة.",
        rows=rows,
    )


async def _invoice(*, chat_id: int, payment_id: int) -> None:
    """Read the authoritative price and receipt status within the owner's tenant."""
    async with await get_session() as session:
        owner_id = await TelegramBillingService(session=session).owner_id(
            chat_id=chat_id
        )
        payments = ManualPaymentService(session=session)
        invoice = await payments.get_invoice(payment_id=payment_id, owner_id=owner_id)
        try:
            receipt = await payments.get_receipt(
                payment_id=payment_id, owner_id=owner_id
            )
        except NotFoundError:
            receipt = None
        receipt_status = receipt.review_status if receipt else None
    status = {"pending": "بانتظار التحقق", "paid": "مدفوعة", "failed": "مرفوضة"}.get(
        invoice.status, invoice.status
    )
    text = (
        f"فاتورة الاشتراك #{invoice.id}\n"
        f"مرجع طلب الدفع: MOULAI-PAY-{invoice.id}\n"
        f"المبلغ: {invoice.amount:.2f} {invoice.currency}\nالحالة: {status}"
    )
    rows = [[_button(text="تحديث الحالة", data=f"mb:invoice:{payment_id}")]]
    if invoice.status == "pending" and receipt_status is None:
        try:
            instructions = transfer_instructions(
                method=cast(ManualPaymentMethod, invoice.payment_method)
            )
        except AppException:
            text += "\n\nطريقة التحويل غير متاحة حالياً. راجع الإدارة قبل إجراء التحويل."
        else:
            text += f"\n\n{instructions}\n\nحوّل المبلغ المطابق، ثم ارفع الإيصال وسجّل مرجع المعاملة. التفعيل بعد تحقق الإدارة من وصول المال فعلياً."
            rows.insert(
                0, [_button(text="رفع إيصال التحويل", data=f"mb:upload:{payment_id}")]
            )
    elif receipt_status is not None:
        text += (
            "\nمراجعة الإيصال: "
            + {"pending": "قيد المراجعة", "approved": "مقبول", "rejected": "مرفوض"}[
                receipt_status
            ]
        )
    await _say(chat_id=chat_id, text=text, rows=rows)


# ==============================================
# CALLBACK ROUTING
# ==============================================


async def billing_callback(
    *, chat_id: int, message_id: int, callback_data: str, match: re.Match[str]
) -> None:
    """Route validated private callbacks; reauthorize every financial operation."""
    del message_id, match
    parts = callback_data.split(":")
    try:
        action = parts[1]
        if action == "home":
            await _owner_menu(chat_id=chat_id)
        elif action == "invoice":
            await _invoice(chat_id=chat_id, payment_id=int(parts[2]))
        elif action in {"plans", "cycle", "method", "checkout"}:
            restaurant_id = int(parts[2])
            async with await get_session() as session:
                billing = TelegramBillingService(session=session)
                owner_id = await billing.owner_id(
                    chat_id=chat_id, restaurant_id=restaurant_id
                )
                if action == "plans":
                    plans = await billing.repo.plans()
                    rows = [
                        [
                            _button(
                                text=name[:60],
                                data=f"mb:cycle:{restaurant_id}:{plan_id}",
                            )
                        ]
                        for plan_id, name in plans[:30]
                    ]
                    await _say(
                        chat_id=chat_id,
                        text="اختر باقة الاشتراك."
                        if rows
                        else "لا توجد باقات متاحة حالياً.",
                        rows=rows,
                    )
                elif action == "cycle":
                    plan_id = int(parts[3])
                    await _say(
                        chat_id=chat_id,
                        text="اختر دورة الفوترة.",
                        rows=[
                            [
                                _button(
                                    text="شهري",
                                    data=f"mb:method:{restaurant_id}:{plan_id}:monthly",
                                ),
                                _button(
                                    text="سنوي",
                                    data=f"mb:method:{restaurant_id}:{plan_id}:yearly",
                                ),
                            ]
                        ],
                    )
                elif action == "method":
                    plan_id, cycle = int(parts[3]), parts[4]
                    rows = []
                    for method in ("ccp", "baridimob"):
                        try:
                            transfer_instructions(
                                method=cast(ManualPaymentMethod, method)
                            )
                        except AppException:
                            continue
                        rows.append(
                            [
                                _button(
                                    text=method.upper(),
                                    data=f"mb:checkout:{restaurant_id}:{plan_id}:{cycle}:{method}",
                                )
                            ]
                        )
                    await _say(
                        chat_id=chat_id,
                        text="اختر طريقة التحويل."
                        if rows
                        else "بيانات استقبال التحويل غير متاحة حالياً. تواصل مع الإدارة.",
                        rows=rows,
                    )
                else:
                    method = cast(ManualPaymentMethod, parts[5])
                    transfer_instructions(method=method)
                    invoice = await SubscriptionCheckoutService(session=session).create(
                        owner_id=owner_id,
                        data=ManualSubscriptionCheckout(
                            restaurant_id=restaurant_id,
                            plan_id=int(parts[3]),
                            billing_cycle=cast(SubscriptionBillingCycle, parts[4]),
                            payment_method=method,
                        ),
                    )
                    payment_id = invoice.id
            if action == "checkout":
                await _invoice(chat_id=chat_id, payment_id=payment_id)
        elif action == "upload":
            payment_id = int(parts[2])
            async with await get_session() as session:
                owner_id = await TelegramBillingService(session=session).owner_id(
                    chat_id=chat_id
                )
                invoice = await ManualPaymentService(session=session).get_invoice(
                    payment_id=payment_id, owner_id=owner_id
                )
                if invoice.status != "pending":
                    raise ValidationError(
                        message="Only pending invoices accept receipts"
                    )
            await _stage(chat_id=chat_id, step="reference", payment_id=payment_id)
            await _say(
                chat_id=chat_id,
                text="أرسل مرجع المعاملة كما في سجل التحويل (3 إلى 120 حرفاً). للإلغاء: /cancel_billing",
            )
        else:
            raise ValidationError(message="Invalid billing action")
    except (AppException, SchemaValidationError, ValueError, IndexError):
        await _say(
            chat_id=chat_id,
            text="تعذر إتمام الطلب. تحقق من الصلاحية والبيانات وحالة الفاتورة، ثم حاول مجدداً.",
        )


# ==============================================
# PRIVATE MESSAGE AND ATTACHMENT FLOW
# ==============================================


async def handle_billing_message(*, message: TelegramPayload) -> bool:
    """Consume commands and active receipt/review messages before the AI agent."""
    if not is_private_actor(message=message, actor=message.get("from", {})):
        return False
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    state = await get_state(chat_id=chat_id)
    active = bool(state and state.get("flow") == BILLING_FLOW)
    if text == "/start" and active:
        await delete_state(chat_id=chat_id)
        return False
    if text not in {"/billing", "/payments_review", "/cancel_billing"} and not active:
        return False
    try:
        if text == "/cancel_billing":
            if active:
                await delete_state(chat_id=chat_id)
            await _say(
                chat_id=chat_id,
                text="أُغلق مسار الإيصال. يمكنك استئناف الفاتورة عبر /billing.",
            )
        elif text == "/billing":
            await _owner_menu(chat_id=chat_id)
        elif text == "/payments_review":
            await _say(
                chat_id=chat_id,
                text="اعتماد التحويلات متاح عبر واجهة الإدارة الموثقة بـKeycloak بعد اكتمال إعدادها. لا يمكن اعتماد الدفع من Telegram.",
            )
        elif state:
            if state.get("expires_at", 0) < time.time():
                await delete_state(chat_id=chat_id)
                await _say(
                    chat_id=chat_id,
                    text="انتهت مهلة العملية. ابدأ مجدداً عبر /billing أو /payments_review.",
                )
                return True
            payment_id = int(state["payment_id"])
            step = state["step"]
            if step in {"reference", "receipt"}:
                await _receive_evidence(
                    chat_id=chat_id, payment_id=payment_id, message=message, state=state
                )
            else:
                await delete_state(chat_id=chat_id)
                raise ValidationError(message="Unsupported receipt workflow")
    except (AppException, SchemaValidationError, ValueError, ArithmeticError):
        await _say(
            chat_id=chat_id,
            text="لم تُحفظ العملية. تحقق من الصلاحيات وصيغة البيانات؛ الإيصال يجب أن يكون PNG أو JPEG أو PDF بحجم لا يتجاوز 2 MiB.",
        )
    return True


# ==============================================
# RECEIVE OWNER EVIDENCE
# ==============================================


async def _receive_evidence(
    *, chat_id: int, payment_id: int, message: TelegramPayload, state: TelegramPayload
) -> None:
    """Check ownership before downloading; store only through the canonical service."""
    async with await get_session() as session:
        owner_id = await TelegramBillingService(session=session).owner_id(
            chat_id=chat_id
        )
        invoice = await ManualPaymentService(session=session).get_invoice(
            payment_id=payment_id, owner_id=owner_id
        )
        if invoice.status != "pending":
            raise ValidationError(message="Invoice no longer accepts receipts")
    if state["step"] == "reference":
        reference = normalize_transfer_reference(value=message.get("text", "").strip())
        await _stage(
            chat_id=chat_id, step="receipt", payment_id=payment_id, reference=reference
        )
        await _say(
            chat_id=chat_id,
            text="أرسل صورة الإيصال أو ملف PNG/JPEG/PDF (2 MiB كحد أقصى). سيبقى الاشتراك معلقاً حتى تحقق الإدارة من وصول المال.",
        )
        return
    document = message.get("document")
    photos = message.get("photo", [])
    if document:
        attachment = document
        media_type = document.get("mime_type", "")
    elif photos:
        attachment = photos[-1]
        media_type = "image/jpeg"
    else:
        raise ValidationError(message="Receipt attachment required")
    if (
        media_type not in {"image/png", "image/jpeg", "application/pdf"}
        or attachment.get("file_size", 0) > MAX_RECEIPT_BYTES
    ):
        raise ValidationError(message="Unsupported or oversized receipt")
    content = await download_receipt(file_id=attachment["file_id"])
    async with await get_session() as session:
        owner_id = await TelegramBillingService(session=session).owner_id(
            chat_id=chat_id
        )
        await ManualPaymentService(session=session).submit_receipt(
            payment_id=payment_id,
            owner_id=owner_id,
            transaction_reference=state["reference"],
            content=content,
            media_type=media_type,
        )
    await delete_state(chat_id=chat_id)
    logger.info(
        "telegram_manual_receipt_submitted",
        extra={"payment_id": payment_id, "owner_id": owner_id},
    )
    await _say(
        chat_id=chat_id,
        text="حُفظ الإيصال للمراجعة. الاشتراك لم يتفعّل بعد؛ التفعيل بعد تحقق الإدارة من وصول المال.",
        rows=[[_button(text="متابعة المراجعة", data=f"mb:invoice:{payment_id}")]],
    )
