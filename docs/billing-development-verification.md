# MoulAI™ — Development Verification and Migration Rehearsal Report

Report date: 2026-10-15. The production migration remains deferred; renewed authorization is not being requested at this stage.

## Approved environment organization — 2026-10-20

The user confirmed the following permanent separation. This section records
the decision; the dated verification results below retain their original scope.

| Configuration / environment | Purpose | Required protection |
| --- | --- | --- |
| `DATABASE_URL` — production Neon | Production database connection. | Changes require explicit approval. Preserve production exclusions and identity checks. |
| `TEST_DATABASE_URL` — development Neon / `neondb_test` | Official development and controlled PostgreSQL validation environment. | Preserve verified project/branch/endpoint identity, TLS and revision checks. No uncontrolled truncation, reset or migration. |
| Isolated local PostgreSQL / `LOCAL_POSTGRES_TEST_*` | Automated tests requiring resets, committed transactions and independent sessions. | Use the dedicated launcher, exact loopback/database/role allowlist and instance attestation; never fall back to either Neon URL. |

The local PostgreSQL 18.3 campaign is **accepted: 110 executed, 110 passed,
zero failures and zero skips**. The issue of the 110 skipped tests is
**RESOLVED**. Results were observed on 2026-10-19 and accepted on 2026-10-20;
acceptance does not constitute another execution. Code and evidence are retained.

Use the [local PostgreSQL launcher](local-postgres-tests.md) for this resettable
selection. Do not repeat it on Neon without an identified technical need and
a reviewed operation scope. Neon remains the official development/validation
environment; the local test profile does not replace it or authorize remote DDL.
Keep DEBUG/DB_ECHO and both OIDC diagnostic flags false. This documentation update
changes no settings, databases or protection logic.

The approved delivery order is **K10 — Authorization MoulAI™ → Frontend →
Business integration → K11 — Production Security → Pilot**.
[K10 is now closed for its validated scope](keycloak-k10-validation.md);
Frontend is next. Existing business-route integration remains a separate step.

## Work Completed Locally

- The tools verified the working directory `D:\MoulAI` and connection target without displaying passwords or a DSN. During the first check on 2026-10-15, the test URL still used the old production endpoint, so execution stopped before connecting. This condition has been **resolved**: the user confirmed the development endpoint and configured the connection locally, after which the actual read-only verification documented below succeeded.
- A central guard was added to require `postgresql+asyncpg`, the `neondb_test` database, and a declared development endpoint distinct from the protected production endpoint. It also rejects connection redirection options. The guard is used by pytest, test Alembic operations, the table preparation tool, and the billing rehearsal.
- The two legacy test tools that derived the test URL from the primary URL and reset tables were removed. The reset option was also removed from the supported tool. No database was deleted, and no tables were reset.
- The migration not yet deployed to production, `c413b7918a20`, and its counterpart in the test history were updated to define `payments.review` only, without automatically assigning it to `admin` or `super_admin`, modifying administrator rows, or binding `auth_subject`. Previously assigned permissions and `*` are not automatically revoked; a wildcard retains the role's broad scope and must be considered when reviewing reviewer access later.
- A tool was completed to rehearse the actual production migration step against its staged predecessor schema in the test database, covering fresh/adoption/drift scenarios. It checks data, constraints, monetary references, and the absence of subscription activation or identity changes, then rolls back and compares public data, schema, and sequences with their prior state. Transactional `ALTER SEQUENCE ... RESTART` protects sequence state against the effects of `nextval`, which alone cannot be rolled back. All three scenarios completed successfully on the approved target; their evidence and scope are documented below.

## Actual Read-Only Verification — 2026-10-15

The actual verification connection succeeded with TLS certificate and hostname validation. The server identity and test target matched the values confirmed by the user:

| Item | Verified Value |
| --- | --- |
| Neon project | `shiny-lab-60817779` |
| Development branch | `br-lively-truth-asga1dtk` |
| Compute endpoint | `ep-quiet-rain-assrs0gv` |
| Actual connected database | `neondb_test` |
| Installed test-history revision | `dce91870b4a2` |
| Public tables | 47 tables |
| Actual PostgreSQL version | 18.6, with `server_version_num=180006` |

The identity guard does not rely on the database name or hostname alone. It requires matching `branch_id` and `project_id` values with a `postmaster` context. The actual server exposed `endpoint_id` with a `superuser` context; the guard accepts this identifier only in a `postmaster` or `superuser` context, with `source='configuration file'`, `setting=reset_val` matching the approved identifier, and `pending_restart=false`, in addition to TLS and hostname validation. Missing values, session or client sources, role/database settings, and other contexts are rejected. The initial guard required `postmaster` for all three identities and rejected the connection before any write. The condition was adjusted for the endpoint alone under these restrictions; a `superuser` context is not treated as evidence that the setting is immutable within a session.

This read did not change the schema, data, or Alembic revision. Its success alone does not establish migration success or the stability of the modified Render deployment.

## Test Evidence and Its Limits

Independent tests without a PostgreSQL connection:

| Test Area | Result |
| --- | --- |
| Endpoint and server identity guards, database name and driver, query overrides, and redaction of configuration errors | 10 passed |
| Migration contracts, table adoption, drift rejection, and absence of role grants or identity bindings | 13 passed |
| Protected operations and rehearsal guards before connection and before writing | 20 passed |
| Startup schema validation and transaction-begin guard | 21 passed |
| Central ORM target selection | 12 passed |
| Payment transaction boundaries and corrected call contracts | 13 passed |
| SQLite schema validation | 3 passed |
| Manual payment contracts | 21 passed |

The final total recorded for this 2026-10-15 verification round is **113 non-overlapping cases**: 76 independent unittest cases with `-W error`, and 37 pytest cases using `--noconftest --no-cov`, comprising 13 payment transaction boundary cases, 3 SQLite schema cases, and 21 manual payment contract cases. The earlier group of 13 is included in the 37 and is not added again. The 76 include the 12 target-selection tests and 21 schema-validation and transaction-begin guard tests; the earlier count of 16 expanded by five guard tests. All earlier totals, including 108, are superseded by this total for that verification round. The `-W error` setting is not attributed to the pytest group without a result demonstrating it. These are local tests; the actual PostgreSQL and application startup results are documented separately below. Ruff F, compilation, and dependency consistency checks also passed.

The results of 622 full-suite tests and 139 affected cases from the preceding round remain historical records. The two groups overlap, and the tools did not rerun them against the new development branch. These counts are not evidence of a current test run against the isolated branch.

## Evidence Provided by the Account Owner

The user confirmed the Render service `moulai-api` (`srv-db7lblc9v7es73cfgfag`), its `main` branch and service URL, and successful startup and root requests. The tools could not verify live HTTP access because of a ConnectError, including an attempt outside network isolation; this does not establish a service failure. The tools did not change the Render connection or deployment, change the Telegram Webhook, or push to GitHub, because Auto-Deploy could deploy against the old production connection.

The user confirmed the Neon project `shiny-lab-60817779` and the permanent development branch `br-lively-truth-asga1dtk` as the approved test target with `neondb_test`. The user reported successfully reading an isolated historical recovery branch from production at the recovery point 2026-10-14 14:00 GMT+1, matching 47 tables, revision a91, and admins/owners/payments/subscriptions counts of 1/1/0/0. This is practical recovery evidence within the reported scope; the session tools did not perform it, and it did not verify every row and relationship.

The reported History window was 6 hours, and the reported recovery-branch deletion time, `2026-10-15 14:26:08 GMT+1`, had passed when the final result was prepared. Its existence was not checked after that deadline, and neither its continued availability nor that of the previous day's recovery point is assumed. This branch is not used for development. Evidence of a recent, available recovery point and a suitable recovery plan is required when production is reconsidered.

## Final Migration Rehearsal Result — All Three Scenarios Passed

All three actual scenarios for the production migration step `a91e7c2b4d10` → `c413b7918a20` passed within rollback-only transactions on `neondb_test`. The [sanitized results file](../artifacts/billing-production-review/development-rehearsal-results.json) records connection identity, scope, and results without rows or secrets. Its recorded SHA-256 matches the bytes of the [rehearsal source](../scripts/billing_test_rehearsal.py): `c75433123ef48b053c01684355e04b9098bea2f61978a67ce33feb3bb2e5e949`.

| Scenario | Measured Result |
| --- | --- |
| fresh | Billing schema creation, enforcement of ten constraint checks, idempotent repetition, and measured rollback all passed. Preservation of existing evidence is not applicable to the fresh-creation scenario. |
| adoption | Existing tables were adopted while preserving payment evidence and data; enforcement of ten constraint checks and idempotent repetition passed. |
| drift | Schema drift was rejected before changes to the core billing fields. |

In fresh and adoption, the tested legacy rows, existing non-empty owner identities, and subscription states were preserved. No administrator identities were bound, and no role grants changed, including the custom non-financial grant. Administrator identity uniqueness metadata and the default value of the new payment currency field were verified. After every scenario, measured comparison confirmed that the rows in all public tables, column definitions, constraints and their validation status, indexes, sequence states, and Alembic revision matched their prior state. The permanent revision remained `dce91870b4a2` with 47 tables; all three scenarios recorded `permanent_database_changes=false` and `production_touched=false`. No reset, `TRUNCATE`, or pytest cleanup fixtures were used.

The rehearsal checks the rejection code for deletion of a payment linked to a receipt according to the server version: `23001` for a `RESTRICT` violation in PostgreSQL 18 instead of the previous `23503`, while verifying the `manual_payment_receipts_payment_id_fkey` constraint rather than accepting arbitrary errors. The official sources explain this behavior in [PostgreSQL 18](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/backend/utils/adt/ri_triggers.c#L2606), [PostgreSQL 17](https://github.com/postgres/postgres/blob/REL_17_STABLE/src/backend/utils/adt/ri_triggers.c), and the [error code table](https://www.postgresql.org/docs/18/errcodes-appendix.html). The measured rollback evidence applies to the completed scenarios recorded in the file; an earlier attempt that stopped before `before_snapshot` and before any DDL is not counted as additional rollback evidence.

This establishes successful migration rehearsal and rollback within the recorded scope. It does not establish archive recovery or PITR, the stability of the modified Render deployment, or completion of all eight prerequisites.

## Actual Local Startup — Passed on 2026-10-15

The file `app/api/payment_webhook.py` and the legacy file `stripe_webhook.py` do not exist on disk, and a search of app/tests/scripts found no imports of them. Their stale IDE tabs do not mean that the application imports them or that they should be restored. Restoring them would revive an obsolete, untrusted payment path.

The attached trace ends with `database schema needs migration`: a normal `app.main` startup was selecting the primary `DATABASE_URL` connected to the production schema at `a91e7c2b4d10`, while its migration was intentionally deferred. This is a startup rejection caused by an incomplete schema. It is not resolved by migrating production, calling `create_all`, or using `stamp`.

Central ORM target selection was added through `DATABASE_TARGET=primary|development`, and its twelve tests passed. The tools added `DATABASE_TARGET=development` locally to the Git-ignored `.env` and verified that neither `DATABASE_URL` nor `TEST_DATABASE_URL` changed. Selecting `APP_ENV=development` alone does not change the database target; the local selection setting does not change Render or OIDC configuration.

**Actual local application startup verification passed.** The [sanitized startup evidence](../artifacts/billing-production-review/development-startup-results.json) recorded `completed=true` at `2026-10-15T13:59:59.448656+00:00`. It used the real `init_db`, completed startup and shutdown lifespan handling, called the real `close_db` exactly once, and verified read-only mode through a session from the isolated verification factory. The `/` and `/health` routes returned status 200, and the health response matched the expected contract. The verification made no external HTTP calls, restored globals modified for verification, and recorded `production_touched=false`.

Through the pooled test connection, the measured values were `transaction_read_only=on` and `default_transaction_read_only=off`, with `read_only_begin_guard_installed=true`. The verification tool's engine guard enforces read-only mode at the start of every transaction, and checking the current mode remains mandatory; transaction mode is not inferred from the default value. An earlier check required both current and default modes to be enabled and rejected the connection before importing the application. Its observed values were not preserved, so no specific value is attributed to that attempt.

The four file hashes in the evidence matched the bytes of `scripts/verify_development_startup.py`, `app/main.py`, `app/core/database.py`, and `app/core/test_database.py`. This was a local ASGI run with a real lifespan and a read-only development connection. It did not verify or deploy the published Render service or establish live Telegram/Keycloak integration.

To run the application locally from PowerShell in `D:\MoulAI`, with the saved local selection `DATABASE_TARGET=development`:

```powershell
$env:DEBUG = 'false'
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Payment transaction handling was also corrected for `sync_transaction` when its value is `None`, and seven calls were aligned with the required keyword arguments. The group of 13 now included in the 37 cases above passed. This is evidence for transaction contracts and boundaries, not deployment or production migration.

## Remaining Work Before Report Completion and Development Deployment Acceptance

1. The user completed local development-target configuration, and the actual read passed the identity and TLS guards. Connection values remain private, and production remains outside the write scope. The guards must be checked again before any new attempt; `PROTECTED_DATABASE_ENDPOINT_ID` must not be bypassed.
2. All three migration scenarios and measured rollback completed, and schema validation and local application startup through development passed the read-only guard. These checks must be repeated after any relevant change. Do not use pytest cleanup fixtures that empty tables for this rehearsal, and do not permanently change the test history at dce.
3. Review Render settings, the live SHA, Auto-Deploy, and switching its connection to development before pushing `main` or accepting a new deployment. This switch has not been performed and cannot be inferred from `APP_ENV=development`.
4. Verification of the deployed Render version, configuration of actual Keycloak values, and live integration remain subsequent work within their approved scope. Administrative review remains closed when configuration or trusted identity is missing. No default administrator identity is created.
5. The [catalog options isolation finding](catalog-options-isolation-finding.md) remains open; billing results do not certify readiness of the rest of the platform.

## Rollback Plan

A DDL/DML failure within the transaction requires rollback and verification that the revision and data remain unchanged. The final run demonstrated preservation of state after all three scenarios, in addition to earlier attempts that captured snapshots. This is not an archive recovery or PITR rehearsal. Following a successful future migration, `alembic downgrade` must not be used as automatic recovery because it deletes payment evidence, audit records, and identity fields. A compatible forward fix or planned recovery to an isolated target with data comparison is preferred, followed by a separate cutover decision. A Render rollback does not restore the Neon database. Recovery over production remains prohibited, as do all changes to its schema and data.

Details and scope-restricted commands are provided in the [deployment and recovery runbook](billing-production-runbook.md).

## Complete Sources and Deliverables

The final package recorded for this 2026-10-15 verification round contained 207 reviewed Python files and 10 removed Python paths, with hashes in the [source manifest](../artifacts/billing-production-review/source-manifest.json) and [removed-files list](../artifacts/billing-production-review/removed-python-files.json). The [complete copyable sources](../artifacts/billing-production-review/complete-python-sources.md) and [Python archive](../artifacts/billing-production-review/moulai-reviewed-python.zip) are available. The manifest includes earlier cleanup changes; it does not establish that all legacy code conforms to the style rules or that isolation is complete across the rest of the platform. Removals are applied through the repository change; extracting the archive alone does not delete obsolete files from another checkout.
