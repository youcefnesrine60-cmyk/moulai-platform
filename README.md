# MoulAI™ Platform — Agent-as-a-Service

MoulAI is a multi-tenant SaaS project for AI-assisted business workflows.
The current implementation focuses on restaurant operations, ordering,
Telegram conversations, and subscription billing. Other business domains
remain part of the longer-term roadmap.

Documentation reviewed: **2026-10-16**. The project is under active development;
this README describes the local implementation and recorded verification,
rather than a production release certification.

## Current status

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
  permission checks, ready for the real identity-provider configuration.
- Guarded development-database selection, migration rehearsal, startup
  verification, and project-specific PowerShell launchers.

Operational work remains before these features can be used on the deployed
service. Keycloak values and trusted identity bindings are pending. The latest
local changes have not all been deployed, and Render's development-database
connection still requires verification.

Authentication and tenant isolation for catalogue option-group and
product-option administration remain incomplete. See the
[catalogue isolation finding](docs/catalog-options-isolation-finding.md).
The verified billing boundaries do not establish security for every API.

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
| Verification | unittest, Pytest, Ruff, PowerShell parser, Pester |

[requirements.txt](requirements.txt) defines the reviewed dependency baseline.
It pins FastAPI `0.136.3`, Starlette `1.8.0`, Pydantic `2.13.5`, and HTTPX
`0.28.1`, with exact ORM, driver, and quality-tool versions. Telegram calls use
HTTPX directly. These are direct and selected transitive pins, rather than a
complete cross-platform lock. See the
[dependency review](docs/dependency-review.md) for compatibility decisions,
isolated verification, and the remaining upstream test-client warning.

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

Missing identity-provider configuration fails closed. No default administrator
or invented identity binding is created. Provisioning or replacing a real
binding is a separate controlled operation.

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

if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

For the existing checkout, work from `D:\MoulAI` and use its virtual environment.
Do not replace an existing `.env`. The example lists maintained variable names;
supply real environment-specific values locally and keep credentials out of Git.

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

The default `tests/conftest.py` performs live database identity and revision
checks. Its database fixtures truncate test tables and reset identity sequences.
Run integration tests only with an approved test dataset on the isolated branch;
do not use a general full-suite command as a harmless startup check.
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
├── docs/                # Architecture, findings, strategy, runbooks
├── scripts/             # Guarded operational tools and shared PS module
├── tests/               # Python suites and isolated PowerShell tests
├── artifacts/           # Local generated output, ignored by Git
├── .env.example         # Variable names and safe configuration template
├── requirements.txt     # Dependency declarations
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
