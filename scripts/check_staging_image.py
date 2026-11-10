# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OFFLINE COMPILED IMAGE SMOKE CHECK
# Import the real image dependencies and exercise static/session boundaries
# in-process, without a listener, database, provider, lifespan or real identity.
# ==============================================

"""Run only in a read-only --network none test container with a temporary /tmp."""

from __future__ import annotations

# isort: split
# ==============================================
# EXPLICIT OFFLINE FIXTURE DEPENDENCIES
# All credentials below are generated test values, not operational configuration.
# ==============================================

import asyncio
import hashlib
import json
import sys
from ipaddress import ip_network
from pathlib import Path

sys.path.insert(0, "/app")

import httpx
from cryptography.fernet import Fernet

from app.staging.config import StagingConfig
from app.staging.target import StagingTarget

# ==============================================
# COMPILED ARTIFACT AND HOST BOUNDARY
# Deliberately omit lifespan so this cannot masquerade as database/startup proof.
# ==============================================


async def check() -> None:
    """Validate imports and actual compiled delivery under mocked deployment inputs."""
    target = StagingTarget.load(path=Path("/app/deploy/staging/target.json"))
    directory = Path("/tmp/staging-image")
    (directory / "private").mkdir(parents=True)
    configuration = StagingConfig(
        target=target,
        directory=directory,
        database_url="postgresql+asyncpg://"
        + target.runtime_role
        + ":offline-fixture@"
        + target.host
        + "/"
        + target.database,
        client_secret="offline-fixture" * 4,
        session_key=Fernet.generate_key().decode(),
        origin="https://staging.example.invalid",
        issuer="https://identity.example.invalid/realms/moulai-staging",
        client_id="offline-browser",
        audience="offline-api",
        proxy_networks=(ip_network("127.0.0.1/32"),),
    )
    configuration.process_environment()
    from app.staging.web import create_staging_app

    frontend = Path("/app/frontend/staging-dist")
    app = create_staging_app(configuration=configuration, frontend=frontend)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
            base_url=configuration.origin,
            headers={"X-Forwarded-Proto": "https"},
        ) as client:
            assert (await client.get("/health")).status_code == 200
            response = await client.get("/access")
            assert (
                response.status_code == 200
                and "sha256-" in response.headers["content-security-policy"]
            )
            assert (await client.get("/api/web/session")).json() is None
            assert (await client.get("/api/web/unknown")).status_code == 401
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "scope": "actual image imports/static/anonymous ASGI only",
                    "lifespan_started": False,
                    "database_connected": False,
                    "provider_called": False,
                    "listener_started": False,
                    "assets": {
                        name: hashlib.sha256(
                            (frontend / "brand" / name).read_bytes()
                        ).hexdigest()
                        for name in [
                            "Icon-help-MoulAI(2).png",
                            "Icon-Assistant-MoulAI(2).png",
                            "GateWay.ico",
                            "GateWay.png",
                        ]
                    },
                }
            )
        )
    finally:
        await app.state.browser_provider.http.aclose()
        await app.state.browser_engine.dispose()


if __name__ == "__main__":
    asyncio.run(check())
