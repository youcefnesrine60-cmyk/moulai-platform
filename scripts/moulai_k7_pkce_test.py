# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""MoulAI K7: local OIDC authorization-code + PKCE verification.
Local test only: no token/password printed or persisted.
"""
import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

ISSUER = "http://localhost:8080/realms/moulai"
CLIENT_ID = "moulai-local-test"
EXPECTED_AUDIENCE = "moulai-api"
EXPECTED_USERNAME = "owner-test"
CALLBACK = "http://localhost:8765/callback"


def get_json(url, data=None):
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def decode_segment(segment):
    return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))


def main():
    discovery = get_json(ISSUER + "/.well-known/openid-configuration")
    assert discovery["issuer"] == ISSUER, "Issuer OIDC incorrect"
    jwks = get_json(discovery["jwks_uri"])
    assert jwks.get("keys"), "JWKS sans clés"
    print("[OK] Discovery + JWKS accessibles")
    verifier = b64url(secrets.token_bytes(48))
    challenge = b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    state = secrets.token_urlsafe(32)
    result = {}
    done = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_error(404)
                return
            params = urllib.parse.parse_qs(parsed.query)
            if params.get("state", [None])[0] != state:
                result["error"] = "State incorrect"
            elif "error" in params:
                result["error"] = params["error"][0]
            else:
                result["code"] = params.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write("<html><body><h3>Retour Keycloak reçu. Vous pouvez fermer cet onglet.</h3></body></html>".encode("utf-8"))
            done.set()

    server = HTTPServer(("127.0.0.1", 8765), CallbackHandler)
    server.timeout = 1
    threading.Thread(target=lambda: ([(server.handle_request()) for _ in iter(lambda: not done.is_set(), False)]), daemon=True).start()
    # A separate timer ensures the script exits if there is no callback.
    query = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": CALLBACK,
        "scope": "openid profile",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    })
    url = discovery["authorization_endpoint"] + "?" + query
    print("Ouverture du navigateur : connectez-vous en tant que owner-test.")
    webbrowser.open(url)
    if not done.wait(120):
        server.server_close()
        raise RuntimeError("Délai expiré (120 s). Relancez le script.")
    server.server_close()
    if result.get("error") or not result.get("code"):
        raise RuntimeError("Échec de l'authentification : " + str(result.get("error", "code absent")))
    token_response = get_json(discovery["token_endpoint"], {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": CALLBACK,
        "code": result["code"],
        "code_verifier": verifier,
    })
    jwt = token_response["access_token"]
    # Prefer existing PyJWT[crypto] in MoulAI's venv.
    import jwt as pyjwt
    key_client = pyjwt.PyJWKClient(discovery["jwks_uri"])
    key = key_client.get_signing_key_from_jwt(jwt)
    payload = pyjwt.decode(jwt, key.key, algorithms=["RS256", "PS256", "ES256", "EdDSA"], audience=EXPECTED_AUDIENCE, issuer=ISSUER)
    roles = payload.get("realm_access", {}).get("roles", [])
    checks = {"issuer": payload.get("iss") == ISSUER,
              "audience": EXPECTED_AUDIENCE in ([payload.get("aud")] if isinstance(payload.get("aud"), str) else payload.get("aud", [])),
              "username": payload.get("preferred_username") == EXPECTED_USERNAME,
              "owner_role": "owner" in roles,
              "subject_present": bool(payload.get("sub"))}
    for label, ok in checks.items():
        print(("[OK] " if ok else "[ECHEC] ") + label)
    if all(checks.values()):
        print("K7 VALIDÉ : signature JWT, issuer, audience, sub et rôle owner vérifiés.")
    else:
        raise RuntimeError("K7 incomplet : une ou plusieurs vérifications ont échoué.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERREUR :", str(exc).splitlines()[0])
        raise SystemExit(1)
