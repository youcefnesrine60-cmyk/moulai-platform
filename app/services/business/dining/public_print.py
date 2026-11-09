# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# RETAINED DOCUMENT AND TABLE PRINTS
# Render real QR artwork and a manual read URL without changing the issued reference.
# ==============================================

"""Only authorized private callers supply document details; public verification stays minimal."""

from __future__ import annotations

# isort: split
# ==============================================
# ESCAPING AND COMMON LOCAL QR ENCODING
# No remote fonts, images, tracking scripts or conversion services enter the print.
# ==============================================

import html
from base64 import b64encode
from pathlib import Path

from app.models.dining_service import DiningPublicLink
from app.schemas.dining import JsonObject
from app.services.business.dining.tickets import validate_locale
from app.services.business.document_qr import (
    public_read_url,
    svg_for_public_url,
)

LABELS = {
    "fr": {
        "table": "Table — menu",
        "reservation": "Confirmation de réservation",
        "food_invoice": "Facture client",
        "receipt": "Reçu",
        "reference": "Référence",
        "version": "Version émise",
        "status": "État du lien",
        "read": "Consultation et statut actuel — lecture seule",
        "retained": "Contenu conservé de la version émise",
        "active": "Actif",
        "invalid": "Invalidé",
        "table_label": "Table",
        "floor": "Étage",
        "room": "Salle",
    },
    "en": {
        "table": "Table — menu",
        "reservation": "Reservation confirmation",
        "food_invoice": "Food invoice",
        "receipt": "Receipt",
        "reference": "Reference",
        "version": "Issued version",
        "status": "Link state",
        "read": "View and current status — read only",
        "retained": "Retained issued version content",
        "active": "Active",
        "invalid": "Invalidated",
        "table_label": "Table",
        "floor": "Floor",
        "room": "Room",
    },
    "ar": {
        "table": "الطاولة — القائمة",
        "reservation": "تأكيد الحجز",
        "food_invoice": "فاتورة العميل",
        "receipt": "إيصال",
        "reference": "المرجع",
        "version": "النسخة الصادرة",
        "status": "حالة الرابط",
        "read": "العرض والحالة الحالية — للقراءة فقط",
        "retained": "محتوى النسخة الصادرة المحفوظ",
        "active": "نشط",
        "invalid": "ملغى",
        "table_label": "الطاولة",
        "floor": "الطابق",
        "room": "القاعة",
    },
}

FIELD_LABELS = {
    "fr": {
        "total": "Total de la facture",
        "currency": "Devise",
        "received_amount": "Montant reçu",
        "received_at": "Encaissement observé le",
        "reference": "Référence de la source",
        "request_id": "Réservation",
        "occupation_id": "Occupation",
        "customer": "Client",
        "party_size": "Personnes",
        "starts_at": "Début",
        "ends_at": "Fin",
        "terms": "Conditions acceptées",
        "advance": "Avance reçue",
        "status": "État de la source lors de l’émission",
        "mode": "Mode d’encaissement",
        "lines": "Lignes de facture",
        "description": "Désignation",
        "quantity": "Quantité",
        "unit_price": "Prix unitaire",
        "amount": "Montant",
    },
    "en": {
        "total": "Invoice total",
        "currency": "Currency",
        "received_amount": "Amount received",
        "received_at": "Collection observed at",
        "reference": "Source reference",
        "request_id": "Reservation",
        "occupation_id": "Occupation",
        "customer": "Customer",
        "party_size": "Party size",
        "starts_at": "Starts at",
        "ends_at": "Ends at",
        "terms": "Accepted terms",
        "advance": "Advance received",
        "status": "Source state when issued",
        "mode": "Collection mode",
        "lines": "Invoice lines",
        "description": "Description",
        "quantity": "Quantity",
        "unit_price": "Unit price",
        "amount": "Amount",
    },
    "ar": {
        "total": "إجمالي الفاتورة",
        "currency": "العملة",
        "received_amount": "المبلغ المستلم",
        "received_at": "التحصيل الملاحظ في",
        "reference": "مرجع المصدر",
        "request_id": "الحجز",
        "occupation_id": "الإشغال",
        "customer": "العميل",
        "party_size": "عدد الأشخاص",
        "starts_at": "البداية",
        "ends_at": "النهاية",
        "terms": "الشروط المقبولة",
        "advance": "العربون المستلم",
        "status": "حالة المصدر عند الإصدار",
        "mode": "طريقة التحصيل",
        "lines": "بنود الفاتورة",
        "description": "الوصف",
        "quantity": "الكمية",
        "unit_price": "سعر الوحدة",
        "amount": "المبلغ",
    },
}

# ==============================================
# PRINT AN ALREADY AUTHORIZED VERSION
# Stable reference and digest distinguish a reprint from a replacement or rotated link.
# ==============================================


def _table_menu_print(
    *, document: JsonObject, url: str, artwork: str, locale: str
) -> str:
    """Compose a customer-facing table card using unchanged official pixels and live identification.

    The caller has already authorized this table. No physical state, digest or
    administrative version is printed; current information is consulted at scan.
    Missing official artwork is an explicit failure, never an approximate logo.
    """
    escape = html.escape
    labels = LABELS[locale]
    instruction = {
        "fr": "Scannez pour consulter le menu",
        "en": "Scan to view the menu",
        "ar": "امسح الرمز للاطلاع على القائمة",
    }[locale]
    location_labels = {
        "fr": {
            "floor": "Étage",
            "room": "Salle",
            "zone": "Zone",
            "location": "Emplacement",
        },
        "en": {
            "floor": "Floor",
            "room": "Room",
            "zone": "Zone",
            "location": "Location",
        },
        "ar": {
            "floor": "الطابق",
            "room": "القاعة",
            "zone": "المنطقة",
            "location": "الموقع",
        },
    }[locale]
    logo = (
        Path(__file__).resolve().parents[4]
        / "frontend/public/brand/moulai-logo-light01.png"
    )
    encoded = b64encode(logo.read_bytes()).decode("ascii")
    location = " · ".join(
        escape(location_labels[key]) + ": " + escape(str(document[key]))
        for key in ("floor", "room", "zone", "location")
        if document.get(key)
    )
    direction = "rtl" if locale == "ar" else "ltr"
    return f"""<!doctype html><html lang="{locale}" dir="{direction}">
<meta charset="utf-8"><meta name="referrer" content="no-referrer">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MoulAI — {labels['table_label']} {escape(str(document.get('table', '')))}</title>
<style>
@page{{size:A5 portrait;margin:10mm}}
*{{box-sizing:border-box}}body{{margin:0;padding:20px;background:#fff;color:#0b1324;font:16px system-ui;text-align:center}}
.menu-card{{max-width:460px;margin:auto;padding:24px 20px;border:1px solid #bdcecf;border-radius:18px;break-inside:avoid}}
.logo{{display:block;width:260px;max-width:100%;height:auto;margin:0 auto 16px}}
h1{{font-size:25px;margin:8px 0}}h2{{font-size:30px;margin:18px 0 10px}}
p{{margin:10px 0;line-height:1.5;overflow-wrap:anywhere}}.branch{{font-size:18px}}.location{{font-size:15px}}
.qr{{display:flex;justify-content:center;background:#fff;padding:12px;margin:12px auto;max-width:280px}}
svg{{display:block;width:240px;max-width:100%;height:auto;background:#fff}}.instruction{{font-size:20px;font-weight:700}}
.manual{{font-size:11px;direction:ltr;display:block;overflow-wrap:anywhere;color:#004c59}}
@media print{{body{{padding:0}}.menu-card{{border:0;padding:0}}}}
</style><main class="menu-card">
<img class="logo" src="data:image/png;base64,{encoded}" alt="MoulAI™">
<h1>{escape(str(document.get('restaurant', '')))}</h1>
<p class="branch">{escape(str(document.get('branch', '')))}</p>
<h2>{labels['table_label']} <bdi>{escape(str(document.get('table', '')))}</bdi></h2>
<p class="location">{location}</p><div class="qr">{artwork}</div>
<p class="instruction">{instruction}</p>
<a class="manual" href="{escape(url, quote=True)}">{escape(url)}</a>
</main></html>"""


# ==============================================
# RENDER SUPPORTED DOCUMENTS
# Keep financial snapshots unchanged while selecting the customer table composition.
# ==============================================


def print_public_document(
    *, link: DiningPublicLink, document: JsonObject, origin: str, locale: str
) -> str:
    """Escape all supplied content and encode only the opaque read address with a quiet zone."""
    validate_locale(locale=locale)
    labels = LABELS[locale]
    url = public_read_url(
        origin=origin,
        page="menu" if link.kind == "table" else "verify-document",
        public_id=link.public_id,
        locale=locale,
    )
    artwork = svg_for_public_url(value=url)
    if link.kind == "table":
        return _table_menu_print(
            document=document, url=url, artwork=artwork, locale=locale
        )
    escape = html.escape
    direction = "rtl" if locale == "ar" else "ltr"
    fields = FIELD_LABELS[locale]
    state_labels = {
        "fr": {
            "finalized": "Finalisée",
            "verified": "Vérifié",
            "confirmed": "Confirmée",
            "arrived": "Arrivée enregistrée",
            "served": "Service terminé",
        },
        "en": {
            "finalized": "Finalized",
            "verified": "Verified",
            "confirmed": "Confirmed",
            "arrived": "Arrived",
            "served": "Served",
        },
        "ar": {
            "finalized": "نهائية",
            "verified": "متحقق منه",
            "confirmed": "مؤكد",
            "arrived": "تم تسجيل الوصول",
            "served": "اكتملت الخدمة",
        },
    }
    rows = []
    keys = (
        ("table", "floor", "room")
        if link.kind == "table"
        else (
            "reference",
            "status",
            "request_id",
            "occupation_id",
            "customer",
            "party_size",
            "starts_at",
            "ends_at",
            "total",
            "advance",
            "received_amount",
            "received_at",
            "currency",
            "mode",
            "terms",
        )
    )
    for key in keys:
        value = document.get(key)
        if value is None:
            continue
        label = (
            labels["table_label"]
            if key == "table"
            else labels[key] if key in {"floor", "room"} else fields[key]
        )
        if key == "status":
            value = state_labels[locale].get(str(value), str(value))
        rows.append(
            "<p><strong>"
            + escape(label)
            + ": </strong><bdi>"
            + escape(str(value))
            + "</bdi></p>"
        )
    invoice_lines = document.get("lines")
    if isinstance(invoice_lines, list):
        keys_line = ("description", "quantity", "unit_price", "amount")
        rows.append(
            "<table><caption>"
            + fields["lines"]
            + "</caption><thead><tr>"
            + "".join("<th>" + fields[key] + "</th>" for key in keys_line)
            + "</tr></thead><tbody>"
        )
        for line in invoice_lines:
            if isinstance(line, dict):
                rows.append(
                    "<tr>"
                    + "".join(
                        "<td><bdi>" + escape(str(line.get(key, "—"))) + "</bdi></td>"
                        for key in keys_line
                    )
                    + "</tr>"
                )
        rows.append("</tbody></table>")
    body = "".join(rows)
    return f"""<!doctype html><html lang="{locale}" dir="{direction}"><meta charset="utf-8"><meta name="referrer" content="no-referrer"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MoulAI — {labels[link.kind]}</title><style>body{{font:16px system-ui;color:#051b2d;background:white;max-width:800px;margin:24px auto;padding:16px}}svg{{display:block;width:220px;height:auto;break-inside:avoid}}a{{overflow-wrap:anywhere}}table{{border-collapse:collapse;width:100%;margin-block:16px}}td,th{{padding:8px;text-align:start;border-bottom:1px solid #8999a7}}p{{overflow-wrap:anywhere}}bdi{{unicode-bidi:isolate}}@media print{{body{{margin:0}}}}</style><h1>MoulAI™ — {labels[link.kind]}</h1><p>{escape(str(document.get('restaurant','')))} · {escape(str(document.get('branch','')))}</p><p>{labels['reference']}: <bdi>{escape(link.reference)}</bdi></p><p>{labels['version']}: {link.version} · {labels['status']}: {labels['active'] if link.active else labels['invalid']}</p>{body}<h2>{labels['read']}</h2>{artwork}<a href="{escape(url,quote=True)}" dir="ltr">{escape(url)}</a><p dir="ltr">SHA-256: {escape(link.digest)}</p></html>"""
