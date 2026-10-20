# K8 - FastAPI and Keycloak OIDC integration

Date: 2026-10-18. Scope: local development only. K9 organization and tenant
mapping is a separate stage.

The subsequent [final real-user end-to-end validation](keycloak-k8-final-e2e.md)
passed all four expected HTTP checks. The automated-review results below retain
their original scope; the earlier live-token replay limitation is now closed
for the local diagnostic flow.

## Architecture and impact review

The review examined security modules, central Settings, FastAPI dependencies,
the existing JWT validator, owner/admin identity mapping, and router registration.
The three OIDC fields and RS256/JWKS verification already existed. K8 reuses
them rather than introducing another authentication mechanism.

The shared verifier now returns verified claims internally. Existing business
dependencies still resolve a verified subject through their established
database associations and current administrative RBAC. Their dependency graph
and HTTPS requirement remain intact. Diagnostics construct an immutable
`OIDCPrincipal`, without acquiring a database session.

`require_realm_roles(roles=frozenset({...}))` requires every named realm role,
case-sensitively. Only `realm_access.roles` supplies roles. Missing roles mean
no role membership; malformed structures are rejected. Client roles, top-level
roles, owner/admin IDs and Telegram identifiers do not replace realm roles or
business permissions. Neither an `owner` nor an `admin` role creates a local
identity, grants enterprise ownership, or grants `payments.review`.

## Signature and claim policy

- RS256 is the only accepted algorithm. The configured JWKS supplies the key
  selected by `kid`; a token's `jku` header cannot choose another provider.
- `iss`, `aud`, `exp` and `sub` are mandatory and verified. Issuer matching is
  exact; the API audience is `moulai-api`, not the login client.
- Existing access-token restrictions remain: required integer `iat` and `exp`,
  valid optional `nbf`, and payload `typ=Bearer`. ID/refresh, expired, premature,
  unsigned and incorrectly signed tokens fail closed.
- JWKS retrieval uses the existing worker thread, five-second timeout,
  five-minute JWKS cache and no permanent per-key cache. An unknown key ID
  triggers a refresh. Unavailable or malformed provider keys fail closed.
- Responses and application log messages do not expose JWTs, secrets or raw
  verified claims. Successful diagnostics prevent response caching.

The implementation uses the declared PyJWT 2.13.0 without upgrading dependencies.
Installed library behavior was checked alongside the
[PyJWT documentation](https://pyjwt.readthedocs.io/en/stable/usage.html) and
[Keycloak OIDC documentation](https://www.keycloak.org/securing-apps/oidc-layers).

## Local configuration

Central Settings retain unset OIDC defaults. `.env.example` documents the
confirmed nonsecret local values, with both diagnostic switches disabled:

```dotenv
OIDC_ISSUER=http://localhost:8080/realms/moulai
OIDC_AUDIENCE=moulai-api
OIDC_JWKS_URL=http://localhost:8080/realms/moulai/protocol/openid-connect/certs
OIDC_DIAGNOSTICS_ENABLED=false
OIDC_ALLOW_LOCAL_HTTP=false
```

The existing local `.env` was checked for `APP_ENV=development`,
`DATABASE_TARGET=development`, `DEBUG=false` and `DB_ECHO=false`. Only the three
supplied OIDC values and the two switches were updated there; both switches are
enabled locally. `.env` remains Git-ignored. Database URLs, database isolation
settings, real identity associations, Render and Telegram settings were preserved.

Diagnostic routes are mounted only when the complete safe local profile and
explicit opt-in are present at application import. The profile is checked again
per request; an unsafe profile returns 404 even on an already-mounted route.
Restart the local application after changing these settings.

The HTTP exception applies only to diagnostics and literal loopback hosts
`localhost`, `127.0.0.1` or `::1`. Issuer and JWKS must share scheme, host, port
and realm endpoint path. Userinfo, queries, fragments and arbitrary HTTP hosts
are rejected. Business owner/admin verification requires HTTPS regardless of
the switch, so this local HTTP realm does not activate business workflows.

## Protected diagnostic contract

| Endpoint | Requirement | Success |
| --- | --- | --- |
| `GET /api/v1/diagnostics/oidc/me` | Valid API access token | 200 |
| `GET /api/v1/diagnostics/oidc/owner` | Valid token and realm role `owner` | 200 |
| `GET /api/v1/diagnostics/oidc/admin` | Valid token and realm role `admin` | 200 |

Missing/invalid credentials return 401 with a Bearer challenge. Insufficient
roles return 403. Invalid provider configuration or unavailable keys return 503.
Successful responses contain only `authenticated`, `subject`, `issuer` and
`realm_roles`, with `Cache-Control: no-store` and `Pragma: no-cache`.

## Verification scope and live-login boundary

Recorded execution: **142 targeted authentication tests passed**, including
K8 and existing owner/admin authentication contracts. The complete offline
selection passed **2,319 collected tests** and **128 separate subtests**, with
zero Python warnings, failures or skips and warnings treated as errors.

| Coverage scope | Covered statements | All statements | Line coverage |
| --- | ---: | ---: | ---: |
| Application: all 385 Python files | 12,455 | 21,559 | 57.77% |
| API: all 56 Python files | 3,699 | 4,531 | 81.64% |

There are no source exclusions. Both unrounded percentages exceed 50%.
Application sources remained unchanged during measurement, shared PostgreSQL
fixtures were not loaded, and the network guard recorded zero denied events.

| Actual ASGI check with simulated JWKS | Expected | Observed |
| --- | ---: | ---: |
| Anonymous request | 401 | 401 |
| Valid owner token on owner probe | 200 | 200 |
| Owner token on admin probe | 403 | 403 |
| Invalid RSA signature | 401 | 401 |

Unit tests use ephemeral RSA keys and simulated JWKS HTTP responses. They keep
PyJWT key selection, signature verification, caching/rotation, FastAPI dependency
execution and role checks real. Isolated child processes verify actual
`app.main` route registration and Bearer metadata, without database access or
application lifespan startup. A separate actual-ASGI status check verifies
200/401/403 with simulated keys.

The local Keycloak discovery document and public JWKS were independently read
successfully; an RS256 signing key is published. No access token was requested
by that read-only check. The user's successful K7 PKCE login remains the prior
real-login evidence. During the initial automated review, a fresh `owner-test`
token had not yet been replayed against K8. The separate
[final end-to-end report](keycloak-k8-final-e2e.md) now records successful real
token verification against the local HTTP diagnostic endpoints.

Never place access tokens in URLs, command arguments, source files, reports or
logs. A live check must keep them in memory and an Authorization header.
Machine-readable evidence is indexed in
[K8 evidence](../artifacts/keycloak-k8/INDEX.md). Historical API reports retain
their original source snapshots and execution scopes.

## Reproduce the automated checks

Use an environment matching `requirements.txt`. Keycloak need not be running:

```powershell
$env:DEBUG = 'false'
$env:DB_ECHO = 'false'
$env:REDIS_URL = ''
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.\.venv\Scripts\python.exe -m pytest tests/test_oidc_k8.py `
    tests/test_keycloak_admin_auth.py tests/test_orders_api_auth.py `
    --noconftest -o addopts= -p pytest_asyncio.plugin `
    -p no:cacheprovider -W error -q
```

For full offline coverage, with the mandatory network guard and live database
fixtures excluded:

```powershell
.\.venv\Scripts\python.exe scripts/run_offline_api_tests.py --name k8-review
```

The existing `.venv` has recorded dependency differences and was preserved.
Accepted full coverage verification uses an isolated environment matching all
43 declared versions. Temporary runtime and wheel copies are removed afterward.

## Modified source inventory

| File | K8 change |
| --- | --- |
| `app/core/security/oidc.py` | Immutable principal and strict realm-role extraction. |
| `app/api/auth.py` | Shared verified claims, diagnostic dependencies, gated local HTTP, safe malformed-JWKS handling. |
| `app/core/config.py` | Two opt-in diagnostic settings; existing OIDC fields retained. |
| `app/schemas/oidc.py` | Minimal response contract. |
| `app/api/v1/oidc_diagnostics.py` | Three protected probes without database access. |
| `app/main.py` | Conditional local router registration. |
| `tests/test_oidc_k8.py` | Cryptographic, HTTP, role, configuration, cache and business-boundary tests. |
| `.env.example` | Supplied local values and switches disabled by default. |

The ignored local `.env` contains the five authorized OIDC updates.
Documentation and evidence are listed in the K8 manifest. The user's existing
K7 script and unrelated in-progress work were preserved.

## Operational boundary and K9

No production database was accessed or modified. No PostgreSQL write test,
Alembic migration, real identity creation or business association was performed.
No GitHub push, deployment, Render edit or Telegram webhook change occurred.

K9 must separately define trusted organization membership and explicit tenant
mapping, review existing subject associations and permissions, and verify
cross-tenant denials before changing business dependencies. An `owner` role
alone never supplies organization membership in K8.
