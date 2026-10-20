# K10 — Authorization MoulAI: final delivery

Date: **2026-10-20**. Status: **CLOSED — Authorization Validated**, for the
requested isolated HTTP integration and local PostgreSQL scope.

## Functional result and reused authority

The K8 verifier validates RS256/JWKS, issuer, audience, expiration and subject.
`IdentityService` resolves the exact `(iss, sub)` pair in PostgreSQL; unknown,
suspended or retired identities are refused. Retirement is the existing
terminal identity status; membership revocation is separately enforced.
Neither JWT realm roles nor an existing restaurant owner ID grants tenant access.
No identity is provisioned automatically.

The existing `TenantContextResolver`, `TenantAuthorizationService`,
`TenantAccessService`, `restaurant_scope` and tenant repository remain the sole
authority for selected-company access. They enforce active organization,
accepted active membership, stored role/permission, current revisions and
company-qualified restaurant grants inside an owned transaction. An empty grant
set exposes no restaurants. Platform RBAC and tenant permissions remain separate;
no role receives `tenant.orders.fulfill`.

`app/api/tenant_dependencies.py` adds authenticated personal membership discovery
and reuses the existing denial mapping. Personal discovery exposes only the
caller's association metadata, including lifecycle history; it neither selects
a company nor authorizes business access through an inactive association.

Only `test_support/tenant_http_app.py` registers these routes, in a disposable
FastAPI application with request-local sessions:

| Route | Backend result |
| --- | --- |
| `GET /test/memberships` | Exact local identity's bounded association metadata. |
| `GET /test/organizations/{organization_id}/restaurants` | Explicit selected company's authorized restaurants. |
| `GET /test/organizations/{organization_id}/restaurants/{restaurant_id}` | One permitted resource; absent, foreign and ungranted resources return the same 404. |

HTTP requests use HTTPX's in-process ASGI transport against the disposable app,
with genuine asyncpg/PostgreSQL storage in the E1 campaign. Observed outcomes
include 200, 401, 403, 404 and validation 422. The reused
K9 HTTP tests also verify transaction/session conflict 409. JWTs, passwords and
authorization codes are absent from outputs and reports.

## Actual verification

| Selection | Passed | Failures / skips / warnings | Evidence |
| --- | --- | --- | --- |
| Existing K9 functional and HTTP tests | 41 | 0 / 0 / 0 | [JUnit](../artifacts/keycloak-k10/k9-regressions.xml) |
| New offline HTTP plus local/offline-runner regressions | 82 | 0 / 0 / 0 | [JUnit](../artifacts/keycloak-k10/offline-targeted.xml) |
| Added exact-profile/revision and collection boundaries | 10 | 0 / 0 / 0 | [JUnit](../artifacts/keycloak-k10/profile-boundaries.xml) |
| Actual local PostgreSQL E1 authorization | 26 | 0 / 0 / 0 | [Validation](../artifacts/postgres-local-tests/6c1c01bbb3d74547a4233a88d1afb36b/validation.json) |

**159 distinct targeted tests passed.** Of the 92 supporting offline cases,
seven exercise the new HTTP composition and 85 cover runner/safety contracts.
No global coverage percentage or whole-suite result is inferred. The accepted
110-test legacy campaign and remote G2 scenarios were not repeated.

The local command was:

```powershell
.venv\Scripts\python.exe scripts/run_local_postgres_tests.py --backend native --profile k10
```

The fresh PostgreSQL **18.3** instance applied the existing independent test
history through E1 `e1b92b200001`, with no stamp or new revision. Observed:
**56 public tables**, nine new tenant tables, five nullable expansions,
65 new-table constraints, 28 triggers, nine functions, three roles and exactly
49 permission rows. Six legacy foreign keys retain E1's NOT VALID state.
The server was stopped successfully; no forbidden network attempt was detected.
Docker execution was not exercised.

Real PostgreSQL cases cover owner A/B separation despite a shared legacy owner;
manager and employee explicit grants; empty grants; foreign-company selection;
unknown and other-issuer identities; missing/pending membership; stored permission
denial despite owner/admin JWT claims; invalid JWTs; identity suspension/retirement;
membership suspension/revocation; company suspension and grant removal.
Pagination, explicit company selection and non-disclosing resource responses
are verified over HTTP.

Transaction cases verify rollback, closed read leases and refusal to rebind a
session to another company. An independent revocation transaction locks the
identity in the established order: PostgreSQL reports it waiting on the read's
shared lock, the read completes, revocation commits, and the next HTTP request
is refused. This is an observed bounded-read concurrency result, not a claim
about unreleased business-write workflows or every possible database writer.

Two initial local fixture runs failed: first, one parameter was reused for
integer/bigint columns; then a status parameter was reused in a text CASE and
varchar column. Separate correctly typed parameters fixed both. Failed artifacts
remain under runs `6badcb41c1d24bd088c8e7b451b91756` and
`19cdd449d6394223b99864ad6835a8cc`; no failure was hidden by changing E1 or its
triggers. The final run passed all 26 cases in **13.03 seconds**.

## Exact delivery files

Added:

- `test_support/tenant_http_app.py`.
- `tests/test_k10_http.py` and `tests/test_k10_postgres.py`.
- This report.

Updated:

- `app/api/tenant_dependencies.py`: personal discovery and shared denial mapping.
- `test_support/local_postgres.py`, `alembic_local_test/env.py` and
  `scripts/run_local_postgres_tests.py`: explicit local-only legacy/K10 profiles,
  exact target revision and E1 catalog verification using the existing verifier.
- `tests/conftest.py` and `scripts/run_offline_api_tests.py`: separate E1 test
  admission; neither remote mode nor the legacy profile can run these fixtures.
- `tests/test_local_postgres_safety.py` and
  `tests/test_pytest_database_boundary.py`: profile, revision and skip boundaries.
- Root `README.md`, `docs/README.md`, `docs/api-testing.md`,
  `docs/local-postgres-tests.md` and `docs/billing-development-verification.md`:
  delivery status, commands, environment separation and roadmap.

[Complete copyable Python sources](../artifacts/keycloak-k10/complete-python-sources.md)
and the [source manifest](../artifacts/keycloak-k10/source-manifest.json) are local
ignored artifacts. [Aggregated results](../artifacts/keycloak-k10/validation.json)
confirm 159 distinct test IDs. Black and Ruff pass for the eleven delivery Python
files; scoped AST review checks headers, docstrings, return annotations and
multi-element import formatting. Untouched legacy conftest functions were not
rewritten for this review. Existing K9/G2/110-test evidence is retained.

## Scope limits and next step

Real storage and real JWT signature verification were exercised together;
JWKS was mocked with in-memory generated keys. No live Keycloak login was
repeated, and no real identity/profile association was created. Synthetic
bindings were explicit fixtures. E1 retention and governance fences stayed active.

Existing business routes, authentication/payment protections, remote migration
environments, `.env`, Neon and production were not changed. No remote connection,
branch operation, deployment, Render/Keycloak/Telegram action or push occurred.
Both OIDC diagnostic flags remain false. Existing branch expirations/review
decisions are unchanged; this delivery performs no resource lifecycle operation.

K10 is closed for its approved scope. The roadmap remains:
**K10 Authorization → Frontend → Business integration → K11 Production Security
→ Pilot**. Frontend is next. Business-route activation, controlled real identity
linking, production migration, production security and deployment remain deferred.
