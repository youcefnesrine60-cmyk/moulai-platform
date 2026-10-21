# Render Health-Only: local correction and validation

Date: **2026-10-20**. Status: **prepared locally; not published or deployed**.
The opt-in mode is disabled by default. K9/K10 remain closed for their accepted
scope; this change neither activates their routes nor starts K11.

**Follow-up, 2026-10-21:** the operator reports successful GitHub publication
and Render deployment of the separate `fix/render-health-only` correction.
The statements below describe this report's original local preparation, not
the current deployed service. The feature-branch version and its combined-test
corrections are being retained separately; no branch merge or deployment is
part of the [final Git synchronization preparation](github-final-sync-preparation.md).

## Runtime behavior

`HEALTH_ONLY_MODE=true` admits exactly **GET /** and **GET /health**. The ASGI
gate is outside the existing CORS/router/dependency stack. All other HTTP
requests return **503**, including HEAD/OPTIONS, docs/OpenAPI, unknown paths,
business reads/writes and `/webhook`. Rejection does not read the body or call
the inner application. WebSocket handshakes are also denied: 503 when the server
supports the ASGI denial-response extension, otherwise close code 1008.

Startup retains the real schema inspection and database shutdown. Business
callback registration is skipped in this mode. Normal routing, callbacks,
business services, tenant permissions and platform RBAC retain their existing
behavior when the flag is false.

Central Settings reject Health-Only before engine construction unless APP_ENV
and DATABASE_TARGET are development, Redis is explicitly empty, DEBUG/DB_ECHO
and both OIDC diagnostic flags are false, and all existing database admission
checks pass. The preserved primary URL must identify the declared protected
Neon endpoint and database neondb; the test URL must identify the different,
approved endpoint and neondb_test. Routing query parameters and nonstandard
ports are refused in this narrowly scoped observation profile. No primary URL
fallback exists. Direct and pooler forms of the protected endpoint are excluded.

The ORM engine captures an immutable identity policy and uses verified TLS.
Every physical connection requests default_transaction_read_only=on. Its begin
listener additionally enforces READ ONLY, verifies its actual mode and calls the
existing immutable Neon identity verifier **before application SQL in every
transaction**, including sessions, pooled reuse and reconnects. Autocommit is
rejected. SQL parameter logging is hidden in this mode. The legacy Psycopg pool
is blocked before initialization, including when an existing pool is present.

The identity SELECT takes a snapshot before caller statements: changing that
transaction to READ WRITE is rejected by PostgreSQL. Changing a session default
does not remove the next transaction's guard. This protects application-owned
ORM connections; it does not revoke operator privileges, constrain unrelated
processes, or constitute K11 hardening. PostgreSQL READ ONLY is a logical
persistent-data protection, not a promise of zero internal disk activity.
[PostgreSQL transaction modes](https://www.postgresql.org/docs/current/sql-set-transaction.html),
[SQLAlchemy async events](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-events-with-the-asyncio-extension).

## Exact code scope

Prepared on `feature/keycloak-k10-complete`, based on
`565309e16d0c557f337d2520e5427ff174f36efe`. No commit, merge or push was made.
The deployed main commit 7a66763 does not contain this mode.

| File | Change |
| --- | --- |
| app/core/health_only.py | New profile admission, frozen transaction policy and outer ASGI gate. |
| app/core/config.py | Default-off flag and early profile validation. |
| app/core/database.py | Guarded engine configuration and transaction listener; normal mode preserved. |
| app/core/db.py | Block the unused legacy pool in Health-Only. |
| app/main.py | Install the outer gate and skip business callbacks only in Health-Only. |
| .env.example | Document the flag, false by default; no real values added. |
| tests/test_health_only.py | Offline configuration, real app HTTP admission and fresh-process wiring tests. |
| tests/test_health_only_postgres.py | Dedicated live local transaction and lifecycle proofs. |
| tests/test_database_target_selection.py | Keep the simulated default-off Settings contract current and explicitly load its isolated security dependencies. |
| scripts/run_local_postgres_tests.py | Add --suite health-only without changing default legacy/K10 selection. |
| scripts/run_offline_api_tests.py | Exclude the new live PostgreSQL file from automatic offline selection. |
| docs/render-development-configuration.md | Point to this replacement isolation proposal. |
| docs/README.md | Link this delivery. |
| This report | Results, settings, rollback and authorization boundary. |

The earlier Render startup diagnostic and preparation documents remain separate
local work. No model, migration, identity link, permission catalogue or K9/K10
service was changed. No dependency was added. Full copyable changed Python
sources are retained in the ignored local evidence directory.

## Targeted local verification

Offline reproduction, with no shared database conftest and a socket-denial guard:

```powershell
.venv\Scripts\python.exe scripts/run_offline_api_tests.py tests/test_database_target_selection.py tests/test_health_only.py tests/test_database_startup_schema.py tests/test_test_database_safety.py tests/test_development_startup_verifier.py tests/test_local_postgres_safety.py --name health-only-target-regression --minimum 0
```

The zero minimum only disables a whole-application coverage threshold for this
targeted selection; it does not disable network guards or test assertions.

Observed offline result: **139 passed, 0 failed, 0 skipped**, plus **59 passing
sub-tests**; zero warnings and zero detected network attempts. The shared
database conftest was not loaded. A fresh process with synthetic configuration
also verified real Settings-to-engine guard installation and the outer gate
without external I/O. Black passes on the changed/new Python files;
Ruff passes on the new module/tests and the two targeted runners. Historical
lint findings in the touched legacy application files are not a general cleanup
scope for this correction.

The subsequent user-supplied full-suite log exposed a gap in that selection:
the database-target test double lacked HEALTH_ONLY_MODE, and its isolated module
loader had not declared the new pure health-policy dependency. The repeated
AttributeErrors and secondary unittest assertion error share that fixture cause.
The correction adds the explicit false test default, checks the real Settings
default, and loads both pure security contracts inside each temporary package
graph. It adds no missing-field fallback to the application and weakens no guard.
The database-target suite also passes independently in a fresh process: **12
tests**, with no detected network attempts. The expanded command above includes
that previously omitted suite and passes: **151 tests and 76 sub-tests**, zero
failures, skips, warnings or detected network attempts; shared database conftest
not loaded. These are targeted results, not a newly executed full application
campaign. The accepted local PostgreSQL cases were not rerun for a fixture-only
change.

### Combined PostgreSQL fixture isolation correction

The user's default local-launcher run then selected 124 cases: the 110 legacy
cases plus the 14 Health-Only cases. It stopped with 55 setup errors because
the Health-Only fixture retained public.health_only_probe. The unchanged legacy
cleanup guard correctly refused that unexpected public table. These failures
shared one cleanup cause; they were not 55 independent business failures.

The fixture now creates a new probe without adopting any pre-existing object,
tracks successful creation, and removes only that owned probe after re-attesting
the local instance. Teardown verifies removal of its owned serial sequence too.
No CASCADE or table-allowlist expansion is used. Both Health-Only test helpers
also restore the original app.main module namespace and FastAPI app object, so
other suites retain their existing imports and dependency overrides.

Focused offline verification after this correction: **78 tests and 17 sub-tests
passed**, zero failures, skips, warnings or detected network attempts. The
combined default local PostgreSQL result is retained with its run evidence.
No application source or shared cleanup safeguard was changed by this fix.

Observed combined result: **124 passed, 0 setup errors, 0 failures, 0 skips and
0 warnings**, native PostgreSQL **18.3**, baseline **dce91870b4a2**, with no
detected forbidden network attempt. Run **9a33e99aa94b4993a62d992709ca873b** stopped
its owned server successfully. The 2,843 nonselected cases were deselected by
the database marker; they are not skipped database cases. This directly repeats
the user's failing default command on a new disposable local instance. Evidence:
`artifacts/postgres-local-tests/9a33e99aa94b4993a62d992709ca873b/validation.json`
and its console/JUnit reports; consolidated observations are retained locally
as `artifacts/render-health-only/fixture-cleanup-validation.json`.

Real local PostgreSQL reproduction, using the existing owned disposable server:

```powershell
.venv\Scripts\python.exe scripts/run_local_postgres_tests.py --backend native --suite health-only
```

Observed live result: **14 passed, 0 failed, 0 skipped, 0 warnings**, PostgreSQL
**18.3**, isolated legacy revision **dce91870b4a2**, 47 initial public tables.
Only the local launcher's required baseline migrations ran. Its unprivileged
setup created a synthetic probe; no remote migration or real business record was
used. Tests cover INSERT/UPDATE/DELETE, TRUNCATE, CREATE/ALTER/DROP, GRANT,
sequence advancement refusal, sessions/savepoints, commit/rollback, changed
session defaults, reconnect, READ WRITE and autocommit refusal, plus real
startup/schema validation and HTTP 200/503. The probe remained unchanged and the
owned server was stopped. Network-denied events: **none**.

The standalone local server cannot supply Neon postmaster identity settings.
Only that identity observation was replaced in these live tests by the existing
real local database/role/owner/instance-marker attestation. The production
transaction listener and PostgreSQL enforcement ran unchanged. Neon admission
and identity rejection retain offline regression coverage; no new Neon runtime
observation is claimed.

An initial sandboxed local server launch was refused; the approved execution
outside that restriction succeeded. Initial offline test-double assertions were
corrected before final verification. These attempts remain in ignored evidence.
The accepted K9/K10 and 110-test PostgreSQL campaigns were not repeated.

Local live evidence:
`artifacts/postgres-local-tests/168b1e54aa2040a98ebc28d91176158d/validation.json`
and its JUnit/console reports. The original offline evidence is under
`artifacts/api-test-review/health-only-final-*`; the fixture-correction evidence
is under `artifacts/api-test-review/health-only-target-regression-*` and
`artifacts/render-health-only/target-selection-standalone.*`. Delivery evidence and complete
Python sources are under `artifacts/render-health-only/`. These files stay local;
they must not be force-added to Git.

## Exact Render configuration proposal: not applied

The operator's existing presence inventory is retained. Verify effective values
privately, including service overrides and linked groups; do not export secrets.

| Variable | Current evidence | Authorized-deployment proposal, still pending |
| --- | --- | --- |
| HEALTH_ONLY_MODE | New setting; Render presence not established | Set true for the reviewed corrected build only. |
| APP_ENV | development | Keep development. |
| DATABASE_TARGET | primary | Change to development only with the corrected build. |
| DATABASE_URL | Production/neondb reference | Keep exactly unchanged; never connect in this mode. |
| TEST_DATABASE_URL | Present; Render destination not inspected | Verify development/neondb_test, asyncpg, default port and no query parameters. Supply privately; trusted TLS comes from the existing engine arguments. |
| TEST_DATABASE_PROJECT_ID | Absent | Add shiny-lab-60817779. |
| TEST_DATABASE_BRANCH_ID | Absent | Add br-lively-truth-asga1dtk. |
| TEST_DATABASE_ENDPOINT_ID | Present; value unconfirmed | Require ep-quiet-rain-assrs0gv. |
| PROTECTED_DATABASE_BRANCH_ID | Absent | Add br-plain-firefly-as17il6w. |
| PROTECTED_DATABASE_ENDPOINT_ID | Absent | Add ep-billowing-term-as9aufue. |
| DEBUG / DB_ECHO | Confirmed false | Keep false. |
| REDIS_URL | Effective instance/sharing unknown | Set an explicit empty service value; do not omit it and fall back to a group/default. |
| OIDC_DIAGNOSTICS_ENABLED / OIDC_ALLOW_LOCAL_HTTP | No activation approved | Ensure both false; no issuer/client/user changes. |
| Telegram token, webhook URL and webhook secret | Remote bot correspondence unverified | Preserve unchanged. The outer 503 gate prevents dispatch; no webhook registration/deletion. |
| AI credentials, SECRET_KEY, manual-payment configuration, sync URLs | No change authorized | Preserve privately. Do not blank mandatory credentials. |

Redis sharing and real Telegram bot correspondence remain unknown, as recorded
in the [preparation report](render-development-configuration.md). This mode makes
neither integration available to incoming business requests; it requires an
empty Redis value before imports can initialize that client. It does not prove
that those integrations are ready for later business activation.

## Approval, activation and rollback boundary

No operational action is authorized by this report. Required later approvals:

1. Review and authorize publication of the exact correction on a named branch;
   choose the resulting build SHA and the service's source/deployment path.
   Do not merge to main or deploy all pending work implicitly.
2. Authorize the exact service-specific variables above and the coordinated
   deployment of that reviewed SHA. Record the prior effective configuration
   privately, including absent keys, source SHA and automatic-deployment state.
   Prevent an intervening deployment of the old build while preparing settings.
   **Never activate development on 7a66763:** it ignores HEALTH_ONLY_MODE.
3. Render's Save only can prepare values without deploying, but they apply at
   the next deployment. Use it only within the approved coordination plan; do
   not leave an old-code automatic deployment able to consume pending values.
   [Render environment behavior](https://render.com/docs/configure-environment-variables).
4. After a separately approved deployment, verify the actual SHA/mode, successful
   guarded startup and GET / plus /health returning 200. Verify a blocked request
   receives the gate's 503 before declaring observation available. No write/API
   workflow, Telegram send or AI generation is needed.

If settings were saved but never deployed, restore the private snapshot using
Save only and remove only keys originally absent. If the corrected build is
already active, **keep Health-Only true while the public service targets
development**. Do not restore full business exposure by toggling that flag alone.
An authorized rollback to the earlier build must first restore the complete
earlier configuration, particularly DATABASE_TARGET=primary, at the coordinated
deployment boundary. That restores the known fail-closed schema refusal, not
service availability. A newer reviewed correction can instead retain Health-Only.
No database downgrade, restore, reset, webhook change or Redis cleanup is part of
either path.

No Render, Neon, Telegram, Redis resource, GitHub or local .env change occurred.
No production access, deployment or remote migration was performed. Publication,
configuration changes and deployment await separate explicit authorization.
