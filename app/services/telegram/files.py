# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Download bounded receipt evidence exclusively from the official Bot API."""

# ==============================================
# IMPORTS
# ==============================================

import re
from pathlib import PurePosixPath

import httpx

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.logger import logger
from app.services.business.manual_payment_service import MAX_RECEIPT_BYTES
from app.services.telegram.client import client

# ==============================================
# DOWNLOAD RECEIPT
# ==============================================


async def download_receipt(*, file_id: str) -> bytes:
    """Bound both declared and streamed sizes; never expose token-bearing URLs."""
    token = settings.BOT_TOKEN
    try:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/getFile",
            json={"file_id": file_id},
            follow_redirects=False,
        )
        if response.status_code != 200:
            raise ValidationError(message="Receipt download unavailable")
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValidationError(message="Invalid Telegram receipt metadata")
        metadata = payload.get("result", {})
        if not isinstance(metadata, dict):
            raise ValidationError(message="Invalid Telegram receipt metadata")
        path = metadata.get("file_path", "")
        file_size = metadata.get("file_size", 0)
        if (
            not payload.get("ok")
            or not isinstance(path, str)
            or not path
            or re.fullmatch(r"[A-Za-z0-9_./-]+", path) is None
            or PurePosixPath(path).is_absolute()
            or ".." in PurePosixPath(path).parts
            or any(character in path for character in "\\?#:")
            or type(file_size) is not int
            or not 0 <= file_size <= MAX_RECEIPT_BYTES
        ):
            raise ValidationError(message="Invalid or oversized Telegram receipt")
        content = bytearray()
        async with client.stream(
            "GET",
            f"https://api.telegram.org/file/bot{token}/{path}",
            follow_redirects=False,
        ) as stream:
            if stream.status_code != 200:
                raise ValidationError(message="Receipt download unavailable")
            async for chunk in stream.aiter_bytes(chunk_size=65_536):
                content.extend(chunk)
                if len(content) > MAX_RECEIPT_BYTES:
                    raise ValidationError(message="Receipt exceeds 2 MiB")
        if not content:
            raise ValidationError(message="Receipt is empty")
        return bytes(content)
    except (httpx.HTTPError, ValueError, TypeError) as error:
        logger.warning("telegram_receipt_download_failed")
        raise ValidationError(message="Receipt download unavailable") from error
