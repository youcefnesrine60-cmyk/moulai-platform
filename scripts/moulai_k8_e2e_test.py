# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Run real local K8 probes with K7 PKCE helpers and memory-only credentials.

Run from the project root with ``python -m scripts.moulai_k8_e2e_test``.
Open the printed loopback start URL and sign in directly to Keycloak. Only
sanitized status evidence is written; no application lifespan or DB is started.
"""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
import hashlib
import json
import logging
import os
import secrets
import threading
import time
from dataclasses import (
    dataclass,
    field,
)
from datetime import (
    datetime,
    timezone,
)
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)
from pathlib import Path
from typing import Any
from urllib.parse import (
    parse_qs,
    urlencode,
    urlparse,
)

import httpx

from scripts import moulai_k7_pkce_test as k7

API_BASE = "http://127.0.0.1:8000"
START_URL = "http://localhost:8765/start"
LOGIN_TIMEOUT_SECONDS = 600
REPORT_PATH = (
    Path(__file__).resolve().parents[1] / "artifacts/keycloak-k8/final-e2e-results.json"
)


# ==============================================
# MEMORY-ONLY CALLBACK AND CLEAN BROWSER RETURN
# ==============================================


@dataclass
class AuthorizationResult:
    """Keep one-time authorization material out of logs and representations."""

    state: str = field(repr=False)
    authorization_url: str = field(repr=False)
    code: str | None = field(default=None, repr=False)
    failure: bool = False
    received: threading.Event = field(default_factory=threading.Event, repr=False)
    clean_page_loaded: threading.Event = field(
        default_factory=threading.Event, repr=False
    )


def callback_handler(*, result: AuthorizationResult) -> type[BaseHTTPRequestHandler]:
    """Build a quiet one-flow listener using K7's registered callback URI."""

    class CallbackHandler(BaseHTTPRequestHandler):
        """Consume the callback privately and redirect to a URL without a query."""

        def log_message(self, format: str, *args: Any) -> None:
            """Suppress request logging because callback URLs contain codes."""
            return

        def _respond(
            self, *, status: int, location: str | None = None, body: bytes = b""
        ) -> None:
            """Prevent caching and referrer propagation on every local response."""
            self.send_response(status)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Pragma", "no-cache")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Type", "text/html; charset=utf-8")
            if location is not None:
                self.send_header("Location", location)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_GET(self) -> None:
            """Handle only start, the registered callback, and clean completion."""
            parts = urlparse(self.path)
            if parts.path == "/start" and not result.received.is_set():
                self._respond(status=302, location=result.authorization_url)
                return
            if parts.path == "/complete":
                self._respond(
                    status=200,
                    body=(
                        b"<html><body><h2>MoulAI K8</h2>"
                        b"<p>Authorization received. Return to the validation console.</p>"
                        b"</body></html>"
                    ),
                )
                result.clean_page_loaded.set()
                return
            if parts.path != urlparse(k7.CALLBACK).path:
                self._respond(status=404)
                return
            if result.received.is_set():
                self._respond(status=410)
                return
            parameters = parse_qs(parts.query, keep_blank_values=True)
            states = parameters.get("state", [])
            codes = parameters.get("code", [])
            valid_state = (
                len(states) == 1
                and states[0].isascii()
                and secrets.compare_digest(states[0], result.state)
            )
            # An unrelated callback cannot consume the legitimate pending flow.
            if not valid_state:
                self._respond(status=400)
                return
            if "error" in parameters or len(codes) != 1 or not codes[0]:
                result.failure = True
            else:
                result.code = codes[0]
            self._respond(status=303, location="/complete")
            result.received.set()

    return CallbackHandler


# ==============================================
# LOCAL PREFLIGHT AND EXISTING VALIDATOR
# ==============================================


def validate_local_configuration() -> None:
    """Check central settings without changing configuration or opening a DB."""
    from app.core.config import settings

    expected = {
        "APP_ENV": "development",
        "DATABASE_TARGET": "development",
        "DEBUG": False,
        "DB_ECHO": False,
        "OIDC_DIAGNOSTICS_ENABLED": True,
        "OIDC_ALLOW_LOCAL_HTTP": True,
        "OIDC_ISSUER": k7.ISSUER,
        "OIDC_AUDIENCE": k7.EXPECTED_AUDIENCE,
        "OIDC_JWKS_URL": k7.ISSUER + "/protocol/openid-connect/certs",
    }
    if any(getattr(settings, name) != value for name, value in expected.items()):
        raise RuntimeError("local_profile_not_verified")


@contextmanager
def local_diagnostic_api() -> Iterator[str]:
    """Reuse a ready API or temporarily serve the real app without its lifespan."""
    with httpx.Client(
        base_url=API_BASE, timeout=3, trust_env=False, follow_redirects=False
    ) as client:
        try:
            response = client.get("/api/v1/diagnostics/oidc/me")
        except httpx.ConnectError:
            response = None
    if response is not None:
        if response.status_code != 401:
            raise RuntimeError("existing_api_diagnostics_not_ready")
        yield "existing_local_api"
        return

    import uvicorn
    from fastapi import HTTPException

    from app.core.database import get_db
    from app.main import app

    async def database_forbidden() -> None:
        """Refuse any unexpected DB dependency during the diagnostic-only run."""
        raise HTTPException(
            status_code=503, detail="Database disabled for K8 validation"
        )

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = database_forbidden
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            lifespan="off",
            access_log=False,
            log_config=None,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.1)
        if not server.started:
            raise RuntimeError("temporary_diagnostic_api_not_ready")
        yield "temporary_actual_app_lifespan_off_database_denied"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


async def verified_identity(*, token: str) -> tuple[str, frozenset[str]]:
    """Use the existing strict OIDC verifier, not K7's broader algorithm list."""
    from fastapi.security import HTTPAuthorizationCredentials

    from app.api.auth import _verified_access_token_claims
    from app.core.security.oidc import extract_realm_roles

    claims = await _verified_access_token_claims(
        credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        allow_local_http=True,
    )
    if claims.get("preferred_username") != k7.EXPECTED_USERNAME:
        raise RuntimeError("unexpected_authenticated_user")
    roles = extract_realm_roles(claims=claims)
    if "owner" not in roles:
        raise RuntimeError("expected_owner_role_missing")
    return claims["sub"], roles


def check_diagnostics(
    *, client: httpx.Client, token: str, subject: str, roles: frozenset[str]
) -> list[dict[str, str | int | bool]]:
    """Send a real token only as Authorization; retain statuses and booleans."""
    outcomes: list[dict[str, str | int | bool]] = []
    for probe, expected in (("me", 200), ("owner", 200), ("admin", 403)):
        path = "/api/v1/diagnostics/oidc/" + probe
        response = client.get(path, headers={"Authorization": "Bearer " + token})
        if response.status_code != expected or token in response.text:
            raise RuntimeError("diagnostic_result_mismatch")
        if expected == 200:
            body = response.json()
            if (
                body.get("authenticated") is not True
                or body.get("subject") != subject
                or body.get("issuer") != k7.ISSUER
                or body.get("realm_roles") != sorted(roles)
                or response.headers.get("cache-control") != "no-store"
            ):
                raise RuntimeError("diagnostic_identity_mismatch")
        outcomes.append(
            {"path": path, "expected": expected, "actual": response.status_code}
        )
    path = "/api/v1/diagnostics/oidc/me"
    response = client.get(path)
    if (
        response.status_code != 401
        or response.headers.get("www-authenticate") != "Bearer"
    ):
        raise RuntimeError("anonymous_request_not_denied")
    outcomes.append(
        {"path": path, "authenticated": False, "expected": 401, "actual": 401}
    )
    return outcomes


# ==============================================
# REAL K7 PKCE FLOW AND SANITIZED EVIDENCE
# ==============================================


def run_validation(*, api_mode: str) -> int:
    """Perform one real PKCE login and four read-only local diagnostic requests."""
    discovery = k7.get_json(k7.ISSUER + "/.well-known/openid-configuration")
    if (
        discovery.get("issuer") != k7.ISSUER
        or discovery.get("authorization_endpoint")
        != k7.ISSUER + "/protocol/openid-connect/auth"
        or discovery.get("token_endpoint")
        != k7.ISSUER + "/protocol/openid-connect/token"
        or "S256" not in discovery.get("code_challenge_methods_supported", [])
    ):
        raise RuntimeError("unexpected_local_provider_metadata")
    with httpx.Client(
        base_url=API_BASE, timeout=15, trust_env=False, follow_redirects=False
    ) as client:
        preflight = client.get("/api/v1/diagnostics/oidc/me")
        if preflight.status_code != 401:
            raise RuntimeError("protected_diagnostics_not_ready")
        verifier = k7.b64url(secrets.token_bytes(48))
        challenge = k7.b64url(hashlib.sha256(verifier.encode("ascii")).digest())
        state = secrets.token_urlsafe(32)
        query = urlencode(
            {
                "client_id": k7.CLIENT_ID,
                "response_type": "code",
                "redirect_uri": k7.CALLBACK,
                "scope": "openid profile",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
            }
        )
        result = AuthorizationResult(
            state=state,
            authorization_url=discovery["authorization_endpoint"] + "?" + query,
        )
        server = HTTPServer(("127.0.0.1", 8765), callback_handler(result=result))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            print(
                "K8 ready: open " + START_URL + " and sign in as owner-test.",
                flush=True,
            )
            if not result.received.wait(timeout=LOGIN_TIMEOUT_SECONDS):
                raise RuntimeError("interactive_login_timed_out")
            if result.failure or not result.code:
                raise RuntimeError("interactive_authorization_failed")
            code, result.code = result.code, None
            token_response = k7.get_json(
                discovery["token_endpoint"],
                {
                    "grant_type": "authorization_code",
                    "client_id": k7.CLIENT_ID,
                    "redirect_uri": k7.CALLBACK,
                    "code": code,
                    "code_verifier": verifier,
                },
            )
            code = verifier = ""
            token = token_response.get("access_token")
            token_response.clear()
            if not isinstance(token, str) or not token:
                raise RuntimeError("access_token_missing")
            subject, roles = asyncio.run(verified_identity(token=token))
            outcomes = check_diagnostics(
                client=client, token=token, subject=subject, roles=roles
            )
            token = ""
            report = {
                "passed": True,
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "scope": "real Keycloak PKCE S256 and running local FastAPI HTTP API",
                "api_mode": api_mode,
                "application_lifespan_started_by_runner": False,
                "real_user": k7.EXPECTED_USERNAME,
                "issuer": k7.ISSUER,
                "audience": k7.EXPECTED_AUDIENCE,
                "authentication_client": k7.CLIENT_ID,
                "existing_k7_helpers_reused": [
                    "get_json",
                    "b64url",
                    "realm/client/callback constants",
                ],
                "existing_oidc_validator_used": True,
                "algorithm": "RS256",
                "username_and_subject_verified_in_memory": True,
                "owner_role_verified": "owner" in roles,
                "http_results": outcomes,
                "tokens_codes_passwords_persisted": False,
                "database_or_identity_mapping_changed": False,
                "migration_or_deployment_executed": False,
                "render_or_telegram_changed": False,
                "full_test_suite_rerun": False,
            }
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
            print(
                json.dumps(
                    {"passed": True, "statuses": [item["actual"] for item in outcomes]}
                ),
                flush=True,
            )
            result.clean_page_loaded.wait(timeout=5)
            return 0
        finally:
            result.code = None
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def main() -> int:
    """Keep unrelated services inactive and select an explicitly guarded local API."""
    # Only this short-lived runner is quiet; an existing API is not reconfigured.
    logging.disable(logging.CRITICAL)
    os.environ["REDIS_URL"] = ""
    validate_local_configuration()
    with local_diagnostic_api() as api_mode:
        return run_validation(api_mode=api_mode)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # Exception messages/tracebacks can contain request or credential data.
        print(
            "K8 validation failed: "
            + type(error).__name__
            + ". No credentials recorded."
        )
        raise SystemExit(1) from None
