# API testing and coverage

This guide describes the repeatable local API verification workflow. Test
results belong to the source state and execution scope recorded in each report.
The project remains under development.

## Local PostgreSQL execution - 2026-10-19

The user accepted this campaign on **2026-10-20**. The 110 skipped-tests issue is
**RESOLVED**. Preserve its evidence and the approved
[three-environment separation](billing-development-verification.md#approved-environment-organization--2026-10-20);
do not repeat this selection on Neon without an identified technical need.

The previously skipped database selection now has a reproducible isolated local
launcher: **110 executed, 110 passed, zero failures and zero skips** on PostgreSQL
18.3. See [local PostgreSQL tests](local-postgres-tests.md) for the exact inventory,
original Pytest reasons, independent allowlist, applied migrations and command.
Existing Neon URLs and protections are unchanged. Ordinary offline pytest still
keeps database execution opt-in; use the local launcher for these 110 cases.

## Windows temporary-directory correction - 2026-10-19

The subsequent operator run recorded **2,694 passed, 110 skipped and two setup
errors**. Both errors occurred in `test_pytest_database_boundary.py`: Windows
denied access to pytest's shared temporary root under `%LOCALAPPDATA%\Temp`.
They were filesystem fixture failures, not PostgreSQL or application failures.

The two child-pytest cases now use a dedicated `boundary_directory` fixture.
It creates unique owned directories under
`artifacts/test-runner-fix/temporary/`, checks their workspace containment and
cleans up only each fixture's own directory. It does not change Windows ACLs,
delete system temporary directories or depend on shared conftest loading.
Two new regressions exercise denied system-temp lookup and independent cleanup
of simultaneous fixture directories.

Observed targeted verification: **16 passed**, zero warnings, with warnings
treated as errors. Both formerly failing cases executed successfully.
Black and Ruff pass. The full application suite was not repeated for this
test-only change; the operator's remaining 2,694 passing cases are not presented
as a new full-suite execution.

The dedicated offline coverage runner also recorded 16 passing cases, pytest
exit code 0 and no denied network events. Its aggregate exit code was 1 because
this infrastructure-only selection covers no API statements: even its diagnostic
minimum of zero requires API coverage strictly above zero. This is not a failed
test, and that targeted coverage result does not replace the previous complete
coverage measurement. The original runner result is retained.

**Skipped means not executed.** The 110 cases depend on the shared PostgreSQL
fixtures and are skipped when `--run-database-tests` is absent. They are not
counted as successes or failures. The existing inventory comprises 52 restaurant
API cases and 58 administration, billing, order and database-integration cases.
This correction neither enables them nor demonstrates their current outcome.

Local ignored evidence:

- [Targeted JUnit results](../artifacts/test-runner-fix/windows-temp-results.xml).
- [Offline diagnostic results](../artifacts/api-test-review/windows-temp-boundary-results.json)
  and [execution capture](../artifacts/test-runner-fix/windows-temp-offline.log).
- [Complete updated Python source](../artifacts/test-runner-fix/windows-temp-complete-python-sources.md).

Only the test module and this guide changed in this correction. No application
code, shared PostgreSQL guard, `.env`, database, migration or Neon resource was
modified. Earlier evidence remains retained.

## Shared pytest setup correction - 2026-10-19

A reported general pytest run ended with **2,792 setup errors** carrying the same
schema-head exception. The session-wide autouse fixture checked Neon even for
unit tests and prevented their test bodies from running. Adding E1 to the test
history advanced its repository head to `e1b92b200001`; E1 acceptance on isolated
W did not authorize applying it to the working development database. The failed
run is not evidence of 2,792 independent application failures. Earlier passing
offline and W-specific results retain their recorded execution boundaries.

Shared fixtures now create their PostgreSQL engine lazily. Ordinary pytest
collection identifies transitive live-fixture consumers and skips them unless
`--run-database-tests` is explicitly supplied. It leaves private SQLite fixtures,
mocked HTTP clients and other unit tests executable. The default path reuses the
existing Python socket audit guard and disables external Redis initialization
in its own process; it does not edit `.env`.

The live path retains the existing endpoint/branch validators, verified TLS,
server identity attestation and exact schema-head requirement. Its schema probe
is read-only. A mismatch refuses cleanup, without suggesting an automatic E1
upgrade. Cleanup is an explicit dependency of the live session/client fixtures;
unit tests cannot trigger it just by using a local fixture named `client`.
The option enables destructive fixtures; it is not migration authorization.

For the ordinary local run:

```powershell
$env:DEBUG = 'false'
$env:DB_ECHO = 'false'
.\.venv\Scripts\python.exe -m pytest
```

Keep both OIDC diagnostic flags false. Do not add `--run-database-tests` without
an approved target/dataset and the applicable database-operation authorization.
Neither production nor development was migrated to correct this setup defect.

Observed after correction: **2,696 passed, 110 skipped, zero failures and zero
setup errors**, in 252.38 seconds, with pytest exit code 0 and no warnings.
All 2,806 collected parent cases are accounted for; the 128 additional unittest
subtests must not inflate that parent total. The 110 skipped cases require live
PostgreSQL fixtures and were not revalidated. The **14 new boundary regressions**
passed separately and are included in the general result, not added to it.
Black and Ruff pass for both changed Python files.

Coverage from the saved run is **59.13% across all 395 application Python files**
and **81.76% across all 57 API Python files**, with no source exclusions. The
ordinary coverage plugin initially omitted 16 unexecuted source files; the final
report explicitly includes the complete source inventory and counts their
uncovered statements. This report regeneration did not rerun any tests.

Local ignored evidence:

- [Validation summary](../artifacts/test-runner-fix/validation.json),
  [JUnit results](../artifacts/test-runner-fix/default-results.xml) and
  [execution log](../artifacts/test-runner-fix/default.log).
- [Complete-source coverage](../artifacts/test-runner-fix/all-app-coverage.json).
- [Complete copyable Python sources](../artifacts/test-runner-fix/complete-python-sources.md)
  and [source hashes](../artifacts/test-runner-fix/source-manifest.json).

Only shared pytest configuration, its new regression tests and the relevant
documentation changed. Application code, migrations, `.env`, OIDC settings,
Neon resources and accepted G2 evidence remain unchanged.

## K8 OIDC integration - 2026-10-18

The accepted `k8-verified` offline execution passed **2,319 collected cases**
and **128 separate subtests**, with zero warnings and warnings treated as errors.
Coverage is **57.77% for all 385 app files** and **81.64% for all 56 API files**,
without source exclusions. A separate targeted selection passed 142 K8 and
existing authentication cases; those overlap with the complete selection.

The actual ASGI application also returned the expected 200/401/403 diagnostic
responses using real RSA signatures and simulated JWKS. The local Keycloak
discovery/JWKS endpoints were read successfully; a fresh real-user token replay
was completed in the subsequent [real-user K8 check](keycloak-k8-final-e2e.md).
K8 did not start a live PostgreSQL workflow or the main
application lifespan; the general offline suite retains its private SQLite tests.

See [K8 validation](keycloak-k8-validation.md) and the
[K8 evidence index](../artifacts/keycloak-k8/INDEX.md) for the source inventory,
configuration, impact review and operational boundary. The earlier reports
below retain their original source snapshots and scopes.

## Integration regression follow-up - 2026-10-17

The seven failures in the reported PostgreSQL execution are corrected. The
two affected integration modules now pass **10 tests**, including new anonymous
and foreign-owner category cases. This is a targeted integration result, not a
rerun of the entire connected PostgreSQL suite.

Before writes, the read-only preflight verified `neondb_test`, endpoint
`ep-quiet-rain-assrs0gv`, development branch `br-lively-truth-asga1dtk`, project
`shiny-lab-60817779`, verified TLS, and test revision `dce91870b4a2`. The shared
fixtures repeated their identity/schema checks before cleaning test tables.
No migration, production write, real identity binding, or deployment occurred.

Category business tests now explicitly provide their seeded owner's principal;
anonymous requests remain unauthorized and foreign resources remain hidden.
Owner binding performs no synchronous SQL from an async service constructor.
It evicts clean cached tenant identities and rejects a first binding with
pending changes. Filtered ORM counts and primary-key reloads retain their
owner predicates while raw protected Core projections remain forbidden.

The complete offline selection then passed **2,248 collected tests** and
**128 separate unittest subtests**, with zero Python warnings, failures, or
skips and warnings treated as errors. The 69 owner-scope cases are included
in that total; they must not be added again. The offline runner loaded no
shared integration fixtures and recorded zero denied network events.

| Scope | Executed statements | All statements | Line coverage |
| --- | ---: | ---: | ---: |
| Entire application (`app/`) | 12,377 | 21,484 | **57.61%** |
| API (`app/api/`) | 3,643 | 4,479 | **81.34%** |

All 382 application files and 55 API files remain included, without source
exclusions. Application sources stayed unchanged during measurement. The full
offline run used isolated Python 3.14.4 with all 43 exact requirements,
installed offline from 65 hash-verified cached wheels. The PostgreSQL selection
used the existing `.venv` that reproduced the reported failures; its 11 pin
differences are recorded separately. Neither `.venv` nor `.env` was modified.

Current local evidence:

- [Offline results](../artifacts/api-test-review/integration-fix-verified-results.json)
  and [coverage HTML](../artifacts/api-test-review/integration-fix-verified-html/index.html).
- [PostgreSQL results](../artifacts/api-test-review/integration-fix-postgres-results.json)
  and [targeted execution log](../artifacts/test-logs/integration-fix-postgres-targeted.log).
- [Declared environment](../artifacts/api-test-review/integration-fix-environment.json)
  and [integration environment differences](../artifacts/api-test-review/integration-fix-postgres-environment.json).
- [Current source manifest](../artifacts/api-test-review/source-manifest.json),
  [complete copyable files](../artifacts/api-test-review/complete-python-sources.md),
  and [Python archive](../artifacts/api-test-review/moulai-reviewed-api-python.zip).

These tests verify the affected database workflows and local regressions.
They do not establish PostgreSQL concurrency behavior, real Keycloak readiness,
production migration approval, or deployed Render behavior.

## Initial authorization review - 2026-10-17

The complete offline suite passed **2,232 collected tests** and **128 separate
unittest subtests**, with **zero Python test warnings**, failures, or skips.
Warnings are treated as errors; the Starlette warning is fixed by replacing
both remaining TestClient regressions with HTTPX `ASGITransport`.

| Scope | Executed statements | All statements | Line coverage |
| --- | ---: | ---: | ---: |
| Entire application (`app/`) | 12,362 | 21,469 | **57.58%** |
| API (`app/api/`) | 3,643 | 4,479 | **81.34%** |

All 382 application files and 55 API files are included; there are no source
exclusions. Both unrounded percentages exceed 50%. The API percentage uses the
expanded source denominator after the authorization changes; it must not be
compared as a same-source before/after result with the initial review below.

Execution used isolated Windows Python 3.14.4 with all 43 declared dependency
versions, including Starlette 1.8.0. Installation used 65 hash-verified cached
wheels without internet access. No existing environment or `.env` file was
changed. The runner recorded zero denied network events and did not load the
shared database integration fixtures. Real database assertions used private
in-memory SQLite fixtures. No Neon or production migration was executed.

A separate 40-case HTTP transport/order selection also passed with warnings
as errors. It includes cases already present in the full suite; do not add
all 40 to the full-suite total. A read-only inventory of the actual application OpenAPI
found bearer-security metadata on all 268 published API operations and no
published metrics simulation route. This metadata check supplements the actual
HTTP rejection and relational isolation tests; it does not replace them.

Local evidence is under `artifacts/api-test-review/`:

- `authorization-verified-results.json`, `authorization-verified-coverage.json`,
  `authorization-verified-coverage.xml`, and `authorization-verified-html/index.html`.
- `authorization-environment.json`, `authorization-install-report.json`, and
  `authorization-wheel-manifest.json` and `authorization-openapi-inventory.json`.
- `authorization-source-quality.json`, `authorization-document-quality.json`,
  and `authorization-import-format.json`.
- `complete-python-sources.md`, `moulai-reviewed-api-python.zip`, and
  `source-manifest.json` contain the complete reviewed Python files.

The access policies and client changes are documented in
[API authorization](api-authorization.md),
[administrative sessions](admin-session-api.md), and
[agent state](agent-api-security.md). Actual Keycloak provisioning, production
permissions, PostgreSQL concurrency, deployment, and proxy configuration remain
separate operational work.

## Initial coverage review - 2026-10-16

The initial accepted run used an isolated Windows Python 3.14.4 environment matching
all 43 declarations in `requirements.txt`. Installation used 65 locally cached
wheels whose SHA-256 hashes matched the retained dependency-review inventory.
The existing `.venv`, root `venv`, and `.env` were preserved.

| Scope | Existing tests | Expanded suite |
| --- | ---: | ---: |
| Application line coverage | 41.96% | **53.60%** |
| API line coverage | 31.43% | **81.77%** |
| Collected tests passed | 554 | **1,600** |
| Unittest subtests passed | 128 | 128 |

Both selections ran against the same source hashes. The expanded suite adds
1,046 collected cases; the 128 subtests are reported separately and must not
be added to the collected-case count. All 381 application Python files and
55 API files remain in the report. Coverage includes 11,221 of 20,936 app
statements and 3,463 of 4,235 API statements. Acceptance uses the unrounded
percentages. No application source changed during either measured run.

Both historical runs recorded one existing `StarletteDeprecationWarning` concerning the
HTTPX backend of older TestClient regressions. It was retained without a
warning filter. The new HTTP contracts use ASGITransport. There were no test
failures, skips, denied Python network events, or shared integration fixtures.
These are offline contracts, not a live PostgreSQL integration result. The
subsequent authorization review replaced the two remaining TestClient uses
with HTTPX `ASGITransport`; no warning filter or extra client was added.

The accepted local evidence is under `artifacts/api-test-review/`:

- `requirements-final-results.json` and `requirements-baseline-results.json`.
- `requirements-final-html/index.html` and `requirements-final-coverage.json`.
- `requirements-environment.json` and `requirements-install-report.json`.
- `recovered-wheel-manifest.json` and `source-manifest.json`.
- `complete-python-sources.md` and `moulai-reviewed-api-python.zip`.

The temporary review environment and recovered wheel copies are removed after
verification; the reports, resolved package inventory, and hashes are retained.
The separate `final-*` reports record the existing local environment, whose
package differences are listed in `environment.json`. The accepted dependency
baseline is identified explicitly by the `requirements-*` report prefix.

## Run the offline suite

Open PowerShell in `D:\MoulAI` and use the project's Python environment:

```powershell
.\.venv\Scripts\python.exe scripts/run_offline_api_tests.py
```

The default command requires **both** application line coverage and API line
coverage to be **strictly greater than 50%**. An exact result of 50% fails this
acceptance threshold. A successful exit also requires successful Pytest results
and no denied network event recorded by the runner.
Warnings are treated as errors, including warnings emitted during collection.

Run the command from the reviewed checkout after installing its declared
dependencies. Keep the existing local `.env` configuration. The runner sets
`DEBUG=false` and an empty `REDIS_URL` in its own process, and leaves `.env`
unchanged. These process settings prevent import-time Redis initialization
from using the configured external endpoint.

The runner supports a report name and an explicit list of test files. Use a
distinct name to retain an earlier execution's evidence:

```powershell
.\.venv\Scripts\python.exe scripts/run_offline_api_tests.py --name review
```

`--minimum` changes the exclusive coverage threshold for a diagnostic run.
The default threshold remains the acceptance requirement for the full suite.
Explicit selections must be existing `test_*.py` files under `tests/`; directory
arguments, protected integration files, and restaurant integration paths are
rejected.

## HTTP verification boundaries

The new HTTP contracts mount the real FastAPI routers in small in-process
applications and send requests through HTTPX `ASGITransport`. They exercise
routing, parameter parsing, Pydantic request validation, response serialization,
HTTP status codes, and domain-error translation. Service and repository doubles
replace storage and external integrations at declared dependency boundaries.

Assertions check the observable response and the business call together.
Relevant cases also verify that a denied request reaches no business read or
write. Order-item tests execute the real ownership SELECT builders against a
recording session and inspect owner and resource parameters. Authentication
regressions use controlled identity inputs and exercise configured failure
paths without contacting Keycloak.

The suite combines the maintained offline regression files directly under
`tests/` with HTTP contracts under `tests/api/unit/`. These include transaction
contracts, identity checks, repository behavior, billing safeguards, and the
additional agent, administrator, catalog, user, owner, payment, registration,
order-item, order, manual billing, and standalone branch contracts. They
supplement the separate restaurant integration tests.

This workflow verifies local contracts. Live PostgreSQL behavior, deployed
startup, real identity-provider configuration, deployment, and Telegram webhook
registration require their own authorized verification procedures.

## Protect the database boundary

The shared `tests/conftest.py` contains opt-in integration fixtures that truncate
test tables. They are lazy and excluded from ordinary offline execution.
The dedicated coverage runner still passes `--noconftest` and clears the default Pytest
`addopts` before collection. Automatic third-party plugin loading is disabled;
the asyncio plugin is selected explicitly.

The runner excludes the known database integration files listed in
`INTEGRATION_FILES` in `scripts/run_offline_api_tests.py`.
Explicit selection also rejects these files. Source files exercised by the
integration suite stay in the coverage denominator.

Keep tests selected by this workflow independent of live database fixtures.
Small in-memory SQLite fixtures and recording SQLAlchemy sessions used by unit
tests remain local to their respective tests. They provide no evidence that a
Neon migration has been executed or that production data has been verified.

Any subsequent database integration work must follow the isolated-development
preflight and authorization boundaries in the
[operational runbook](billing-production-runbook.md) and
[development verification](billing-development-verification.md).

## Network protection and its scope

The runner installs a Python audit hook before importing application tests. It
rejects the monitored DNS and socket transmission events. The exception for
Python's local Windows asyncio socket pair is restricted to the standard
library implementation and loopback addresses. Event counters record
categories without storing destination addresses or credentials.

This mechanism protects Python socket operations observed by the audit hook.
Native extensions that open connections directly and independent child
processes require separate controls. The runner is not an operating-system
network sandbox. Storage and external-service mocks remain part of the safety
boundary, and new tests must preserve those boundaries.

The audit-hook regression uses an isolated child process that installs its own
hook and emits synthetic audit events. It does not attempt a real connection.

## Coverage accounting and acceptance

Coverage measures the complete `app/` tree with repository coverage
configuration disabled. Namespace-package reporting is enabled so that source
files without `__init__.py`, including unexecuted API routers, remain visible.

After execution, the runner compares the reported source paths with the exact
inventory of Python files under `app/`. A mismatch fails verification. Each
report includes source hashes and separate aggregates for:

- All application Python files under `app/`.
- All API Python files under `app/api/`.

Line coverage is the number of executed executable lines divided by the full
executable-line count in the respective tree. Imports and declarations count
according to Coverage.py's normal line semantics. Meaningful behavior is also
assessed through the HTTP and service assertions; a percentage alone does not
establish route correctness or authorization.

The results JSON records collected cases, outcomes, setup or teardown errors,
failed test identifiers, and Pytest's exit code. Unittest subtest outcomes have
their own counter and do not inflate the number of collected test cases.
Network-event counters and the coverage threshold participate in the final
`passed` result.

## Reports and local logs

The default report name is `final`. Generated files are stored under
`artifacts/api-test-review/`:

| File | Purpose |
| --- | --- |
| `final-results.json` | Test outcomes, scope, hashes, and acceptance result |
| `final-coverage.json` | Executed and missing lines for every source file |
| `final-coverage.xml` | Machine-readable coverage report |
| `final-html/index.html` | Browsable line-by-line coverage |
| `final.coverage` | Coverage.py measurement data |

Other report names replace the `final` prefix. Reusing a name replaces that
name's generated reports, so preserve useful historical executions with
distinct names.

Console captures belong in `artifacts/test-logs/`. To retain a local capture,
ensure the output directory exists and redirect the same command:

```powershell
New-Item -ItemType Directory -Force artifacts/test-logs | Out-Null
.\.venv\Scripts\python.exe scripts/run_offline_api_tests.py `
    *> artifacts/test-logs/api-final-tests.log
```

The [local artifact index](../artifacts/README.md) describes the output policy.
The entire `artifacts/` directory is excluded from Git and Docker. Generated
evidence is intended for local review and may be unavailable in a GitHub
checkout. Keep maintained test source, this guide, and any dated result summary
in the repository.

## Authorization remediation and deployment boundaries

The previously documented catalog, agent, standalone branch, and global user
registry gaps now have explicit verified-identity policies. Catalog, agent, and
branch services use immutable owner-scoped SQLAlchemy sessions. The global user
registry requires the existing administrative `admins.manage` permission.
The global restaurant administration aggregate requires `restaurants.manage`;
its simulation router is no longer registered in the application.
See [API authorization](api-authorization.md) for the boundary and limitations,
and the [catalog review](catalog-options-isolation-finding.md) for that finding.

Additional tests execute real scoped SQL and complete HTTP/service/repository
flows against disposable in-memory SQLite databases. They verify foreign-owner
denials, scoped aggregates, valid writes, complete-batch validation, parent
relationships, and scoped bulk mutations. SQLite adapters preserve actual ORM
events and stored rows, while avoiding a remote async driver. These cases do
not certify PostgreSQL concurrency or locking.

Session lookup credentials now use headers on static URLs. Removed credential
paths have no compatibility aliases, and retired credential query parameters
are rejected before operations. See the
[administrative session migration](admin-session-api.md). Clients must adopt
the new contract. A proxy can still log a retired URL sent by an obsolete
client, so deployed header/body capture and obsolete-client traffic retain
their operational review requirement.

Passing the offline suite does not configure Keycloak, bind real identities,
grant production permissions, authorize a migration, verify deployed proxy
configuration, or establish production release readiness. Those operations
remain governed by the existing runbook and independent authorization.

## K10 authorization — isolated HTTP and real local PostgreSQL

[The K10 delivery](keycloak-k10-validation.md) records 41 K9 regressions,
seven new offline HTTP cases, 85 launcher/offline-boundary checks and 26 actual
PostgreSQL E1 cases, all passing. These are targeted results, not a new global
coverage measurement or a repeat of the accepted 110-test legacy campaign.

JWT signatures use generated RS256 keys and mocked JWKS; identity, membership,
permissions, resource grants and transaction/concurrency behavior use real
PostgreSQL in the K10 local profile. The three routes exist only in a disposable
FastAPI application. No production business route or OIDC flag is changed.
The dedicated command and opt-in boundaries are in the
[local PostgreSQL guide](local-postgres-tests.md#k10-authorization-profile--local-e1).

## Defects verified and corrected

The new contracts first reproduced failures before their localized fixes:

- Agent search, status, type, user, and bulk routes, plus administrator
  statistics, were shadowed by dynamic identifier routes. Static routes now
  precede the conflicting dynamic routes.
- Conversation, payment-list, and registration-list status parameters masked
  HTTP status constants. Their public query contracts remain unchanged.
- Product-option creation now forwards the group identifier separately from
  the validated option payload for both single and bulk requests.
- Session creation and deactivation use the actual repository contracts.
  Bulk deactivation supports preserving a specified session and processes all
  matching active sessions without a paginated read limit.
- Session request timestamps normalize to the existing UTC database convention;
  expired historical sessions remain serializable in read responses.
- Invalid administrator-log filters return 422. Internal service validation
  failures retain their server-error boundary.
- Tested session log paths exclude credentials, prefixes, and SQL parameter
  exception text. Inherited creation has an explicit sensitive-error policy
  for the session repository; other repositories retain their existing policy.
- Catalog, agent, and standalone branch requests enforce owner scope in the
  HTTP, service, and SQLAlchemy session boundaries. Global registry and
  restaurant administration requests enforce their existing administrative
  permission codes.
- Real SQL checks exposed missing product-name lookup, nonexistent channel
  search columns, and an invalid conversation JSON cast; their repository
  implementations now use the actual mapped schema.
- Conversation status and message content type persist in existing JSON
  columns through validated mappings. See [agent state](agent-api-security.md)
  for the storage contract and historical defaults.
- Branch reactivation enforces feature access and capacity. Branch state and
  usage updates are atomic, with idempotent repeated transitions and verified
  rollback after injected usage failures.
