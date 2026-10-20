# K8 final end-to-end validation

**Result: PASS.** Observed on 2026-10-18 at 10:08:56
(Africa/Lagos, UTC+1), with the real Keycloak user `owner-test`.

| Local HTTP request | Expected | Observed |
| --- | ---: | ---: |
| `/api/v1/diagnostics/oidc/me`, real access token | 200 | 200 |
| `/api/v1/diagnostics/oidc/owner`, same token | 200 | 200 |
| `/api/v1/diagnostics/oidc/admin`, same token | 403 | 403 |
| `/api/v1/diagnostics/oidc/me`, no token | 401 | 401 |

The run reused K7's PKCE helpers, client `moulai-local-test`, and registered
callback. Authorization Code + PKCE S256 obtained a real access token from
realm `moulai`. The existing OIDC validator verified RS256, issuer, API audience
`moulai-api`, expiry and subject. The username, owner role and identity returned
by both successful probes were checked in memory. No signing keys or JWT
validation were mocked.

Both local switches were enabled, with `APP_ENV=development`,
`DATABASE_TARGET=development`, `DEBUG=false` and `DB_ECHO=false`.
The API token was sent only in the Authorization header. The callback suppressed
request logging and redirected to a clean URL. Evidence contains no access
token, authorization code, password or actual subject identifier.

The original API became unavailable during preflight. The runner temporarily
served the actual `app.main` application on `127.0.0.1:8000`, with lifespan and
access logging disabled and DB dependencies refused. Both temporary listeners
(8000 and 8765) were confirmed closed afterward. K7 and application security
source hashes remained unchanged.

This validates the real diagnostic HTTP/authentication path. It does not
validate database startup, business tenant mapping, a deployed proxy or Render.
No migration, production operation, identity association, GitHub publication,
Render edit or Telegram webhook change occurred. K9 remains separate.

The prior **2,458 passing tests and 64% global coverage** were reported by the
user and were not rerun or remeasured. Only the new validation runner received
syntax, Black and Ruff checks.

[Observed results](../artifacts/keycloak-k8/final-e2e-results.json) ·
[Source hashes](../artifacts/keycloak-k8/final-e2e-source-manifest.json) ·
[Complete runner source](../artifacts/keycloak-k8/complete-e2e-python-source.md)
