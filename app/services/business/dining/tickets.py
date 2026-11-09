# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# READ-ONLY OPAQUE RESERVATION VERIFICATION
# Generate offline QR artwork and return only a redacted current booking status.
# ==============================================

"""QR possession is a read capability only; it never approves money or arrival."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND TOKEN BOUNDARY
# Keep the token in a browser fragment and POST body, outside access-log URL paths.
# ==============================================

import base64
import hashlib
import html
import json
import re
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dining import DiningRequest
from app.schemas.dining import JsonObject
from app.services.business.dining.values import DiningError
from app.services.business.document_qr import (
    DocumentQrError,
    public_read_url,
    svg_for_public_url,
)

# ==============================================
# TICKET SVG
# Create a real SVG QR locally for an explicitly configured trusted origin.
# ==============================================


def ticket_svg(*, token: str, verification_origin: str, locale: str = "fr") -> str:
    """Create a real SVG QR locally for an explicitly configured trusted origin."""
    validate_locale(locale=locale)
    try:
        return svg_for_public_url(
            value=public_read_url(
                origin=verification_origin,
                page="verify-reservation",
                public_id=token,
                locale=locale,
            )
        )
    except DocumentQrError as error:
        raise DiningError(code="dining_verification_origin_or_token_invalid") from error


# ==============================================
# VERIFY TICKET
# Expose only reference and current status, with no PII or mutation method.
# ==============================================


async def verify_ticket(*, session: AsyncSession, token: str) -> TicketStatus:
    """Expose only reference and current status, with no PII or mutation method."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise DiningError(code="dining_ticket_unavailable")
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    result = (
        await session.execute(
            select(DiningRequest.reference, DiningRequest.status).where(
                DiningRequest.qr_hash == digest
            )
        )
    ).one_or_none()
    if result is None:
        raise DiningError(code="dining_ticket_unavailable")
    return {
        "reference": result.reference,
        "status": result.status,
        "valid": result.status in {"confirmed", "arrived", "served"},
    }


# ==============================================
# SELF-CONTAINED PRINT PRESENTATION
# Escape every customer field; embed only locally generated trusted SVG markup.
# ==============================================


PRINT_LABELS = {
    "fr": [
        "Confirmation de réservation",
        "Référence",
        "Statut",
        "Restaurant",
        "Succursale",
        "Tables",
        "Client",
        "Personnes",
        "Début",
        "Fin",
        "Durée (secondes)",
        "Événement",
        "Proposition acceptée",
        "Avance reçue",
        "Devise",
        "Conditions acceptées",
        "Vérification du statut — lecture seule",
        "Confirmation valide",
        "Justificatif invalide",
        "Vérification indisponible",
        "Vérification en cours…",
    ],
    "en": [
        "Reservation confirmation",
        "Reference",
        "Status",
        "Restaurant",
        "Branch",
        "Tables",
        "Customer",
        "Guests",
        "Start",
        "End",
        "Duration (seconds)",
        "Event",
        "Accepted proposal",
        "Received advance",
        "Currency",
        "Accepted terms",
        "Read-only status verification",
        "Valid confirmation",
        "Invalid confirmation",
        "Verification unavailable",
        "Checking current status…",
    ],
    "ar": [
        "تأكيد الحجز",
        "المرجع",
        "الحالة",
        "المطعم",
        "الفرع",
        "الطاولات",
        "العميل",
        "الأشخاص",
        "البداية",
        "النهاية",
        "المدة بالثواني",
        "المناسبة",
        "العرض المقبول",
        "العربون المستلم",
        "العملة",
        "الشروط المقبولة",
        "التحقق من الحالة — للقراءة فقط",
        "تأكيد صالح",
        "مستند غير صالح",
        "التحقق غير متاح",
        "جارٍ التحقق من الحالة…",
    ],
}
STATUS_LABELS = {
    "fr": {
        "confirmed": "Confirmée",
        "arrived": "Arrivée enregistrée",
        "served": "Service terminé",
        "cancelled": "Annulée",
        "pending": "En attente",
        "held": "Blocage temporaire",
        "manual_review": "Vérification humaine",
    },
    "en": {
        "confirmed": "Confirmed",
        "arrived": "Arrived",
        "served": "Served",
        "cancelled": "Cancelled",
        "pending": "Pending",
        "held": "Temporary hold",
        "manual_review": "Human review",
    },
    "ar": {
        "confirmed": "مؤكد",
        "arrived": "تم تسجيل الوصول",
        "served": "اكتملت الخدمة",
        "cancelled": "ملغى",
        "pending": "قيد الانتظار",
        "held": "حجز مؤقت",
        "manual_review": "مراجعة بشرية",
    },
}


# ==============================================
# TICKETSTATUS
# Possession of the QR grants only an expurgated current validity read.
# ==============================================


class TicketStatus(TypedDict):
    """Possession of the QR grants only an expurgated current validity read."""

    reference: str
    status: str
    valid: bool


# ==============================================
# VALIDATE LOCALE
# Accept only the three owner-approved document languages.
# ==============================================


def validate_locale(*, locale: str) -> None:
    """Accept only the three owner-approved document languages."""
    if locale not in PRINT_LABELS:
        raise DiningError(code="dining_document_locale_invalid")


# ==============================================
# PRINTABLE CONFIRMATION
# Render an escaped, localized and printable frozen confirmation with real QR.
# ==============================================


def printable_confirmation(
    *, document: JsonObject, verification_origin: str, locale: str = "fr"
) -> str:
    """Render an escaped, localized and printable frozen confirmation with real QR."""
    validate_locale(locale=locale)
    token = document.get("qr_token")
    if not isinstance(token, str):
        raise DiningError(code="dining_confirmation_ticket_missing")
    artwork = ticket_svg(
        token=token, verification_origin=verification_origin, locale=locale
    )
    keys = [
        "reference",
        "status",
        "restaurant",
        "branch",
        "tables",
        "customer",
        "party_size",
        "starts_at",
        "ends_at",
        "duration_seconds",
        "event_id",
        "menu",
        "advance",
        "currency",
        "terms",
    ]
    labels = PRINT_LABELS[locale]
    rows = []
    for position, key in enumerate(keys, 1):
        value = document.get(key)
        if key == "status":
            display = STATUS_LABELS[locale].get(str(value), str(value))
        elif key == "menu" and isinstance(value, list):
            pieces = []
            for item in value:
                if isinstance(item, dict):
                    kind = str(item.get("kind", ""))
                    kind_name = {
                        "fr": {
                            "table": "Table",
                            "preparation": "Préparation",
                            "menu": "Menu",
                        },
                        "en": {
                            "table": "Table",
                            "preparation": "Preparation",
                            "menu": "Menu",
                        },
                        "ar": {
                            "table": "الطاولة",
                            "preparation": "التحضير",
                            "menu": "القائمة",
                        },
                    }[locale].get(kind, kind)
                    pieces.append(
                        f"{kind_name} {item.get('description','')} : {item.get('quantity','')} × {item.get('rate','')} = {item.get('amount','')} {document.get('currency','')}"
                    )
            display = "\n".join(pieces)
        else:
            display = (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else str(value if value is not None else "—")
            )
        rows.append(
            f"<dt>{html.escape(labels[position])}</dt><dd><bdi>{html.escape(display)}</bdi></dd>"
        )
    direction = "rtl" if locale == "ar" else "ltr"
    return (
        f'<!doctype html><html lang="{locale}" dir="{direction}"><meta charset="utf-8"><meta name="referrer" content="no-referrer"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MoulAI — {labels[0]}</title><style>body{{font:16px system-ui;max-width:800px;margin:32px auto;padding:20px;color:#051b2d}}dt{{font-weight:700;margin-top:16px}}dd{{margin:4px 0;overflow-wrap:anywhere;white-space:pre-line}}svg{{width:200px;height:auto}}@media print{{body{{margin:0;padding:0}}svg{{break-inside:avoid}}}}</style><h1>MoulAI™ — {labels[0]}</h1><dl>'
        + "".join(rows)
        + f"</dl><h2>{labels[16]}</h2>"
        + artwork
        + "</html>"
    )


# ==============================================
# VERIFICATION VIEWER
# Localize a same-origin read-only viewer; a cancelled QR explicitly becomes invalid.
# ==============================================


def verification_viewer(*, locale: str) -> tuple[str, str]:
    """Localize a same-origin read-only viewer; a cancelled QR explicitly becomes invalid."""
    validate_locale(locale=locale)
    labels = PRINT_LABELS[locale]
    translations = json.dumps(
        {
            "valid": labels[17],
            "invalid": labels[18],
            "unavailable": labels[19],
            "states": STATUS_LABELS[locale],
        },
        ensure_ascii=False,
    )
    script = (
        "const copy="
        + translations
        + ";const token=location.hash.slice(1);const result=document.getElementById('result');if(!/^[A-Za-z0-9_-]{43}$/.test(token)){result.textContent=copy.invalid;}else{fetch('/dining/verify-reservation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token}),credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer'}).then(async response=>{if(!response.ok)throw new Error('unavailable');return response.json();}).then(data=>{result.textContent=(data.valid?copy.valid:copy.invalid)+' — '+data.reference+' — '+(copy.states[data.status]||data.status);result.dataset.valid=String(data.valid);}).catch(()=>{result.textContent=copy.unavailable;});}"
    )
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    direction = "rtl" if locale == "ar" else "ltr"
    content = (
        f'<!doctype html><html lang="{locale}" dir="{direction}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>MoulAI — {labels[16]}</title><h1>MoulAI™ — {labels[16]}</h1><p id="result" role="status">{labels[20]}</p><script>'
        + script
        + "</script></html>"
    )
    return (
        content,
        f"default-src 'none'; script-src 'sha256-{digest}'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
    )
