# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SYNTHETIC STAGING WEB FACTORY
# Serve a separately compiled frontend and authenticated adapters without
# importing deployed main, test identities, fixture loaders or background workers.
# ==============================================

"""Prepared for explicit activation; a successful build is not a remote receipt."""

from __future__ import annotations

# isort: split
# ==============================================
# STATIC DELIVERY AND SHARED BUSINESS COMPOSITION
# Only server-attested configuration can construct this host.
# ==============================================

import hashlib
import json
import re
from base64 import b64encode
from collections.abc import (
    Awaitable,
    Callable,
)
from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
)
from fastapi.responses import FileResponse

from app.integration.web import compose_browser_app
from app.staging.config import StagingConfig

# ==============================================
# VERIFIED STAGING ENTRY
# Reject disconnected/review output and protect SPA fallback from API confusion.
# ==============================================


def create_staging_app(*, configuration: StagingConfig, frontend: Path) -> FastAPI:
    """Mount real server permissions and explicitly labelled synthetic acceptance UI."""
    if not isinstance(configuration, StagingConfig):
        raise TypeError("staging_configuration_required")
    frontend = frontend.resolve()
    manifest = json.loads((frontend / "staging-build.json").read_text())
    if manifest != {
        "mode": "staging",
        "syntheticOnly": True,
        "fixtureAdapterIncluded": False,
    }:
        raise RuntimeError("staging_frontend_build_required")
    page = (frontend / "index.html").read_text(encoding="utf-8")
    hashes = [
        "'sha256-" + b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'"
        for body in re.findall(
            r"<script(?:\s[^>]*)?>(.*?)</script>", page, flags=re.DOTALL
        )
        if body.strip()
    ]
    app = compose_browser_app(configuration=configuration)

    # ==============================================
    # STAGING RESPONSE HARDENING
    # The appearance bootstrap is allowed by exact content hashes, not unsafe script.
    # ==============================================

    @app.middleware("http")
    async def staging_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add a bounded CSP and explicit test marker without exposing private settings."""
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' "
            + " ".join(hashes)
            + "; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["X-MoulAI-Environment"] = "staging-synthetic-only"
        response.headers["Strict-Transport-Security"] = "max-age=3600"
        return response

    # ==============================================
    # READ-ONLY STATIC AND SPA DELIVERY
    # Unknown API paths remain 404 and path traversal cannot leave the compiled tree.
    # ==============================================

    @app.get("/{requested_path:path}")
    async def frontend_page(requested_path: str) -> FileResponse:
        """Deliver compiled files or a browser route, never application source/private data."""
        if requested_path == "api" or requested_path.startswith(
            ("api/", "health/", ".")
        ):
            raise HTTPException(status_code=404)
        candidate = (frontend / requested_path).resolve()
        if not candidate.is_relative_to(frontend):
            raise HTTPException(status_code=404)
        if candidate.is_file():
            return FileResponse(candidate)
        if Path(requested_path).suffix:
            raise HTTPException(status_code=404)
        return FileResponse(frontend / "index.html")

    return app
