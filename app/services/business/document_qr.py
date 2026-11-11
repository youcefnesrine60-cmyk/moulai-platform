# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# COMMON READ-ONLY DOCUMENT QR PRIMITIVES
# Encode only an explicit public origin, a supported read page and an opaque reference.
# ==============================================

"""Local SVG generation shared by reservations, tables and supported emitted documents."""

from __future__ import annotations

# isort: split
# ==============================================
# LOCAL ENCODING AND STRICT URL VALIDATION
# No provider, transport, personal data or authentication assertion enters a QR payload.
# ==============================================

import re
from io import BytesIO
from typing import (
    Literal,
    TypeAlias,
)
from urllib.parse import (
    parse_qs,
    urlsplit,
)

import qrcode
from qrcode.image.svg import SvgPathImage

ReadPage: TypeAlias = Literal[
    "menu", "verify-document", "verify-reservation", "verify-saas-document"
]
READ_PAGES = frozenset(
    {"/menu", "/verify-document", "/verify-reservation", "/verify-saas-document"}
)


# ==============================================
# BOUNDED QR CONFIGURATION FAILURE
# Individual modules translate this error without leaking document or token contents.
# ==============================================


class DocumentQrError(ValueError):
    """Reject an invalid origin, unsupported write page or nonopaque identifier."""


# ==============================================
# PUBLIC OPAQUE REFERENCE
# The identifier is not a login credential and contains no business/customer fields.
# ==============================================


def valid_public_id(*, value: str) -> bool:
    """Accept only the fixed-length cryptographically generated URL-safe representation."""
    return (
        isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{43}", value) is not None
    )


# ==============================================
# EXPLICIT ORIGIN ADMISSION
# HTTP is limited to loopback rehearsal; deployed read links require an HTTPS origin.
# ==============================================


def checked_public_origin(*, value: str) -> str:
    """Require an origin without credentials, path, query, fragment or fallback setting."""
    try:
        parsed = urlsplit(value)
        _validated_port = parsed.port
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or (
                parsed.scheme == "http"
                and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            )
        ):
            raise DocumentQrError("document_qr_origin_invalid")
    except (ValueError, TypeError) as error:
        raise DocumentQrError("document_qr_origin_invalid") from error
    return value.rstrip("/")


# ==============================================
# READ-ONLY ADDRESS BUILDER
# The fragment keeps opaque values out of ordinary HTTP request URL logs.
# ==============================================


def public_read_url(*, origin: str, page: ReadPage, public_id: str, locale: str) -> str:
    """Return a scanable/manual read address with no mutation or finance authority."""
    if (
        "/" + page not in READ_PAGES
        or not valid_public_id(value=public_id)
        or locale not in {"fr", "en", "ar"}
    ):
        raise DocumentQrError("document_qr_reference_invalid")
    return f"{checked_public_origin(value=origin)}/{page}?locale={locale}#{public_id}"


# ==============================================
# GENERATE A REAL SVG QR OFFLINE
# Validate the entire payload again so direct callers cannot encode an action endpoint.
# ==============================================


def svg_for_public_url(*, value: str) -> str:
    """Generate the supplied read address with a standard quiet zone and no network I/O."""
    parsed = urlsplit(value)
    checked_public_origin(value=f"{parsed.scheme}://{parsed.netloc}")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if (
        parsed.path not in READ_PAGES
        or set(query) != {"locale"}
        or len(query["locale"]) != 1
        or query["locale"][0] not in {"fr", "en", "ar"}
        or not valid_public_id(value=parsed.fragment)
    ):
        raise DocumentQrError("document_qr_payload_invalid")
    image = qrcode.make(value, image_factory=SvgPathImage, border=4)
    output = BytesIO()
    image.save(output)
    return output.getvalue().decode("utf-8")
