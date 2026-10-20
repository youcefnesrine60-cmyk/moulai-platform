# Standalone Render Health-Only correction

Date: **2026-10-20**. Branch: **fix/render-health-only**. Publication,
Render configuration and deployment are **not authorized by this document**.

## Exact base and scope

This branch starts directly at **7a667633f593afbabc9949cef12f603535eba94e**, the
reported deployed main commit. It contains one local correction commit. Its exact
SHA is obtained with `git rev-parse HEAD` and recorded in the delivery evidence.
No merge from the later feature branch is involved. Main and that branch's
uncommitted work remain unchanged.

Only the opt-in observation mode and its necessary tests/tooling are carried
forward. Existing API routers, business services, repositories, models, security
policies, financial code, migrations and requirements are unchanged from the
base. No tenant foundation/E1, membership services or K8 diagnostic routes are
introduced. No data migration is needed by this correction.

| File | Responsibility |
| --- | --- |
| app/core/health_only.py | Profile admission, immutable identity policy, transaction guard and outer HTTP gate. |
| app/core/config.py | Default-off flag and early safety validation; two false OIDC observation flags. |
| app/core/database.py | Capture the validated target and install READ ONLY/identity checks on every ORM transaction. |
| app/core/db.py | Refuse the legacy unguarded pool while observing health. |
| app/main.py | Install the gate before CORS/routes and skip business callback registration in this mode. |
| .env.example | Document the default-off mode without credentials. |
| tests/test_database_target_selection.py | Update offline Settings doubles and their explicit module dependencies. |
| tests/test_health_only.py | Real app HTTP refusals, configuration and fresh-process wiring/Redis absence. |
| tests/test_health_only_postgres.py | Real PostgreSQL write refusals, sessions, reconnects and application startup. |
| tests/test_health_only_local_safety.py | Local destination, identity and network admission regressions. |
| test_support/health_only_safety.py | Reuse the existing socket policy/result accounting with synthetic test settings. |
| test_support/local_postgres.py | Strict owned-loopback database admission; compatibility profile only. |
| test_support/__init__.py | Test-support package. |
| scripts/run_health_only_tests.py | Network-denied, explicitly selected offline tests without shared conftest. |
| scripts/run_health_only_postgres_tests.py | Own a new local instance and run only the 14 Health-Only proofs. |
| alembic_local_test/env.py | Test-only pinned connection at exactly dce91870b4a2; no new revision. |
| compose.postgres-tests.yml | Optional isolated local Docker backend; native execution was verified. |
| docs/README.md | Index entry. |
| This document | Validation and the proposed coordinated operations. |

The local test launcher reuses the existing three test-history revisions already
in the base. Its compatibility-only environment admits no arbitrary revision or
remote target. Neither Render's build command nor its uvicorn start command
invokes that launcher or Alembic. Runtime dependencies are already declared by
the unchanged requirements.txt; none was added or upgraded.

## Behavior and observed validation

HEALTH_ONLY_MODE defaults to false. When true, only **GET /** and **GET /health**
pass the outer ASGI gate. Other HTTP methods, docs/OpenAPI, webhook, business
reads/writes and unknown paths receive 503 before inner middleware/dependencies
or body processing. WebSockets are denied too. Business routes and authorization
retain their original behavior with the mode disabled.

The mode refuses primary/production targets, missing/unsafe development identity,
Redis values other than an explicit empty string, DEBUG/DB_ECHO or OIDC diagnostic
flags enabled. The preserved production URL must match the protected endpoint;
the development URL must identify a different endpoint and neondb_test. Verified
TLS is supplied centrally; routing query options are refused in this profile.

The application-owned SQLAlchemy engine captures an immutable policy. Every
transaction forces READ ONLY, checks its mode and attests the actual Neon
database/project/branch/endpoint before application SQL. Autocommit is refused.
The legacy pool is unavailable. This is an application observation boundary,
not a replacement for production database privilege hardening or K11.

Standalone observed results:

- **138 offline tests and 76 sub-tests passed**, zero failures, skips, warnings
  or detected network attempts. Shared conftest was not loaded. This deliberately
  scoped selection differs from the larger feature-branch campaigns.
- **14 tests passed on native PostgreSQL 18.3**, zero failures/skips/warnings,
  at baseline dce91870b4a2 with 47 tables. INSERT/UPDATE/DELETE, DDL, TRUNCATE,
  GRANT, sequences, sessions/savepoints, reconnect, READ WRITE and autocommit
  refusal were exercised. Synthetic probes and their sequences were removed;
  the original application object was restored and the owned server stopped.
- **Fresh read-only development observation passed** on project
  shiny-lab-60817779, branch br-lively-truth-asga1dtk, endpoint
  ep-quiet-rain-assrs0gv, database neondb_test. Actual revision dce91870b4a2 and
  47 public tables; real init_db/lifespan startup and shutdown succeeded. Root
  and health returned 200; webhook and docs returned 503. Redis client absent;
  no other network destination attempted. No mutation or migration was sent.

Neon's observed default_transaction_read_only was **off**, while the actual
transaction_read_only was **on**. The per-transaction listener is the mandatory
protection; setting an asyncpg startup default alone is not the guarantee. Local
proofs explicitly cover a session default of off. An initial observation probe
incorrectly expected the default itself to be on; its verification was corrected
to assess the actual guarded transaction. No application admission rule was
changed or bypassed. Sandbox-denied launch/read attempts preceded authorized
executions; only the successful observations above establish validation.

The ORM models and all migration files match the deployed base. The successful
live startup confirms compatibility with the existing development schema; no
schema repair is required for this mode. No production SQL connection occurred.
The local environment used Python 3.14.4 and existing installed packages; this is
not a completed Render build/deployment. Docker execution was not repeated.

From this checkout, using its intended Python environment:

```powershell
python scripts/run_health_only_tests.py
python scripts/run_health_only_postgres_tests.py --backend native
```

The PostgreSQL command creates/migrates only its new disposable local database,
not Neon. It uses exactly 127.0.0.1:55432 and refuses an occupied port. Local
evidence, source exports and raw logs remain under ignored artifacts/. They are
not included in the commit or publication. Black passes on all touched/new
Python files; scoped Ruff checks pass. Historical lint in untouched legacy code
is outside this correction.

## Publication proposal: separate explicit approval required

Publish **only this dedicated branch**, with no force push and no merge to main:

```powershell
git push --set-upstream origin fix/render-health-only
git ls-remote origin refs/heads/fix/render-health-only
```

Compare the remote branch SHA with the delivered local SHA before any Render
operation. The commit message includes `[skip render]` as an additional
auto-deploy precaution, not as a substitute for checking service configuration.
No publication command has been run. Do not open or merge a feature-branch PR
implicitly as part of this procedure.

## Coordinated Render proposal: not performed

Service: **moulai-api / srv-db7lblc9v7es73cfgfag**, linked repository
youcefnesrine60-cmyk/moulai-platform. Reconfirm those values, linked main branch,
current deployment and the absence of a running/queued deployment before changes.

1. After separate authorization, privately capture the effective environment,
   original absent keys, current SHA and auto-deploy setting. Set **Auto-Deploy:
   Off before preparing variables**. Coordinate against other manual/API/hook
   deployments; automatic-branch protection does not stop an operator action.
2. Apply only the service-specific values below using **Save only**. Do not edit
   a shared environment group or import the working .env. Neither Save and deploy
   nor Save, rebuild, and deploy is appropriate: they could activate the old
   unguarded source with development settings.
3. Open **Manual Deploy > Deploy a specific commit**, paste the complete
   published correction SHA, verify it, then **Deploy Commit** only after
   deployment authorization. Render documents selecting a commit from the linked
   repository instead of the linked branch's latest commit. No branch switch or
   merge of K8/K9/K10 into main is needed. The dashboard's specific-commit method
   disables automatic deploys; verify they remain Off afterward.
4. Verify the actual deployed SHA and Health-Only startup, GET / and /health at
   200, and the gate's 503 on docs, webhook and a non-GET health request. Perform
   no real bot message, AI generation or business write. Leave Auto-Deploy Off.

[Render specific-commit and auto-deploy behavior](https://render.com/docs/deploys#deploying-a-specific-commit),
[Render environment save behavior](https://render.com/docs/configure-environment-variables).

| Variable | Exact proposed action, pending authorization |
| --- | --- |
| HEALTH_ONLY_MODE | Add/set true. |
| APP_ENV | Keep development. |
| DATABASE_TARGET | Change primary to development only for the corrected deployment. |
| DATABASE_URL | Preserve the production/neondb reference unchanged; it is not used for observation. |
| TEST_DATABASE_URL | Already present: privately verify the approved development/neondb_test asyncpg URL, default port, no query options. Do not publish it. |
| TEST_DATABASE_PROJECT_ID | Add shiny-lab-60817779. |
| TEST_DATABASE_BRANCH_ID | Add br-lively-truth-asga1dtk. |
| TEST_DATABASE_ENDPOINT_ID | Already present: require ep-quiet-rain-assrs0gv. |
| PROTECTED_DATABASE_BRANCH_ID | Add br-plain-firefly-as17il6w. |
| PROTECTED_DATABASE_ENDPOINT_ID | Add ep-billowing-term-as9aufue. |
| DEBUG / DB_ECHO | Keep false. |
| OIDC_DIAGNOSTICS_ENABLED / OIDC_ALLOW_LOCAL_HTTP | Set/keep false; no diagnostic route or authentication activation is added. |
| REDIS_URL | Explicit empty service override; do not delete the key and inherit a value. |
| Telegram settings, AI credentials, SECRET_KEY, manual billing, sync URLs | Preserve privately unchanged. No integration registration or resource operation. |

The old commit 7a66763 ignores HEALTH_ONLY_MODE. Never allow it to consume pending
development settings through an intervening deployment. A restart uses the
deployed environment; it does not apply Save-only settings. Do not select latest
commit or a feature-branch SHA when the approved correction SHA is intended.

## Rollback and remaining limits

If changes were saved only, restore the private environment snapshot and remove
only keys originally absent. If the corrected service is active, keep Health-Only
true while its public URL targets development. Never disable just that flag.
Any authorized rollback to 7a66763 must restore the earlier complete environment,
particularly DATABASE_TARGET=primary, at the coordinated deployment boundary.
That returns to the known fail-closed production-schema refusal, not service
availability. Alternatively retain the corrected SHA and repair its configuration
under authorization. Keep automatic deploys Off during review.

No database restore/downgrade/reset, Telegram change or Redis cleanup accompanies
either path. Telegram bot correspondence and Redis production sharing remain
unverified; Health-Only excludes their business usage rather than declaring them
ready. Business activation, K11 and deployment remain separate decisions.

No push, merge, Render change, deployment, Neon migration or production access
occurred during this preparation. Development SQL was exclusively read-only;
local synthetic writes were confined to the owned disposable PostgreSQL instance.
