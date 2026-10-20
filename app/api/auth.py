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

"""MoulAI operational module for auth.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
)
from dataclasses import dataclass
from functools import lru_cache
from typing import (
    Annotated,
    Any,
    TypeAlias,
)
from urllib.parse import urlparse

import jwt
from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.database import get_db
from app.core.logger import logger
from app.core.security.oidc import (
    OIDCPrincipal,
    extract_realm_roles,
)
from app.core.security.tenant_scope import bind_owner_scope
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.owner import Owner
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.subscription import Subscription

# ==============================================
# 📋 CONSTANTS
# ==============================================

_ALLOWED_ALGORITHMS = ("RS256",)
"""خوارزميات التوقيع المسموح بها للتحقق من الرموز."""

_REQUIRED_CLAIMS = ("exp", "iss", "aud", "sub", "iat", "typ")
"""المطالبات الإلزامية في رمز JWT."""

_JWKS_CLIENT_CACHE_SIZE = 4
"""حجم ذاكرة التخزين المؤقت لعملاء JWKS."""

_JWKS_TIMEOUT_SECONDS = 5
"""مهلة الاتصال بمزود مفاتيح JWKS بالثواني."""

_JWKS_CACHE_SECONDS = 300
"""مدة حفظ مجموعة المفاتيح، دون إبقاء المفاتيح المسحوبة في ذاكرة دائمة."""

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


# ==============================================
#  GET JWKS CLIENT
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
        cache_keys=False,
        cache_jwk_set=True,
        lifespan=_JWKS_CACHE_SECONDS,
        timeout=_JWKS_TIMEOUT_SECONDS,
    )


# ==============================================
# ⚙️ OIDC CONFIGURATION
# التحقق من إعدادات OIDC
# ==============================================


# ==============================================
#  OIDC CONFIGURATION
# ==============================================


def _oidc_configuration(*, allow_local_http: bool = False) -> tuple[str, str, str]:
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
    if (
        not isinstance(issuer, str)
        or not isinstance(audience, str)
        or not isinstance(jwks_url, str)
        or not issuer
        or not audience
        or not jwks_url
        or any(character.isspace() for character in audience)
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trusted Keycloak authentication is not configured",
        )

    local_http = allow_local_http and oidc_diagnostics_available()
    for value in (issuer, jwks_url):
        try:
            parts = urlparse(value)
            valid = (
                (
                    parts.scheme == "https"
                    or (
                        local_http
                        and settings.OIDC_ALLOW_LOCAL_HTTP
                        and parts.scheme == "http"
                        and parts.hostname in {"localhost", "127.0.0.1", "::1"}
                    )
                )
                and bool(parts.hostname)
                and parts.username is None
                and parts.password is None
                and (parts.port is None or 1 <= parts.port <= 65535)
                and not any(
                    character.isspace() or ord(character) < 32 for character in value
                )
                and not any(character in value for character in "\\?#")
            )
        except ValueError:
            valid = False
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Trusted Keycloak endpoints must be valid HTTPS URLs",
            )
    if urlparse(issuer).scheme == "http" or urlparse(jwks_url).scheme == "http":
        issuer_parts = urlparse(issuer)
        jwks_parts = urlparse(jwks_url)
        if (issuer_parts.scheme, issuer_parts.netloc) != (
            jwks_parts.scheme,
            jwks_parts.netloc,
        ) or jwks_parts.path != issuer_parts.path.rstrip(
            "/"
        ) + "/protocol/openid-connect/certs":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Local Keycloak issuer and JWKS must share the realm origin",
            )
    # Preserve the configured issuer exactly; never invent a realm or normalize
    # issuer paths, trailing slashes, subjects, or the expected API audience.
    return issuer, audience, jwks_url


# ==============================================
# 🔍 BASE SELECT
# استعلامات أساسية لجلب المعرفات مع عزل المالك
# ==============================================


# ==============================================
#  BASE RESTAURANT SELECT
# ==============================================


def _base_restaurant_select() -> Select:
    """
    استعلام أساسي لجلب معرف المطعم مع عزل المالك.

    Returns:
        Select: استعلام SQLAlchemy الأساسي.
    """
    return select(Restaurant.id)


# ==============================================
#  BASE ORDER SELECT
# ==============================================


def _base_order_select() -> Select:
    """
    استعلام أساسي لجلب معرف الطلب مع ربط المطعم.

    Returns:
        Select: استعلام SQLAlchemy الأساسي مع join على جدول المطعم.
    """
    return select(Order.restaurant_id).join(
        Restaurant,
        Order.restaurant_id == Restaurant.id,
    )


# ==============================================
#  BASE ORDER ITEM SELECT
# ==============================================


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
#  BASE PAYMENT SELECT
# ==============================================


def _base_payment_select() -> Select:
    """Return the tenant-scoped base select for platform payments."""
    return select(Payment.id)


# ==============================================
#  BASE SUBSCRIPTION SELECT
# ==============================================


def _base_subscription_select() -> Select:
    """Return the tenant-scoped base select for subscriptions."""
    return select(Subscription.id)


# ==============================================
# 🔐 GET CURRENT OWNER
# التحقق من الرمز واستخراج هوية المالك
# ==============================================


# ==============================================
# GET CURRENT OWNER
# ==============================================


async def get_current_owner(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
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
    subject = await _get_authenticated_subject(credentials)

    owner_id = (
        await session.execute(
            select(Owner.id).where(Owner.auth_subject == subject),
        )
    ).scalar_one_or_none()
    if owner_id is None:
        logger.warning("Authenticated identity is not linked to an owner")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated identity is not linked to an owner",
        )
    return OwnerPrincipal(owner_id=owner_id)


# ==============================================
# 🏪 REQUIRE OWNED RESTAURANT
# التحقق من ملكية المطعم مع عزل البيانات
# ==============================================


# ==============================================
# REQUIRE OWNED RESTAURANT
# ==============================================


async def get_owner_tenant_db(
    owner: Annotated[OwnerPrincipal, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncIterator[AsyncSession]:
    """Yield a request session whose SQL and pending writes enforce owner scope."""
    bind_owner_scope(session=session, owner_id=owner.owner_id)
    yield session


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


# ==============================================
# REQUIRE OWNED ORDER
# ==============================================


async def require_owned_order(
    *,
    order_id: int,
    owner: OwnerPrincipal,
    session: AsyncSession,
) -> int:
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
    restaurant_id = result.scalar_one_or_none()
    if restaurant_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return restaurant_id


# ==============================================
# REQUIRE OWNED PAYMENT
# ==============================================


async def require_owned_payment(
    *,
    payment_id: int,
    owner: OwnerPrincipal,
    session: AsyncSession,
) -> None:
    """Hide payments that do not belong to the authenticated owner."""
    result = await session.execute(
        _base_payment_select().where(
            Payment.id == payment_id,
            Payment.owner_id == owner.owner_id,
        ),
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )


# ==============================================
# REQUIRE OWNED SUBSCRIPTION
# ==============================================


async def require_owned_subscription(
    *,
    subscription_id: int,
    owner: OwnerPrincipal,
    session: AsyncSession,
) -> None:
    """Hide subscriptions that do not belong to the authenticated owner."""
    result = await session.execute(
        _base_subscription_select().where(
            Subscription.id == subscription_id,
            Subscription.owner_id == owner.owner_id,
        ),
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )


# ==============================================
# 🧾 REQUIRE OWNED ORDER ITEM
# التحقق من ملكية عنصر الطلب مع عزل البيانات
# ==============================================


# ==============================================
# REQUIRE OWNED ORDER ITEM
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


# ==============================================
# VERIFY AUTHENTICATED OIDC SUBJECT
# ==============================================


async def _verified_access_token_claims(
    *,
    credentials: HTTPAuthorizationCredentials | None,
    allow_local_http: bool = False,
) -> dict[str, Any]:
    """Verify access-token claims using the existing RS256/JWKS trust boundary.

    Business subject mapping never enables the diagnostic HTTP exception.
    JWKS retrieval runs in a worker thread with the existing bounded cache
    and timeout. Token data and validation exceptions are never logged.
    """

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    issuer, audience, jwks_url = _oidc_configuration(allow_local_http=allow_local_http)
    try:
        header = jwt.get_unverified_header(credentials.credentials)
        if (
            header.get("alg") not in _ALLOWED_ALGORITHMS
            or not isinstance(header.get("kid"), str)
            or not header["kid"].strip()
            or header.get("typ") not in ("JWT", "at+jwt")
        ):
            raise jwt.InvalidTokenError("Unsupported access token header")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
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
    except (jwt.PyJWKError, jwt.PyJWKSetError, ValueError, TypeError) as exc:
        logger.error("Identity provider keys are invalid")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity provider keys are invalid",
        ) from exc

    try:
        claims: dict[str, Any] = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=list(_ALLOWED_ALGORITHMS),
            audience=audience,
            issuer=issuer,
            options={
                "require": list(_REQUIRED_CLAIMS),
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_sub": True,
            },
        )
        if (
            claims.get("iss") != issuer
            or claims.get("typ") != "Bearer"
            or type(claims.get("iat")) is not int
            or type(claims.get("exp")) is not int
            or claims["iat"] < 0
            or claims["exp"] <= claims["iat"]
            or (
                "nbf" in claims
                and (type(claims["nbf"]) is not int or claims["nbf"] < 0)
            )
        ):
            raise jwt.InvalidTokenError("Invalid Keycloak access token claims")
    except (jwt.PyJWTError, ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = claims.get("sub")
    if (
        not isinstance(subject, str)
        or not subject
        or subject != subject.strip()
        or len(subject) > 255
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token has no valid subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims


async def _get_authenticated_subject(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    """Keep business identity mapping on the established HTTPS-only verifier."""
    claims = await _verified_access_token_claims(credentials=credentials)
    return claims["sub"]


# ==============================================
# DIAGNOSTIC IDENTITY AND REALM ROLE DEPENDENCIES
# ==============================================


def oidc_diagnostics_available() -> bool:
    """Require explicit opt-in and the complete safe local execution profile."""
    return (
        settings.OIDC_DIAGNOSTICS_ENABLED
        and settings.APP_ENV == "development"
        and settings.DATABASE_TARGET == "development"
        and settings.DEBUG is False
        and settings.DB_ECHO is False
    )


async def get_current_oidc_principal(
    *,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> OIDCPrincipal:
    """Authenticate diagnostic requests without looking up or creating a tenant."""
    if not oidc_diagnostics_available():
        raise HTTPException(status_code=404, detail="Not found")
    claims = await _verified_access_token_claims(
        credentials=credentials, allow_local_http=True
    )
    try:
        roles = extract_realm_roles(claims=claims)
    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    return OIDCPrincipal(subject=claims["sub"], issuer=claims["iss"], realm_roles=roles)


OIDCRoleDependency: TypeAlias = Callable[[OIDCPrincipal], Awaitable[OIDCPrincipal]]


def require_realm_roles(*, roles: frozenset[str]) -> OIDCRoleDependency:
    """Require every named realm role without granting any business permission."""
    if not roles or any(
        not isinstance(role, str) or not role or role != role.strip() for role in roles
    ):
        raise ValueError("Explicit nonempty realm roles are required")

    async def authorize(
        *,
        principal: Annotated[OIDCPrincipal, Depends(get_current_oidc_principal)],
    ) -> OIDCPrincipal:
        """Return the verified principal or deny insufficient realm roles."""
        if not roles.issubset(principal.realm_roles):
            raise HTTPException(status_code=403, detail="Required realm role missing")
        return principal

    return authorize


@dataclass(frozen=True)
class AdminPrincipal:
    """Identify an active administrator through a verified stored OIDC subject."""

    admin_id: int


AdminPermissionDependency: TypeAlias = Callable[
    [AdminPrincipal, AsyncSession], Awaitable[AdminPrincipal]
]


# ==============================================
# RESOLVE VERIFIED ADMINISTRATOR IDENTITY
# ==============================================


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminPrincipal:
    """Map a verified token subject to one active persisted administrator."""

    from app.models.admin import Admin

    # An administrator ID or Telegram chat mapping cannot bypass an absent
    # trusted identity provider, including when no bearer token is supplied.
    _oidc_configuration()
    subject = await _get_authenticated_subject(credentials)
    admin_id = (
        await session.execute(
            select(Admin.id).where(
                Admin.auth_subject == subject, Admin.is_active.is_(True)
            )
        )
    ).scalar_one_or_none()
    if admin_id is None:
        raise HTTPException(
            status_code=403, detail="Identity is not linked to an active administrator"
        )
    return AdminPrincipal(admin_id=admin_id)


# ==============================================
# REQUIRE LIVE ADMINISTRATOR PERMISSION
# ==============================================


def require_admin_permission(permission: str) -> AdminPermissionDependency:
    """Build a dependency that rechecks active database RBAC for each request."""

    async def authorize(
        admin: Annotated[AdminPrincipal, Depends(get_current_admin)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> AdminPrincipal:
        """Reject authenticated administrators without the requested permission."""

        from app.core.exceptions import UnauthorizedError
        from app.services.business.admin.admin_service import AdminService

        try:
            await AdminService(session).check_admin_permission(
                admin_id=admin.admin_id, required_permission=permission
            )
        except UnauthorizedError as error:
            raise HTTPException(
                status_code=403, detail="Administrator permission required"
            ) from error
        return admin

    return authorize
