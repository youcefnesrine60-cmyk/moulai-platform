# MoulAI™ Platform — Agent-as-a-Service

MoulAI is a multi-tenant SaaS project for AI-assisted business workflows.
The current implementation focuses on restaurant operations, ordering,
Telegram conversations, and subscription billing. Other business domains
remain part of the longer-term roadmap.

Documentation reviewed: **2026-10-20**. The project is under active development;
this README describes the local implementation and recorded verification,
rather than a production release certification.

## Current status

K9 — Organizations / Tenant Mapping is **CLOSED — Foundation & Functional Tenant Reads Validated**.
See the [official closure](docs/keycloak-k9-closure.md) for accepted results and
deferred scope. K10 — Authorization MoulAI™ is now
**CLOSED — Authorization Validated** for the isolated HTTP integration:
41 K9 regressions, 26 real local PostgreSQL E1 cases and 92 targeted offline
HTTP/launcher checks passed. See the [K10 delivery](docs/keycloak-k10-validation.md).
The next roadmap step is **Frontend**; current business routes retain their
existing protections until the separate business integration step.

The local PostgreSQL campaign is accepted: **110 passed, zero failures and zero
skips**. The skipped-tests issue is resolved. Production `DATABASE_URL`, official
Neon development `TEST_DATABASE_URL` and isolated resettable local tests retain
their distinct roles and protections, documented in the
[development guide](docs/billing-development-verification.md#approved-environment-organization--2026-10-20).

Implemented capabilities include:

- Restaurant, branch, catalogue, cart, order, and order-payment workflows.
- Arabic, English, and French language handling, intent classification,
  entity extraction, conversation memory, and confirmed agent actions.
- SQLAlchemy repositories and business services with asynchronous database
  access and explicit transaction boundaries.
- Manual CCP and BaridiMob subscription payments, private receipt submission,
  administrative review, duplicate prevention, and audit history.
- Telegram checkout instructions and receipt upload.
- Keycloak OIDC access-token validation and database-backed administrative
  permission checks, with opt-in local K8 authentication and realm-role probes.
- PostgreSQL tenant identities, memberships, permissions and restaurant grants,
  with transaction-bound TenantContext resolution and validated K10 authorization
  in an isolated HTTP application.
- Guarded development-database selection, migration rehearsal, startup
  verification, and project-specific PowerShell launchers.

Operational work remains before these features can be used on the deployed
service. K9 foundations and K10 isolated authorization are validated; trusted
business identity bindings and integration into current business routes remain
deferred. OIDC diagnostics remain disabled. The latest
local changes have not all been deployed, and Render's development-database
connection still requires verification.

Catalogue, agent, and standalone branch REST operations require a verified
owner and an owner-scoped database session. The global Telegram user registry
requires an administrator with `admins.manage`. See the
[API authorization policy](docs/api-authorization.md) and
[catalogue isolation review](docs/catalog-options-isolation-finding.md).
The global restaurant administration aggregate requires `restaurants.manage`;
the synthetic metrics simulation route is no longer published.

Production database migrations, administrative identity changes, permission
grants, and live Telegram webhook changes remain deferred under the approved
[operational runbook](docs/billing-production-runbook.md).

## Architecture

HTTP routes validate transport and identity, business services enforce use
cases and transaction boundaries, and repositories execute database queries.
Payment settlement and subscription activation are separate responsibilities
coordinated within the business transaction.

| Layer | Current components |
| --- | --- |
| HTTP API | FastAPI, Pydantic V2, Uvicorn |
| Persistence | SQLAlchemy AsyncSession, asyncpg, PostgreSQL, Alembic |
| Workflow state | Redis-backed application services |
| Agent | Language detection, NLU, action execution, memory, prompts |
| Channels | Telegram handlers and an authenticated webhook |
| Identity | Keycloak OIDC, PyJWT, JWKS, database-backed RBAC |
| Tenant authority | PostgreSQL Identity, Organization, Membership, permissions and restaurant grants |
| Verification | unittest, Pytest, Ruff, PowerShell parser, Pester |

[requirements.txt](requirements.txt) defines the reviewed dependency baseline.
It pins FastAPI `0.136.3`, Starlette `1.8.0`, Pydantic `2.13.5`, and HTTPX
`0.28.1`, with exact ORM, driver, and quality-tool versions. Telegram calls use
HTTPX directly. These are direct and selected transitive pins, rather than a
complete cross-platform lock. See the
[dependency review](docs/dependency-review.md) for compatibility decisions,
isolated verification, and the subsequent HTTP test transport correction.

K9/K10 require no additional Python package or Keycloak SDK. The local PostgreSQL
launcher reuses SQLAlchemy, Alembic and asyncpg. PostgreSQL server binaries and
Docker are external prerequisites, installed independently of pip.

The local virtual environment uses **Python 3.14.4**. The
[Dockerfile](Dockerfile) still selects Python 3.11, and
[docker-compose.yml](docker-compose.yml) does not yet mirror the guarded
development configuration. Container compatibility and configuration need
alignment and verification before those files are used for deployment.

### API entry points

Application routes are registered in [app/main.py](app/main.py):

| Path | Purpose |
| --- | --- |
| `/api/v1` | Business APIs, including orders, payments, and manual billing |
| `POST /webhook` | Telegram updates, guarded by the configured secret token |
| `/` | Application metadata |
| `/health` | Process-level status and application metadata |
| `/docs`, `/redoc` | Interactive API documentation |
| `/openapi.json` | API schema |

The `/health` response does not probe PostgreSQL, Redis, Keycloak, or payment
services. Application startup validates the selected database schema and
registers callback routes. It does not create tables or apply migrations.

### Agent workflow boundaries

Order modification currently changes quantities of existing items on pending
orders. Complaint handling creates an open restaurant-scoped ticket, optionally
linked to the customer's order; a restaurant-side resolution workflow remains
to be implemented. Intent recognition alone does not imply a complete workflow.

## Manual billing and trusted identity

### Payment flow

Phase one supports **manual CCP and BaridiMob transfers in DZD**. Both methods
use the `manual_transfer` provider; a payment method and a provider are separate
concepts.

1. An authenticated owner selects an owned restaurant, plan, billing cycle,
   and enabled payment method. Server-side pricing creates or reuses a pending
   subscription invoice.
2. The owner receives the invoice amount, payment reference, and configured
   beneficiary details, then makes the transfer independently.
3. The owner submits a transaction reference and a PNG, JPEG, or PDF receipt.
   Evidence is private, limited to 2 MiB, and checked for duplicate submission.
4. An authorized reviewer checks the actual bank credit independently and
   records the reference, amount, currency, and review note.
5. Verified approval updates the payment, activates the subscription, and
   records the decision atomically. Rejection leaves the subscription inactive.

Uploading a receipt never activates a subscription. Database constraints and
idempotent commands prevent repeated settlement and reuse of submitted evidence.
Manual transfers have no bank API that independently confirms receipt of funds.

Telegram's private `/billing` flow provides checkout, payment instructions, and
receipt submission. Methods with missing beneficiary configuration are hidden.
Administrative approval is performed through the protected API; Telegram chat
identifiers do not authenticate a financial reviewer.

See [the payment strategy](docs/payment-integration-strategy.md) for endpoint
contracts, receipt handling, review rules, and provider extension boundaries.
Stripe, PayPal, CIB, and Edahabia integrations are not implemented or enabled.

### Keycloak and authorization

The implemented validator accepts **RS256** access tokens and verifies trusted
JWKS signatures, issuer, audience, expiry, subject, and the required Keycloak
access-token claims. Set the real `OIDC_ISSUER`, `OIDC_AUDIENCE`, and
`OIDC_JWKS_URL` only after the Realm and API client are configured.

Protected owner APIs map the verified subject to `owners.auth_subject`.
Administrative review requires an active, trusted admin binding and a current
database permission check for `payments.review`. Knowing an `admin_id` or
Telegram `chat_id` grants no access. Telegram and Keycloak identities remain
separate.

Administrative session lookup now uses static URLs and credential headers,
alongside the Keycloak access token. Clients must follow the
[updated session contract](docs/admin-session-api.md); retired credential URLs
have no compatibility aliases.

Missing identity-provider configuration fails closed. No default administrator
or invented identity binding is created. Provisioning or replacing a real
binding is a separate controlled operation.

### Tenant authorization - K10

K10 resolves a verified JWT through the exact `(iss, sub)` pair in `identities`.
The selected organization must be explicit. PostgreSQL verifies its active state,
an accepted active membership, stored role and permission, and restaurant grants.
The existing identity, context, authorization and access services own these checks
and transaction boundaries. A Keycloak `owner` or `admin` role grants no tenant
or platform permission by itself. Empty restaurant grants grant no restaurant
access, and `tenant.orders.fulfill` remains unavailable.

The three K10 HTTP routes exist only in a disposable FastAPI test application:
personal memberships, a selected organization's restaurants and one permitted
restaurant. Current business routes retain their existing authentication and
authorization. Real identity linking, route conversion and production activation
remain deferred. See the [K10 delivery](docs/keycloak-k10-validation.md) for the
159 targeted results, PostgreSQL evidence and limitations.

### Local OIDC diagnostics - K8

K8 reuses the verifier for three protected local probes under
`/api/v1/diagnostics/oidc/`: `me`, `owner`, and `admin`. They expose no business
operations and never create identity or tenant associations. Realm roles remain
distinct from business permissions.

Diagnostics are disabled by default. Explicit local opt-in additionally requires
`APP_ENV=development`, `DATABASE_TARGET=development`, `DEBUG=false`, and
`DB_ECHO=false`. The local HTTP exception applies only to diagnostics;
business authentication retains HTTPS and its stored subject/RBAC requirements.
See [K8 validation](docs/keycloak-k8-validation.md) for the confirmed local
configuration, tests, live-login boundary, and file inventory. K9 organization
and tenant foundations are now [closed for their validated scope](docs/keycloak-k9-closure.md);
integration into existing business routes remains deferred.

The [final K8 end-to-end check](docs/keycloak-k8-final-e2e.md) passed with the real
`owner-test` user: `me` 200, `owner` 200, `admin` 403, and anonymous access 401.
It used the actual local HTTP application without its database startup lifecycle.

## Local development

### Prerequisites and installation

Use the reviewed local Python 3.14 environment, access to the approved isolated
Neon development branch, and Redis for workflows that use shared state.
A valid local configuration is required before importing the application.

From PowerShell:

```powershell
git clone https://github.com/youcefnesrine60-cmyk/moulai-platform.git
cd moulai-platform
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check

if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

For the existing checkout, work from `D:\MoulAI` and use its virtual environment.
Do not replace an existing `.env`. The example lists maintained variable names;
supply real environment-specific values locally and keep credentials out of Git.

The requirements retain the dependency baseline reviewed on 2026-10-16, with
imports and K10 requirements checked again on 2026-10-20. They are not a freeze
of the existing `.venv`. A read-only comparison found these differences:

| Package | Declared baseline | Existing `.venv` |
| --- | --- | --- |
| FastAPI | `0.136.3` | `0.136.1` |
| Starlette | `1.8.0` | `1.0.0` |
| annotated-doc | `0.0.5` | `0.0.4` |
| bcrypt | `4.0.1` | `5.0.0` |
| certifi | `2026.7.22` | `2026.4.22` |
| Pydantic | `2.13.5` | `2.13.4` |
| pydantic-core | `2.46.5` | `2.46.4` |
| typing-inspection | `0.4.4` | `0.4.2` |
| python-dotenv | `1.2.4` | `1.2.2` |
| Redis | `7.4.1` | `7.4.0` |
| pytest-cov | `7.1.0` | `5.0.0` |

The existing environment's `pip check` succeeds, but it does not compare that
environment with this requirements file. In particular, bcrypt `5.0.0` is not
the reviewed Passlib pairing; keep the declared `4.0.1` compatibility pin.
The K10 campaign used the existing environment and did not exercise password
hashing or certify a fresh installation of every declared version. No package
was installed, upgraded or downgraded by this documentation/dependency review.

For local PostgreSQL tests, install PostgreSQL 18.3 binaries or provide a running
Docker engine. The native Windows backend was verified; Docker execution remains
unverified. These tools are not installed by `pip install -r requirements.txt`.

### Select the isolated development database

The approved target is **Neon development → neondb_test**. A database named
`neondb_test` on the production branch is not an acceptable substitute.

Configure through the central Settings system:

- Set `APP_ENV=development`, `DATABASE_TARGET=development`, `DEBUG=false`,
  and `DB_ECHO=false`.
- Supply `TEST_DATABASE_URL` using `postgresql+asyncpg`.
- Supply the verified `TEST_DATABASE_ENDPOINT_ID`,
  `TEST_DATABASE_BRANCH_ID`, and `TEST_DATABASE_PROJECT_ID`.
- Supply `PROTECTED_DATABASE_ENDPOINT_ID` and
  `PROTECTED_DATABASE_BRANCH_ID` for the excluded production target.
- Preserve the existing primary `DATABASE_URL`.

`APP_ENV=development` alone does not select the development database.
`DATABASE_TARGET=primary` selects the primary connection. The development
guard checks the database name, endpoint, live branch and project identity,
protected-target separation, and TLS before permitted operations proceed.
Missing or inconsistent identity data stops execution.

Keep the three environments distinct:

| Configuration | Role |
| --- | --- |
| `DATABASE_URL` | Production; changes require explicit approval. |
| `TEST_DATABASE_URL` | Official Neon development and controlled validation; preserve target attestation and data. |
| `LOCAL_POSTGRES_TEST_*` | Ephemeral local automated tests; supplied by the launcher with an exact loopback allowlist and no Neon fallback. |

Do not persist a disposable local test URL in either Neon setting. Ordinary
development startup and the local test launcher have separate responsibilities.

The dedicated `alembic_test` history and the production `alembic` history
have different revision identifiers. Do not compare their identifiers as
chronological values or substitute one migration history for the other.

Follow the [development verification guide](docs/billing-development-verification.md)
for schema preparation and the guarded rehearsal. The launchers do not migrate
databases. Production schema and data changes require independent approval.

### Configure channels and payment instructions

Use [the central configuration example](.env.example) for:

- Redis, AI provider, application-secret, and Telegram bot settings.
- `TELEGRAM_WEBHOOK_SECRET_TOKEN`, `WEBHOOK_URL`, and `WEBHOOK_PATH`.
- `MANUAL_CCP_ENABLED` and `MANUAL_BARIDIMOB_ENABLED`.
- `MANUAL_TRANSFER_BENEFICIARY`, `MANUAL_CCP_ACCOUNT`, `MANUAL_CCP_KEY`,
  and `MANUAL_BARIDIMOB_RIP`.
- The real Keycloak OIDC values when available.

CCP and BaridiMob instructions must identify the same configured receiving
account when both refer to that postal account. Account details belong in the
environment, never in source code. They are intentionally displayed to paying
customers and should not appear in unnecessary logs.

The deployed Telegram endpoint must validate the same secret used when
registering its webhook. Setting local variables does not configure Render or
register a live webhook; follow the runbook for those deferred operations.

### Start and stop the local server

After configuration and schema verification:

```powershell
Get-Location
$env:DEBUG = 'false'
.\start_or_keep_moulai.ps1
```

The launcher keeps an existing server owned by this checkout or starts one in
the foreground. `run_moulai.ps1` starts a foreground server directly.

Preview and perform a stop with:

```powershell
.\stop_moulai.ps1 -WhatIf
.\stop_moulai.ps1
```

The launchers use the project's virtualenv, preserve exit codes, and check
process ownership and PID creation times. See
[PowerShell standards](docs/powershell-standards.md) for execution-policy
requirements, process handling, and isolated verification commands.

## Verification and recorded evidence

The following are separate recorded checks, not a fresh full-suite result:

| Check | Recorded scope |
| --- | --- |
| Development regression checks | 113 local cases: 76 unittest and 37 Pytest |
| Billing CLI and JSON output | 24 offline unittest cases |
| PowerShell runtime | 24 isolated Pester cases with process mocks |
| Migration rehearsal | Fresh, adoption, and drift scenarios with rollback |
| Application startup | Local ASGI lifespan and read-only development access |

The billing CLI group reuses 17 existing cases and adds seven output cases.
It overlaps the earlier regression group; these figures must not be added into
a single passing-test total. Earlier complete-suite runs in the architecture
audit describe earlier source states.

The migration rehearsal exercised the real production billing migration
`a91e7c2b4d10` → `c413b7918a20` against a staged predecessor schema inside
rollback-only development transactions and verified preserved state afterward.
It did not replay the entire production migration history.
The startup check exercised the real application lifespan and local HTTP paths.
Neither proves the latest code is deployed on Render or that live Keycloak and
Telegram integrations are configured.

### API regression coverage

The current K10 targeted verification on 2026-10-20 passed **159 distinct tests**:
41 existing K9 functional/HTTP cases, 92 offline HTTP/launcher checks and 26 actual
local PostgreSQL E1 cases. All passed without failures, skips or warnings. Real
RS256 signatures and PostgreSQL storage were exercised together, with in-memory
test keys and simulated JWKS. HTTP uses a disposable ASGI application.
This campaign does not provide a new global coverage percentage. The original
110-test PostgreSQL campaign remains accepted and was not repeated for K10.

The historical K8 offline verification on 2026-10-18 passed **2,319 collected tests**
and **128 separate subtests**, without warnings. Coverage is **57.77% across all
385 app files** and **81.64% across all 56 API files**, without source exclusions.
Actual ASGI diagnostic checks also confirm 200/401/403 using simulated JWKS.
See [K8 validation](docs/keycloak-k8-validation.md) for the live-login boundary.

The following PostgreSQL and authorization results record the preceding source
snapshot and remain separate from the K8 offline execution.

The 2026-10-17 integration follow-up passed **2,248 collected offline tests** and
**128 separate unittest subtests**, with warnings treated as errors and **zero
Python test warnings**. Full application line coverage is **57.61%**;
API line coverage is **81.34%**. All 382 application Python files and all
55 API files remain in the denominator, including unexecuted modules.

The two PostgreSQL modules affected by the reported category and branch
failures also pass **10 tests**, after live development-branch identity and
schema checks. These include anonymous and foreign-owner category regressions.
This targeted integration execution does not represent the entire connected
PostgreSQL suite.

The review fixes the Starlette TestClient warning and adds verified owner
isolation and administrative permission boundaries. Real SQL/HTTP tests also
cover foreign-parent rejection, scoped counts and bulk operations, valid
writes, persisted agent state, and branch usage rollback. Session credentials
now use headers on static URLs. The global restaurant administration aggregate
requires `restaurants.manage`.

The historical offline checks above used the 43 exact declared requirements in an isolated Windows
Python 3.14.4 environment. The PostgreSQL selection used the existing `.venv`;
its dependency differences are recorded separately. No live migration, real identity binding,
production grant, deployment, or Telegram change occurred. PostgreSQL locking
and real Keycloak/proxy configuration retain separate verification boundaries.

See [API testing and coverage](docs/api-testing.md) for commands, accepted
reports, corrected defects, historical measurements, and operational limits.

### Run isolated checks

After preparing the local settings, these examples avoid the shared PostgreSQL
fixtures:

```powershell
$env:DEBUG = 'false'
$modules = @(
    'tests.test_billing_operations',
    'tests.test_billing_report_output'
)
.\.venv\Scripts\python.exe -W error -m unittest $modules -v
```

For the isolated transaction, schema, and manual-payment contract checks:

```powershell
$testFiles = @(
    'tests/test_payment_transaction.py',
    'tests/test_database_startup_schema.py',
    'tests/test_manual_payment_contracts.py'
)
.\.venv\Scripts\python.exe -m pytest $testFiles `
    --noconftest --no-cov -p no:cacheprovider -q
```

The default `python -m pytest` run uses the offline socket guard. Tests requiring
the shared PostgreSQL fixtures are reported as skipped; local unit/HTTP tests
do not open a Neon connection or require its schema to be at Alembic head.
Live fixtures require the explicit `--run-database-tests` option and separate
authorization for the isolated test dataset. They retain identity/revision
checks before truncating test tables and resetting identity sequences.
Pytest neither migrates a mismatched database nor grants migration approval.

Execute the PostgreSQL selection on a fresh local instance with:

```powershell
.\.venv\Scripts\python.exe scripts/run_local_postgres_tests.py --backend native
```

The recorded local result is **110 passed, zero skips**. The launcher also supports
a running Docker engine with `--backend docker`; it never uses the Neon test URL
as a fallback. See [local PostgreSQL tests](docs/local-postgres-tests.md).

For K10 authorization against a fresh local E1 schema:

```powershell
.\.venv\Scripts\python.exe scripts/run_local_postgres_tests.py --backend native --profile k10
```

The K10 profile applies the existing test history through `e1b92b200001`, verifies
56 public tables, nine tenant tables, five nullable expansions, 28 triggers,
three roles and 49 permissions, then runs the 26 authorization tests. It creates
only explicit synthetic associations, preserves E1's lifecycle/retention guards
and stops its owned server afterward. The default `legacy` profile remains at
`dce91870b4a2` for the 110 resettable tests. The two profiles use separate fresh
instances; the K10 tests are intentionally opt-in and cannot run through the
remote database option. Neither command migrates Neon.

The dedicated rehearsal and startup verifier have their own guarded contracts,
documented in the development guide.

## Reports and generated artifacts

Capture console output under `artifacts/test-logs/`. Application logging uses
standard output; saved test captures are historical diagnostic evidence.

For example, append this redirection to an authorized test command:

```powershell
New-Item -ItemType Directory -Path artifacts/test-logs -Force | Out-Null
.\.venv\Scripts\python.exe -W error -m unittest $modules -v `
    *> artifacts/test-logs/billing-json-report-tests.log
```

| Local path | Purpose |
| --- | --- |
| `artifacts/test-logs/INDEX.md` | Test captures and diagnostic snapshots |
| `artifacts/billing-reports/INDEX.md` | Valid standalone billing JSON reports |
| `artifacts/billing-production-review/` | Source exports and local evidence |
| `artifacts/powershell-review/` | PowerShell sources and verification results |
| `artifacts/dependency-review/` | Dependency metadata, resolved versions, and results |
| `artifacts/keycloak-k10/` | Targeted K10 results, source hashes and complete copyable Python sources |
| `artifacts/postgres-local-tests/` | Separate local compatibility/E1 runs, PostgreSQL logs and catalogs |
| `artifacts/project-cleanup/` | Cleanup records and archived retired entry points |

These are local generated files, intentionally excluded from Git and Docker.
Captured `.log`, `.err`, and `.out` files are also ignored. An ignore rule
prevents new additions; it does not hide files in the editor or remove previously
tracked files. Archived tracked captures appear as deletions to include in the
next commit, and earlier versions remain in Git history.

The local [artifact index](artifacts/README.md) groups the retained evidence.
[Project maintenance](docs/project-maintenance.md) records the output and cache
policy, archived legacy diagnostics, and supported replacements. The main
`.venv`, separate root `venv`, and `.env` are preserved. The disposable
dependency-review environment and wheel downloads were removed after recording
their inventory; their reports and resolved versions remain available.

The recovered billing reports preserve historical observations extracted from
mixed console output. They do not establish a new production state.
For future authorized checks, only `preflight` and `constraint-diagnostics`
accept `--output FILENAME.json`. This saves one UTF-8 JSON document under
`artifacts/billing-reports/`; pass a filename, not a directory or path.
Console output can include logger records and should not be redirected to a
`.json` report.

## Deployment and remaining work

The approved path is GitHub → the existing Render service `moulai-api`,
on branch `main`. The reported public URL is
[the MoulAI Render service](https://moulai-api.onrender.com).

The existing service was reported running, but that does not verify the latest
local revision. Before an authorized push that could trigger Auto-Deploy,
verify the service, branch, deployed SHA, and development database target.
Do not create a replacement service or assume local `.env` changes affect
Render.

Build command:

```text
pip install -r requirements.txt
```

Start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No automatic migration belongs in build, startup, or a pre-deploy hook under
the current authorization. Production `neondb`, administrative bindings,
permission changes, and Telegram registration remain separate controlled work.
The existing recovery verification is historical; confirm an available recovery
point again before any future production migration window.

### Roadmap

Approved delivery order:

1. **K10 — Authorization MoulAI™** — closed for the validated scope.
2. **Frontend**.
3. **Business integration**.
4. **K11 — Production Security**.
5. **Pilot**.

Supporting and longer-term work:

- Complete real Keycloak setup, trusted identity provisioning, and deployment
  verification against the approved development target.
- Complete authentication and tenant enforcement for catalogue options.
- Finish restaurant-side complaint handling and broaden agent workflows.
- Integrate CIB and Edahabia only with official contracts and documentation.
- Add international providers, multiple currencies, recurring subscriptions,
  refunds, reconciliation, and invoicing in later phases.
- Extend management interfaces, analytics, other communication channels,
  and additional business domains.

See the [payment integration strategy](docs/payment-integration-strategy.md)
for phase boundaries.

## Project layout

```text
moulai-platform/
├── app/
│   ├── agent/           # Language, NLU, executor, memory, prompts
│   ├── api/             # Authentication, versioned APIs, Telegram webhook
│   ├── core/            # Settings, database lifecycle, security, guards
│   ├── handlers/        # Telegram messages, callbacks, manual billing
│   ├── models/          # SQLAlchemy models
│   ├── repositories/    # Database queries
│   ├── schemas/         # Pydantic contracts
│   ├── services/        # Business and Telegram services
│   └── views/           # Telegram interface rendering
├── alembic/             # Production migration history
├── alembic_test/        # Dedicated test migration history
├── alembic_local_test/  # Pinned local-only migration environment
├── migration_support/  # Frozen E1 schema, SQL and migration operations
├── docs/                # Architecture, findings, strategy, runbooks
├── scripts/             # Guarded operational tools and shared PS module
├── tests/               # Python suites and isolated PowerShell tests
├── test_support/        # Local admission and disposable tenant HTTP app
├── artifacts/           # Local generated output, ignored by Git
├── .env.example         # Variable names and safe configuration template
├── requirements.txt     # Dependency declarations
├── compose.postgres-tests.yml # Disposable local PostgreSQL backend
├── run_moulai.ps1
├── start_or_keep_moulai.ps1
├── stop_moulai.ps1
└── README.md
```

## Engineering references

- [Documentation index and language conventions](docs/README.md)
- [Architecture and refactoring audit](docs/order-architecture-audit.md)
- [Manual payment strategy and API contracts](docs/payment-integration-strategy.md)
- [Development verification](docs/billing-development-verification.md)
- [K9 closure](docs/keycloak-k9-closure.md)
- [K10 authorization delivery](docs/keycloak-k10-validation.md)
- [Local PostgreSQL profiles](docs/local-postgres-tests.md)
- [Reviewed dependency baseline](docs/dependency-review.md)
- [Deployment and recovery runbook](docs/billing-production-runbook.md)
- [Catalogue isolation finding](docs/catalog-options-isolation-finding.md)
- [PowerShell standards](docs/powershell-standards.md)
- [Repository maintenance and artifact policy](docs/project-maintenance.md)

Maintained changes use the agreed source headers, typed interfaces, explicit
keyword arguments in repository and service contracts, reusable base SELECT
queries, and transaction ownership. Ruff checks and focused regression tests
support reviews. These practices do not imply that every legacy module has
already been audited.

## Author

Youcef Nesrine

- [GitHub profile](https://github.com/youcefnesrine60-cmyk)
- [LinkedIn profile](https://linkedin.com/in/nesrine-youcef-data-engineer)

## License

Copyright © 2026 Youcef Nesrine. All rights reserved.

Licensed under Creative Commons Attribution-NonCommercial-NoDerivatives 4.0
International. See [LICENSE](LICENSE) for the complete terms.
