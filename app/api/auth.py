# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔐 ORDERS API AUTHENTICATION
# مصادقة واجهة برمجة الطلبات
# يتضمن: التحقق من الرمز، صلاحيات المالك، عزل بيانات المطاعم
# ==============================================

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional
from urllib.parse import urlparse

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from starlette.concurrency import run_in_threadpool

from app.core.logger import logger
from app.core.config import settings
from app.core.database import get_db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.owner import Owner
from app.models.restaurant import Restaurant

# ==============================================
# 📋 CONSTANTS
# ==============================================

_ALLOWED_ALGORITHMS = ("RS256", "ES256")
"""خوارزميات التوقيع المسموح بها للتحقق من الرموز."""

_REQUIRED_CLAIMS = ("exp", "iss", "aud", "sub")
"""المطالبات الإلزامية في رمز JWT."""

_JWKS_CLIENT_CACHE_SIZE = 4
"""حجم ذاكرة التخزين المؤقت لعملاء JWKS."""

_JWKS_TIMEOUT_SECONDS = 5
"""مهلة الاتصال بمزود مفاتيح JWKS بالثواني."""

# ==============================================
# 🔐 HTTP BEARER SCHEME
# ==============================================

bearer_scheme = HTTPBearer(auto_error=False)


# ==============================================
# 🧑💼 OWNER PRINCIPAL
# هوية المالك بعد التحقق من الرمز
# ==============================================

@dataclass(frozen=True)
class OwnerPrincipal:
    """
    هوية المالك المستخرجة من الرمز بعد التحقق.

    Attributes:
        owner_id: معرف المالك في قاعدة البيانات.
    """
    owner_id: int


# ==============================================
# 🔑 JWKS CLIENT CACHE
# ذاكرة تخزين مؤقت لعملاء JWKS
# ==============================================

@lru_cache(maxsize=_JWKS_CLIENT_CACHE_SIZE)
def _get_jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    """
    إنشاء أو إرجاع عميل JWKS مع التخزين المؤقت.

    Args:
        jwks_url: رابط مزود مفاتيح JWKS.

    Returns:
        jwt.PyJWKClient: عميل JWKS جاهز للاستخدام.
    """
    return jwt.PyJWKClient(
        jwks_url,
        cache_keys=True,
        timeout=_JWKS_TIMEOUT_SECONDS,
    )


# ==============================================
# ⚙️ OIDC CONFIGURATION
# التحقق من إعدادات OIDC
# ==============================================

def _oidc_configuration() -> tuple[str, str, str]:
    """
    التحقق من إعدادات OIDC وإرجاع القيم المطلوبة.

    Returns:
        tuple[str, str, str]: (issuer, audience, jwks_url).

    Raises:
        HTTPException: إذا كانت الإعدادات ناقصة أو غير آمنة.
    """
    issuer = settings.OIDC_ISSUER
    audience = settings.OIDC_AUDIENCE
    jwks_url = settings.OIDC_JWKS_URL
    if not issuer or not audience or not jwks_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orders API authentication is not configured",
        )

    issuer_parts = urlparse(issuer)
    jwks_parts = urlparse(jwks_url)
    if (
        issuer_parts.scheme != "https"
        or not issuer_parts.netloc
        or jwks_parts.scheme != "https"
        or not jwks_parts.netloc
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orders API identity provider must use HTTPS",
        )
    return issuer, audience, jwks_url


# ==============================================
# 🔍 BASE SELECT
# استعلامات أساسية لجلب المعرفات مع عزل المالك
# ==============================================

def _base_restaurant_select() -> Select:
    """
    استعلام أساسي لجلب معرف المطعم مع عزل المالك.

    Returns:
        Select: استعلام SQLAlchemy الأساسي.
    """
    return select(Restaurant.id)


def _base_order_select() -> Select:
    """
    استعلام أساسي لجلب معرف الطلب مع ربط المطعم.

    Returns:
        Select: استعلام SQLAlchemy الأساسي مع join على جدول المطعم.
    """
    return (
        select(Order.id)
        .join(Restaurant, Order.restaurant_id == Restaurant.id)
    )


def _base_order_item_select() -> Select:
    """
    استعلام أساسي لجلب معرف عنصر الطلب مع ربط الطلب والمطعم.

    Returns:
        Select: استعلام SQLAlchemy الأساسي مع join على الطلب والمطعم.
    """
    return (
        select(OrderItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .join(Restaurant, Order.restaurant_id == Restaurant.id)
    )


# ==============================================
# 🔐 GET CURRENT OWNER
# التحقق من الرمز واستخراج هوية المالك
# ==============================================

async def get_current_owner(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> OwnerPrincipal:
    """
    التحقق من رمز Bearer واستخراج هوية المالك.

    Args:
        credentials: بيانات الاعتماد المستخرجة من الترويسة.
        session: جلسة قاعدة البيانات غير المتزامنة.

    Returns:
        OwnerPrincipal: هوية المالك بعد التحقق.

    Raises:
        HTTPException: إذا كان الرمز غير صالح أو الهوية غير مرتبطة بمالك.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    issuer, audience, jwks_url = _oidc_configuration()
    try:
        signing_key = await run_in_threadpool(
            _get_jwks_client(jwks_url).get_signing_key_from_jwt,
            credentials.credentials,
        )
    except jwt.PyJWKClientConnectionError as exc:
        logger.error(
            "Identity provider keys are unavailable",
            extra={"jwks_url": jwks_url},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity provider keys are unavailable",
        ) from exc
    except (jwt.PyJWKClientError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        claims: dict[str, Any] = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=list(_ALLOWED_ALGORITHMS),
            audience=audience,
            issuer=issuer,
            options={"require": list(_REQUIRED_CLAIMS)},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token has no valid subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    owner_id = (
        await session.execute(
            select(Owner.id).where(Owner.auth_subject == subject),
        )
    ).scalar_one_or_none()
    if owner_id is None:
        logger.warning(
            "Authenticated identity is not linked to an owner",
            extra={"subject": subject},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated identity is not linked to an owner",
        )
    return OwnerPrincipal(owner_id=owner_id)


# ==============================================
# 🏪 REQUIRE OWNED RESTAURANT
# التحقق من ملكية المطعم مع عزل البيانات
# ==============================================

async def require_owned_restaurant(
    *,
    restaurant_id: int,
    owner: OwnerPrincipal,
    session: AsyncSession,
) -> None:
    """
    التحقق من أن المطعم يخص المالك الحالي.

    Args:
        restaurant_id: معرف المطعم.
        owner: هوية المالك الحالي.
        session: جلسة قاعدة البيانات غير المتزامنة.

    Raises:
        HTTPException: إذا لم يكن المطعم مملوكاً للمالك.
    """
    result = await session.execute(
        _base_restaurant_select().where(
            Restaurant.id == restaurant_id,
            Restaurant.owner_id == owner.owner_id,
        ),
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found",
        )


# ==============================================
# 📦 REQUIRE OWNED ORDER
# التحقق من ملكية الطلب مع عزل بيانات المطعم
# ==============================================

async def require_owned_order(
    *,
    order_id: int,
    owner: OwnerPrincipal,
    session: AsyncSession,
) -> None:
    """
    التحقق من أن الطلب يخص مطعماً يملكه المالك الحالي.

    Args:
        order_id: معرف الطلب.
        owner: هوية المالك الحالي.
        session: جلسة قاعدة البيانات غير المتزامنة.

    Raises:
        HTTPException: إذا لم يكن الطلب مملوكاً للمالك.
    """
    result = await session.execute(
        _base_order_select().where(
            Order.id == order_id,
            Restaurant.owner_id == owner.owner_id,
        ),
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )


# ==============================================
# 🧾 REQUIRE OWNED ORDER ITEM
# التحقق من ملكية عنصر الطلب مع عزل البيانات
# ==============================================

async def require_owned_order_item(
    *,
    order_item_id: int,
    owner: OwnerPrincipal,
    session: AsyncSession,
) -> None:
    """
    التحقق من أن عنصر الطلب يخص مطعماً يملكه المالك الحالي.

    Args:
        order_item_id: معرف عنصر الطلب.
        owner: هوية المالك الحالي.
        session: جلسة قاعدة البيانات غير المتزامنة.

    Raises:
        HTTPException: إذا لم يكن عنصر الطلب مملوكاً للمالك.
    """
    result = await session.execute(
        _base_order_item_select().where(
            OrderItem.id == order_item_id,
            Restaurant.owner_id == owner.owner_id,
        ),
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order item not found",
        )