# Reproducible local PostgreSQL tests

Date: **2026-10-19**. Observed result: **110 executed, 110 passed, zero failures,
zero setup errors and zero skips** on native PostgreSQL **18.3**. Test duration:
131.22 seconds. The dedicated server was stopped after execution.

**Accepted by the user on 2026-10-20. Status: RESOLVED — the 110 formerly skipped
tests have passed in the isolated local campaign.** No rerun accompanies this
acceptance. The three environments and their respective protections remain as
defined in the [development guide](billing-development-verification.md#approved-environment-organization--2026-10-20).
Neon retains its official development/validation role; this resettable campaign
must not be repeated there without an identified technical need.

## Original skips and actual prerequisites

The fresh `pytest -m database -rs` inventory recorded exactly 110 skips and 2,698
deselected offline cases. Every skipped case consumed the shared database-engine
fixture, directly or transitively. Each reported the disabled database-mode
reason; inspection found no additional conditional skip in these test files.
The exact node IDs, original reasons and subsequent outcomes are retained in
[the case inventory](../artifacts/postgres-local-tests/case-inventory.json).

| Test group | Cases | Required behavior |
| --- | --- | --- |
| Restaurant APIs | 52 | Persisted CRUD, constraints, authorization and per-test data reset. |
| Administrative permission refresh | 3 | Independent commits and authorization re-reading. |
| Manual payment review | 15 | Receipt uniqueness, real settlement rollback and concurrent review. |
| Order transactions | 18 | Real commits/rollback, separate readers and atomic order/payment changes. |
| Payment/subscription transactions | 16 | Idempotency, concurrent settlement and atomic activation. |
| Persisted pricing | 1 | Database-backed discount rules. |
| RBAC and branch features | 5 | Stored permissions, subscription limits and usage counters. |

Some CRUD assertions are portable SQLAlchemy contracts rather than intrinsically
PostgreSQL-specific SQL. They still require a real, resettable relational fixture
in this suite. PostgreSQL is used for all 110 to verify the actual supported
backend, including real transaction and concurrency behavior. None of these
cases is made successful by replacing its storage with a mock.

## Run locally

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/run_local_postgres_tests.py --backend native
```

The observed Windows run used `C:\Program Files\PostgreSQL\18\bin`. Supply
`--postgres-bin` for another installed binary directory. The launcher initializes
a new cluster; it neither connects to nor modifies an existing PostgreSQL service.

For a running Docker engine:

```powershell
.\.venv\Scripts\python.exe scripts/run_local_postgres_tests.py --backend docker
```

[The dedicated Compose file](../compose.postgres-tests.yml) uses `postgres:18.3`,
a loopback-only published port and disposable tmpfs data. The launcher owns a
unique Compose project and shuts down only that project. Docker execution was
not verified here because its engine was unavailable. The default `auto` mode
prefers a running Docker engine, otherwise installed native binaries.

## Isolation and migrations

- Exact destination: `127.0.0.1:55432`, database/role `moulai_pytest`, asyncpg.
  DNS hosts, other ports, other databases/users and URL query overrides fail.
  An occupied port stops provisioning; existing listeners are never terminated.
- Fresh random credentials and instance marker are supplied only to the local
  process. No connection URL or password is included in reports or command-line
  arguments. The temporary bootstrap password file is removed after initdb.
- The test role is not a superuser and cannot create roles/databases. Before
  migration and cleanup, SELECT-only attestation checks its role, database owner,
  server port and the database's unique instance marker.
- The socket audit policy allows only the exact loopback test port and Python's
  asyncio socket pair. Other local services, Redis, identity providers and Neon
  connections remain denied. This is a Python audit boundary, not an OS sandbox.
- The independent local Alembic environment applies the existing test revisions
  `ae6a266365fb -> b7d33e89f4a1 -> dce91870b4a2` to the empty local database.
  The default `legacy` profile uses an admitted pinned connection. No stamp,
  metadata create_all or change to either remote Alembic environment is used.
- These legacy integration tests require the pre-E1 compatibility schema:
  **47 public tables**. E1's retained tenant history is outside this resettable
  profile and remains covered by the separately accepted G2 evidence.
- Cleanup checks the exact legacy table allowlist, then truncates those public
  tables and resets their sequences without CASCADE. Revision/identity/catalog
  mismatch stops cleanup. Test-created commits remain inside this disposable DB.
- Native clusters and logs stay under ignored `artifacts/postgres-local-tests/`
  run directories; each later run creates a fresh cluster. The server is stopped
  automatically. Retained native data directories are diagnostic artifacts, not
  active development targets. Docker tmpfs data disappears with its owned project.

`DATABASE_URL`, `TEST_DATABASE_URL`, `.env`, the Neon validation module and the
existing remote migration environments are unchanged by this implementation.
Local settings use the independent `LOCAL_POSTGRES_TEST_*` namespace and do not
read `.env`. Process DEBUG/DB_ECHO and both OIDC diagnostic flags remain false.
No production/development Neon SQL, deployment, remote migration or push occurred.

Ordinary `python -m pytest` intentionally keeps database tests opt-in. Use the
launcher above to execute this PostgreSQL selection with zero skips. A bare
`--local-postgres-tests` without its local configuration fails once before
collection; it cannot fall back to Neon.

## Health-Only cases in the default local campaign

The default legacy campaign now includes the 14 Health-Only PostgreSQL cases,
for **124 cases** including the original 110. On 2026-10-20, the combined native
PostgreSQL 18.3 run passed **124/124**, without failures, setup errors, skips or
warnings; the owned server was stopped. See the
[Health-Only correction](render-health-only-validation.md#combined-postgresql-fixture-isolation-correction).

The Health-Only fixture removes only its own newly created probe table and owned
sequence after local re-attestation. It also restores the original application
object after lifespan testing. The strict shared public-table cleanup allowlist
remains unchanged. The standalone selection is still available with
`--suite health-only`; the same cases are also included in the default command.

## K10 authorization profile — local E1

The independent `k10` profile creates another fresh local instance and applies
the same test history through `e1b92b200001`. It verifies **56 public tables**,
including the nine tenant tables, five expansions, 28 triggers, three roles and
49 permission rows. It runs only the K10 PostgreSQL tests:

```powershell
.\.venv\Scripts\python.exe scripts/run_local_postgres_tests.py --backend native --profile k10
```

Observed on 2026-10-20: **26 passed, zero failures, skips or warnings** on
PostgreSQL 18.3. See the [K10 delivery](keycloak-k10-validation.md).
The default command still selects the original 110-test compatibility profile;
those accepted tests were not repeated for K10.

K10 uses explicit synthetic identity links, real committed E1 records and
independent SQLAlchemy sessions. It never invokes the legacy truncate fixtures
or disables E1 retention/lifecycle triggers. Each case uses independent explicit
IDs; retained records remain in the disposable instance until it is stopped.
Both profiles retain the same exact local destination and instance checks.
K10 tests are intentionally skipped outside their local E1 profile, including
when the remote database-test option is supplied. The offline runner excludes
this file. Neither profile reads a Neon URL or permits remote execution.

## Observed validation and retained evidence

- [Successful PostgreSQL run](../artifacts/postgres-local-tests/5f17a39659264a61be7f3e91c5fbf46a/validation.json),
  [JUnit cases](../artifacts/postgres-local-tests/5f17a39659264a61be7f3e91c5fbf46a/postgres-results.xml)
  and [execution log](../artifacts/postgres-local-tests/5f17a39659264a61be7f3e91c5fbf46a/postgres-tests.log).
- [Original Pytest skip reasons](../artifacts/postgres-local-tests/skipped.log).
- [Safety regression results](../artifacts/postgres-local-tests/safety-results.xml):
  **53 tests and 59 subtests passed**, with warnings treated as errors. These
  include existing Neon guard regressions and independent local refusal cases.
- [Complete Python sources](../artifacts/postgres-local-tests/complete-python-sources.md).

Startup attempts are preserved separately: restricted Windows process startup,
an inherited-pipe wait in pg_ctl invocation, and strict environment-port parsing
were corrected before the successful run. Earlier failed results are not
overwritten. The 110 cases needed no application business-code changes.
